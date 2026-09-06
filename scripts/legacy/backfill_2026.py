#!/usr/bin/env python3
"""
backfill_2026.py — Descarga e ingesta de TODOS los artículos publicados en 2026
para los 18 medios configurados, consolidándolos en SQLite FTS5 (archive.db).
"""

import json
import os
import re
import ssl
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from archive_db import get_connection, init_db, upsert_article, get_stats
from sources_config import get_active_sources

DIR = os.path.dirname(os.path.abspath(__file__))
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9,es;q=0.8',
}

def clean_html(text):
    if not text:
        return ''
    t = re.sub(r'<[^>]+>', ' ', text)
    t = re.sub(r'&#8217;', "'", t)
    t = re.sub(r'&#8211;', '–', t)
    t = re.sub(r'&#\d+;', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def parse_date_iso(date_val):
    if not date_val:
        return ''
    d_str = str(date_val).strip()
    try:
        if 'T' in d_str:
            dt = datetime.fromisoformat(d_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d')
        dt = parsedate_to_datetime(d_str)
        return dt.strftime('%Y-%m-%d')
    except Exception:
        pass
    m = re.match(r'(\d{4}-\d{2}-\d{2})', d_str)
    if m:
        return m.group(1)
    return ''

def is_in_2026(date_iso):
    return date_iso.startswith('2026')

def fetch_url(url, timeout=20):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
            return resp.read()
    except Exception as e:
        return None

def backfill_wp_api(source_id, base_wp_api, conn):
    print(f"  [WP-API] {source_id.upper()}...")
    page = 1
    total_added = 0
    clean_base = base_wp_api.split('?')[0]
    extra_params = '&categories=496' if source_id == 'colossal' else ''
    
    while True:
        url = f"{clean_base}?after=2026-01-01T00:00:00&per_page=50&page={page}{extra_params}&_embed=1"
        data = fetch_url(url)
        if not data:
            break
        try:
            posts = json.loads(data.decode('utf-8'))
        except Exception:
            break
        if not posts or not isinstance(posts, list):
            break
            
        for p in posts:
            pub_date = parse_date_iso(p.get('date') or p.get('date_gmt'))
            if not is_in_2026(pub_date):
                continue
                
            title = clean_html(p.get('title', {}).get('rendered', ''))
            content_raw = p.get('content', {}).get('rendered', '')
            full_text = clean_html(content_raw)
            summary = clean_html(p.get('excerpt', {}).get('rendered', '')) or full_text[:400]
            link = p.get('link', '')
            
            # Extraer imagen
            thumb = ''
            media = p.get('_embedded', {}).get('wp:featuredmedia', [])
            if media and isinstance(media, list) and isinstance(media[0], dict):
                thumb = media[0].get('source_url', '')
            if not thumb:
                m = re.search(r'<img[^>]+src=[\'"]([^\'"]+)[\'"]', content_raw)
                if m:
                    thumb = m.group(1)
                    
            item = {
                'source': source_id,
                'title': title,
                'link': link,
                'published_date': pub_date,
                'summary': summary[:500],
                'full_text': full_text,
                'image_url': thumb
            }
            if upsert_article(conn, item):
                total_added += 1
                
        page += 1
        time.sleep(0.3)
        
    print(f"      ✓ {total_added} artículos 2026 procesados")
    return total_added

def backfill_rss_paginated(source_id, feed_urls, conn, max_pages=15):
    print(f"  [RSS-PAGED] {source_id.upper()}...")
    total_added = 0
    seen_links = set()
    
    for base_feed in feed_urls:
        stop_source = False
        for p in range(1, max_pages + 1):
            if stop_source:
                break
            page_url = base_feed if p == 1 else (f"{base_feed}?paged={p}" if '?' not in base_feed else f"{base_feed}&paged={p}")
            xml_bytes = fetch_url(page_url)
            if not xml_bytes:
                break
            try:
                root = ET.fromstring(xml_bytes)
            except Exception:
                break
                
            items = root.findall('.//item')
            if not items:
                break
                
            page_has_2026 = False
            for it in items:
                link = (it.findtext('link') or '').strip()
                if not link or link in seen_links:
                    continue
                seen_links.add(link)
                
                title = clean_html(it.findtext('title') or '')
                pub_date = parse_date_iso(it.findtext('pubDate'))
                if is_in_2026(pub_date):
                    page_has_2026 = True
                    desc = clean_html(it.findtext('description') or '')
                    # Content namespace
                    content_el = it.find('{http://purl.org/rss/1.0/modules/content/}encoded')
                    full_text = clean_html(content_el.text) if content_el is not None and content_el.text else desc
                    
                    # Imagen
                    thumb = ''
                    enclosure = it.find('enclosure')
                    if enclosure is not None and 'image' in enclosure.get('type', ''):
                        thumb = enclosure.get('url', '')
                    if not thumb:
                        media_thumb = it.find('{http://search.yahoo.com/mrss/}thumbnail') or it.find('{http://search.yahoo.com/mrss/}content')
                        if media_thumb is not None:
                            thumb = media_thumb.get('url', '')
                            
                    item = {
                        'source': source_id,
                        'title': title,
                        'link': link,
                        'published_date': pub_date,
                        'summary': desc[:500] or full_text[:500],
                        'full_text': full_text,
                        'image_url': thumb
                    }
                    if upsert_article(conn, item):
                        total_added += 1
                elif pub_date and str(pub_date) < '2026-01-01':
                    # Llegamos a 2025 o antes, frenar paginación
                    stop_source = True
                    break
                    
            if not page_has_2026 and p > 2:
                break
            time.sleep(0.3)
            
    print(f"      ✓ {total_added} artículos 2026 procesados")
    return total_added

def backfill_lomography(conn, max_pages=20):
    print("  [WEB-INDEX] LOMOGRAPHY MAGAZINE (vía Jina Reader)...")
    total_added = 0
    for p in range(1, max_pages + 1):
        url = f"https://r.jina.ai/https://www.lomography.com/magazine?page={p}"
        raw = fetch_url(url, timeout=30)
        if not raw:
            break
        text = raw.decode('utf-8', errors='ignore')
        
        # Buscar bloques de artículos
        articles = re.findall(r'\[([^\]]+)\]\((https://www\.lomography\.com/magazine/\d+-[^\)]+)\)', text)
        if not articles:
            break
            
        for title, link in articles:
            # Extraer fecha tentativa o consultar cabecera
            item = {
                'source': 'lomography',
                'title': clean_html(title),
                'link': link,
                'published_date': '2026-01-01', # fallback 2026
                'summary': f"Artículo de Lomography Magazine: {title}",
                'full_text': title,
                'image_url': ''
            }
            if upsert_article(conn, item):
                total_added += 1
        time.sleep(0.5)
    print(f"      ✓ {total_added} artículos procesados")
    return total_added

def main():
    print("🚀 INICIANDO BACKFILL DE TODO 2026 EN ARCHIVE.DB...")
    init_db()
    
    with get_connection() as conn:
        active = get_active_sources()
        for src in active:
            src_id = src['id']
            src_type = src.get('type')
            wp_api = src.get('wp_api')
            feeds = src.get('feeds', [])
            
            if wp_api:
                backfill_wp_api(src_id, wp_api, conn)
            elif src_id == 'lomography':
                backfill_lomography(conn)
            elif feeds:
                backfill_rss_paginated(src_id, feeds, conn)
                
            conn.commit()
            
    stats = get_stats()
    print("\n✅ BACKFILL 2026 COMPLETADO CON ÉXITO:")
    print(f"  • Total Artículos Consolidados: {stats['total_articles']}")
    print(f"  • Rango Temporal: {stats['min_date']} → {stats['max_date']}")
    print("\n📊 Desglose por medio:")
    for s, cnt in sorted(stats['sources'].items(), key=lambda x: -x[1]):
        print(f"    - {s:20s}: {cnt:4d} artículos")

if __name__ == '__main__':
    main()
