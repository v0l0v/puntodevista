#!/usr/bin/env python3
"""
Módulo de traducción inteligente de artículos para Punto de Vista usando Gemini API.
Incorpora Circuit Breaker para protección contra rate-limits (HTTP 429) y degradación elegante.
"""
import os
import json
import re
import time
import hashlib
import requests
import logging

from config import get_gemini_key, get_gemini_model, ensure_warp_proxy
from data_paths import get_data_path

logger = logging.getLogger('pdv.translator')

GEMINI_KEY = get_gemini_key()
_PREFERRED_MODEL = get_gemini_model('gemini-3.5-flash-lite')

GEMINI_MODELS = [
    _PREFERRED_MODEL,
    'gemini-3.5-flash-lite',
    'gemini-flash-latest',
    'gemini-3.5-flash',
    'gemini-3.6-flash',
    'gemini-flash-lite-latest',
]
# Eliminar duplicados preservando el orden
GEMINI_MODELS = list(dict.fromkeys([m for m in GEMINI_MODELS if m]))

CACHE_FILE = get_data_path('translations_cache.json')
CIRCUIT_FILE = get_data_path('.gemini_circuit.json')
_CACHE = {}

# ─── Circuit Breaker ─────────────────────────────────────────────────────────
CIRCUIT_COOLDOWN_SECONDS = 300  # 5 minutos de pausa tras agotarse la cuota

def is_circuit_open():
    """Verifica si el Circuit Breaker está abierto (bloqueando llamadas a Gemini)."""
    if not os.path.exists(CIRCUIT_FILE):
        return False
    try:
        with open(CIRCUIT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        until = data.get('blocked_until', 0)
        remaining = until - time.time()
        if remaining > 0:
            return True
        # El cooldown expiró, intentar recuperar
        return False
    except Exception:
        return False

def open_circuit(reason="Quota 429 exceeded"):
    """Abre el circuito e impide peticiones durante el tiempo de cooldown."""
    blocked_until = time.time() + CIRCUIT_COOLDOWN_SECONDS
    try:
        with open(CIRCUIT_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'state': 'OPEN',
                'reason': reason,
                'blocked_until': blocked_until,
                'timestamp': time.time()
            }, f, indent=2)
        print(f"⚡ Circuit Breaker ACTIVADO: {reason}. Omitiendo traducciones durante {CIRCUIT_COOLDOWN_SECONDS // 60} min para evitar bloqueos.")
    except Exception as e:
        logger.warning(f"Error escribiendo estado de Circuit Breaker: {e}")

def close_circuit():
    """Cierra el circuito tras una llamada exitosa."""
    if os.path.exists(CIRCUIT_FILE):
        try:
            os.remove(CIRCUIT_FILE)
        except Exception:
            pass

# ─── Caché de Traducciones ───────────────────────────────────────────────────
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
        logger.warning(f"Error guardando caché de traducción: {e}")

def call_gemini(prompt, max_retries=2):
    """
    Invoca la API de Gemini con rotación de modelos y protección Circuit Breaker.
    """
    if not GEMINI_KEY:
        return None

    if is_circuit_open():
        return None

    ensure_warp_proxy()
    body = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {
            'temperature': 0.1,
            'maxOutputTokens': 8192,
        }
    }

    quota_exhausted_count = 0

    for model_name in GEMINI_MODELS:
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_KEY}'
        for attempt in range(max_retries):
            try:
                resp = requests.post(url, json=body, timeout=25)
                if resp.status_code == 200:
                    close_circuit()
                    res_json = resp.json()
                    candidates = res_json.get('candidates', [])
                    if candidates and 'content' in candidates[0]:
                        parts = candidates[0]['content'].get('parts', [])
                        if parts and 'text' in parts[0]:
                            return parts[0]['text'].strip()
                elif resp.status_code == 429:
                    if attempt < max_retries - 1:
                        time.sleep(3.0 * (attempt + 1))
                        continue
                    quota_exhausted_count += 1
                    break
                elif resp.status_code == 404:
                    break  # Modelo no soportado en esta versión de API
            except Exception:
                time.sleep(0.5 * (attempt + 1))

    # Si todos los modelos consultados fallaron por límite de cuota (429), abrir Circuit Breaker
    if quota_exhausted_count >= len(GEMINI_MODELS):
        open_circuit("Cuota de Gemini API agotada (HTTP 429 en todos los modelos)")
    else:
        logger.warning("Traducción no completada: todos los modelos de respaldo devolvieron error.")

    return None

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
        clean_res = re.sub(r'^```html\s*', '', res, flags=re.IGNORECASE)
        clean_res = re.sub(r'\s*```$', '', clean_res).strip()
        clean_res = re.sub(r'^["«\']|["»\']$', '', clean_res).strip()
        _CACHE[h] = clean_res
        save_cache()
        return clean_res
    return text

def translate_article_entry(entry):
    """
    Traduce una entrada de artículo si no ha sido traducida previamente.
    """
    if not entry or entry.get('translated'):
        return entry

    translated_any = False
    title = entry.get('title')
    if title:
        tr_title = translate_text(title, is_html=False)
        if tr_title and tr_title.strip() != title.strip():
            entry['title'] = tr_title
            translated_any = True

    content = entry.get('content')
    if content and len(content) > 40:
        tr_content = translate_text(content, is_html=True)
        if tr_content and tr_content.strip() != content.strip():
            entry['content'] = tr_content
            translated_any = True

    if translated_any:
        entry['translated'] = True
    return entry
