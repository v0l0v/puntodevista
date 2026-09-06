import argparse
import json
import os
import re
import time
from datetime import date

import requests

from data_paths import get_data_path
from config import get_telegram_creds, get_config

DIR = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = get_data_path('telegram_sent.json')

TG_TOKEN, TG_CHAT_ID = get_telegram_creds()

SOURCES = {
    'colossal': 'Colossal · Fotografía',
    'lomography': 'Lomography Magazine',
    'booooooom': 'Booooooom',
    'tpj': 'The Photographic Journal',
    'swan': 'Swann Galleries',
    'huck': 'Huck Magazine',
}

BAD_IMG_RE = re.compile(r'facebook\.com|google|tracking', re.I)


def item_date(item):
    d = item.get('date') or item.get('_parsedDate') or ''
    return str(d)[:10]


def get_image(item):
    thumb = item.get('thumbnail') or ''
    if thumb and not BAD_IMG_RE.search(thumb):
        return thumb
    content = item.get('content') or ''
    for m in re.finditer(r'<img[^>]+src="([^"]+)"', content):
        url = m.group(1)
        if not BAD_IMG_RE.search(url):
            return url
    return None


def load_feeds():
    try:
        with open(get_data_path('feeds.json'), encoding='utf-8') as f:
            return json.load(f).get('items', [])
    except Exception:
        return []


def load_state():
    try:
        with open(STATE_PATH, encoding='utf-8') as f:
            data = json.load(f)
        return set(data.get('sent', []))
    except Exception:
        return set()


def save_state(sent):
    tmp = STATE_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump({'updated': date.today().isoformat(), 'sent': sorted(sent)},
                  f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_PATH)


def send_photo(photo_url, caption):
    url = f'https://api.telegram.org/bot{TG_TOKEN}/sendPhoto'
    try:
        resp = requests.post(url, json={
            'chat_id': TG_CHAT_ID,
            'photo': photo_url,
            'caption': caption,
            'parse_mode': 'HTML',
        }, timeout=60)
        return resp.json()
    except requests.RequestException as e:
        print(f'  Error Telegram photo: {e}')
        return None


def send_message(text):
    url = f'https://api.telegram.org/bot{TG_TOKEN}/sendMessage'
    try:
        resp = requests.post(url, json={
            'chat_id': TG_CHAT_ID,
            'text': text,
            'parse_mode': 'HTML',
        }, timeout=30)
        return resp.json()
    except requests.RequestException as e:
        print(f'  Error Telegram message: {e}')
        return None


def caption_for(item):
    title = (item.get('title') or '').strip()
    if title.startswith('**') and title.endswith('**'):
        title = title[2:-2]
    source = SOURCES.get(item.get('_source'), item.get('_source') or '')
    link = item.get('link') or ''
    return f'<b>{title}</b>\n\n{source}\n\n{link}'


def main():
    parser = argparse.ArgumentParser(description='Envía noticias nuevas a Telegram.')
    parser.add_argument('--date', default=date.today().isoformat(),
                        help='Fecha objetivo (YYYY-MM-DD). Por defecto: hoy.')
    parser.add_argument('--dry-run', action='store_true',
                        help='Solo simula: imprime lo que enviaría sin mandar nada.')
    args = parser.parse_args()

    today = args.date
    if not TG_TOKEN or not TG_CHAT_ID:
        print('  Falta TG_TOKEN o TG_CHAT_ID')
        return

    items = load_feeds()
    if not items:
        print('  feeds.json vacío o no disponible')
        return

    today_items = [i for i in items if item_date(i) == today and i.get('link')]
    if not today_items:
        print(f'  Sin artículos de {today}')
        return

    sent = load_state()
    current_links = {i.get('link') for i in items if i.get('link')}
    sent = sent & current_links

    new_items = [i for i in today_items if i.get('link') not in sent]
    print(f'  {len(today_items)} artículos de {today}, {len(new_items)} nuevos')

    if args.dry_run:
        for item in new_items:
            img = get_image(item)
            print(f'  📋 {item["_source"]}: {(item.get("title") or "")[:70]}')
            print(f'     img: {img}')
        print(f'  [dry-run] habría enviado {len(new_items)} mensajes')
        return

    sent_ok = 0
    for item in new_items:
        img = get_image(item)
        caption = caption_for(item)
        result = send_photo(img, caption) if img else send_message(caption)
        ok = bool(result and result.get('ok'))
        if ok:
            sent.add(item['link'])
            sent_ok += 1
            print(f'  ✅ {item["link"][:70]}')
        else:
            err = (result or {}).get('description', '?')
            print(f'  ❌ {item["link"][:70]}: {err}')
            time.sleep(3)
        time.sleep(1)

    if sent_ok:
        save_state(sent)
    print(f'  Enviados: {sent_ok}')


if __name__ == '__main__':
    main()
