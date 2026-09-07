#!/usr/bin/env python3
"""
scripts/repair_all_translations.py — Saneamiento y traducción masiva por lotes de todo el catálogo.
1. Elimina marcas falsas de traducción (donde content_original == content).
2. Traduce progresivamente artículos de *_articles.json y feeds.json usando gemini-3.6-flash.
3. Respeta rate-limits con pausas y guarda progreso atómicamente.
"""
import os
import sys
import json
import time
import glob
import argparse

DIR = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(DIR)
sys.path.insert(0, PARENT)

from translator import translate_text, is_circuit_open
from data_paths import get_data_path
from config import ensure_warp_proxy

def fix_false_translations(articles):
    """Detecta y limpia artículos marcados falsamente como traducidos."""
    fixed = 0
    for url, art in articles.items():
        if not isinstance(art, dict):
            continue
        orig = art.get('content_original')
        curr = art.get('content')
        is_tr = art.get('translated')
        if is_tr and orig and curr and orig.strip() == curr.strip():
            art['translated'] = False
            art.pop('content_original', None)
            fixed += 1
    return fixed

def repair_article_cache_file(filepath, limit=15, sleep_sec=1.5):
    """Traduce hasta 'limit' artículos pendientes en un archivo de caché."""
    if not os.path.exists(filepath):
        return 0, 0

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    articles = data.get('articles', {})
    false_cleaned = fix_false_translations(articles)
    
    translated_count = 0
    items_to_translate = []

    for url, art in articles.items():
        if not isinstance(art, dict):
            continue
        # Candidatos: no traducidos que tengan contenido significativo
        if not art.get('translated') and art.get('content') and len(art.get('content')) > 40:
            items_to_translate.append((url, art))

    # Priorizar artículos más recientes (al final de la inserción en el diccionario)
    items_to_translate.reverse()

    if not items_to_translate and false_cleaned == 0:
        return 0, 0

    print(f"\n📁 {os.path.basename(filepath)}: {len(items_to_translate)} pendientes (limpiados falsos: {false_cleaned})")

    for idx, (url, art) in enumerate(items_to_translate[:limit], 1):
        if is_circuit_open():
            print("⚡ Circuit Breaker activo. Pausando traducción por lotes.")
            break

        content = art.get('content', '')
        title = art.get('title', url.split('/')[-1])
        print(f"  [{idx}/{min(len(items_to_translate), limit)}] Traduciendo: {title[:45]}...")

        # Traducir contenido HTML
        tr_content = translate_text(content, is_html=True)
        if tr_content and tr_content.strip() != content.strip():
            art['content_original'] = content
            art['content'] = tr_content
            art['translated'] = True
            translated_count += 1
            print("    ✅ Contenido traducido con éxito")
        else:
            print("    ⚠️ Traducción no aplicada (fallback a original)")

        # Guardado incremental cada 3 traducciones
        if translated_count % 3 == 0:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        time.sleep(sleep_sec)

    # Guardado final del archivo
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return false_cleaned, translated_count

def repair_feeds_json(limit=30, sleep_sec=1.0):
    """Traduce títulos de artículos recientes en feeds.json que aún estén en inglés."""
    feeds_path = get_data_path('feeds.json')
    if not os.path.exists(feeds_path):
        return 0

    with open(feeds_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    items = data.get('items', [])
    translated_count = 0
    print(f"\n📰 feeds.json: Comprobando {len(items)} entradas para portada...")

    for idx, it in enumerate(items):
        if translated_count >= limit or is_circuit_open():
            break

        # Traducir solo si no está marcado como traducido
        if not it.get('translated'):
            title = it.get('title', '')
            if title and len(title) > 5:
                tr_title = translate_text(title, is_html=False)
                if tr_title and tr_title.strip() != title.strip():
                    it['title'] = tr_title
                    it['translated'] = True
                    translated_count += 1
                    print(f"  ✅ Título traducido [{translated_count}]: {tr_title[:50]}")
                    time.sleep(sleep_sec)

    if translated_count > 0:
        with open(feeds_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  Guardadas {translated_count} traducciones de portada en feeds.json")

    return translated_count

def main():
    parser = argparse.ArgumentParser(description="Reparar y traducir artículos en bloque")
    parser.add_argument('--limit-per-source', type=int, default=15, help="Límite de artículos por medio")
    parser.add_argument('--feeds-limit', type=int, default=40, help="Límite de entradas en feeds.json")
    parser.add_argument('--sleep', type=float, default=1.5, help="Pausa en segundos entre llamadas")
    parser.add_argument('--source', type=str, default=None, help="Filtrar por medio específico (ej: odlp, 35mmc)")
    args = parser.parse_args()

    ensure_warp_proxy()
    print("=== Iniciando Saneamiento y Traducción Integral de Punto de Vista ===")

    article_files = sorted(glob.glob(get_data_path('*_articles.json')))
    if args.source:
        article_files = [f for f in article_files if args.source.lower() in os.path.basename(f).lower()]
    total_cleaned = 0
    total_translated = 0

    for f in article_files:
        c, t = repair_article_cache_file(f, limit=args.limit_per_source, sleep_sec=args.sleep)
        total_cleaned += c
        total_translated += t

    feeds_tr = 0
    if not args.source:
        feeds_tr = repair_feeds_json(limit=args.feeds_limit, sleep_sec=args.sleep)

    print("\n=======================================================")
    print(f"🎉 SANEAMIENTO COMPLETADO:")
    print(f"  • Artículos falsos limpiados: {total_cleaned}")
    print(f"  • Artículos extensos traducidos: {total_translated}")
    print(f"  • Títulos de portada traducidos: {feeds_tr}")
    print("=======================================================")

if __name__ == '__main__':
    main()
