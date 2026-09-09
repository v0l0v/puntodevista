import argparse
import json
import os
import subprocess
import sys
import time
from datetime import date

from update_static_data import (
    fetch_colossal, fetch_lomography, fetch_booooooom,
    fetch_tpj, fetch_swan, fetch_huck, load_previous_items,
    update_lomography_articles, update_booooooom_articles, update_swan_articles,
    fetch_lensculture, update_lensculture_articles,
    fetch_odlp, update_odlp_articles, fetch_magnum, update_magnum_articles,
    fetch_shootitwithfilm, fetch_wp_api, fetch_rss, load_article_cache,
    update_35mmc_articles, update_emulsive_articles, update_huck_articles,
    update_phroom_articles, update_tpj_articles
)

from sources_config import get_active_sources
from data_paths import get_data_path

DIR = os.path.dirname(os.path.abspath(__file__))

FETCH_MAP = {
    'colossal': fetch_colossal,
    'lomography': fetch_lomography,
    'booooooom': fetch_booooooom,
    'tpj': fetch_tpj,
    'swan': fetch_swan,
    'huck': fetch_huck,
    'lensculture': fetch_lensculture,
    'odlp': fetch_odlp,
    'magnum': fetch_magnum,
    'shootitwithfilm': fetch_shootitwithfilm,
}

def _inject_thumb(items, cache_file):
    try:
        import re
        cache = load_article_cache(cache_file)
        for item in items:
            data = cache.get(item.get('link'))
            if isinstance(data, dict):
                cur_thumb = str(item.get('thumbnail') or '')
                # Si no tiene thumbnail, o si el actual es un YouTube embed o Huck sin escalar
                if data.get('thumbnail') and (not cur_thumb or 'youtube.com/embed/' in cur_thumb or 'w=4000' in cur_thumb):
                    item['thumbnail'] = data['thumbnail']
                if data.get('photographer') and not item.get('photographer'):
                    item['photographer'] = data['photographer']
            # Sanitizar miniaturas de YouTube en cualquier caso
            if item.get('thumbnail') and 'youtube.com/embed/' in item['thumbnail']:
                yt_m = re.search(r'youtube\.com/embed/([a-zA-Z0-9_-]+)', item['thumbnail'])
                if yt_m:
                    item['thumbnail'] = f'https://img.youtube.com/vi/{yt_m.group(1)}/hqdefault.jpg'
    except Exception:
        pass

CACHE_UPDATERS = {
    'lomography': lambda items: update_lomography_articles(items),
    'booooooom': lambda items: update_booooooom_articles(items),
    'swan': lambda items: (update_swan_articles(items), _inject_thumb(items, 'swan_articles.json')),
    'lensculture': lambda items: (update_lensculture_articles(items[:10]), _inject_thumb(items, 'lensculture_articles.json')),
    'odlp': lambda items: (update_odlp_articles(items[:10]), _inject_thumb(items, 'odlp_articles.json')),
    'magnum': lambda items: (update_magnum_articles(items[:10]), _inject_thumb(items, 'magnum_articles.json')),
    '35mmc': lambda items: (update_35mmc_articles(items[:10]), _inject_thumb(items, '35mmc_articles.json')),
    'emulsive': lambda items: (update_emulsive_articles(items[:10]), _inject_thumb(items, 'emulsive_articles.json')),
    'huck': lambda items: (update_huck_articles(items[:10]), _inject_thumb(items, 'huck_articles.json')),
    'phroom': lambda items: (update_phroom_articles(items[:10]), _inject_thumb(items, 'phroom_articles.json')),
    'tpj': lambda items: (update_tpj_articles(items[:10]), _inject_thumb(items, 'tpj_articles.json')),
}


def save_payload(filename, items, all_entries=None):
    payload = {'items': items, 'count': len(items), 'updated': date.today().isoformat()}
    dest_path = get_data_path(filename)
    with open(dest_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False)
    print(f'  Guardado {filename} ({len(items)})')


