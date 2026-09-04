import html
import http.server
import json
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request

PORT = 8080
DIR = os.path.dirname(os.path.abspath(__file__))
CACHE = {'data': None, 'time': 0, 'ttl': 120}


def is_rate_limited(text):
    return 'rate limit exceeded' in (text or '').lower()


JINA_HEADER_RE = re.compile(r'^Title:.*?\nMarkdown Content:\n', re.S)


def strip_jina_header(md):
    return JINA_HEADER_RE.sub('', md, count=1)


def get_jina_key():
    # 1. Intentar desde variable de entorno
    key = os.environ.get('JINA_API_KEY')
    if key:
        return key
    # 2. Intentar desde config.json local
    try:
        config_path = os.path.join(DIR, 'config.json')
        if os.path.exists(config_path):
            with open(config_path) as f:
                return json.load(f).get('JINA_API_KEY')
    except Exception:
        pass
    return None


def fetch_markdown(url, timeout=60, selector=None):
    headers = {'User-Agent': 'Mozilla/5.0', 'X-Respond-With': 'markdown'}
    jina_key = get_jina_key()
    if jina_key:
        headers['Authorization'] = f'Bearer {jina_key}'
    if selector:
        headers['X-Target-Selector'] = selector
    try:
        req = urllib.request.Request('https://r.jina.ai/' + url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except urllib.error.HTTPError as e:
        # Si la API key está agotada (402 Payment Required / Insufficient Balance), reintentar gratis sin key
        if e.code == 402 or 'Authorization' in headers:
            try:
                headers_free = {'User-Agent': 'Mozilla/5.0', 'X-Respond-With': 'markdown'}
                if selector:
                    headers_free['X-Target-Selector'] = selector
                req_free = urllib.request.Request('https://r.jina.ai/' + url, headers=headers_free)
                with urllib.request.urlopen(req_free, timeout=timeout) as resp_free:
                    return resp_free.read().decode('utf-8', errors='ignore')
            except Exception:
                return None
        return None
    except Exception:
        return None


def is_bot_challenge(md):
    return ('Performing security verification' in md or
            'Just a moment...' in md or
            'This website uses a security service' in md)


def trim_lomo_body(md):
    # Jina devuelve la página completa: navegación + aviso de cookies antes del H1.
    m = re.search(r'^# [^\n]+$', md, re.MULTILINE)
    if m:
        md = md[m.end():]
    md = re.sub(r'^\s*(\[\d+\]\([^)]*\)\s*)+', '', md)
    return md


def firecrawl_scrape(url, timeout=60, retries=2, selector=None):
    # Extracción vía Jina Reader (renderiza JS, devuelve markdown limpio y sin cuotas).
    for attempt in range(retries + 1):
        md = fetch_markdown(url, timeout=timeout, selector=selector)
        if md and not is_bot_challenge(md) and not is_rate_limited(md):
            return strip_jina_header(md)
        if attempt < retries:
            time.sleep(3)
    return None

def parse_magazine_list(md):
    md = strip_jina_header(md or '')
    articles = []
    seen = set()

    matches = list(re.finditer(
        r'\[([^\]]+)\]\((https://www\.lomography\.com/magazine/\d+-[^)]+)\)', md))
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        url = m.group(2).strip()
        if re.fullmatch(r'[\d\W_]+', title) or len(title) < 8:
            continue
        if url in seen:
            continue
        seen.add(url)

        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        block = md[m.start():end]

        date = ''
        dm = re.search(r'\b(20\d{2}-\d{2}-\d{2})\b', block)
        if dm:
            date = dm.group(1)
        else:
            date = resolve_lomo_article_date(url) or ''

        thumb = ''
        tm = re.search(r'!\[[^\]]*\]\(([^)]+)\)', block)
        if tm:
            thumb = tm.group(1)

        excerpt_lines = []
        for line in block.split('\n'):
            s = line.strip()
            if not s or s.startswith('[') or s.startswith('![') or s.startswith('#') \
               or s.startswith('*') or s.startswith('http') or s.startswith('on ') \
               or s.startswith('|') or s.lower().startswith('written by'):
                continue
            excerpt_lines.append(s)
        excerpt = ' '.join(excerpt_lines)
        excerpt = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', excerpt)
        excerpt = re.sub(r'\[\d+\]\([^)]+\)', '', excerpt).strip()

        articles.append({
            '_source': 'lomography',
            'title': title,
            'link': url,
            'date': date,
            'thumbnail': thumb,
            'excerpt': excerpt
        })

    return articles


def parse_lomo_articles(md):
    return parse_magazine_list(md)

LOMO_ARTICLE_DATE_CACHE = {}

def resolve_lomo_article_date(url):
    if url in LOMO_ARTICLE_DATE_CACHE:
        return LOMO_ARTICLE_DATE_CACHE[url]
    md = firecrawl_scrape(url, timeout=60)
    if not md:
        LOMO_ARTICLE_DATE_CACHE[url] = None
        return None
    idx = re.search(r'## (?:One|\d+) Likes?|## No Comments|Please login to leave a comment|More Interesting Articles', md)
    clean = md[:idx.start()] if idx else md
    m = re.search(r'\bwritten by\b[^\n]*?\bon\s+(\d{4}-\d{2}-\d{2})', clean, re.IGNORECASE)
    if m:
        LOMO_ARTICLE_DATE_CACHE[url] = m.group(1)
        return m.group(1)
    m = re.search(r'\b(20\d{2}-\d{2}-\d{2})\b', clean)
    LOMO_ARTICLE_DATE_CACHE[url] = m.group(1) if m else None
    return LOMO_ARTICLE_DATE_CACHE[url]

def scrape_lomography():
    now = time.time()
    if CACHE['data'] and now - CACHE['time'] < CACHE['ttl']:
        return CACHE['data']
    md = firecrawl_scrape('https://www.lomography.com/magazine/', timeout=60)
    articles = parse_lomo_articles(md or '')
    CACHE['data'] = articles
    CACHE['time'] = now
    return articles

LENSCULTURE_CACHE = {'data': None, 'time': 0, 'ttl': 120}

def scrape_lensculture():
    now = time.time()
    if LENSCULTURE_CACHE['data'] and now - LENSCULTURE_CACHE['time'] < LENSCULTURE_CACHE['ttl']:
        return LENSCULTURE_CACHE['data']
    url = 'https://www.lensculture.com/feeds/feed.rss'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_data = resp.read()
        import xml.etree.ElementTree as ET
        from html import unescape
        from datetime import datetime
        root = ET.fromstring(xml_data.lstrip())
        articles = []
        for item in root.iter('item'):
            title = ''
            link = ''
            pub_date = ''
            title_el = item.find('title')
            if title_el is not None and title_el.text:
                title = unescape(title_el.text.strip())
            link_el = item.find('link')
            if link_el is not None and link_el.text:
                link = link_el.text.strip()
            pub_el = item.find('pubDate')
            if pub_el is not None and pub_el.text:
                try:
                    dt = datetime.strptime(pub_el.text.strip()[:25].strip(), '%a, %d %b %Y %H:%M:%S')
                    pub_date = dt.strftime('%Y-%m-%d')
                except Exception:
                    pub_date = ''
            articles.append({
                '_source': 'lensculture',
                'title': title,
                'link': link,
                'date': pub_date,
                'excerpt': ''
            })
        LENSCULTURE_CACHE['data'] = articles
        LENSCULTURE_CACHE['time'] = now
        return articles
    except Exception as e:
        print('Error scrape_lensculture:', e)
        return []

ODLP_CACHE = {'data': None, 'time': 0, 'ttl': 120}

def scrape_odlp():
    now = time.time()
    if ODLP_CACHE['data'] and now - ODLP_CACHE['time'] < ODLP_CACHE['ttl']:
        return ODLP_CACHE['data']
    url = 'https://loeildelaphotographie.com/en/feed/'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_data = resp.read()
        import xml.etree.ElementTree as ET
        from html import unescape
        from datetime import datetime
        root = ET.fromstring(xml_data.lstrip())
        articles = []
        for item in root.iter('item'):
            title = ''
            link = ''
            pub_date = ''
            title_el = item.find('title')
            if title_el is not None and title_el.text:
                title = unescape(title_el.text.strip())
            link_el = item.find('link')
            if link_el is not None and link_el.text:
                link = link_el.text.strip()
            pub_el = item.find('pubDate')
            if pub_el is not None and pub_el.text:
                try:
                    dt = datetime.strptime(pub_el.text.strip()[:25].strip(), '%a, %d %b %Y %H:%M:%S')
                    pub_date = dt.strftime('%Y-%m-%d')
                except Exception:
                    pub_date = ''
            articles.append({
                '_source': 'odlp',
                'title': title,
                'link': link,
                'date': pub_date,
                'excerpt': ''
            })
        ODLP_CACHE['data'] = articles
        ODLP_CACHE['time'] = now
        return articles
    except Exception as e:
        print('Error scrape_odlp:', e)
        return []

MAGNUM_CACHE = {'data': None, 'time': 0, 'ttl': 120}

def scrape_magnum():
    now = time.time()
    if MAGNUM_CACHE['data'] and now - MAGNUM_CACHE['time'] < MAGNUM_CACHE['ttl']:
        return MAGNUM_CACHE['data']
    url = 'https://www.magnumphotos.com/wp-json/wp/v2/posts?per_page=30'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        articles = []
        for post in data:
            from html import unescape
            from datetime import datetime
            title = unescape(post.get('title', {}).get('rendered', '').strip())
            link = post.get('link', '').strip()
            date_str = post.get('date', '')
            pub_date = ''
            if date_str:
                try:
                    dt = datetime.strptime(date_str[:10], '%Y-%m-%d')
                    pub_date = dt.strftime('%Y-%m-%d')
                except Exception:
                    pub_date = date_str[:10]
            articles.append({
                '_source': 'magnum',
                'title': title,
                'link': link,
                'date': pub_date,
                'excerpt': ''
            })
        MAGNUM_CACHE['data'] = articles
        MAGNUM_CACHE['time'] = now
        return articles
    except Exception as e:
        print('Error scrape_magnum:', e)
        return []

def inline_to_html(text):
    # 1. Procesar imágenes enlazadas: [![alt](img_url)](link_url)
    text = re.sub(
        r'\[!\[([^\]]*)\]\((https?://[^)\s]+)\)\]\((https?://[^)\s]+)\)',
        r'<a href="\3" target="_blank" rel="noopener"><img src="\2" alt="\1" loading="lazy"></a>',
        text
    )

    # 2. Procesar imágenes normales de markdown: ![alt](img_url)
    text = re.sub(
        r'!\[([^\]]*)\]\((https?://[^)\s]+)\)',
        r'<img src="\2" alt="\1" loading="lazy">',
        text
    )

    # 3. Procesar enlaces y estilos
    urls = []

    def _save_url(m):
        urls.append(m.group(0))
        return f'\x00{len(urls) - 1}\x00'

    def _restore(i):
        return urls[int(i)]

    text = re.sub(r'https?://[^)\s<>"]+', _save_url, text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'_\*([^*]+)\*_', r'<em>\1</em>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'_(.+?)_', r'<em>\1</em>', text)
    text = re.sub(r'\[([^\]]+)\]\(\x00(\d+)\x00\)',
                  lambda m: f'<a href="{_restore(m.group(2))}" target="_blank" rel="noopener">{m.group(1)}</a>', text)
    text = re.sub(r'\x00(\d+)\x00', lambda m: _restore(m.group(1)), text)
    return text

def md_to_html(md):
    lines = md.split('\n')
    result = []
    in_list = False
    for line in lines:
        s = line.strip()
        if not s:
            if in_list:
                result.append('</ul>')
                in_list = False
            continue
        if re.match(r'^-{3,}$', s) or re.match(r'^\*{3,}$', s):
            if in_list:
                result.append('</ul>')
                in_list = False
            result.append('<hr>')
            continue
        hm = re.match(r'^(#{1,3})\s+(.+)$', s)
        if hm:
            if in_list:
                result.append('</ul>')
                in_list = False
            result.append(f'<h{len(hm.group(1))}>{inline_to_html(hm.group(2))}</h{len(hm.group(1))}>')
            continue
        if s.startswith('- ') or s.startswith('* '):
            if not in_list:
                result.append('<ul>')
                in_list = True
            result.append(f'<li>{inline_to_html(s[2:])}</li>')
            continue
        if in_list:
            result.append('</ul>')
            in_list = False

        html_line = inline_to_html(s)
        # Si la línea consiste exclusivamente en etiquetas <img> o <a href><img...>, no meter en <p> redundante
        if re.match(r'^(?:<(?:img|a|picture|figure)[^>]*>.*</(?:a|picture|figure)>|<img[^>]*>|\s*)+$', html_line):
            result.append(html_line)
        else:
            result.append(f'<p>{html_line}</p>')
    if in_list:
        result.append('</ul>')
    return '\n'.join(result)

SOCIAL_RE = re.compile(
    r'\[([^\]]+)\]\((https://(?:www\.)?(?:instagram\.com|x\.com|twitter\.com|facebook\.com|flickr\.com|tiktok\.com|youtube\.com|bsky\.app|threads\.net)[^)]+)\)',
    re.IGNORECASE
)

LOMO_PROFILE_CACHE = {}

def resolve_lomo_profile(url):
    now = time.time()
    if url in LOMO_PROFILE_CACHE and now - LOMO_PROFILE_CACHE[url]['time'] < 3600:
        return LOMO_PROFILE_CACHE[url]['data']
    md = firecrawl_scrape(url, timeout=30)
    if not md:
        LOMO_PROFILE_CACHE[url] = {'data': None, 'time': now}
        return None
    idx = re.search(r'## (?:One|\d+) Likes?|## No Comments|Please login to leave a comment|More Interesting Articles', md)
    if idx:
        md = md[:idx.start()]
    links = SOCIAL_RE.findall(md)
    links.sort(key=lambda x: (0 if 'instagram.com' in x[1].lower() else 1))
    if links:
        social = {'name': links[0][0], 'url': links[0][1]}
        LOMO_PROFILE_CACHE[url] = {'data': social, 'time': now}
        return social
    LOMO_PROFILE_CACHE[url] = {'data': None, 'time': now}
    return None

ARTICLE_CACHE = {}
BOOM_ARTICLE_CACHE = {}

def boom_credit_platform(raw_name, url):
    h = url.lower()
    platforms = {
        'instagram.com': 'instagram', 'twitter.com': 'x', 'x.com': 'x',
        'facebook.com': 'facebook', 'flickr.com': 'flickr', 'vimeo.com': 'vimeo',
        'youtube.com': 'youtube', 'youtu.be': 'youtube', 'bsky.app': 'bluesky',
        'tiktok.com': 'tiktok', 'threads.net': 'threads',
    }
    for frag, name in platforms.items():
        if frag in h:
            return name
    m = re.search(r' on (\w+)$', raw_name, re.I)
    if m:
        return {'instagram': 'instagram', 'twitter': 'x', 'x': 'x'}.get(m.group(1).lower(), m.group(1).lower())
    return 'web'


def scrape_booooooom_article(url):
    now = time.time()
    if url in BOOM_ARTICLE_CACHE and now - BOOM_ARTICLE_CACHE[url]['time'] < 300:
        return BOOM_ARTICLE_CACHE[url]['data']
    md = firecrawl_scrape(url, timeout=60, selector='.post-content')
    if md and len(md.strip()) < 500:
        md = firecrawl_scrape(url, timeout=60)
    if not md:
        return None

    md = md.replace('\u2060', '').replace('\u200b', '')
    md = re.sub(r'^\[Submit\][^\n]*\n?', '', md)

    # Recorta promos / footer / related articles en cuanto empiezan
    cut = len(md)
    for pat in (
        r'\[!\[[^\]]*\]\([^)]*\)\]\(https?://(?:www\.|shop\.)?booooooom\.com/',
        r'A Letter From the Founder',
        r"Tomorrow['’]s Talent \d",
        r'Join our Secret Email Club',
        r'\*\*Related Articles\*\*',
        r'Twitter Widget Iframe',
        r'^#{1,6}\s+',
    ):
        m = re.search(pat, md, re.MULTILINE)
        if m and m.start() < cut:
            cut = m.start()
    md = md[:cut].strip()

    images = []
    seen_urls = set()
    for im in re.finditer(r'!\[([^\]]*)\]\(([^)]+)\)', md):
        img_url = im.group(2).strip()
        if img_url in seen_urls:
            continue
        seen_urls.add(img_url)
        images.append({'url': img_url, 'alt': im.group(1)})

    credits = []
    seen_names = set()
    credit_pat = re.compile(r"(?:['’]s (?:Website|Portfolio|Site|Blog))|(?: on (?:Instagram|Twitter|Facebook|Flickr|Vimeo|YouTube|Bluesky|TikTok))$", re.I)
    for cm in re.finditer(r'^_?\[([^\]]+)\]\((https?://[^)]+)\)_?[ \t]*$', md, re.MULTILINE):
        raw_name = cm.group(1).strip().strip('_')
        url = cm.group(2).strip()
        if not credit_pat.search(raw_name):
            continue
        name = re.sub(r"[’']s (?:Website|Portfolio|Site|Blog)$", '', raw_name, flags=re.I)
        name = re.sub(r'\s+on\s+(?:Instagram|Twitter|Facebook|Flickr|Vimeo|YouTube|Bluesky|TikTok)$', '', name, flags=re.I).strip()
        if not name or name.lower() in seen_names:
            continue
        seen_names.add(name.lower())
        credits.append({'name': name, 'url': url, 'platform': boom_credit_platform(raw_name, url)})

    # Los créditos se muestran aparte en el frontend, fuera del contenido
    content_md = re.sub(r'^_?\[[^\]]+\]\((https?://[^)]+)\)_?[ \t]*\n?', '', md, flags=re.MULTILINE)

    data = {'status': 'ok', 'content': md_to_html(content_md), 'images': images, 'credits': credits}
    BOOM_ARTICLE_CACHE[url] = {'data': data, 'time': now}
    return data

LOMO_CREDIT_BLACKLIST = {'random home', 'search homes', 'home', 'my lomohome',
                         'lomography', 'shop', 'photos', 'magazine', 'sign up',
                         'log in', 'login', 'logout', 'cart', 'about', 'blog',
                         'help', 'contact', 'community', 'explore', 'profile',
                         'settings', 'account', 'deals', 'store locator',
                         'start a shop', 'wishlist', 'track order', 'privacy policy',
                         'terms of use', 'newsletter'}


def clean_lomo_credit_name(name):
    n = (name or '').strip().strip('@').strip()
    if not n or len(n) < 2:
        return None
    if n.lower() in LOMO_CREDIT_BLACKLIST:
        return None
    if re.search(r'\s', n):
        return None
    return n


def scrape_lomography_article(url, resolve_profiles=True):
    now = time.time()
    if url in ARTICLE_CACHE and now - ARTICLE_CACHE[url]['time'] < 300:
        return ARTICLE_CACHE[url]['data']
    md = firecrawl_scrape(url, timeout=60)
    if not md:
        return None
    idx = re.search(r'## (?:One|\d+) Likes?|## No Comments|Please login to leave a comment|More Interesting Articles', md)
    clean_md = md[:idx.start()] if idx else md
    clean_md = trim_lomo_body(clean_md)
    img_list = []
    seen_urls = set()
    for m in re.finditer(r'!\[([^\]]*)\]\((https?://[^\s\)]+)\)', clean_md):
        u = m.group(2)
        if u not in seen_urls and 'avatar' not in u.lower() and 'icon' not in u.lower():
            seen_urls.add(u)
            img_list.append({'url': u, 'alt': m.group(1)})
    for m in re.finditer(r'<img[^>]+src=["\'](https?://[^"\']+)["\']', clean_md, re.I):
        u = m.group(1)
        if u not in seen_urls and 'avatar' not in u.lower() and 'icon' not in u.lower():
            seen_urls.add(u)
            img_list.append({'url': u, 'alt': ''})
    images = img_list
    body_md = re.split(r'\nwritten by\b', clean_md, maxsplit=1)[0] if re.search(r'\nwritten by\b', clean_md) else clean_md
    content = md_to_html(body_md)
    credits = []
    seen_names = set()
    for cm in re.finditer(r'\[([^\]]+)\]\((https://www\.lomography\.com/homes/[^)]+)\)', clean_md):
        name = clean_lomo_credit_name(cm.group(1))
        if not name:
            continue
        if name.lower() in seen_names:
            continue
        seen_names.add(name.lower())
        if resolve_profiles:
            social = resolve_lomo_profile(cm.group(2))
            if social:
                credits.append({'name': name, 'url': social['url']})
                continue
        credits.append({'name': name, 'url': cm.group(2)})
    data = {'status': 'ok', 'content': content, 'images': images, 'credits': credits}
    ARTICLE_CACHE[url] = {'data': data, 'time': now}
    return data


LENSCULTURE_ARTICLE_CACHE = {}

def scrape_lensculture_article(url):
    now = time.time()
    if url in LENSCULTURE_ARTICLE_CACHE and now - LENSCULTURE_ARTICLE_CACHE[url]['time'] < 300:
        return LENSCULTURE_ARTICLE_CACHE[url]['data']
    md = firecrawl_scrape(url, timeout=60)
    if not md:
        return None
    
    m = re.search(r'^#\s+\w+', md, re.MULTILINE)
    content_md = md[m.start():] if m else md
    
    cut = len(content_md)
    pats = [
        r'\[(?:Feature|Book review|Interview|Article|Review|Project|Photo essay|Gallery)\s+!\[',
        r'See more articles',
        r'## Get our weekly newsletter',
        r'## Get our free newsletter',
        r'#### Stay connected',
        r'\[!\[Image \d+:[^\]]*\]\(https://assets\.lensculture\.com/static/'
    ]
    for pat in pats:
        mm = re.search(pat, content_md, re.MULTILINE)
        if mm and mm.start() < cut:
            cut = mm.start()
    content_md = content_md[:cut].strip()
    
    # Limpieza de artefactos de extracción en LensCulture
    content_md = re.sub(r'!\[Image \d+:\s*', '![', content_md)
    content_md = re.sub(r'\[\]\([^)]+\)', '', content_md)
    content_md = re.sub(r'\[!\[[^\]]*\]\([^)]+/thumb\)\s*[^\]]*\]\(https://www\.lensculture\.com/[^)]+\)', '', content_md)
    
    # Deduplicar bloques de texto idénticos (p. ej. título y subtítulo duplicados al inicio)
    parts = [p.strip() for p in content_md.split('\n\n') if p.strip()]
    deduped_parts = []
    for p in parts:
        if p in deduped_parts and len(p) > 20:
            continue
        deduped_parts.append(p)
    content_md = '\n\n'.join(deduped_parts)
    
    images = [{'url': im.group(2), 'alt': im.group(1)} for im in re.finditer(r'!\[([^\]]*)\]\(([^)]+)\)', content_md)]
    images = [img for img in images if 'logo' not in img['url'].lower() and 'menu-icon' not in img['url'].lower()]
    
    content = md_to_html(content_md)
    thumbnail = images[0]['url'] if images else ''
    data = {'status': 'ok', 'content': content, 'images': images, 'credits': [], 'thumbnail': thumbnail}
    LENSCULTURE_ARTICLE_CACHE[url] = {'data': data, 'time': now}
    return data


ODLP_ARTICLE_CACHE = {}

def scrape_odlp_article(url):
    now = time.time()
    if url in ODLP_ARTICLE_CACHE and now - ODLP_ARTICLE_CACHE[url]['time'] < 300:
        return ODLP_ARTICLE_CACHE[url]['data']
    md = firecrawl_scrape(url, timeout=60)
    if not md:
        return None
    
    idx = md.find('Printer Friendly, PDF & Email')
    if idx != -1:
        end_idx = md.find(')', idx)
        content_md = md[end_idx+1:] if end_idx != -1 else md[idx+35:]
    else:
        m = re.search(r'loeildelaphotographie\.com/en/author/[^)]+\)', md)
        content_md = md[m.end():] if m else md
    
    cut = len(content_md)
    pats = [
        r'\*\s+\[Share\]\(https://www\.facebook\.com/sharer',
        r'POST ID:',
        r'Subscribe now for full access to The Eye of Photography!',
        r'## Today\'s headlines',
        r'## Today’s headlines'
    ]
    for pat in pats:
        mm = re.search(pat, content_md, re.MULTILINE)
        if mm and mm.start() < cut:
            cut = mm.start()
    content_md = content_md[:cut].strip()
    images = [{'url': im.group(2), 'alt': im.group(1)} for im in re.finditer(r'!\[([^\]]*)\]\(([^)]+)\)', md)]
    images = [img for img in images if 'loeildelaphotographie.com/wp-content/uploads/' in img['url']]
    
    content = md_to_html(content_md)
    thumbnail = images[0]['url'] if images else ''
    data = {'status': 'ok', 'content': content, 'images': images, 'credits': [], 'thumbnail': thumbnail}
    ODLP_ARTICLE_CACHE[url] = {'data': data, 'time': now}
    return data


MAGNUM_ARTICLE_CACHE = {}


def scrape_magnum_article(url):
    now = time.time()
    if url in MAGNUM_ARTICLE_CACHE and now - MAGNUM_ARTICLE_CACHE[url]['time'] < 300:
        return MAGNUM_ARTICLE_CACHE[url]['data']
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html_data = resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print('Error fetching magnum article:', e)
        return None

    # Título, lead e intro
    title_m = re.search(r'<h1[^>]*>(.*?)</h1>', html_data, re.DOTALL)
    lead_m = re.search(r'class=[\"\'](?:b-story-intro__lead|story-subtitle|story-lead)[\"\'][^>]*>(.*?)</div>', html_data, re.DOTALL)
    
    content_parts = []
    if lead_m:
        lead_txt = html.unescape(re.sub(r'<[^>]+>', '', lead_m.group(1))).strip()
        if lead_txt:
            content_parts.append(f"**{lead_txt}**")

    # Extraer bloques de texto enriquecido (RTE) y citas
    blocks_text = re.findall(r'<(?:div class=[\"\']rte[\"\']|blockquote[^>]*)>(.*?)</(?:div|blockquote)>', html_data, re.DOTALL)
    for block in blocks_text:
        text = block.strip()
        text = re.sub(r'</?p>', '\n\n', text)
        text = re.sub(r'</?strong>', '**', text)
        text = re.sub(r'</?em>', '_', text)
        text = re.sub(r'<a href="([^"]+)"[^>]*>(.*?)</a>', r'[\2](\1)', text)
        text = re.sub(r'<[^>]+>', '', text)
        text = html.unescape(text)
        if text.strip():
            content_parts.append(text.strip())

    content_md = '\n\n'.join([p for p in content_parts if p])
    content = md_to_html(content_md)

    # Imágenes con pies de foto descriptivos y copyright completos de Magnum
    images = []
    blocks_img = re.split(r'class=[\"\'](?:story-big-image|story-grid-image|story-image)', html_data)
    for b in blocks_img[1:]:
        img_match = re.search(r'src=[\"\']([^\"\']+)[\"\']', b)
        if img_match:
            img_url = img_match.group(1)
            cap_match = re.search(r'class=[\"\']b-caption__text[\"\'][^>]*>(.*?)</div>', b, re.DOTALL)
            cred_match = re.search(r'class=[\"\']b-caption__credit[\"\'][^>]*>(.*?)</span>', b, re.DOTALL)
            caption = ''
            if cap_match:
                caption = html.unescape(re.sub(r'<[^>]+>', '', cap_match.group(1))).strip()
            if cred_match:
                credit = html.unescape(re.sub(r'<[^>]+>', '', cred_match.group(1))).strip()
                caption = f"{caption} ({credit})" if caption and credit else (caption or credit)
            images.append({'url': img_url, 'alt': caption, 'caption': caption})

    seen_urls = set()
    unique_images = []
    for img in images:
        if img['url'] not in seen_urls:
            seen_urls.add(img['url'])
            unique_images.append(img)

    thumbnail = unique_images[0]['url'] if unique_images else ''
    data = {'status': 'ok', 'content': content, 'images': unique_images, 'credits': [], 'thumbnail': thumbnail}
    MAGNUM_ARTICLE_CACHE[url] = {'data': data, 'time': now}
    return data


TPJ_ARTICLE_CACHE = {}


def scrape_tpj_article(url):
    now = time.time()
    if url in TPJ_ARTICLE_CACHE and now - TPJ_ARTICLE_CACHE[url]['time'] < 300:
        return TPJ_ARTICLE_CACHE[url]['data']
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html_page = resp.read().decode('utf-8', errors='ignore')

        cover_m = re.search(r'class=[\"\']cover[\"\'][^>]*style=[\"\'][^\"\']*url\((https?[^)]+)\)', html_page)
        cover_img = cover_m.group(1) if cover_m else ''

        by_m = re.search(r'<ul class=[\"\']staff[\"\']>\s*<li>\s*(?:by\s+)?(.*?)</li>', html_page, re.DOTALL)
        author = html.unescape(re.sub(r'<[^>]+>', '', by_m.group(1))).strip() if by_m else ''

        sec_m = re.search(r'<section class=[\"\'](?:essay|interview|feature)[^\"\']*[\"\']>(.*?)(?:<div class=[\"\']footer|<footer)', html_page, re.DOTALL)
        sec_html = sec_m.group(1) if sec_m else html_page

        images = []
        seen = set()
        if cover_img:
            seen.add(cover_img)
            images.append({'url': cover_img, 'alt': 'Cover', 'caption': 'Cover'})

        for im in re.finditer(r'<img[^>]+src=[\"\'](https?://thephotographicjournal\.com/wp-content/uploads/[^\"\']+)[\"\']', sec_html):
            u = im.group(1)
            clean_u = re.sub(r'-\d+x\d+(\.[a-zA-Z]+)$', r'\1', u)
            if clean_u not in seen:
                seen.add(clean_u)
                alt_m = re.search(r'alt=[\"\']([^\"\']*)[\"\']', im.group(0))
                images.append({'url': clean_u, 'alt': alt_m.group(1) if alt_m else '', 'caption': ''})

        credits = []
        if author:
            credits.append({'name': author, 'url': url})
        for sm in re.finditer(r'<a[^>]+href=[\"\'](https?://(?:www\.)?instagram\.com/[^\"\']+)[\"\'][^>]*>(.*?)</a>', sec_html, re.I):
            credits.append({'name': re.sub(r'<[^>]+>', '', sm.group(2)).strip(), 'url': sm.group(1)})

        clean_html = re.sub(r'<script[^>]*>.*?</script>', '', sec_html, flags=re.DOTALL | re.I)
        clean_html = re.sub(r'<style[^>]*>.*?</style>', '', clean_html, flags=re.DOTALL | re.I)
        clean_text = re.sub(r'<[^>]+>', ' ', clean_html)
        clean_text = html.unescape(re.sub(r'\s+', ' ', clean_text).strip())

        thumbnail = images[0]['url'] if images else ''
        data = {
            'status': 'ok',
            'content': clean_html,
            'clean_text': clean_text,
            'images': images,
            'credits': credits,
            'thumbnail': thumbnail,
            'photographer': author
        }
        TPJ_ARTICLE_CACHE[url] = {'data': data, 'time': now}
        return data
    except Exception as e:
        print(f'Error scraping TPJ {url}: {e}')
        return None


SWAN_ARTICLE_CACHE = {}
SWAN_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}


def swan_og_image(url):
    try:
        req = urllib.request.Request(url, headers=SWAN_HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html_page = resp.read().decode('utf-8', errors='ignore')
        m = re.search(r'property="og:image" content="([^"]+)"', html_page)
        return m.group(1) if m else ''
    except Exception:
        return ''


def scrape_swan_article(url):
    now = time.time()
    if url in SWAN_ARTICLE_CACHE and now - SWAN_ARTICLE_CACHE[url]['time'] < 300:
        return SWAN_ARTICLE_CACHE[url]['data']
    md = firecrawl_scrape(url, timeout=60)
    if not md:
        return None

    idx = md.find('### Related Content')
    content_md = md[:idx] if idx != -1 else md
    cut = len(content_md)
    for pat in (
        r'^Subscribe to our',
        r'^Sign [Uu]p',
        r'^Join our',
        r'^Get our',
        r'^Never miss',
        r'^Bid Online',
        r'^Contact Us',
        r'^About Swann',
        r'^View Lots',
        r'^\*\*\*\s*$',
    ):
        mm = re.search(pat, content_md, re.MULTILINE)
        if mm and mm.start() < cut:
            cut = mm.start()
    content_md = content_md[:cut].strip()
    content_md = re.sub(r'!\[[^\]]*\]\(<[^>]*>\)', '', content_md)
    content_md = re.sub(r'(?<!!)\[\]\([^)]*\)', '', content_md)

    images = []
    seen_urls = set()
    for im in re.finditer(r'!\[([^\]]*)\]\(([^)]+)\)', content_md):
        img_url = im.group(2).strip()
        if img_url.startswith('<') or img_url in seen_urls:
            continue
        seen_urls.add(img_url)
        images.append({'url': img_url, 'alt': im.group(1), 'caption': im.group(1)})

    data = {'status': 'ok', 'content': md_to_html(content_md), 'images': images,
            'credits': [], 'thumbnail': swan_og_image(url)}
    SWAN_ARTICLE_CACHE[url] = {'data': data, 'time': now}
    return data


# --- SCRAPERS PARA 35MMC, EMULSIVE, HUCK, PHROOM Y ARTÍCULOS GENÉRICOS ---

ARTICLE_GENERIC_CACHE = {}


def extract_html_article_payload(html_page, url, source_id=''):
    content_html = ''
    images = []
    seen_imgs = set()
    
    if source_id == '35mmc' or '35mmc.com' in url:
        m = re.search(r'<div class=[\"\']text-content[\"\']>(.*?)(?:<div class=[\"\']author-details|<div class=[\"\']post-closer|<footer)', html_page, re.DOTALL)
        if m:
            content_html = m.group(1)
        
        # Extraer figuras con máxima resolución de srcset y sus figcaptions
        for f in re.finditer(r'<figure[^>]*>(.*?)</figure>', html_page, re.DOTALL):
            f_html = f.group(1)
            srcset_m = re.search(r'srcset=[\"\']([^\"\']+)[\"\']', f_html)
            src_m = re.search(r'src=[\"\']([^\"\']+)[\"\']', f_html)
            cap_m = re.search(r'<figcaption[^>]*>(.*?)</figcaption>', f_html, re.DOTALL)
            
            img_u = None
            if srcset_m:
                img_u = srcset_m.group(1).split(',')[-1].strip().split(' ')[0]
            elif src_m:
                img_u = src_m.group(1)
            if img_u:
                img_u = re.sub(r'-\d+x\d+(\.[a-zA-Z]+)$', r'\1', img_u)
                if img_u not in seen_imgs:
                    seen_imgs.add(img_u)
                    caption = html.unescape(re.sub(r'<[^>]+>', '', cap_m.group(1))).strip() if cap_m else ''
                    images.append({'url': img_u, 'alt': caption, 'caption': caption})

    elif source_id == 'huck' or 'huckmag.com' in url:
        m = re.search(r'<div class=[\"\'][^\"\']*(?:article__body|article-body|story-body)[^\"\']*[\"\']>(.*?)(?:<aside|<footer|<div class=[\"\']share)', html_page, re.DOTALL)
        if m:
            content_html = m.group(1)
        
        # Standfirst / subtítulo
        lead_m = re.search(r'class=[\"\'][^\"\']*standfirst[^\"\']*[\"\'][^>]*>(.*?)</div>', html_page, re.DOTALL)
        if lead_m:
            lead_t = html.unescape(re.sub(r'<[^>]+>', '', lead_m.group(1))).strip()
            if lead_t:
                content_html = f"<p><strong>{lead_t}</strong></p>\n" + content_html

        # Extraer todas las fotos en alta resolución de CDN Huck
        for im_h in re.finditer(r'<img[^>]+src=[\"\'](https://tco-london\.transforms\.svdcdn\.com/production/tco/images/[^\"\']+)[\"\']', html_page):
            raw_u = im_h.group(1).replace('&amp;', '&')
            clean_u = re.sub(r'\?.*', '?w=1800&q=85&auto=format', raw_u)
            if clean_u not in seen_imgs:
                seen_imgs.add(clean_u)
                alt_m = re.search(r'alt=[\"\']([^\"\']*)[\"\']', im_h.group(0))
                images.append({'url': clean_u, 'alt': alt_m.group(1) if alt_m else '', 'caption': ''})

    elif source_id == 'phroom' or 'phroom' in url:
        m = re.search(r'<div class=[\"\'][^\"\']*(?:entry-content|post-content)[^\"\']*[\"\']>(.*?)(?:<footer|<div class=[\"\']sharedaddy)', html_page, re.DOTALL)
        if m:
            content_html = m.group(1)
        
        # Extraer todas las imágenes no comprimidas
        for im_p in re.finditer(r'<img[^>]+(?:data-orig-file|data-large-file|src)=[\"\'](https?://[^\"\']+\.(?:jpg|jpeg|png|webp))[\"\']', html_page):
            u_p = im_p.group(1)
            if not any(ign in u_p.lower() for ign in ['logo', 'avatar', 'banner', 'icon']):
                clean_p = re.sub(r'-\d+x\d+(\.[a-zA-Z]+)$', r'\1', u_p)
                if clean_p not in seen_imgs:
                    seen_imgs.add(clean_p)
                    images.append({'url': clean_p, 'alt': '', 'caption': ''})

    elif source_id == 'emulsive' or 'emulsive.org' in url:
        m = re.search(r'<div class=[\"\'][^\"\']*entry-content[^\"\']*[\"\']>(.*?)</div>\s*<!-- \.?entry-content', html_page, re.DOTALL)
        if not m:
            m = re.search(r'<div class=[\"\'][^\"\']*entry-content[^\"\']*[\"\']>(.*?)(?:<footer|<div id=[\"\']comments[\"\'])', html_page, re.DOTALL)
        if m:
            content_html = m.group(1)

    if not content_html:
        m = re.search(r'<article[^>]*>(.*?)</article>', html_page, re.DOTALL | re.IGNORECASE)
        if m:
            content_html = m.group(1)
        else:
            m_main = re.search(r'<main[^>]*>(.*?)</main>', html_page, re.DOTALL | re.IGNORECASE)
            content_html = m_main.group(1) if m_main else html_page

    # Extraer imágenes genéricas restantes si no se encontraron antes
    if not images:
        for im in re.finditer(r'<img[^>]+src=[\"\'](https?://[^\"\']+\.(?:jpg|jpeg|png|webp|avif)(?:\?[^\"\']*)?)[\"\']', content_html, re.I):
            u = im.group(1)
            if not any(ign in u.lower() for ign in ['avatar', 'icon', 'logo', 'badge', 'emoji', 'pixel', 'advert', 'banner', 'button', 'track']):
                if u not in seen_imgs:
                    seen_imgs.add(u)
                    alt_m = re.search(r'alt=[\"\']([^\"\']*)[\"\']', im.group(0))
                    alt = alt_m.group(1) if alt_m else ''
                    images.append({'url': u, 'alt': alt, 'caption': alt})

    # Limpieza de scripts y estilos
    clean_html = re.sub(r'<script[^>]*>.*?</script>', '', content_html, flags=re.DOTALL | re.I)
    clean_html = re.sub(r'<style[^>]*>.*?</style>', '', clean_html, flags=re.DOTALL | re.I)
    clean_html = re.sub(r'class=[\"\'][^\"\']*[\"\']', '', clean_html)
    clean_html = re.sub(r'id=[\"\'][^\"\']*[\"\']', '', clean_html)
    clean_html = re.sub(r'<div[^>]*>\s*</div>', '', clean_html)

    # Texto limpio para resúmenes
    clean_text = re.sub(r'<[^>]+>', ' ', clean_html)
    clean_text = html.unescape(re.sub(r'\s+', ' ', clean_text).strip())

    thumbnail = images[0]['url'] if images else ''
    return {
        'status': 'ok',
        'content': clean_html,
        'clean_text': clean_text,
        'images': images,
        'credits': [],
        'thumbnail': thumbnail
    }


def scrape_35mmc_article(url):
    now = time.time()
    if url in ARTICLE_GENERIC_CACHE and now - ARTICLE_GENERIC_CACHE[url]['time'] < 300:
        return ARTICLE_GENERIC_CACHE[url]['data']
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html_page = resp.read().decode('utf-8', errors='ignore')
        data = extract_html_article_payload(html_page, url, '35mmc')
        ARTICLE_GENERIC_CACHE[url] = {'data': data, 'time': now}
        return data
    except Exception as e:
        print(f'Error scraping 35mmc {url}: {e}')
        return None


def scrape_emulsive_article(url):
    now = time.time()
    if url in ARTICLE_GENERIC_CACHE and now - ARTICLE_GENERIC_CACHE[url]['time'] < 300:
        return ARTICLE_GENERIC_CACHE[url]['data']
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html_page = resp.read().decode('utf-8', errors='ignore')
        data = extract_html_article_payload(html_page, url, 'emulsive')
        ARTICLE_GENERIC_CACHE[url] = {'data': data, 'time': now}
        return data
    except Exception as e:
        print(f'Error scraping emulsive {url}: {e}')
        return None


def scrape_huck_article(url):
    now = time.time()
    if url in ARTICLE_GENERIC_CACHE and now - ARTICLE_GENERIC_CACHE[url]['time'] < 300:
        return ARTICLE_GENERIC_CACHE[url]['data']
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html_page = resp.read().decode('utf-8', errors='ignore')
        data = extract_html_article_payload(html_page, url, 'huck')
        ARTICLE_GENERIC_CACHE[url] = {'data': data, 'time': now}
        return data
    except Exception as e:
        print(f'Error scraping huck {url}: {e}')
        return None


def scrape_phroom_article(url):
    now = time.time()
    if url in ARTICLE_GENERIC_CACHE and now - ARTICLE_GENERIC_CACHE[url]['time'] < 300:
        return ARTICLE_GENERIC_CACHE[url]['data']
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html_page = resp.read().decode('utf-8', errors='ignore')
        data = extract_html_article_payload(html_page, url, 'phroom')
        ARTICLE_GENERIC_CACHE[url] = {'data': data, 'time': now}
        return data
    except Exception as e:
        print(f'Error scraping phroom {url}: {e}')
        return None


def scrape_generic_article(url, source_id=''):
    if not url:
        return None
    now = time.time()
    if url in ARTICLE_GENERIC_CACHE and now - ARTICLE_GENERIC_CACHE[url]['time'] < 300:
        return ARTICLE_GENERIC_CACHE[url]['data']

    if source_id == 'tpj' or 'thephotographicjournal.com' in url:
        return scrape_tpj_article(url)
    if source_id == '35mmc' or '35mmc.com' in url:
        return scrape_35mmc_article(url)
    if source_id == 'emulsive' or 'emulsive.org' in url:
        return scrape_emulsive_article(url)
    if source_id == 'huck' or 'huckmag.com' in url:
        return scrape_huck_article(url)
    if source_id == 'phroom' or 'phroom' in url:
        return scrape_phroom_article(url)
    if source_id == 'swan' or 'swanngalleries.com' in url:
        return scrape_swan_article(url)
    if source_id == 'lensculture' or 'lensculture.com' in url:
        return scrape_lensculture_article(url)
    if source_id == 'odlp' or 'loeildelaphotographie.com' in url:
        return scrape_odlp_article(url)
    if source_id == 'magnum' or 'magnumphotos.com' in url:
        return scrape_magnum_article(url)
    if source_id == 'booooooom' or 'booooooom.com' in url:
        return scrape_booooooom_article(url)
    if source_id == 'lomography' or 'lomography.com' in url:
        return scrape_lomography_article(url, resolve_profiles=False)

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html_page = resp.read().decode('utf-8', errors='ignore')
        data = extract_html_article_payload(html_page, url, source_id)
        ARTICLE_GENERIC_CACHE[url] = {'data': data, 'time': now}
        return data
    except Exception as e:
        print(f'Error generic scrape {url}: {e}')
        return None


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/api/lomography':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            try:
                articles = scrape_lomography()
                data = json.dumps({'status': 'ok', 'items': articles, 'count': len(articles)})
            except subprocess.TimeoutExpired:
                data = json.dumps({'status': 'error', 'message': 'timeout scraping lomography'})
            except Exception as e:
                data = json.dumps({'status': 'error', 'message': str(e)})
            self.wfile.write(data.encode())
        elif parsed.path == '/api/lensculture':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            try:
                articles = scrape_lensculture()
                data = json.dumps({'status': 'ok', 'items': articles, 'count': len(articles)})
            except Exception as e:
                data = json.dumps({'status': 'error', 'message': str(e)})
            self.wfile.write(data.encode())
        elif parsed.path == '/api/odlp':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            try:
                articles = scrape_odlp()
                data = json.dumps({'status': 'ok', 'items': articles, 'count': len(articles)})
            except Exception as e:
                data = json.dumps({'status': 'error', 'message': str(e)})
            self.wfile.write(data.encode())
        elif parsed.path == '/api/magnum':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            try:
                articles = scrape_magnum()
                data = json.dumps({'status': 'ok', 'items': articles, 'count': len(articles)})
            except Exception as e:
                data = json.dumps({'status': 'error', 'message': str(e)})
            self.wfile.write(data.encode())
        elif parsed.path == '/api/booooooom':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            try:
                with open(os.path.join(DIR, 'booooooom.json')) as f:
                    items = json.load(f).get('items', [])
                data = json.dumps({'status': 'ok', 'items': items, 'count': len(items)})
            except Exception as e:
                data = json.dumps({'status': 'error', 'message': str(e)})
            self.wfile.write(data.encode())
        elif parsed.path == '/api/tpj':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            try:
                with open(os.path.join(DIR, 'tpj.json')) as f:
                    items = json.load(f).get('items', [])
                data = json.dumps({'status': 'ok', 'items': items, 'count': len(items)})
            except Exception as e:
                data = json.dumps({'status': 'error', 'message': str(e)})
            self.wfile.write(data.encode())
        elif parsed.path == '/api/huck':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            try:
                with open(os.path.join(DIR, 'huck.json')) as f:
                    items = json.load(f).get('items', [])
                data = json.dumps({'status': 'ok', 'items': items, 'count': len(items)})
            except Exception as e:
                data = json.dumps({'status': 'error', 'message': str(e)})
            self.wfile.write(data.encode())
        elif parsed.path == '/api/swan':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            try:
                with open(os.path.join(DIR, 'swan.json')) as f:
                    items = json.load(f).get('items', [])
                data = json.dumps({'status': 'ok', 'items': items, 'count': len(items)})
            except Exception as e:
                data = json.dumps({'status': 'error', 'message': str(e)})
            self.wfile.write(data.encode())
        elif parsed.path == '/api/sources':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            try:
                with open(os.path.join(DIR, 'sources.json')) as f:
                    data = f.read()
            except Exception as e:
                data = json.dumps({'status': 'error', 'message': str(e)})
            self.wfile.write(data.encode())
        elif parsed.path == '/api/shootitwithfilm':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            try:
                with open(os.path.join(DIR, 'shootitwithfilm.json')) as f:
                    items = json.load(f).get('items', [])
                data = json.dumps({'status': 'ok', 'items': items, 'count': len(items)})
            except Exception as e:
                data = json.dumps({'status': 'error', 'message': str(e)})
            self.wfile.write(data.encode())
        elif parsed.path == '/api/tpj/article':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            qs = urllib.parse.parse_qs(parsed.query)
            url = qs.get('url', [None])[0]
            if not url:
                self.wfile.write(json.dumps({'status': 'error', 'message': 'missing url'}).encode())
                return
            data = scrape_tpj_article(url)
            if data is None:
                self.wfile.write(json.dumps({'status': 'error', 'message': 'error scraping article'}).encode())
            else:
                self.wfile.write(json.dumps(data).encode())
        elif parsed.path == '/api/swan/article':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            qs = urllib.parse.parse_qs(parsed.query)
            url = qs.get('url', [None])[0]
            if not url:
                self.wfile.write(json.dumps({'status': 'error', 'message': 'missing url'}).encode())
                return
            data = scrape_swan_article(url)
            if data is None:
                self.wfile.write(json.dumps({'status': 'error', 'message': 'error scraping article'}).encode())
            else:
                self.wfile.write(json.dumps(data).encode())
        elif parsed.path == '/api/booooooom/article':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            qs = urllib.parse.parse_qs(parsed.query)
            url = qs.get('url', [None])[0]
            if not url:
                self.wfile.write(json.dumps({'status': 'error', 'message': 'missing url'}).encode())
                return
            data = scrape_booooooom_article(url)
            if data is None:
                self.wfile.write(json.dumps({'status': 'error', 'message': 'error scraping article'}).encode())
            else:
                self.wfile.write(json.dumps(data).encode())
        elif parsed.path == '/api/lomography/article':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            qs = urllib.parse.parse_qs(parsed.query)
            url = qs.get('url', [None])[0]
            if not url:
                self.wfile.write(json.dumps({'status': 'error', 'message': 'missing url'}).encode())
                return
            data = scrape_lomography_article(url, resolve_profiles=False)
            if data is None:
                self.wfile.write(json.dumps({'status': 'error', 'message': 'error scraping article'}).encode())
            else:
                self.wfile.write(json.dumps(data).encode())
        elif parsed.path == '/api/lensculture/article':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            qs = urllib.parse.parse_qs(parsed.query)
            url = qs.get('url', [None])[0]
            if not url:
                self.wfile.write(json.dumps({'status': 'error', 'message': 'missing url'}).encode())
                return
            data = scrape_lensculture_article(url)
            if data is None:
                self.wfile.write(json.dumps({'status': 'error', 'message': 'error scraping article'}).encode())
            else:
                self.wfile.write(json.dumps(data).encode())
        elif parsed.path == '/api/odlp/article':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            qs = urllib.parse.parse_qs(parsed.query)
            url = qs.get('url', [None])[0]
            if not url:
                self.wfile.write(json.dumps({'status': 'error', 'message': 'missing url'}).encode())
                return
            data = scrape_odlp_article(url)
            if data is None:
                self.wfile.write(json.dumps({'status': 'error', 'message': 'error scraping article'}).encode())
            else:
                self.wfile.write(json.dumps(data).encode())
        elif parsed.path == '/api/magnum/article':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            qs = urllib.parse.parse_qs(parsed.query)
            url = qs.get('url', [None])[0]
            if not url:
                self.wfile.write(json.dumps({'status': 'error', 'message': 'missing url'}).encode())
                return
            data = scrape_magnum_article(url)
            if data is None:
                self.wfile.write(json.dumps({'status': 'error', 'message': 'error scraping article'}).encode())
            else:
                self.wfile.write(json.dumps(data).encode())
        elif parsed.path == '/api/35mmc/article':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            qs = urllib.parse.parse_qs(parsed.query)
            url = qs.get('url', [None])[0]
            if not url:
                self.wfile.write(json.dumps({'status': 'error', 'message': 'missing url'}).encode())
                return
            data = scrape_35mmc_article(url)
            if data is None:
                self.wfile.write(json.dumps({'status': 'error', 'message': 'error scraping article'}).encode())
            else:
                self.wfile.write(json.dumps(data).encode())
        elif parsed.path == '/api/emulsive/article':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            qs = urllib.parse.parse_qs(parsed.query)
            url = qs.get('url', [None])[0]
            if not url:
                self.wfile.write(json.dumps({'status': 'error', 'message': 'missing url'}).encode())
                return
            data = scrape_emulsive_article(url)
            if data is None:
                self.wfile.write(json.dumps({'status': 'error', 'message': 'error scraping article'}).encode())
            else:
                self.wfile.write(json.dumps(data).encode())
        elif parsed.path == '/api/huck/article':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            qs = urllib.parse.parse_qs(parsed.query)
            url = qs.get('url', [None])[0]
            if not url:
                self.wfile.write(json.dumps({'status': 'error', 'message': 'missing url'}).encode())
                return
            data = scrape_huck_article(url)
            if data is None:
                self.wfile.write(json.dumps({'status': 'error', 'message': 'error scraping article'}).encode())
            else:
                self.wfile.write(json.dumps(data).encode())
        elif parsed.path == '/api/phroom/article':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            qs = urllib.parse.parse_qs(parsed.query)
            url = qs.get('url', [None])[0]
            if not url:
                self.wfile.write(json.dumps({'status': 'error', 'message': 'missing url'}).encode())
                return
            data = scrape_phroom_article(url)
            if data is None:
                self.wfile.write(json.dumps({'status': 'error', 'message': 'error scraping article'}).encode())
            else:
                self.wfile.write(json.dumps(data).encode())
        elif parsed.path == '/api/article':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            qs = urllib.parse.parse_qs(parsed.query)
            url = qs.get('url', [None])[0]
            source_id = qs.get('source', [''])[0]
            if not url:
                self.wfile.write(json.dumps({'status': 'error', 'message': 'missing url'}).encode())
                return
            data = scrape_generic_article(url, source_id)
            if data is None:
                self.wfile.write(json.dumps({'status': 'error', 'message': 'error scraping article'}).encode())
            else:
                self.wfile.write(json.dumps(data).encode())
        elif parsed.path == '/api/search':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            qs = urllib.parse.parse_qs(parsed.query)
            q = qs.get('q', [''])[0].strip()
            limit = int(qs.get('limit', [15])[0])
            mode = qs.get('mode', ['hybrid'])[0]
            source = qs.get('source', [None])[0]

            if not q:
                self.wfile.write(json.dumps({'status': 'ok', 'items': [], 'count': 0}).encode())
                return

            try:
                import vector_search
                if mode == 'semantic':
                    items = vector_search.search_semantic(q, limit=limit, source=source)
                elif mode == 'podcast':
                    items = vector_search.search_podcasts_semantic(q, limit=limit)
                else:
                    items = vector_search.search_hybrid(q, limit=limit)

                self.wfile.write(json.dumps({'status': 'ok', 'query': q, 'mode': mode, 'items': items, 'count': len(items)}).encode())
            except Exception as e:
                self.wfile.write(json.dumps({'status': 'error', 'message': str(e)}).encode())
        elif parsed.path == '/api/lineage':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            qs = urllib.parse.parse_qs(parsed.query)
            article_id = int(qs.get('id', [0])[0])
            limit = int(qs.get('limit', [3])[0])

            if not article_id:
                self.wfile.write(json.dumps({'status': 'error', 'message': 'missing article id'}).encode())
                return

            try:
                import vector_search
                lineage = vector_search.find_visual_lineage(article_id, limit=limit)
                self.wfile.write(json.dumps({'status': 'ok', 'article_id': article_id, 'lineage': lineage}).encode())
            except Exception as e:
                self.wfile.write(json.dumps({'status': 'error', 'message': str(e)}).encode())
        else:
            super().do_GET()

if __name__ == '__main__':
    os.chdir(DIR)
    server = http.server.HTTPServer(('0.0.0.0', PORT), Handler)
    print(f'Server on http://localhost:{PORT}')
    server.serve_forever()
