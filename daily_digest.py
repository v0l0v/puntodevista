import json
import os
import random
import re
import urllib.request
from datetime import date, datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

from server import firecrawl_scrape, parse_magazine_list, clean_lomo_credit_name, trim_lomo_body
from update_static_data import (fetch_booooooom, fetch_tpj, fetch_swan, fetch_huck,
                                fetch_lensculture, fetch_odlp, fetch_magnum, fetch_shootitwithfilm)
from fetch_email_newsletter import fetch_email_newsletters

DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(DIR, 'resumenes')
TODAY = date.today()
WP_API = 'https://www.thisiscolossal.com/wp-json/wp/v2/posts'


def is_within_24h(date_val, target_date=None, hours=24):
    """
    Comprueba si una fecha/hora está dentro de las últimas `hours` horas.
    Soporta datetime, date o string (ISO, RFC2822 o YYYY-MM-DD).
    """
    now_utc = datetime.now(timezone.utc)
    if target_date and target_date != date.today():
        cutoff = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, tzinfo=timezone.utc) - timedelta(days=1)
        end_cutoff = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, tzinfo=timezone.utc)
    else:
        cutoff = now_utc - timedelta(hours=hours)
        end_cutoff = now_utc + timedelta(hours=4)

    if isinstance(date_val, datetime):
        dt = date_val
    elif isinstance(date_val, date):
        iso = date_val.isoformat()
        yesterday_iso = ((target_date or date.today()) - timedelta(days=1)).isoformat()
        today_iso = (target_date or date.today()).isoformat()
        return iso in (today_iso, yesterday_iso)
    elif isinstance(date_val, str):
        date_str = date_val.strip()
        dt = None
        try:
            if 'T' in date_str:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                dt = parsedate_to_datetime(date_str)
        except Exception:
            try:
                dt = datetime.strptime(date_str[:19], '%Y-%m-%d %H:%M:%S')
            except Exception:
                if len(date_str) >= 10 and re.match(r'^\d{4}-\d{2}-\d{2}', date_str):
                    iso = date_str[:10]
                    yesterday_iso = ((target_date or date.today()) - timedelta(days=1)).isoformat()
                    today_iso = (target_date or date.today()).isoformat()
                    return iso in (today_iso, yesterday_iso)
                return False
    else:
        return False

    if dt:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return cutoff <= dt <= end_cutoff

    return False


SOURCES = [
    ('colossal', 'Colossal · Fotografía'),
    ('lomography', 'Lomography Magazine'),
    ('booooooom', 'Booooooom'),
    ('tpj', 'The Photographic Journal'),
    ('swan', 'Swann Galleries'),
    ('huck', 'Huck Magazine'),
    ('lensculture', 'LensCulture'),
    ('odlp', 'L\'Œil de la Photographie'),
    ('magnum', 'Magnum Photos'),
    ('shootitwithfilm', 'Shoot It With Film'),
    ('email', 'Newsletters · Email'),
]

RSS_SOURCES = [
    ('booooooom', 'Booooooom', fetch_booooooom),
    ('tpj', 'The Photographic Journal', fetch_tpj),
    ('swan', 'Swann Galleries', fetch_swan),
    ('huck', 'Huck Magazine', fetch_huck),
    ('lensculture', 'LensCulture', fetch_lensculture),
    ('odlp', 'L\'Œil de la Photographie', fetch_odlp),
    ('magnum', 'Magnum Photos', fetch_magnum),
    ('shootitwithfilm', 'Shoot It With Film', fetch_shootitwithfilm),
]

EMOJI_RE = re.compile(
    '[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF'
    '\U0001F1E0-\U0001F1FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F'
    '\U0001FA70-\U0001FAFF\u2702-\u27B0\u24C2-\U0001F251'
    '\U0001F004\u2596-\u27BF\u2600-\u26FF\uFE0F]'
)

