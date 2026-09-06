import json
import os
import re
import urllib.request
from datetime import date, datetime

from server import firecrawl_scrape, resolve_lomo_article_date

DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(DIR, 'resumenes')
TODAY = date.today()
WP_API = 'https://www.thisiscolossal.com/wp-json/wp/v2/posts'

def fetch_colossal():
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
    return [p for p in all_posts if p['date'][:10] == TODAY.isoformat()]

def fetch_lomography():
    md = firecrawl_scrape('https://www.lomography.com/magazine/', timeout=60)
    if not md:
        return []
    articles = []
    seen = set()
    matches = list(re.finditer(r'^(?:- )?### \[(.+?)\]\((https://www\.lomography\.com/magazine/[^)]+)\)', md, re.MULTILINE))
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        url = m.group(2).strip()
        key = re.sub(r'[^a-z0-9]', '', title.lower())[:40]
        if key in seen:
            continue
        seen.add(key)
        block_start = m.start()
        block_end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        block = md[block_start:block_end]
        dm = re.search(r'\b(20\d{2}-\d{2}-\d{2})\b', block)
        if dm:
            date_str = dm.group(1)
        else:
            date_str = resolve_lomo_article_date(url)
        if not date_str or date_str != TODAY.isoformat():
            continue
        thumb = ''
        tm = re.search(r'\[!\[.*?\]\(([^)]+)\)\]', block)
        if tm:
            thumb = tm.group(1)
        excerpt_lines = []
        for line in block.split('\n'):
            s = line.strip()
            if not s or s.startswith('###') or s.startswith('[') or s.startswith('written by') or s.startswith('http'):
                continue
            if re.match(r'^\[!\[', s):
                continue
            if s.startswith('#'):
                continue
            excerpt_lines.append(s)
        excerpt = ' '.join(excerpt_lines)
        excerpt = re.sub(r'\[\d+\]\([^)]+\)', '', excerpt).strip()[:200]
        articles.append({'title': title, 'link': url, 'thumbnail': thumb, 'excerpt': excerpt})
    return articles

def markdown(colossal, lomo):
    lines = [f'# Resumen fotográfico · {TODAY.isoformat()}', '',
             f'_{len(colossal) + len(lomo)} artículos hoy_', '', '---', '']
    if colossal:
        lines.append('## Colossal · Fotografía')
        lines.append('')
        for a in colossal:
            lines.append(f'- [{a["title"]["rendered"]}]({a["link"]})')
        lines.append('')
    if lomo:
        lines.append('## Lomography Magazine')
        lines.append('')
        for a in lomo:
            lines.append(f'- [{a["title"]}]({a["link"]})')
            if a['excerpt']:
                lines.append(f'  > {a["excerpt"]}')
        lines.append('')
    if not colossal and not lomo:
        lines.append('_No hubo artículos hoy._')
        lines.append('')
    lines.append(f'---\n_Generado el {datetime.now().strftime("%Y-%m-%d %H:%M")}_')
    return '\n'.join(lines)

def html(md_text):
    h = md_text
    h = re.sub(r'^# (.+)$', r'<h1>\1</h1>', h, flags=re.M)
    h = re.sub(r'^## (.+)$', r'<h2>\1</h2>', h, flags=re.M)
    h = re.sub(r'^_(.+?)_\s*$', r'<p><em>\1</em></p>', h, flags=re.M)
    h = re.sub(r'^-\s+\[(.+?)\]\((.+?)\)$', r'<li><a href="\2">\1</a></li>', h, flags=re.M)
    h = re.sub(r'^  > (.+)$', r'<blockquote>\1</blockquote>', h, flags=re.M)
    h = re.sub(r'^---$', r'<hr>', h, flags=re.M)
    h = '<ul>\n' + h + '\n</ul>'
    h = re.sub(r'</ul>\n<li>', '</ul>\n<li>', h)
    h = re.sub(r'<li>\n</li>', '', h)
    h = re.sub(r'</ul>\n<h', '</ul>\n\n<h', h)
    h = re.sub(r'(</h\d>)\n(<ul>)', r'\1\n\n\2', h)
    h = re.sub(r'<hr>\n<ul>', '<hr>\n\n<ul>', h)
    return f'''<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><title>Resumen {TODAY}</title>
<style>body{{font-family:sans-serif;max-width:600px;margin:2rem auto;padding:0 1rem;line-height:1.6;color:#222}}
a{{color:#0366d6}}hr{{border:none;border-top:1px solid #ddd}}blockquote{{color:#555;border-left:3px solid #ddd;padding-left:1rem;margin:0;margin-left:0}}
p{{margin:0.5rem 0}}ul{{padding-left:1.2rem}}</style>
<body>
{h}
<p><a href="../index.html">← feed</a></p>
</body></html>'''

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f'[{datetime.now().isoformat()}] Generando resumen de {TODAY}...')
    colossal = fetch_colossal()
    print(f'  Colossal: {len(colossal)} artículos')
    lomo = fetch_lomography()
    print(f'  Lomography: {len(lomo)} artículos')
    md_text = markdown(colossal, lomo)
    stem = f'resumen-{TODAY.isoformat()}'
    with open(os.path.join(OUT_DIR, f'{stem}.md'), 'w') as f:
        f.write(md_text)
    with open(os.path.join(OUT_DIR, f'{stem}.html'), 'w') as f:
        f.write(html(md_text))
    print(f'  Guardado: {stem}.md y {stem}.html')

if __name__ == '__main__':
    main()
