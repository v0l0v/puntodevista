#!/usr/bin/env python3
"""
health_check.py — Generador de métricas de salud y observabilidad de Punto de Vista.
Inspecciona el estado de los feeds, base de datos SQLite, Circuit Breaker, proxy WARP y almacenamiento.
Escribe atómicamente en data/health.json.
"""
import os
import json
import time
import shutil
import sqlite3
from datetime import datetime, timezone

from config import ensure_warp_proxy
from data_paths import get_data_path, get_db_path

DIR = os.path.dirname(os.path.abspath(__file__))
HEALTH_PATH = get_data_path('health.json')
FEEDS_PATH = get_data_path('feeds.json')
CIRCUIT_PATH = get_data_path('.gemini_circuit.json')
PODCAST_META_PATH = get_data_path('podcast_meta.json')
DB_PATH = get_db_path()

def get_iso_now():
    return datetime.now(timezone.utc).isoformat()

def format_timestamp(ts):
    if not ts:
        return None
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()

def check_circuit_breaker():
    if not os.path.exists(CIRCUIT_PATH):
        return {'state': 'CLOSED', 'reason': None, 'remaining_seconds': 0}
    try:
        with open(CIRCUIT_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        until = data.get('blocked_until', 0)
        remaining = max(0, int(until - time.time()))
        if remaining > 0:
            return {
                'state': 'OPEN',
                'reason': data.get('reason'),
                'remaining_seconds': remaining
            }
    except Exception:
        pass
    return {'state': 'CLOSED', 'reason': None, 'remaining_seconds': 0}

def check_database():
    stats = {'articles_total': 0, 'podcasts_total': 0, 'status': 'missing'}
    if not os.path.exists(DB_PATH):
        return stats
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM articles")
        stats['articles_total'] = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM podcasts")
        stats['podcasts_total'] = c.fetchone()[0]
        stats['status'] = 'ok'
        conn.close()
    except Exception as e:
        stats['status'] = f'error: {e}'
    return stats

def check_feeds():
    stats = {
        'total_items': 0,
        'updated_at': None,
        'sources_count': {},
        'status': 'missing'
    }
    if not os.path.exists(FEEDS_PATH):
        return stats
    try:
        mtime = os.path.getmtime(FEEDS_PATH)
        stats['updated_at'] = format_timestamp(mtime)
        with open(FEEDS_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        items = data.get('items', []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        stats['total_items'] = len(items)
        counts = {}
        for item in items:
            src = item.get('_source') or item.get('source') or 'unknown'
            counts[src] = counts.get(src, 0) + 1
        stats['sources_count'] = counts
        stats['status'] = 'ok'
    except Exception as e:
        stats['status'] = f'error: {e}'
    return stats

def check_podcast_meta():
    stats = {'total_episodes': 0, 'latest_date': None, 'status': 'missing'}
    if not os.path.exists(PODCAST_META_PATH):
        return stats
    try:
        with open(PODCAST_META_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list) and len(data):
            stats['total_episodes'] = len(data)
            stats['latest_date'] = data[-1].get('date')
            stats['status'] = 'ok'
    except Exception as e:
        stats['status'] = f'error: {e}'
    return stats

def check_disk():
    try:
        total, used, free = shutil.disk_usage(DIR)
        return {
            'total_gb': round(total / (1024 ** 3), 1),
            'used_gb': round(used / (1024 ** 3), 1),
            'free_gb': round(free / (1024 ** 3), 1),
            'free_percent': round((free / total) * 100, 1)
        }
    except Exception:
        return None

def generate_health_report():
    warp_active = ensure_warp_proxy()
    circuit = check_circuit_breaker()
    db_stats = check_database()
    feeds_stats = check_feeds()
    pod_stats = check_podcast_meta()
    disk = check_disk()

    # Evaluación de estado general
    overall_status = "healthy"
    issues = []

    if feeds_stats['status'] != 'ok' or feeds_stats['total_items'] == 0:
        overall_status = "degraded"
        issues.append("feeds.json no disponible o vacío")

    if circuit['state'] == 'OPEN':
        overall_status = "degraded"
        issues.append(f"Circuit Breaker activo ({circuit['remaining_seconds']}s restantes)")

    if disk and disk['free_percent'] < 10:
        overall_status = "warning"
        issues.append("Espacio libre en disco inferior al 10%")

    report = {
        'status': overall_status,
        'generated_at': get_iso_now(),
        'issues': issues,
        'pipeline': {
            'last_feeds_update': feeds_stats['updated_at'],
            'warp_proxy_active': warp_active,
            'circuit_breaker': circuit
        },
        'feeds': {
            'total_entries': feeds_stats['total_items'],
            'sources_tracked': len(feeds_stats['sources_count']),
            'sources_breakdown': feeds_stats['sources_count']
        },
        'database': db_stats,
        'podcast': pod_stats,
        'system': {
            'disk': disk
        }
    }

    # Escritura atómica
    tmp_path = HEALTH_PATH + '.tmp'
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, HEALTH_PATH)
        print(f"✅ Reporte de salud generado atómicamente en {HEALTH_PATH} (Estado: {overall_status})")
    except Exception as e:
        print(f"⚠️ Error guardando health.json: {e}")
        if os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except: pass

    return report

if __name__ == '__main__':
    generate_health_report()