def fetch_colossal_articles():
    all_posts = []
    for page in range(1, 4):
        url = f'{WP_API}?categories=496&per_page=20&page={page}'
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            if not data:
                break
            all_posts.extend(data)
        except:
            break
    posts = [p for p in all_posts if is_within_24h(p.get('date_gmt') or p.get('date'), TODAY)]
    if not posts:
        try:
            with open(os.path.join(DIR, 'feeds.json'), encoding='utf-8') as f:
                feeds = json.load(f).get('items', [])
            for a in feeds:
                if a.get('_source') == 'colossal' and is_within_24h(a.get('_parsedDate') or a.get('date'), TODAY):
                    posts.append({
                        'title': {'rendered': a['title']},
                        'content': {'rendered': a['content']},
                        'link': a['link'],
                        'date': a.get('_parsedDate') or a.get('date'),
                    })
        except Exception:
            pass
    return posts

def extract_colossal_photographer(html):
    m = re.search(r'All images [©©] ([^,]+)', html)
    if m:
        return m.group(1).strip()
    m = re.search(r'<figcaption[^>]*>([\s\S]*?)</figcaption>', html)
    if m:
        names = re.findall(r'<a[^>]*>([^<]+)</a>', m.group(1))
        if names:
            return names[0].strip()
    m = re.search(r'(?:Photos?|Images?) (?:by|©) ([A-Z][a-z]+ [A-Z][a-z]+)', html)
    if m:
        return m.group(1).strip()
    return None

def extract_colossal_summary(html):
    texts = []
    for m in re.finditer(r'<p[^>]*>(.*?)</p>', html):
        t = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        t = re.sub(r'&#8217;', "'", t)
        t = re.sub(r'&#8211;', '–', t)
        t = re.sub(r'&#\d+;', '', t)
        if len(t) < 40 or re.match(r'^\(.*\)$', t):
            continue
        texts.append(t)
    result = []
    for t in texts:
        result.append(t)
        if len(' '.join(result)) > 400:
            break
    return ' '.join(result)

def process_colossal(post):
    html = post['content']['rendered']
    photographer = extract_colossal_photographer(html)
    summary = extract_colossal_summary(html)
    full = re.sub(r'<[^>]+>', ' ', html)
    full = re.sub(r'&#8217;', "'", full)
    full = re.sub(r'&#8211;', '–', full)
    full = re.sub(r'&#\d+;', '', full)
    full = re.sub(r'\s+', ' ', full).strip()
    images = []
    for im in re.finditer(r'<img[^>]+src="([^"]+)"', html):
        src = im.group(1).split('?')[0]
        if src and src not in images:
            images.append(src)
    return {
        'title': post['title']['rendered'],
        'link': post['link'],
        'photographer': photographer,
        'summary': summary,
        'full_text': full,
        'image': images[0] if images else '',
        'images': images,
        'source': 'Colossal'
    }

def fetch_lomography_articles():
    md = firecrawl_scrape('https://www.lomography.com/magazine/', timeout=60)
    if not md:
        return []
    return [a for a in parse_magazine_list(md) if is_within_24h(a.get('date'), TODAY)]

def fetch_lomo_article_content(url):
    md = firecrawl_scrape(url, timeout=45)
    if not md:
        return None, [], []
    idx = re.search(r'## (?:One|\d+) Likes?|## No Comments|Please login to leave a comment|More Interesting Articles', md)
    clean_md = md[:idx.start()] if idx else md
    clean_md = trim_lomo_body(clean_md)
    body_md = re.split(r'\nwritten by\b', clean_md, maxsplit=1)[0] if re.search(r'\nwritten by\b', clean_md) else clean_md
    credits = []
    seen_names = set()
    for cm in re.finditer(r'\[([^\]]+)\]\((https://www\.lomography\.com/homes/[^)]+)\)', clean_md):
        name = clean_lomo_credit_name(cm.group(1))
        if name and name.lower() not in seen_names:
            seen_names.add(name.lower())
            credits.append({'name': name, 'url': cm.group(2)})
    images = []
    seen_imgs = set()
    for m in re.finditer(r'!\[([^\]]*)\]\((https?://[^\s\)]+)\)', clean_md):
        u = m.group(2)
        if u not in seen_imgs and 'avatar' not in u.lower() and 'icon' not in u.lower():
            seen_imgs.add(u)
            images.append(u)
    for m in re.finditer(r'<img[^>]+src=["\'](https?://[^"\']+)["\']', clean_md, re.I):
        u = m.group(1)
        if u not in seen_imgs and 'avatar' not in u.lower() and 'icon' not in u.lower():
            seen_imgs.add(u)
            images.append(u)
    return body_md, credits, images

