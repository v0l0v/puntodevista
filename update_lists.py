import argparse
import json
import os
import subprocess
from datetime import date

from update_static_data import (fetch_colossal, fetch_lomography, fetch_booooooom,
                                fetch_tpj, fetch_swan, fetch_huck, load_previous_items,
                                update_lomography_articles, update_booooooom_articles, update_swan_articles,
                                fetch_lensculture, update_lensculture_articles,
                                fetch_odlp, update_odlp_articles, fetch_magnum, update_magnum_articles,
                                fetch_shootitwithfilm)

DIR = os.path.dirname(os.path.abspath(__file__))


def save_payload(filename, items, all_entries):
    payload = {'items': items, 'count': len(items), 'updated': date.today().isoformat()}
    if filename == 'feeds.json':
        payload = {'items': all_entries, 'count': len(all_entries), 'updated': date.today().isoformat()}
    with open(os.path.join(DIR, filename), 'w') as f:
        json.dump(payload, f, ensure_ascii=False)
    print(f'  Guardado {filename} ({len(items)})')


def main():
    parser = argparse.ArgumentParser(description='Actualiza las listas de feeds (JSON).')
    parser.add_argument('--fresh-lomography', action='store_true',
                        help='Refresca la lista de Lomography (gratis vía Jina). '
                             'Sin esta flag se conserva el último dato de Lomography.')
    args = parser.parse_args()

    ts = date.today().isoformat()
    print(f'[{ts}] Actualizando listas de feeds...')

    print('  1. Colossal...')
    colossal = fetch_colossal()
    print(f'     {len(colossal)} artículos')

    print('  2. Lomography...')
    if args.fresh_lomography:
        lomo = fetch_lomography()
        if not lomo:
            lomo = load_previous_items('lomography.json')
        print(f'     {len(lomo)} artículos')
    else:
        lomo = load_previous_items('lomography.json')
        print(f'     {len(lomo)} artículos (modo ahorro: sin refrescar Lomography)')

    print('  3. Booooooom...')
    boom = fetch_booooooom()
    if not boom:
        boom = load_previous_items('booooooom.json')
    print(f'     {len(boom)} artículos')

    print('  4. The Photographic Journal...')
    tpj = fetch_tpj()
    if not tpj:
        tpj = load_previous_items('tpj.json')
    print(f'     {len(tpj)} artículos')

    print('  5. Swann Galleries...')
    swan = fetch_swan()
    if not swan:
        swan = load_previous_items('swan.json')
    print(f'     {len(swan)} artículos')

    print('  6. Huck Magazine...')
    huck = fetch_huck()
    if not huck:
        huck = load_previous_items('huck.json')
    print(f'     {len(huck)} artículos')

    print('  6b. LensCulture...')
    lensculture = fetch_lensculture()
    if not lensculture:
        lensculture = load_previous_items('lensculture.json')
    print(f'     {len(lensculture)} artículos')

    print('  6c. L\'Œil de la Photographie...')
    odlp = fetch_odlp()
    if not odlp:
        odlp = load_previous_items('odlp.json')
    print(f'     {len(odlp)} artículos')

    print('  6d. Magnum Photos...')
    magnum = fetch_magnum()
    if not magnum:
        magnum = load_previous_items('magnum.json')
    print(f'     {len(magnum)} artículos')

    print('  6e. Shoot It With Film...')
    shootit = fetch_shootitwithfilm()
    if not shootit:
        shootit = load_previous_items('shootitwithfilm.json')
    print(f'     {len(shootit)} artículos')

    print('  6f. Actualizando cachés de artículos...')
    if lomo:
        update_lomography_articles(lomo)
    if boom:
        update_booooooom_articles(boom)
    
    # Load caches and inject thumbnails
    from update_static_data import load_article_cache
    
    if swan:
        update_swan_articles(swan)
        swan_cache = load_article_cache('swan_articles.json')
        for item in swan:
            data = swan_cache.get(item.get('link'))
            if isinstance(data, dict) and data.get('thumbnail'):
                item['thumbnail'] = data['thumbnail']
                
    if lensculture:
        update_lensculture_articles(lensculture[:10])
        lens_cache = load_article_cache('lensculture_articles.json')
        for item in lensculture:
            data = lens_cache.get(item.get('link'))
            if isinstance(data, dict) and data.get('thumbnail'):
                item['thumbnail'] = data['thumbnail']
                
    if odlp:
        update_odlp_articles(odlp[:10])
        odlp_cache = load_article_cache('odlp_articles.json')
        for item in odlp:
            data = odlp_cache.get(item.get('link'))
            if isinstance(data, dict) and data.get('thumbnail'):
                item['thumbnail'] = data['thumbnail']

    if magnum:
        update_magnum_articles(magnum[:10])
        magnum_cache = load_article_cache('magnum_articles.json')
        for item in magnum:
            data = magnum_cache.get(item.get('link'))
            if isinstance(data, dict) and data.get('thumbnail'):
                item['thumbnail'] = data['thumbnail']

    all_entries = sorted(colossal + lomo + boom + tpj + swan + huck + lensculture + odlp + magnum + shootit,
                         key=lambda x: x.get('_parsedDate') or x.get('date') or '',
                         reverse=True)

    save_payload('lomography.json', lomo, all_entries)
    save_payload('booooooom.json', boom, all_entries)
    save_payload('tpj.json', tpj, all_entries)
    save_payload('swan.json', swan, all_entries)
    save_payload('huck.json', huck, all_entries)
    save_payload('lensculture.json', lensculture, all_entries)
    save_payload('odlp.json', odlp, all_entries)
    save_payload('magnum.json', magnum, all_entries)
    save_payload('shootitwithfilm.json', shootit, all_entries)
    save_payload('feeds.json', all_entries, all_entries)

    print('  7. Subiendo a GitHub...')
    try:
        subprocess.run(
            ['git', 'add', 'lomography.json', 'booooooom.json', 'tpj.json', 'swan.json', 'huck.json', 'lensculture.json', 'odlp.json', 'magnum.json', 'shootitwithfilm.json', 'feeds.json',
             'lomography_articles.json', 'booooooom_articles.json', 'swan_articles.json', 'lensculture_articles.json', 'odlp_articles.json', 'magnum_articles.json'],
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
        
        # Reintentos con rebase para evitar colisiones en CI
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


if __name__ == '__main__':
    main()
