import argparse
import json
import os
import re
import subprocess
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime
from pathlib import Path
from html import unescape

from server import (firecrawl_scrape, parse_magazine_list, scrape_lomography_article,
                    scrape_booooooom_article, scrape_swan_article, scrape_lensculture_article,
                    scrape_lensculture, scrape_odlp_article, scrape_odlp, scrape_magnum_article,
                    scrape_magnum)

DIR = os.path.dirname(os.path.abspath(__file__))

RSS_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'application/rss+xml, application/xml;q=0.9, */*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

from sources_config import load_sources_config, get_active_sources, get_source_by_id

def _src_prop(src_id, prop, default):
    s = get_source_by_id(src_id)
    return (s and s.get(prop)) or default

WP_API = _src_prop('colossal', 'wp_api', 'https://www.thisiscolossal.com/wp-json/wp/v2/posts?categories=496&per_page=20')
LOMO_URL = _src_prop('lomography', 'url', 'https://www.lomography.com/magazine/')
BOOM_URL = (_src_prop('booooooom', 'feeds', ['https://www.booooooom.com/blog/photo/feed/']) or [''])[0]
TPJ_URLS = _src_prop('tpj', 'feeds', [
    'https://thephotographicjournal.com/essays/rss',
    'https://thephotographicjournal.com/interviews/feed',
    'https://thephotographicjournal.com/features/feed',
])
SWAN_URL = (_src_prop('swan', 'feeds', ['https://www.swanngalleries.com/news/category/photographs-and-photobooks/feed']) or [''])[0]
HUCK_URL = (_src_prop('huck', 'feeds', ['https://www.huckmag.com/topic/photography/feed']) or [''])[0]
LENSCULTURE_URL = (_src_prop('lensculture', 'feeds', ['https://www.lensculture.com/feeds/feed.rss']) or [''])[0]
ODLP_URL = (_src_prop('odlp', 'feeds', ['https://loeildelaphotographie.com/en/feed/']) or [''])[0]
MAGNUM_URL = _src_prop('magnum', 'wp_api', 'https://www.magnumphotos.com/wp-json/wp/v2/posts?per_page=30')
SHOOTIT_URL = (_src_prop('shootitwithfilm', 'feeds', ['https://shootitwithfilm.com/category/features/feed/']) or [''])[0]
SHOOTIT_WP_API = _src_prop('shootitwithfilm', 'wp_api', 'https://shootitwithfilm.com/wp-json/wp/v2/posts?per_page=20&_embed=1')


def fetch_colossal():
    all_posts = []
    for page in range(1, 4):
        url = f'{WP_API}&page={page}'
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            if not data:
                break
            for p in data:
                all_posts.append({
                    '_source': 'colossal',
                    '_id': p['id'],
                    '_parsedDate': p['date'],
                    'link': p['link'],
                    'title': p['title']['rendered'],
                    'content': p['content']['rendered']
                })
        except Exception as e:
            print(f'  Error Colossal: {e}')
            break
    return all_posts


def fetch_lomography():
    md = firecrawl_scrape(LOMO_URL, timeout=60)
    if not md:
        return []
    return parse_magazine_list(md)