def extract_lomo_summary(md):
    lines = md.split('\n')
    texts = []
    for line in lines:
        s = line.strip()
        if not s or s.startswith('#') or s.startswith('[') or s.startswith('!['):
            continue
        if re.match(r'^\d+$', s):
            continue
        s = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', s)
        s = re.sub(r'\*\*(.+?)\*\*', r'\1', s)
        s = re.sub(r'\*(.+?)\*', r'\1', s)
        if len(s) > 30:
            texts.append(s)
    result = []
    for t in texts:
        result.append(t)
        if len(' '.join(result)) > 400:
            break
    return ' '.join(result)

def process_lomo(article):
    content_md, credits, images = fetch_lomo_article_content(article['link'])
    if content_md:
        summary = extract_lomo_summary(content_md) or article['excerpt']
        full = content_md
    else:
        summary = article['excerpt']
        full = article['excerpt']
    photographers = [c['name'] for c in credits] if credits else None
    return {
        'title': article['title'],
        'link': article['link'],
        'photographers': photographers,
        'summary': summary,
        'full_text': full,
        'image': article['thumbnail'],
        'images': images if images else [article['thumbnail']] if article.get('thumbnail') else [],
        'source': 'Lomography'
    }

def process_rss_item(a, label):
    content = a.get('content') or a.get('excerpt') or ''
    full_text = clean_text(content)
    summary = clean_text(a.get('excerpt') or content)
    if len(summary) > 400:
        summary = summary[:397] + '…'
    thumb = a.get('thumbnail') or ''
    return {
        'title': a['title'],
        'link': a['link'],
        'photographer': None,
        'photographers': None,
        'summary': summary,
        'full_text': full_text,
        'image': thumb,
        'images': [thumb] if thumb else [],
        'source': label
    }


def pick_day_image(items_by_source):
    candidates = []
    for key, _ in SOURCES:
        for item in items_by_source.get(key) or []:
            img = item.get('image') or ''
            if img:
                candidates.append(img.split('?')[0])
    if candidates:
        return random.choice(candidates)

    # Fallback 1: buscar en feeds.json fotos de artículos recientes
    try:
        feeds_path = os.path.join(DIR, 'feeds.json')
        if os.path.exists(feeds_path):
            with open(feeds_path, encoding='utf-8') as f:
                feeds = json.load(f).get('items', [])
            for item in feeds:
                t = item.get('thumbnail') or ''
                if t and 'instagram' not in t and 'avatar' not in t.lower():
                    candidates.append(t.split('?')[0])
    except Exception:
        pass

    # Fallback 2: buscar en digests anteriores
    if not candidates:
        try:
            for p in sorted(Path(OUT_DIR).glob('*.images.json'), reverse=True):
                with open(p, encoding='utf-8') as f:
                    imgs = json.load(f)
                    if imgs:
                        candidates.extend(imgs[:5])
                        break
        except Exception:
            pass

    return random.choice(candidates) if candidates else ''


