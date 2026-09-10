#!/usr/bin/env python3
"""
phonetic_adapter.py — Normalizador fonético para locución TTS en Punto de Vista.

Adapta nombres propios extranjeros, fotógrafos anglosajones, marcas y términos
técnicos a grafías fonéticas en castellano para que el sintetizador de voz (Kokoro/espeak-ng)
los pronuncie con dicción impecable y sin deletrear prefijos como 'Mc'.
"""

import json
import os
import re
import logging
from data_paths import get_data_path

logger = logging.getLogger('pdv.phonetics')
LEXICON_PATH = get_data_path('phonetic_lexicon.json')

_LEXICON = None


def load_phonetic_lexicon():
    global _LEXICON
    if _LEXICON is not None:
        return _LEXICON

    _LEXICON = {}
    if os.path.exists(LEXICON_PATH):
        try:
            with open(LEXICON_PATH, 'r', encoding='utf-8') as f:
                _LEXICON = json.load(f)
        except Exception as e:
            logger.warning(f"Error cargando {LEXICON_PATH}: {e}")
    return _LEXICON


# Reglas algorítmicas universales (para nombres no contemplados en el léxico)
UNIVERSAL_PATTERNS = [
    # 1. Prefijo escocés/irlandés Mc... (evita que diga 'eme-ce')
    (re.compile(r'\bMc([A-ZÁÉÍÓÚa-záéíóú])'), r'Mac\1'),
    # 2. Prefijo O'...
    (re.compile(r'\bO\'([A-ZÁÉÍÓÚa-záéíóú])'), r'O\1'),
    # 3. Nombres anglosajones frecuentes
    (re.compile(r'\bSteve\b', re.IGNORECASE), 'Stiv'),
    (re.compile(r'\bMike\b', re.IGNORECASE), 'Maik'),
    (re.compile(r'\bDave\b', re.IGNORECASE), 'Deiv'),
    (re.compile(r'\bJames\b', re.IGNORECASE), 'Jeims'),
    (re.compile(r'\bGeorge\b', re.IGNORECASE), 'Yorch'),
    (re.compile(r'\bCharles\b', re.IGNORECASE), 'Charls'),
    (re.compile(r'\bPaul\b', re.IGNORECASE), 'Pol'),
    (re.compile(r'\bBrian\b', re.IGNORECASE), 'Bráian'),
    (re.compile(r'\bPeter\b', re.IGNORECASE), 'Píter'),
    (re.compile(r'\bMichael\b', re.IGNORECASE), 'Máikel'),
    (re.compile(r'\bTyler\b', re.IGNORECASE), 'Táiler'),
    (re.compile(r'\bCheryl\b', re.IGNORECASE), 'Chéril'),
    (re.compile(r'\bJohn\b', re.IGNORECASE), 'Yon'),
    # 4. Palabras clave de fotografía en inglés
    (re.compile(r'\bStraight\b', re.IGNORECASE), 'Streit'),
    (re.compile(r'\bStreet\b', re.IGNORECASE), 'Strit'),
    (re.compile(r'\bLight\b', re.IGNORECASE), 'Lait'),
    (re.compile(r'\bNight\b', re.IGNORECASE), 'Nait'),
    (re.compile(r'\bWhite\b', re.IGNORECASE), 'Uait'),
    (re.compile(r'\bBlack\b', re.IGNORECASE), 'Blac'),
    (re.compile(r'\bShutter\b', re.IGNORECASE), 'Shóter'),
    (re.compile(r'\bNewsletter\b', re.IGNORECASE), 'Niusleter'),
    (re.compile(r'\bNewsletters\b', re.IGNORECASE), 'Niusleters'),
    (re.compile(r'\bPhotobook\b', re.IGNORECASE), 'Fotolibro'),
    (re.compile(r'\bPhotobooks\b', re.IGNORECASE), 'Fotolibros'),
    # 5. Sufijos ingleses comunes
    (re.compile(r'(\w+)shire\b', re.IGNORECASE), r'\1sher'),
    (re.compile(r'(\w+)wood\b', re.IGNORECASE), r'\1wud'),
    (re.compile(r'(\w+)ville\b', re.IGNORECASE), r'\1vil'),
    (re.compile(r'(\w+)field\b', re.IGNORECASE), r'\1fild'),
]


def adapt_text_phonetics(text: str) -> str:
    """
    Aplica la adaptación fonética completa a un texto locutable:
    1. Sustituye términos y nombres del diccionario persistente (ordenados por longitud descendente).
    2. Aplica reglas universales para nombres anglosajones no registrados.
    """
    if not text or not isinstance(text, str):
        return text

    adapted = text
    lexicon = load_phonetic_lexicon()

    # Ordenar por longitud de clave descendente para evitar colisiones (ej. 'Steve McCurry' antes de 'Steve')
    sorted_keys = sorted(lexicon.keys(), key=lambda x: len(x), reverse=True)
    for k in sorted_keys:
        v = lexicon[k]
        pattern = r'\b' + re.escape(k) + r'\b'
        adapted = re.sub(pattern, v, adapted, flags=re.IGNORECASE)

    # Reglas universales
    for pat, rep in UNIVERSAL_PATTERNS:
        adapted = pat.sub(rep, adapted)

    return adapted


if __name__ == '__main__':
    frases_prueba = [
        "Steve McCurry fotografió a William Klein para Aperture.",
        "Tyler Mattas viaja por Yorkshire con una cámara de Street Photography.",
        "Frank Horvat expone en The Met y Victoria & Albert.",
        "Un nuevo proyecto de Cheryl Newman con película Black and White."
    ]

    print("🧪 Probando normalizador fonético:")
    for f in frases_prueba:
        res = adapt_text_phonetics(f)
        print(f"  • ORIGINAL: {f}")
        print(f"    FONÉTICA: {res}\n")
