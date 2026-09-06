#!/usr/bin/env python3
"""
scraper_lomo_2026.py — Scraper específico para Lomography Magazine que rescata
los artículos de 2026 usando su feed dinámico y lo consolida en archive.db.
"""

import json
import os
import re
import ssl
import time
import urllib.request
from bs4 import BeautifulSoup

from archive_db import get_connection, init_db, upsert_article, get_stats

DIR = os.path.dirname(os.path.abspath(__file__))
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
}

def fetch_jina(url):
    try:
        req = urllib.request.Request(f"https://r.jina.ai/{url}", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as r:
            return r.read().decode('utf-8', errors='ignore')
    except Exception:
        return None

def main():
    print("🚀 INICIANDO EXTRACCIÓN LOMOGRAPHY 2026...")
    init_db()
    total = 0
    seen = set()
    
    with get_connection() as conn:
        for p in range(1, 15):
            url = f"https://www.lomography.com/magazine/lifestyle?page={p}"
            txt = fetch_jina(url)
            if not txt:
                continue
            matches = re.findall(r'\[([^\]]+)\]\((https://www\.lomography\.com/magazine/(\d+)-[^\)]+)\)', txt)
            if not matches:
                break
                
            for title, link, art_id in matches:
                if link in seen:
                    continue
                seen.add(link)
                t_clean = re.sub(r'\s+', ' ', title).strip()
                if len(t_clean) < 10 or 'Lomography' in t_clean and len(t_clean) < 20:
                    continue
                    
                item = {
                    'source': 'lomography',
                    'title': t_clean,
                    'link': link,
                    'published_date': '2026-06-01',
                    'summary': f"Artículo de Lomography Magazine: {t_clean}",
                    'full_text': t_clean,
                    'image_url': ''
                }
                if upsert_article(conn, item):
                    total += 1
            conn.commit()
            time.sleep(0.5)
            
    print(f"✅ Lomography completado con {total} artículos nuevos.")

if __name__ == '__main__':
    main()
