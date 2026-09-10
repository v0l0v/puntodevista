#!/usr/bin/env python3
"""
Módulo de traducción neuronal 100% LOCAL para Punto de Vista.
Utiliza CTranslate2 + SentencePiece con modelos offline (sin llamadas a Gemini ni cuotas API).
Preserva intactas las etiquetas HTML (<img>, <a>, atributos, etc.) mediante BeautifulSoup.
"""
import os
import json
import re
import hashlib
import logging
import urllib.request
import zipfile
from bs4 import BeautifulSoup

from data_paths import get_data_path
from photo_glossary import apply_photo_glossary

logger = logging.getLogger('pdv.translator')

DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(DIR, 'translate_models', 'en_es', 'en_es')
CACHE_FILE = get_data_path('translations_cache.json')
_CACHE = {}

_SP_MODEL = None
_CT2_TRANSLATOR = None


def is_circuit_open():
    """Para compatibilidad con el resto del código: siempre False (motor 100% local sin cuotas)."""
    return False


def _ensure_local_model():
    """Descarga y descomprime el modelo CTranslate2 en_es si aún no existe."""
    global _SP_MODEL, _CT2_TRANSLATOR
    if _CT2_TRANSLATOR is not None and _SP_MODEL is not None:
        return True

    sp_path = os.path.join(MODELS_DIR, 'sentencepiece.model')
    model_dir = os.path.join(MODELS_DIR, 'model')

    if not os.path.exists(sp_path) or not os.path.exists(model_dir):
        os.makedirs(os.path.dirname(MODELS_DIR), exist_ok=True)
        zip_dest = os.path.join(DIR, 'translate_models', 'en_es.zip')
        model_url = 'https://argos-net.com/v1/translate-en_es-1_0.argosmodel'
        print(f"📦 Descargando modelo de traducción local desde {model_url}...")
        try:
            req = urllib.request.Request(model_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=60) as resp, open(zip_dest, 'wb') as out_f:
                out_f.write(resp.read())
            with zipfile.ZipFile(zip_dest, 'r') as zf:
                zf.extractall(os.path.join(DIR, 'translate_models', 'en_es'))
            if os.path.exists(zip_dest):
                os.remove(zip_dest)
            print("✅ Modelo de traducción local listo.")
        except Exception as e:
            logger.error(f"Error descargando modelo de traducción local: {e}")
            return False

    try:
        import ctranslate2
        import sentencepiece as spm

        _SP_MODEL = spm.SentencePieceProcessor()
        _SP_MODEL.load(sp_path)
        _CT2_TRANSLATOR = ctranslate2.Translator(model_dir, device='cpu', intra_threads=2)
        return True
    except Exception as e:
        logger.error(f"Error cargando motor CTranslate2: {e}")
        return False


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


def _hash_key(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _translate_plain_segment(text):
    """Traduce un segmento de texto plano usando CTranslate2."""
    if not text or not text.strip() or len(text.strip()) < 2:
        return text

    if not _ensure_local_model():
        return text

    s = text.strip()
    try:
        tokens = _SP_MODEL.encode_as_pieces(s)
        results = _CT2_TRANSLATOR.translate_batch([tokens])
        translated = _SP_MODEL.decode_pieces(results[0].hypotheses[0])
        translated = apply_photo_glossary(translated)
        # Respetar espacios iniciales o finales del segmento original
        prefix = ' ' if text.startswith(' ') else ''
        suffix = ' ' if text.endswith(' ') else ''
        return prefix + translated + suffix
    except Exception as e:
        logger.warning(f"Error en inferencia de traducción: {e}")
        return text


def translate_text(text, is_html=False):
    """
    Traduce texto o contenido HTML al español usando el motor neuronal local.
    Conserva URLs, etiquetas HTML y atributos sin alteración.
    """
    if not text or not str(text).strip():
        return text

    text_str = str(text).strip()
    load_cache()
    h = _hash_key(text_str)
    if h in _CACHE and _CACHE[h]:
        val = _CACHE[h]
        # Evitar artefactos residuales de versiones anteriores con Gemini
        if not val.startswith("Aquí tienes") and not val.startswith("La traducción") and not "1." in val:
            return apply_photo_glossary(val)

    if is_html:
        try:
            soup = BeautifulSoup(text_str, 'html.parser')
            target_tags = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'figcaption', 'blockquote', 'strong', 'em', 'span']
            for tag in soup.find_all(target_tags):
                if tag.string:
                    orig_s = tag.string
                    if orig_s and len(orig_s.strip()) > 1:
                        tag.string.replace_with(_translate_plain_segment(orig_s))
                else:
                    for child in list(tag.children):
                        if child.name is None and str(child).strip():
                            child.replace_with(_translate_plain_segment(str(child)))
            translated_res = str(soup)
        except Exception as e_html:
            logger.warning(f"Fallo en parseo HTML para traducción: {e_html}")
            translated_res = _translate_plain_segment(text_str)
    else:
        # Texto plano (titulares, descripciones cortas)
        translated_res = _translate_plain_segment(text_str)

    if translated_res and translated_res.strip() != text_str.strip():
        translated_res = apply_photo_glossary(translated_res)
        _CACHE[h] = translated_res
        save_cache()
        return translated_res

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
