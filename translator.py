#!/usr/bin/env python3
"""Módulo de traducción inteligente de artículos para Punto de Vista usando Gemini API."""
import os
import json
import re
import time
import urllib.request

DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG = {}
cfg_file = os.path.join(DIR, 'config.json')
if os.path.exists(cfg_file):
    try:
        with open(cfg_file, encoding='utf-8') as f:
            CONFIG = json.load(f)
    except Exception:
        pass

GEMINI_KEY = os.environ.get('GEMINI_KEY') or CONFIG.get('GEMINI_KEY')
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3.6-flash')
GEMINI_URL = f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_KEY}'

CACHE_FILE = os.path.join(DIR, 'translations_cache.json')
_CACHE = {}

def load_cache():
    global _CACHE
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                _CACHE = json.load(f)
        except Exception:
            _CACHE = {}
    return _CACHE

def save_cache():
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(_CACHE, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Error guardando caché de traducción: {e}")

def call_gemini(prompt, max_retries=3):
    if not GEMINI_KEY:
        return None
    body = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {
            'temperature': 0.2,
            'maxOutputTokens': 8192,
        }
    }
    data = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(GEMINI_URL, data=data, headers={'Content-Type': 'application/json'})
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                return result['candidates'][0]['content']['parts'][0]['text'].strip()
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
            else:
                print(f"⚠️ Error API traducción Gemini: {e}")
                return None

def translate_text(text, is_html=False):
    if not text or not text.strip():
        return text
    load_cache()
    h = str(hash(text))
    if h in _CACHE:
        return _CACHE[h]

    if is_html:
        prompt = (
            "Eres un traductor y editor literario especializado en fotografía y artes visuales.\n"
            "Traduce el siguiente contenido HTML al español de forma natural, culta y fluida.\n"
            "REGLAS OBLIGATORIAS:\n"
            "1. Conserva exactamente todas las etiquetas HTML (<img>, <a>, <figure>, <figcaption>, <p>, <div>, clases, etc.).\n"
            "2. No alteres las URLs de imágenes ni los enlaces href.\n"
            "3. Traduce los textos descriptivos, pies de foto y párrafos con máxima fidelidad y naturalidad editorial.\n"
            "4. Devuelve ÚNICAMENTE el HTML traducido, sin bloques de código ```html ni texto introductorio.\n\n"
            f"{text}"
        )
    else:
        prompt = (
            "Traduce el siguiente titular o resumen de fotografía al español de forma natural y atractiva.\n"
            "Devuelve ÚNICAMENTE la traducción, sin comillas ni explicaciones:\n\n"
            f"{text}"
        )

    res = call_gemini(prompt)
    if res:
        # Limpiar si devolvió markdown
        clean_res = re.sub(r'^```html\s*', '', res, flags=re.IGNORECASE)
        clean_res = re.sub(r'\s*```$', '', clean_res)
        _CACHE[h] = clean_res.strip()
        save_cache()
        return clean_res.strip()
    return text

def translate_article_entry(entry):
    """Traduce un objeto de artículo (title, excerpt, content) respetando el original."""
    if not entry:
        return entry
    
    # Guardar originales si no existen
    if 'title_original' not in entry:
        entry['title_original'] = entry.get('title', '')
    if 'excerpt_original' not in entry and entry.get('excerpt'):
        entry['excerpt_original'] = entry.get('excerpt', '')
    if 'content_original' not in entry and entry.get('content'):
        entry['content_original'] = entry.get('content', '')

    # Traducir título
    if entry.get('title'):
        entry['title'] = translate_text(entry['title'], is_html=False)
    
    # Traducir excerpt
    if entry.get('excerpt'):
        entry['excerpt'] = translate_text(entry['excerpt'], is_html=False)

    # Traducir content completo si existe
    if entry.get('content') and len(entry['content']) > 30:
        entry['content'] = translate_text(entry['content'], is_html=True)

    return entry

if __name__ == '__main__':
    t_test = "A look into the darkroom alchemy of large format monochrome film."
    print("Original:", t_test)
    print("Traducido:", translate_text(t_test))