def render_html(items_by_source):
    total = sum(len(v) for v in items_by_source.values())
    parts = ['''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Inspiración fotográfica · ''' + TODAY.isoformat() + '''</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#fafafa;color:#222;line-height:1.6;padding:2rem 1rem}
.container{max-width:640px;margin:0 auto}
h1{font-size:1.6rem;font-weight:700;margin-bottom:0.25rem;letter-spacing:-0.02em}
.sub{color:#888;font-size:0.9rem;margin-bottom:2rem}
.source{font-size:0.75rem;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;color:#888;margin-bottom:0.5rem;margin-top:2.5rem}
.source.colossal{color:#d4a017}.source.lomography{color:#e25555}
.source.booooooom{color:#c2410c}.source.tpj{color:#2f6f6f}
.source.swan{color:#7c3aed}.source.huck{color:#0f766e}
.card{background:#fff;border-radius:12px;padding:1.5rem;margin-bottom:1rem;box-shadow:0 1px 3px rgba(0,0,0,0.06)}
.card h2{font-size:1.1rem;font-weight:600;margin-bottom:0.5rem}
.card h2 a{color:#222;text-decoration:none}
.card h2 a:hover{text-decoration:underline}
.card .meta{font-size:0.8rem;color:#888;margin-bottom:0.75rem}
.card .sum{color:#444;font-size:0.9rem}
.card .sum a{color:#0366d6}
.photographer{display:inline-block;font-size:0.8rem;color:#555;margin-top:0.75rem;padding-top:0.75rem;border-top:1px solid #eee}
.photographer strong{color:#222}
hr{border:none;border-top:1px solid #eee;margin:2rem 0}
.footer{text-align:center;color:#aaa;font-size:0.8rem;margin-top:2rem}
</style>
</head>
<body>
<div class="container">
<h1>Inspiración fotográfica</h1>
<p class="sub">''' + TODAY.isoformat() + ''' · ''' + str(total) + ''' artículos</p>
''']

    for key, label in SOURCES:
        items = items_by_source.get(key) or []
        if not items:
            continue
        parts.append(f'<div class="source {key}">{label}</div>')
        for item in items:
            photo = ''
            if item.get('photographer'):
                photo = f'<div class="photographer"><strong>Fotógrafo:</strong> {item["photographer"]}</div>'
            elif item.get('photographers'):
                photo = '<div class="photographer"><strong>Fotógrafos:</strong> ' + ', '.join(item['photographers']) + '</div>'
            parts.append(f'''<div class="card">
<h2><a href="{item['link']}">{item['title']}</a></h2>
<div class="sum">{item['summary']}</div>
{photo}
</div>''')

    if total == 0:
        parts.append('<p style="color:#888">No hubo artículos hoy.</p>')

    parts.append(f'''</div>
<div class="footer">Generado el {datetime.now().strftime("%Y-%m-%d %H:%M")} · <a href="../index.html">Punto de vista</a></div>
</body></html>''')

    return '\n'.join(parts)