def main():
    parser = argparse.ArgumentParser(description='Actualiza las listas de feeds (JSON) para todas las fuentes activas.')
    parser.add_argument('--keep-lomo', action='store_true',
                        help='Reutiliza lomography.json sin scrapear la revista.')
    parser.add_argument('--fresh-lomography', action='store_true',
                        help='Fuerza el refresco de Lomography.')
    parser.add_argument('--push', action='store_true',
                        help='Sube los cambios a GitHub al finalizar.')
    args = parser.parse_args()

    ts = date.today().isoformat()
    print(f'[{ts}] Actualizando listas de feeds de todas las fuentes activas...')

    active_sources = get_active_sources()
    source_items = {}

    for i, src in enumerate(active_sources, 1):
        s_id = src['id']
        name = src['name']
        print(f'  {i}. {name} ({s_id})...')
        items = []

        try:
            if s_id == 'lomography':
                if args.keep_lomo:
                    items = load_previous_items('lomography.json')
                    print(f'     {len(items)} artículos (modo ahorro: sin refrescar Lomography)')
                else:
                    items = fetch_lomography()
                    if not items:
                        items = load_previous_items('lomography.json')
                    print(f'     {len(items)} artículos')
            elif s_id in FETCH_MAP:
                items = FETCH_MAP[s_id]()
                print(f'     {len(items)} artículos')
            elif src.get('type') == 'wp-api' and src.get('wp_api'):
                items = fetch_wp_api(src['wp_api'], s_id)
            elif src.get('feeds'):
                for feed_url in src['feeds']:
                    items.extend(fetch_rss(feed_url, s_id, include_content=True, fetch_page_fallback=False))
                print(f'     {len(items)} artículos (RSS)')
        except Exception as e_fetch:
            print(f'     ⚠️ Error obteniendo {s_id}: {e_fetch}')

        if not items:
            items = load_previous_items(f'{s_id}.json')
            if items:
                print(f'     (recuperados {len(items)} artículos previos de {s_id}.json)')

        source_items[s_id] = items

    print('  Actualizando cachés de artículos y miniaturas...')
    for s_id, updater in CACHE_UPDATERS.items():
        if s_id in source_items and source_items[s_id]:
            try:
                updater(source_items[s_id])
            except Exception as e_cache:
                print(f'     ⚠️ Error en cache de {s_id}: {e_cache}')

    print('  Traducción automática de titulares y resúmenes al español...')
    try:
        from translator import translate_article_entry, is_circuit_open
        if not is_circuit_open():
            for s_id, items in source_items.items():
                if items:
                    untranslated = [it for it in items if not it.get('translated')]
                    for it in untranslated[:3]:
                        if is_circuit_open():
                            break
                        translate_article_entry(it)
            print('     ✅ Traducción completada con éxito')
        else:
            print('     ⚡ Traducción omitida temporalmente (Circuit Breaker activo por cuota 429)')
    except Exception as e_trans:
        print(f'     ⚠️ Error en traducción automática: {e_trans}')

    print('  Guardando JSONs individuales por fuente...')
    all_entries = []
    for s_id, items in source_items.items():
        all_entries.extend(items)
        save_payload(f'{s_id}.json', items)

    print('  Sincronizando con archivo histórico y generando feeds.json consolidado...')
    try:
        from sync_archive import sync_source_json_files, export_full_feeds_json
        from archive_db import get_connection
        with get_connection() as conn:
            sync_source_json_files(conn)
            conn.commit()
        export_full_feeds_json()
    except Exception as e_sync:
        print(f'  ⚠️ Error en sincronización de archivo histórico: {e_sync}')
        all_entries.sort(key=lambda x: x.get('_parsedDate') or x.get('date') or '', reverse=True)
        save_payload('feeds.json', all_entries)

    should_push = args.push or '--push' in sys.argv or os.environ.get('PUSH_TO_GITHUB') == '1'
    if should_push:
        print('  Subiendo a GitHub...')
        try:
            subprocess.run(
                ['git', 'add', 'data/'],
                capture_output=True, text=True, cwd=DIR
            )
            res = subprocess.run(
                ['git', 'commit', '-m', f'chore: update static feeds {ts}'],
                capture_output=True, text=True, cwd=DIR
            )
            if 'nothing to commit' in res.stdout:
                print('     Sin cambios')
                return
            if res.returncode != 0 and 'nothing to commit' not in (res.stdout + res.stderr):
                print(f'     ⚠️ Error commit: {res.stderr[:300]}')
                return
            
            pushed = False
            for attempt in range(4):
                pull = subprocess.run(['git', 'pull', '--rebase', '--autostash'], capture_output=True, text=True, cwd=DIR)
                push = subprocess.run(['git', 'push'], capture_output=True, text=True, cwd=DIR)
                if push.returncode == 0:
                    print('     ✅ Push a GitHub OK')
                    pushed = True
                    break
                time.sleep(3 * (attempt + 1))
            if not pushed:
                print(f'     ⚠️ Push fallido tras reintentos')
        except Exception as e:
            print(f'     ⚠️ Git error: {e}')
    else:
        print('  Archivos de datos actualizados en data/.')


if __name__ == '__main__':
    main()
