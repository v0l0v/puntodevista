#!/usr/bin/env python3
"""Script de alerta para fallos en cron y pipelines de Punto de Vista."""
import os
import sys
import json
import requests

DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG = {}
config_path = os.path.join(DIR, 'config.json')
if os.path.exists(config_path):
    try:
        with open(config_path, encoding='utf-8') as f:
            CONFIG = json.load(f)
    except Exception:
        pass

TG_TOKEN = os.environ.get('TG_TOKEN') or CONFIG.get('TG_TOKEN')
TG_CHAT_ID = os.environ.get('TG_CHAT_ID') or CONFIG.get('TG_CHAT_ID')

def send_alert(message):
    if not TG_TOKEN or not TG_CHAT_ID:
        print("⚠️ No hay TG_TOKEN o TG_CHAT_ID configurado para alertas.")
        return False
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": f"🚨 <b>PDV Error Alert</b>\n\n{message}",
        "parse_mode": "HTML"
    }
    try:
        resp = requests.post(url, json=payload, timeout=15)
        return resp.status_code == 200
    except Exception as e:
        print(f"Error enviando alerta: {e}")
        return False

if __name__ == '__main__':
    msg = sys.argv[1] if len(sys.argv) > 1 else "Fallo no especificado en el proceso diario."
    send_alert(msg)
