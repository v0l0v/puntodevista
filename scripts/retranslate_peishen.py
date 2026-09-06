#!/usr/bin/env python3
"""
scripts/retranslate_peishen.py — Traduce el artículo de Peishen Liang y corrige las marcas falsas de traducción.
"""
import json
import os
import sys

DIR = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(DIR)
sys.path.insert(0, PARENT)

from translator import translate_text
from data_paths import get_data_path

def main():
    odlp_path = get_data_path('odlp_articles.json')
    if not os.path.exists(odlp_path):
        print("odlp_articles.json no encontrado")
        return

    with open(odlp_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    target_url = 'https://loeildelaphotographie.com/en/peishen-liang/'
    articles = data.get('articles', {})

    if target_url in articles:
        art = articles[target_url]
        content_to_translate = art.get('content_original') or art.get('content')
        print("Traduciendo artículo de Peishen Liang...")
        translated = translate_text(content_to_translate, is_html=True)
        if translated and translated.strip() != content_to_translate.strip():
            art['content_original'] = content_to_translate
            art['content'] = translated
            art['translated'] = True
            print("✅ Traducción completada con éxito:")
            print(translated[:300])
        else:
            print("⚠️ La traducción no produjo cambios.")

    # Guardar
    with open(odlp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("Guardado en", odlp_path)

if __name__ == '__main__':
    main()
