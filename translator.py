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
GEMINI_MODELS = [
    os.environ.get('GEMINI_MODEL'),
    'gemini-3.5-flash-lite',
    'gemini-3.6-flash',
]
GEMINI_MODELS = [m for m in GEMINI_MODELS if m]

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

def call_gemini(prompt, max_retries=2):
    if not GEMINI_KEY:
        return None
    body = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {
            'temperature': 0.1,
            'maxOutputTokens': 8192,
        }
    }
    data = json.dumps(body).encode('utf-8')

    for model_name in GEMINI_MODELS:
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_KEY}'
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    result = json.loads(resp.read().decode('utf-8'))
                    return result['candidates'][0]['content']['parts'][0]['text'].strip()
            except Exception as e:
                time.sleep(1 * (attempt + 1))
    print(f"⚠️ Error API traducción Gemini en todos los modelos de respaldo")
    return None

import hashlib

def _hash_key(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def translate_text(text, is_html=False):
    if not text or not str(text).strip():
        return text
    text_str = str(text).strip()
    load_cache()
    h = _hash_key(text_str)
    if h in _CACHE and _CACHE[h]:
        val = _CACHE[h]
        if not val.startswith("Aquí tienes") and not val.startswith("La traducción") and not "1." in val:
            return val

    if is_html:
        prompt = (
            "Eres un traductor y editor literario especializado en fotografía y artes visuales.\n"
            "Traduce el siguiente contenido HTML al español de forma natural, culta y fluida.\n"
            "REGLAS OBLIGATORIAS:\n"
            "1. Conserva exactamente todas las etiquetas HTML (<img>, <a>, <figure>, <figcaption>, <p>, <div>, <span>, <h2>, <h3>, <ul>, <li>, clases y atributos).\n"
            "2. No alteres ninguna URL de imágenes (src), enlaces (href) ni identificadores.\n"
            "3. Traduce todos los textos descriptivos, pies de foto, citas y párrafos con máxima fidelidad y naturalidad editorial al español.\n"
            "4. Devuelve ÚNICAMENTE el HTML traducido, sin bloques de código ```html ni texto introductorio.\n\n"
            f"{text_str[:12000]}"
        )
    else:
        prompt = (
            "Eres un editor fotográfico profesional. Traduce el siguiente titular o resumen al español de forma directa, elegante y natural.\n"
            "REGLAS CRÍTICAS:\n"
            "- Devuelve EXCLUSIVAMENTE el texto traducido.\n"
            "- No incluyas explicaciones, notas, alternativas ni comillas adicionales.\n\n"
            f"{text_str}"
        )

    res = call_gemini(prompt)
    if res:
        # Limpiar si devolvió markdown o comillas envolventes
        clean_res = re.sub(r'^```html\s*', '', res, flags=re.IGNORECASE)
        clean_res = re.sub(r'\s*```$', '', clean_res).strip()
        clean_res = re.sub(r'^["«\']|["»\']$', '', clean_res).strip()
        _CACHE[h] = clean_res
        save_cache()
        return clean_res
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
