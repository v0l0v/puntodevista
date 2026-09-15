#!/usr/bin/env python3
"""
scripts/migrate_to_original_storage.py — Migra todos los JSONs de data/ y archive.db
para garantizar que title y content estén en el idioma original y las traducciones
se almacenen en title_es y content_es.
"""

import os
import sys
import json
from pathlib import Path

DIR = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(DIR)
sys.path.insert(0, PARENT)

from data_paths import get_data_dir, get_data_path
from archive_db import get_connection, init_db
from sync_archive import sync_source_json_files, export_full_feeds_json

def migrate_json_file(filepath):
    if not os.path.exists(filepath):
        return 0, 0

    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except Exception:
            return 0, 0

    modified = False
    restored_count = 0

    if isinstance(data, dict) and 'articles' in data:
        articles = data['articles']
        if isinstance(articles, dict):
            article_iterable = articles.values()
        elif isinstance(articles, list):
            article_iterable = articles
        else:
            article_iterable = []

        for art in article_iterable:
            if not isinstance(art, dict):
                continue
            orig = art.pop('content_original', None)
            orig_t = art.pop('title_original', None)
            curr_c = art.get('content')
            curr_t = art.get('title')

            if orig and curr_c and orig.strip() != curr_c.strip():
                art['content'] = orig
                art['content_es'] = curr_c
                restored_count += 1
                modified = True
            elif orig:
                art['content'] = orig
                modified = True

            if orig_t and curr_t and orig_t.strip() != curr_t.strip():
                art['title'] = orig_t
                art['title_es'] = curr_t
                modified = True
            elif orig_t:
                art['title'] = orig_t
                modified = True

    elif isinstance(data, dict) and 'items' in data:
        items = data['items']
        for item in items:
            if not isinstance(item, dict):
                continue
            orig = item.pop('content_original', None)
            orig_t = item.pop('title_original', None)
            curr_c = item.get('content')
            curr_t = item.get('title')

            if orig and curr_c and orig.strip() != curr_c.strip():
                item['content'] = orig
                item['content_es'] = curr_c
                restored_count += 1
                modified = True
            elif orig:
                item['content'] = orig
                modified = True

            if orig_t and curr_t and orig_t.strip() != curr_t.strip():
                item['title'] = orig_t
                item['title_es'] = curr_t
                modified = True
            elif orig_t:
                item['title'] = orig_t
                modified = True

    elif isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            orig = item.pop('content_original', None)
            orig_t = item.pop('title_original', None)
            curr_c = item.get('content')
            curr_t = item.get('title')

            if orig and curr_c and orig.strip() != curr_c.strip():
                item['content'] = orig
                item['content_es'] = curr_c
                restored_count += 1
                modified = True
            elif orig:
                item['content'] = orig
                modified = True

            if orig_t and curr_t and orig_t.strip() != curr_t.strip():
                item['title'] = orig_t
                item['title_es'] = curr_t
                modified = True
            elif orig_t:
                item['title'] = orig_t
                modified = True

    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2 if 'articles' in data else None)

    return 1 if modified else 0, restored_count


def main():
    data_dir = get_data_dir()
    print(f"🔄 Migrando archivos JSON en {data_dir}...")
    
    total_files = 0
    total_restored = 0
    for p in Path(data_dir).glob('*.json'):
        mod, count = migrate_json_file(p)
        if mod:
            total_files += 1
            total_restored += count

    print(f"✅ {total_files} archivos JSON migrados ({total_restored} artículos restaurados a original).")

    print("🔄 Sincronizando con SQLite archive.db...")
    init_db()
    with get_connection() as conn:
        sync_source_json_files(conn)
        conn.commit()

    export_full_feeds_json()
    print("✅ Base de datos SQLite e índice FTS5 re-sincronizados correctamente.")

if __name__ == '__main__':
    main()