def fetch_rss(url, source, include_content=False, fetch_page_fallback=True):
    try:
        req = urllib.request.Request(url, headers=RSS_HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_data = resp.read()
    except Exception as e:
        print(f'  Error {source}: {e}')
        return []

    articles = []
    seen = set()
    try:
        root = ET.fromstring(xml_data.lstrip())
        for item in root.iter('item'):
            title = ''
            link = ''
            pub_date = ''
            content = ''
            description = ''

            title_el = item.find('title')
            if title_el is not None and title_el.text:
                title = unescape(title_el.text.strip())

            link_el = item.find('link')
            if link_el is not None and link_el.text:
                link = link_el.text.strip()

            pub_iso = ''
            pub_el = item.find('pubDate')
            if pub_el is not None and pub_el.text:
                try:
                    dt = datetime.strptime(pub_el.text.strip(),
                                          '%a, %d %b %Y %H:%M:%S %z')
                    pub_date = dt.strftime('%Y-%m-%d')
                    pub_iso = dt.isoformat()
                except:
                    pub_date = pub_el.text.strip()[:10]
                    pub_iso = pub_el.text.strip()

            content_el = item.find('{http://purl.org/rss/1.0/modules/content/}encoded')
            if content_el is None:
                content_el = item.find('{http://wellformedweb.org/CommentAPI/}encoded')
            if content_el is None:
                content_el = item.find('content:encoded')
            if content_el is not None and content_el.text:
                content = content_el.text.strip()
            else:
                desc_el = item.find('description')
                if desc_el is not None and desc_el.text:
                    content = desc_el.text.strip()

            if not title or not link:
                continue

            key = re.sub(r'[^a-z0-9]', '', title.lower())[:40]
            if key in seen:
                continue
            seen.add(key)

            thumb = ''
            for tm in re.finditer(r'<img[^>]+src="([^"]+)"', content):
                url_img = tm.group(1)
                if 'facebook.com' not in url_img and 'google' not in url_img and 'tracking' not in url_img:
                    thumb = url_img
                    break

            if not thumb and link and fetch_page_fallback:
                try:
                    req2 = urllib.request.Request(link, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req2, timeout=10) as resp2:
                        html2 = resp2.read().decode('utf-8', errors='ignore')
                    for tm2 in re.finditer(r'<img[^>]+src="([^"]+)"', html2):
                        url_img2 = tm2.group(1)
                        if 'facebook.com' not in url_img2 and 'google' not in url_img2 and 'tracking' not in url_img2:
                            thumb = url_img2
                            break
                except Exception:
                    pass

            excerpt = re.sub(r'<[^>]+>', '', content)[:300]
            excerpt = unescape(re.sub(r'\s+', ' ', excerpt).strip())

            article = {
                '_source': source,
                'title': title,
                'link': link,
                'date': pub_date,
                '_parsedDate': pub_iso or pub_date,
                'thumbnail': thumb,
                'excerpt': excerpt
            }
            if include_content:
                article['content'] = content
            articles.append(article)
    except ET.ParseError as e:
        print(f'  Error parsing RSS {source}: {e}')

    return articles


def fetch_rss_multi(urls, source, **kwargs):
    articles = []
    seen = set()
    for url in urls:
        for a in fetch_rss(url, source, **kwargs):
            key = re.sub(r'[^a-z0-9]', '', a['title'].lower())[:40]
            if key in seen:
                continue
            seen.add(key)
            articles.append(a)
    return articles


def fetch_booooooom():
    return fetch_rss(BOOM_URL, 'booooooom')


def fetch_tpj():
    return fetch_rss_multi(TPJ_URLS, 'tpj', include_content=True, fetch_page_fallback=False)


def fetch_swan():
    return fetch_rss(SWAN_URL, 'swan')


def fetch_huck():
    return fetch_rss(HUCK_URL, 'huck', include_content=True, fetch_page_fallback=False)


def fetch_lensculture():
    return fetch_rss(LENSCULTURE_URL, 'lensculture', fetch_page_fallback=False)


def fetch_odlp():
    return fetch_rss(ODLP_URL, 'odlp', fetch_page_fallback=False)


def fetch_magnum():
    return scrape_magnum()


def fetch_shootitwithfilm():
    try:
        req = urllib.request.Request(SHOOTIT_WP_API, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=20) as resp:
            posts = json.loads(resp.read().decode('utf-8'))
        items = []
        for p in posts:
            thumb = ''
            try:
                thumb = p.get('_embedded', {}).get('wp:featuredmedia', [{}])[0].get('source_url', '')
            except Exception:
                thumb = ''
            items.append({
                '_source': 'shootitwithfilm',
                '_id': str(p.get('id') or p.get('link')),
                'title': p.get('title', {}).get('rendered', ''),
                'link': p.get('link', ''),
                'date': p.get('date', '')[:10],
                '_parsedDate': p.get('date', ''),
                'thumbnail': thumb,
                'content': p.get('content', {}).get('rendered', ''),
                'excerpt': p.get('excerpt', {}).get('rendered', ''),
            })
        if items:
            return items
    except Exception as e:
        print(f'     error fetch_shootitwithfilm (WP API): {e}')
    return fetch_rss(SHOOTIT_URL, 'shootitwithfilm', fetch_page_fallback=False)


def load_previous_items(filename):
    try:
        with open(os.path.join(DIR, filename)) as f:
            old = json.load(f).get('items', [])
        if old:
            print(f'     scrape vacío → conservando {len(old)} previos de {filename}')
        return old
    except Exception:
        return []


def load_article_cache(filename):
    try:
        with open(os.path.join(DIR, filename)) as f:
            return json.load(f).get('articles', {})
    except Exception:
        return {}


def update_article_cache(filename, items, scrape_fn):
    cache = load_article_cache(filename)
    new = 0
    attempts = 0
    for item in items:
        url = item.get('link')
        if not url or url in cache:
            continue
        if attempts:
            time.sleep(7)
        attempts += 1
        data = scrape_fn(url)
        if data and data.get('status') == 'ok':
            cache[url] = data
            new += 1
            print(f'    + {url.split("/")[-1][:50]}')
        else:
            print(f'    - error {url.split("/")[-1][:50]}')
    if new:
        with open(os.path.join(DIR, filename), 'w') as f:
            json.dump({'updated': date.today().isoformat(), 'articles': cache}, f, ensure_ascii=False)
    return new


def purge_bad_articles(filename):
    cache = load_article_cache(filename)
    bad = [url for url, data in cache.items()
           if isinstance(data, dict) and 'Rate limit exceeded' in str(data.get('content', ''))]
    if bad:
        for url in bad:
            del cache[url]
        with open(os.path.join(DIR, filename), 'w') as f:
            json.dump({'updated': date.today().isoformat(), 'articles': cache}, f, ensure_ascii=False)
        print(f'    {len(bad)} artículos con error purgados de {filename}')
    return len(bad)


def update_lomography_articles(items):
    return update_article_cache('lomography_articles.json', items,
                                lambda url: scrape_lomography_article(url, resolve_profiles=False))


def update_booooooom_articles(items):
    return update_article_cache('booooooom_articles.json', items, scrape_booooooom_article)


def update_swan_articles(items):
    return update_article_cache('swan_articles.json', items, scrape_swan_article)


def update_lensculture_articles(items):
    return update_article_cache('lensculture_articles.json', items, scrape_lensculture_article)


def update_odlp_articles(items):
    return update_article_cache('odlp_articles.json', items, scrape_odlp_article)


def update_magnum_articles(items):
    return update_article_cache('magnum_articles.json', items, scrape_magnum_article)


def main():
    parser = argparse.ArgumentParser(description='Genera datos estáticos (feeds + caches de artículos).')
    parser.add_argument('--keep-lomo', action='store_true',
                        help='Reutiliza lomography.json sin scrapear la revista.')
    args = parser.parse_args()

    ts = date.today().isoformat()
    print(f'[{ts}] Generando datos estáticos...')

    print('  1. Colossal...')
    colossal = fetch_colossal()
    print(f'     {len(colossal)} artículos')

    print('  2. Lomography...')
    if args.keep_lomo:
        lomo = load_previous_items('lomography.json')
        print(f'     {len(lomo)} artículos (modo ahorro: sin refrescar Lomography)')
    else:
        lomo = fetch_lomography()
        if not lomo:
            lomo = load_previous_items('lomography.json')
        print(f'     {len(lomo)} artículos')

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

    print('  7. Lomography articles (cache GitHub Pages)...')
    purge_bad_articles('lomography_articles.json')
    new_articles = update_lomography_articles(lomo)
    print(f'     {new_articles} nuevos | {len(load_article_cache("lomography_articles.json"))} en cache')

    print('  8. Booooooom articles (cache GitHub Pages)...')
    purge_bad_articles('booooooom_articles.json')
    new_boom_articles = update_booooooom_articles(boom)
    print(f'     {new_boom_articles} nuevos | {len(load_article_cache("booooooom_articles.json"))} en cache')

    print('  9. Swann articles (cache GitHub Pages)...')
    purge_bad_articles('swan_articles.json')
    new_swan_articles = update_swan_articles(swan)
    swan_cache = load_article_cache('swan_articles.json')
    print(f'     {new_swan_articles} nuevos | {len(swan_cache)} en cache')

    for item in swan:
        data = swan_cache.get(item.get('link'))
        if isinstance(data, dict) and data.get('thumbnail'):
            item['thumbnail'] = data['thumbnail']

    print('  9b. LensCulture articles (cache GitHub Pages)...')
    purge_bad_articles('lensculture_articles.json')
    new_lens_articles = update_lensculture_articles(lensculture[:10])
    lens_cache = load_article_cache('lensculture_articles.json')
    print(f'     {new_lens_articles} nuevos | {len(lens_cache)} en cache')

    for item in lensculture:
        data = lens_cache.get(item.get('link'))
        if isinstance(data, dict) and data.get('thumbnail'):
            item['thumbnail'] = data['thumbnail']

    print('  9c. L\'Œil de la Photographie articles (cache GitHub Pages)...')
    purge_bad_articles('odlp_articles.json')
    new_odlp_articles = update_odlp_articles(odlp[:10])
    odlp_cache = load_article_cache('odlp_articles.json')
    print(f'     {new_odlp_articles} nuevos | {len(odlp_cache)} en cache')

    for item in odlp:
        data = odlp_cache.get(item.get('link'))
        if isinstance(data, dict) and data.get('thumbnail'):
            item['thumbnail'] = data['thumbnail']

    print('  9d. Magnum Photos articles (cache GitHub Pages)...')
    purge_bad_articles('magnum_articles.json')
    new_magnum_articles = update_magnum_articles(magnum[:10])
    magnum_cache = load_article_cache('magnum_articles.json')
    print(f'     {new_magnum_articles} nuevos | {len(magnum_cache)} en cache')

    for item in magnum:
        data = magnum_cache.get(item.get('link'))
        if isinstance(data, dict) and data.get('thumbnail'):
            item['thumbnail'] = data['thumbnail']

    all_entries = sorted(colossal + lomo + boom + tpj + swan + huck + lensculture + odlp + magnum + shootit,
                         key=lambda x: x.get('_parsedDate') or x.get('date') or '',
                         reverse=True)

    with open(os.path.join(DIR, 'lomography.json'), 'w') as f:
        json.dump({'items': lomo, 'count': len(lomo), 'updated': ts}, f)

    with open(os.path.join(DIR, 'booooooom.json'), 'w') as f:
        json.dump({'items': boom, 'count': len(boom), 'updated': ts}, f)

    with open(os.path.join(DIR, 'tpj.json'), 'w') as f:
        json.dump({'items': tpj, 'count': len(tpj), 'updated': ts}, f)

    with open(os.path.join(DIR, 'swan.json'), 'w') as f:
        json.dump({'items': swan, 'count': len(swan), 'updated': ts}, f)

    with open(os.path.join(DIR, 'huck.json'), 'w') as f:
        json.dump({'items': huck, 'count': len(huck), 'updated': ts}, f)

    with open(os.path.join(DIR, 'lensculture.json'), 'w') as f:
        json.dump({'items': lensculture, 'count': len(lensculture), 'updated': ts}, f)

    with open(os.path.join(DIR, 'odlp.json'), 'w') as f:
        json.dump({'items': odlp, 'count': len(odlp), 'updated': ts}, f)

    with open(os.path.join(DIR, 'magnum.json'), 'w') as f:
        json.dump({'items': magnum, 'count': len(magnum), 'updated': ts}, f)

    with open(os.path.join(DIR, 'shootitwithfilm.json'), 'w') as f:
        json.dump({'items': shootit, 'count': len(shootit), 'updated': ts}, f)

    with open(os.path.join(DIR, 'feeds.json'), 'w') as f:
        json.dump({'items': all_entries, 'count': len(all_entries), 'updated': ts}, f)

    print(f'  Guardado: lomography.json, booooooom.json, tpj.json, swan.json, huck.json, lensculture.json, odlp.json, magnum.json, feeds.json ({len(all_entries)} total)')

    print('  10. Subiendo a GitHub...')
    try:
        result = subprocess.run(
            ['git', 'add', 'lomography.json', 'booooooom.json', 'tpj.json', 'swan.json', 'huck.json', 'lensculture.json', 'odlp.json', 'magnum.json', 'shootitwithfilm.json', 'feeds.json',
             'lomography_articles.json', 'booooooom_articles.json', 'swan_articles.json', 'lensculture_articles.json', 'odlp_articles.json', 'magnum_articles.json'],
            capture_output=True, text=True, cwd=DIR
        )
        result = subprocess.run(
            ['git', 'commit', '-m', f'chore: update static feeds {ts}'],
            capture_output=True, text=True, cwd=DIR
        )
        if 'nothing to commit' in result.stdout:
            print('     Sin cambios')
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


if __name__ == '__main__':
    main()