def clean_text(t):
    t = EMOJI_RE.sub('', t)
    t = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', t)
    t = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', t)
    t = re.sub(r'<\/?[^>]+>', '', t)
    t = re.sub(r'\*\*(.+?)\*\*', r'\1', t)
    t = re.sub(r'\*(.+?)\*', r'\1', t)
    t = re.sub(r'[_*~`]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    t = re.sub(r'&#8217;', "'", t)
    t = re.sub(r'&#8211;', '–', t)
    t = re.sub(r'&#\d+;', '', t)
    t = t.replace('\\', '')
    t = re.sub(r'\|', ', ', t)
    return t

def text_summary(item):
    lines = [f'  Artículo: {item["title"]}', f'  Fuente: {item["source"]}']
    if item.get('photographer'):
        lines.append(f'  Fotógrafo: {item["photographer"]}')
    elif item.get('photographers'):
        lines.append(f'  Fotógrafos: {", ".join(item["photographers"])}')
    s = clean_text(item['summary'])
    lines.append(f'  Resumen: {s}')
    return '\n'.join(lines) + '\n'

def render_text(items_by_source):
    total = sum(len(v) for v in items_by_source.values())
    lines = [f'INSPIRACIÓN FOTOGRÁFICA · {TODAY.isoformat()}',
             f'{total} artículos', '', '=' * 50, '']
    for key, label in SOURCES:
        items = items_by_source.get(key) or []
        if not items:
            continue
        lines.append(label.upper())
        lines.append('-' * 30)
        for item in items:
            lines.append(text_summary(item))
    if total == 0:
        lines.append('No hubo artículos hoy.')
    return '\n'.join(lines)

def render_podcast(items_by_source):
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    total = sum(len(v) for v in items_by_source.values())
    lines = [f'# Instrucciones para podcast diario · {TODAY.isoformat()}', '',
             'Eres un productor de podcast especializado en fotografía. Tu tarea es:', '',
             '1. **Leer** el texto completo de cada artículo a continuación.',
             '2. **Resumir** cada artículo en 2-3 frases en español, destacando la inspiración fotográfica.',
             '3. **Redactar un texto locutable** en español, con tono natural y cercano, como para un programa de radio.',
             '4. **Generar el audio** del texto locutable: solo voz, sin música, sin efectos de sonido.',
             '',
             'Formato del resultado final (para enviar por correo):',
             '  - Un texto en español con los resúmenes de todos los artículos del día.',
             '  - Un archivo de audio con la locución de ese texto.',
             '',
             'A continuación tienes el texto completo de cada artículo. Léelos todos',
             'y a partir de ahí genera el resumen locutable. No te saltes ningún artículo.',
             '',
             '---',
             f'_Generado el {now}_',
             '',
             '## Contenido del día',
             '']
    for key, label in SOURCES:
        items = items_by_source.get(key) or []
        if not items:
            continue
        lines.append(f'### {label}')
        lines.append('')
        for item in items:
            lines.append(f'**{item["title"]}**')
            if item.get('photographer'):
                lines.append(f'Fotógrafo: {item["photographer"]}')
            elif item.get('photographers'):
                lines.append(f'Fotógrafos: {", ".join(item["photographers"])}')
            lines.append('')
            lines.append(clean_text(item['full_text']))
            lines.append('')
    if total == 0:
        lines.append('No hubo artículos hoy.')
    return '\n'.join(lines)

def collect_all_images(items_by_source):
    all_images = []
    for key, label in SOURCES:
        items = items_by_source.get(key) or []
        for item in items:
            imgs = item.get('images') or []
            if item.get('image') and item['image'] not in imgs:
                imgs.append(item['image'])
            if imgs:
                all_images.extend(imgs)
    seen = set()
    unique = []
    for url in all_images:
        clean = url.split('?')[0]
        if clean not in seen:
            seen.add(clean)
            unique.append(clean)
    return unique

def main():
    import sys
    global TODAY
    if len(sys.argv) > 1:
        TODAY = date.fromisoformat(sys.argv[1])
    os.makedirs(OUT_DIR, exist_ok=True)
    ts = datetime.now().isoformat()
    print(f'[{ts}] Generando digest de {TODAY}...')

    items_by_source = {}

    print('  1. Colossal...')
    posts = fetch_colossal_articles()
    colossal = []
    for p in posts:
        print(f'    → {p["title"]["rendered"][:60]}')
        colossal.append(process_colossal(p))
    items_by_source['colossal'] = colossal
    print(f'    {len(colossal)} artículos')

    print('  2. Lomography...')
    lomo_articles = fetch_lomography_articles()
    lomo = []
    for a in lomo_articles:
        print(f'    → {a["title"][:60]}')
        lomo.append(process_lomo(a))
    items_by_source['lomography'] = lomo
    print(f'    {len(lomo)} artículos')

    print('  3. Booooooom, TPJ, Swann, Huck, LensCulture, L\'Œil de la Photographie (RSS)...')
    for key, label, fn in RSS_SOURCES:
        articles = [a for a in fn() if is_within_24h(a.get('_parsedDate') or a.get('pubDate') or a.get('date'), TODAY)]
        if key == 'odlp':
            filtered = []
            for a in articles:
                t = a.get('title', '').lower()
                if 'summer is here' in t or "c'est l'été" in t or "c’est l’été" in t:
                    print(f'    → [Omitido por etiqueta de verano] {a.get("title")[:60]}')
                    continue
                filtered.append(a)
            articles = filtered
        items = [process_rss_item(a, label) for a in articles]
        items_by_source[key] = items
        for item in items:
            print(f'    → {item["title"][:60]}')
        print(f'    {len(items)} artículos')

    print('  4. Newsletters por email (label: fotopodcast)...')
    email_items = fetch_email_newsletters(TODAY, hours=24)
    items_by_source['email'] = email_items
    print(f'    {len(email_items)} newsletter(s)')

    html = render_html(items_by_source)
    podcast = render_podcast(items_by_source)
    stem = f'digest-{TODAY.isoformat()}'
    with open(os.path.join(OUT_DIR, f'{stem}.html'), 'w') as f:
        f.write(html)
    with open(os.path.join(OUT_DIR, f'{stem}.podcast.md'), 'w') as f:
        f.write(podcast)

    day_image = pick_day_image(items_by_source)
    if day_image:
        with open(os.path.join(OUT_DIR, f'{stem}.image'), 'w') as f:
            f.write(day_image)
        print(f'  Imagen del día: {day_image[:90]}')

    all_images = collect_all_images(items_by_source)
    if all_images:
        with open(os.path.join(OUT_DIR, f'{stem}.images.json'), 'w') as f:
            json.dump(all_images, f, ensure_ascii=False, indent=2)
        print(f'  Imágenes del artículo ({len(all_images)})')
    print(f'  Guardado: {stem}.html, {stem}.podcast.md')

if __name__ == '__main__':
    main()
