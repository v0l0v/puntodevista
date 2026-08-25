#!/usr/bin/env python3
"""
sync_archive.py — Ingesta e indexación de todo el histórico de artículos y podcasts en SQLite FTS5 y sqlite-vec.
"""


import json
import os
import re
from pathlib import Path
from archive_db import get_connection, init_db, upsert_article, upsert_podcast, get_stats

DIR = os.path.dirname(os.path.abspath(__file__))
RESUMENES_DIR = os.path.join(DIR, 'resumenes')


def clean_html_tags(text):
    if not text:
        return ''
    return re.sub(r'<[^>]+>', ' ', text).strip()


def sync_podcasts(conn):
    """Ingesta de podcasts desde podcast_meta.json y archivos en resumenes/."""
    meta_path = os.path.join(DIR, 'podcast_meta.json')
    if not os.path.exists(meta_path):
        return 0

    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)

    count = 0
    for item in meta:
        ep_date = item.get('date')
        if not ep_date:
            continue

        locutable_text = ''
        locutable_path = os.path.join(RESUMENES_DIR, f'digest-{ep_date}.locutable.txt')
        if os.path.exists(locutable_path):
            try:
                with open(locutable_path, 'r', encoding='utf-8') as lf:
                    locutable_text = lf.read()
            except Exception:
                pass

        if not locutable_text:
            podcast_md = os.path.join(RESUMENES_DIR, f'digest-{ep_date}.podcast.md')
            if os.path.exists(podcast_md):
                try:
                    with open(podcast_md, 'r', encoding='utf-8') as pf:
                        locutable_text = pf.read()
                except Exception:
                    pass

        item['locutable_text'] = locutable_text
        if upsert_podcast(conn, item):
            count += 1

    return count


def sync_feeds_json(conn):
    """Ingesta de artículos desde feeds.json."""
    feeds_path = os.path.join(DIR, 'feeds.json')
    if not os.path.exists(feeds_path):
        return 0

    with open(feeds_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    items = data.get('items', []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    count = 0
    for item in items:
        if not item.get('link') and not item.get('url'):
            continue
        if upsert_article(conn, item):
            count += 1
    return count


def sync_source_json_files(conn):
    """Ingesta desde todos los archivos de fuente individuales."""
    count = 0
    json_files = list(Path(DIR).glob('*.json'))
    ignore_files = {'feeds.json', 'podcast_meta.json', 'config.json', 'config.example.json', 'sources.json', 'telegram_sent.json'}

    for p in json_files:
        if p.name in ignore_files or p.name.startswith('.'):
            continue

        try:
            with open(p, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            continue

        items = data.get('items', []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        source_name = p.stem.replace('_articles', '')

        for item in items:
            if not isinstance(item, dict):
                continue
            if not item.get('link') and not item.get('url'):
                continue
            if not item.get('source') and not item.get('_source'):
                item['source'] = source_name
            if upsert_article(conn, item):
                count += 1

    return count


def main():
    print("🚀 Iniciando sincronización del archivo histórico en SQLite FTS5...")
    init_db()

    with get_connection() as conn:
        print("  1/3 Sincronizando episodios de podcasts...")
        podcasts_count = sync_podcasts(conn)
        conn.commit()
        print(f"      ✓ {podcasts_count} podcasts procesados.")

        print("  2/3 Sincronizando feeds.json...")
        feeds_count = sync_feeds_json(conn)
        conn.commit()
        print(f"      ✓ {feeds_count} artículos procesados de feeds.json.")

        print("  3/3 Sincronizando datasets históricos individuales...")
        sources_count = sync_source_json_files(conn)
        conn.commit()
        print(f"      ✓ {sources_count} artículos procesados de archivos de fuentes.")

    stats = get_stats()
    print("\n✅ Sincronización completada con éxito:")
    print(f"  • Total Artículos Consolidados: {stats['total_articles']}")
    print(f"  • Total Podcasts Consolidados: {stats['total_podcasts']}")
    print(f"  • Rango Temporal: {stats['min_date']} → {stats['max_date']}")
    print("\n📊 Desglose por fuente:")
    for src, cnt in sorted(stats['sources'].items(), key=lambda x: -x[1]):
        print(f"    - {src:20s}: {cnt:4d} artículos")

    # Ingesta e indexación de vectores con sqlite-vec
    print("\n⚡ Indexando vectores en sqlite-vec...")
    try:
        from vector_search import index_missing_embeddings, index_missing_podcasts
        index_missing_embeddings(batch_limit=100)
        index_missing_podcasts()
    except Exception as e:
        print(f"⚠️ Vector indexation skipped: {e}")

    # Exportar todo el archivo consolidado a feeds.json
    print("\n📦 Exportando todo el archivo consolidado (850+ artículos) a feeds.json...")
    export_full_feeds_json()


def export_full_feeds_json():
    """Exporta todos los artículos consolidados de archive.db a feeds.json incluyendo sus etiquetas."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT id, url as link, source as _source, title, photographer,
                   published_date as date, summary as excerpt, summary as content,
                   image_url as image, image_url as thumbnail, tags
            FROM articles
            ORDER BY published_date DESC, id DESC
        """).fetchall()
        items = [dict(r) for r in rows]
        for item in items:
            item['_id'] = str(item['id'])
            item['_parsedDate'] = item['date']
            raw_tags = item.get('tags')
            if isinstance(raw_tags, str):
                try:
                    item['tags'] = json.loads(raw_tags)
                except Exception:
                    item['tags'] = []
            elif not isinstance(raw_tags, list):
                item['tags'] = []

        feeds_path = os.path.join(DIR, 'feeds.json')
        with open(feeds_path, 'w', encoding='utf-8') as f:
            json.dump({'items': items, 'count': len(items), 'updated': json_files_date()}, f, ensure_ascii=False)
        print(f"   ✓ feeds.json generado con éxito conteniendo {len(items)} artículos históricos con etiquetas.")


def json_files_date():
    from datetime import datetime
    return datetime.now().strftime('%Y-%m-%d')


if __name__ == '__main__':
    main()


