#!/usr/bin/env python3
"""
daily_podcast.py — Generador del Podcast Diario de 'Punto de vista' (Formato Monovoz: Roberto)
Estructura editorial en 4 Actos:
 1. Titulares rápidos (180s): Roberto repasa las noticias del día agrupadas por medio.
 2. Tema central & Linaje Visual: Roberto profundiza en el proyecto estrella conectándolo con archive.db.
 3. Disparador Creativo: Roberto propone un reto práctico y tangible para hacer hoy con la cámara.
 4. Cierre coral y despedida.
"""

import json
import os
import random
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path

import requests

DIR = os.path.dirname(os.path.abspath(__file__))
# Asegurar TMPDIR en directorio con permisos de ejecucion para phonemizer / libespeak-ng
user_tmp = os.path.join(DIR, 'tmp_audio')
os.makedirs(user_tmp, exist_ok=True)
os.environ['TMPDIR'] = user_tmp
import tempfile
tempfile.tempdir = user_tmp

from data_paths import get_data_path, get_db_path

OUT_DIR = os.path.join(DIR, 'resumenes')
PODCAST_DIR = os.path.join(DIR, 'podcast')
META_PATH = get_data_path('podcast_meta.json')
DB_PATH = get_db_path()
from config import get_telegram_creds, get_gemini_key, get_gemini_model, get_config, ensure_warp_proxy
from museum_archive import get_museum_treasure
from photo_enricher import analyze_daily_facets, build_editorial_facet_prompts

ensure_warp_proxy()
TG_TOKEN, TG_CHAT_ID = get_telegram_creds()
GEMINI_KEY = get_gemini_key()
_PREFERRED_MODEL = get_gemini_model('gemini-3.5-flash-lite')
GEMINI_MODELS = [
    _PREFERRED_MODEL,
    'gemini-3.5-flash-lite',
    'gemini-3.1-flash-lite',
    'gemini-3.5-flash',
    'gemini-3.6-flash',
    'gemma-4-26b-a4b-it',
    'gemini-3-flash-preview',
    'gemini-flash-latest',
]
GEMINI_MODELS = list(dict.fromkeys([m for m in GEMINI_MODELS if m]))

TTS_ENGINE = os.environ.get('TTS_ENGINE', 'kokoro')
TTS_VOICE = os.environ.get('TTS_VOICE', 'es-ES-AlvaroNeural')
TTS_RATE = os.environ.get('TTS_RATE', '-3%')

# Trío de locutores de Punto de Vista
VOICE_CAST = {
    'ROBERTO': 'em_alex',    # Conductor principal y noticias
    'BEATRIZ': 'ef_dora',    # Análisis central y linaje histórico
    'NICOLAS': 'em_santa',   # Reto práctico y taller creativo
}

KOKORO_ONNX = os.path.join(DIR, 'kokoro_models', 'kokoro-v1.0.onnx')
KOKORO_VOICES = os.path.join(DIR, 'kokoro_models', 'voices-v1.0.bin')

MAX_RETRIES = 3
RETRY_DELAY = 10

TITLE_MARKER = '---TITLE---'
LOCUTABLE_MARKER = '---LOCUTABLE---'

DIAS_SEMANA_ES = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
MESES_ES = [
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
]


def fmt_fecha_es(d):
    return f'{d.day} de {MESES_ES[d.month - 1]} de {d.year}'


def fmt_fecha_completa_es(d):
    dia_sem = DIAS_SEMANA_ES[d.weekday()]
    return f'{dia_sem}, {d.day} de {MESES_ES[d.month - 1]} de {d.year}'


def get_episode_number(target_date, meta_path=META_PATH):
    try:
        if os.path.exists(meta_path):
            with open(meta_path, encoding='utf-8') as f:
                meta = json.load(f)
            dates = sorted(set(m.get('date') for m in meta if m.get('date')))
            target_iso = target_date.isoformat()
            if target_iso in dates:
                return dates.index(target_iso) + 1
            else:
                prior_dates = [d for d in dates if d < target_iso]
                return len(prior_dates) + 1
    except Exception:
        pass
    return 1


def find_latest_podcast(target_date=None):
    files = sorted(Path(OUT_DIR).glob('*.podcast.md'), reverse=True)
    if target_date:
        for f in files:
            if target_date.isoformat() in f.name:
                return f
        return None
    return files[0] if files else None


def gemini_request(prompt):
    if not GEMINI_KEY:
        print("  ⚠️ No hay GEMINI_KEY configurada.")
        return None
    ensure_warp_proxy()
    body = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {
            'temperature': 0.7,
            'maxOutputTokens': 8192,
        }
    }
    for model_name in GEMINI_MODELS:
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_KEY}'
        for attempt in range(MAX_RETRIES):
            try:
                resp = requests.post(url, json=body, timeout=120)
                if resp.status_code == 200:
                    result = resp.json()
                    candidates = result.get('candidates', [])
                    if candidates and 'content' in candidates[0]:
                        parts = candidates[0]['content'].get('parts', [])
                        if parts and 'text' in parts[0]:
                            print(f'  ✅ Respuesta recibida usando modelo {model_name}')
                            return parts[0]['text'].strip()
                elif resp.status_code == 429:
                    wait = RETRY_DELAY * (attempt + 1)
                    print(f'  Cuota excedida en {model_name}, reintentando en {wait}s...')
                    time.sleep(wait)
                    continue
                elif resp.status_code == 404:
                    print(f'  Modelo {model_name} no disponible (404), pasando al siguiente...')
                    break
                else:
                    print(f'  HTTP {resp.status_code} en {model_name}: {resp.text[:200]}')
                    break
            except Exception as e:
                print(f'  Error en petición a {model_name} (intento {attempt + 1}): {e}')
                time.sleep(3)
    print('  ❌ Se agotaron todos los modelos y reintentos.')
    return None


def parse_digest_markdown(filepath):
    """Parsea el archivo digest-{fecha}.podcast.md extrayendo todos los artículos con su texto completo."""
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return []

    sections = re.split(r'\n###\s+', content)
    articles = []
    for sec in sections[1:]:
        lines = sec.split('\n')
        source = lines[0].strip()
        body = '\n'.join(lines[1:])
        parts = re.split(r'\n\*\*([^*]+)\*\*\n', body)
        if len(parts) > 1:
            for i in range(1, len(parts), 2):
                title = parts[i].strip()
                text = parts[i+1].strip() if i+1 < len(parts) else ''
                author_match = re.search(r'Fotógrafos?:\s*([^\n]+)', text)
                author = author_match.group(1).strip() if author_match else ''
                articles.append({
                    'source': source,
                    'title': title,
                    'photographer': author,
                    'summary': text[:600],
                    'full_text': text
                })
        else:
            articles.append({
                'source': source,
                'title': lines[0],
                'photographer': '',
                'summary': body[:600],
                'full_text': body
            })
    return articles


def get_articles_for_day(target_date_str=None):
    """Obtiene todos los artículos de las últimas 24 horas desde el digest markdown y archive.db."""
    target_dt = date.fromisoformat(target_date_str) if target_date_str else date.today()
    target_iso = target_dt.isoformat()
    yesterday_iso = date.fromordinal(target_dt.toordinal() - 1).isoformat()

    articles = []
    seen_titles = set()

    # 1. Prioridad: Leer el digest generado para esta fecha
    digest_path = os.path.join(OUT_DIR, f'digest-{target_iso}.podcast.md')
    if os.path.exists(digest_path):
        parsed = parse_digest_markdown(digest_path)
        for a in parsed:
            tit_key = (a.get('title') or '').strip().lower()
            if tit_key and tit_key not in seen_titles and len(a.get('full_text', '')) > 20:
                seen_titles.add(tit_key)
                articles.append(a)

    # 2. Complementar con archive.db para las últimas 24 horas (hoy y ayer)
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("""
                SELECT id, url, source, title, photographer, published_date, summary, full_text, image_url
                FROM articles
                WHERE published_date IN (?, ?) OR created_at >= ?
                ORDER BY published_date DESC, id DESC
            """, (target_iso, yesterday_iso, f'{yesterday_iso} 00:00:00'))
            rows = [dict(r) for r in c.fetchall()]
            conn.close()
            for r in rows:
                tit_key = (r.get('title') or '').strip().lower()
                if tit_key and tit_key not in seen_titles:
                    seen_titles.add(tit_key)
                    articles.append(r)
        except Exception as e:
            print(f'  ⚠️ Error leyendo archive.db: {e}')

    return articles


# --- Ponderación editorial por cadencia de publicación ---
SOURCE_CADENCE_WEIGHT = {
    # Publicación semanal / quincenal / baja frecuencia (Premio a la rareza/artesanal)
    'tpj': 1.6,
    'aperture': 1.6,
    'huck': 1.6,
    '1854': 1.6,
    'clavoardiendo': 1.6,
    'phroom': 1.6,
    'casualphotophile': 1.6,
    'shootitwithfilm': 1.4,

    # Publicación media (2-4 veces por semana)
    'blind': 1.2,
    'booooooom': 1.2,
    'asx': 1.2,
    'magnum': 1.2,
    'lensculture': 1.2,
    'featureshoot': 1.2,
    'aintbad': 1.2,

    # Publicación diaria / alto volumen
    'colossal': 1.0,
    'lomography': 1.0,
    '35mmc': 1.0,
    'c41': 1.0,
    'kosmofoto': 1.0,
    'odlp': 1.0,
    'emulsive': 1.0,
}


def get_recent_primary_sources(target_date, days=7, meta_path=META_PATH):
    """Devuelve un historial de fuentes que han sido tema principal en los últimos N días."""
    history = {}
    target_dt = date.fromisoformat(target_date) if isinstance(target_date, str) else target_date

    if os.path.exists(meta_path):
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            for m in meta:
                d_str = m.get('date')
                if not d_str:
                    continue
                try:
                    d = date.fromisoformat(d_str)
                    diff = (target_dt - d).days
                    if 0 < diff <= days:
                        src = (m.get('primary_source') or '').lower()
                        if src:
                            if src not in history or diff < history[src]:
                                history[src] = diff
                except Exception:
                    pass
        except Exception:
            pass

    # Complementar buscando en guiones anteriores si meta no tenía primary_source
    for i in range(1, days + 1):
        prev_d = date.fromordinal(target_dt.toordinal() - i)
        guion_p = os.path.join(OUT_DIR, f'podcast-{prev_d.isoformat()}.guion.txt')
        if os.path.exists(guion_p):
            try:
                txt = open(guion_p, encoding='utf-8').read()
                for src_id in SOURCE_CADENCE_WEIGHT.keys():
                    if src_id not in history and (f'[{src_id.upper()}]' in txt or f'MEDIO: {src_id.upper()}' in txt):
                        history[src_id] = i
            except Exception:
                pass

    return history


def get_rotation_factor(source_id, history):
    """Calcula el factor de rotación (penalización si ha salido recientemente, bonificación por frescura)."""
    s = (source_id or '').lower().strip()
    if s not in history:
        return 1.60  # No ha salido en los últimos días o nunca

    days_ago = history[s]
    if days_ago == 1:
        return 0.15  # Salió ayer -> penalización del 85%
    elif days_ago == 2:
        return 0.40  # Salió hace 2 días
    elif days_ago == 3:
        return 0.70  # Salió hace 3 días
    elif days_ago == 4:
        return 1.10
    elif days_ago == 5:
        return 1.35
    else:
        return 1.60


def extract_photographer_candidates(article):
    """Extrae posibles nombres propios de fotógrafos desde el campo photographer o desde el título."""
    names = []
    p = (article.get('photographer') or '').strip()
    if p and len(p.split()) >= 2 and len(p) < 45:
        names.append(p)

    title = article.get('title') or ''
    # Patrones comunes en títulos periodísticos de fotografía
    patterns = [
        r'(?:with|by|con|de|sobre|,)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)',
        r'^([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)(?:\s*[:—–\']|\s+Takes|\s+Shoots|\s+Hunts|\s+Herds|\s+repasa|\s+muestra)',
        r'([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\’s\b'
    ]
    ignore = {'Blind Magazine', 'Feature Shoot', 'Casual Photophile', 'Photographic Journal', 'British Journal', 'Foto Colectania', 'Donostia Cuatro', 'New York', 'North Carolina', 'Sound Squad'}
    for pat in patterns:
        for match in re.findall(pat, title):
            cand = match.strip()
            if cand not in ignore and cand not in names and len(cand.split()) >= 2 and len(cand) < 40:
                names.append(cand)
    return names


def find_monographic_counterpart(article, db_path=DB_PATH):
    """
    Busca si en archive.db existe otra obra del mismo fotógrafo.
    Devuelve (counterpart_dict, mode, author_name) donde mode es 'monografico_cruzado' o 'monografico_mismo_medio'.
    """
    if not os.path.exists(db_path) or not article:
        return None, None, None

    art_id = article.get('id', 0)
    art_url = article.get('url') or article.get('link') or ''
    art_title = (article.get('title') or '').strip()
    src = (article.get('source') or '').lower().strip()

    names = extract_photographer_candidates(article)
    if not names:
        return None, None, None

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Nivel 1: Monográfico Cruzado (otro medio)
    for name in names:
        try:
            c.execute("""
                SELECT id, url, source, title, photographer, published_date, summary, full_text
                FROM articles
                WHERE id != ? AND url != ? AND title != ? AND LOWER(source) != ?
                  AND (photographer LIKE ? OR title LIKE ? OR summary LIKE ?)
                ORDER BY id DESC LIMIT 1
            """, (art_id, art_url, art_title, src, f'%{name}%', f'%{name}%', f'%{name}%'))
            row = c.fetchone()
            if row:
                conn.close()
                return dict(row), 'monografico_cruzado', name
        except Exception:
            pass

    # Nivel 2: Monográfico Mismo Medio (excepción: otra obra anterior diferente en la misma revista)
    for name in names:
        try:
            c.execute("""
                SELECT id, url, source, title, photographer, published_date, summary, full_text
                FROM articles
                WHERE id != ? AND url != ? AND title != ? AND LOWER(source) == ?
                  AND (photographer LIKE ? OR title LIKE ?)
                ORDER BY id DESC LIMIT 1
            """, (art_id, art_url, art_title, src, f'%{name}%', f'%{name}%'))
            row = c.fetchone()
            if row:
                conn.close()
                return dict(row), 'monografico_mismo_medio', name
        except Exception:
            pass

    conn.close()
    return None, None, None


def had_recent_monograph(target_date, days=3, meta_path=META_PATH):
    """Verifica si en los últimos N días ya se emitió un episodio monográfico."""
    target_dt = date.fromisoformat(target_date) if isinstance(target_date, str) else target_date
    if os.path.exists(meta_path):
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            for m in meta:
                d_str = m.get('date')
                if not d_str:
                    continue
                try:
                    d = date.fromisoformat(d_str)
                    diff = (target_dt - d).days
                    if 0 < diff <= days and m.get('monographic'):
                        return True
                except Exception:
                    pass
        except Exception:
            pass
    return False


def select_primary_article(articles, target_date=None, meta_path=META_PATH):
    """
    Selecciona el artículo protagonista del podcast aplicando los 4 baremos editoriales:
      1. Filtro del 50% de longitud relativa respecto al máximo del día.
      2. Factor de rotación reciente (penaliza repeticiones continuas).
      3. Bonus de cadencia (premia medios de publicación semanal/artesanal).
      4. Bonus Monográfico (premia proyectos con obra gemela del mismo autor, regulado cada 3 días).
    """
    if not articles:
        return None
    if len(articles) == 1:
        return articles[0]

    d = target_date or date.today()
    d_iso = d.isoformat() if isinstance(d, date) else str(d)
    history = get_recent_primary_sources(d_iso, days=7, meta_path=meta_path)
    recent_monograph = had_recent_monograph(d_iso, days=3, meta_path=meta_path)

    # 1. Medir longitudes
    lengths = []
    for a in articles:
        text = a.get('full_text') or a.get('summary') or ''
        lengths.append(len(text.strip()))

    max_len = max(lengths) if lengths else 0
    if max_len == 0:
        return articles[0]

    # Umbral del 50% (con un suelo mínimo absoluto de 600 caracteres)
    threshold = max(600, int(max_len * 0.50))
    candidates = []
    for a in articles:
        t_len = len((a.get('full_text') or a.get('summary') or '').strip())
        if t_len >= threshold:
            candidates.append((a, t_len))

    # Fallback si ningún artículo supera el suelo
    if not candidates:
        candidates = [(a, len((a.get('full_text') or a.get('summary') or '').strip())) for a in articles]

    print(f"\n  📊 Evaluación editorial de tema principal ({len(candidates)}/{len(articles)} superaron el corte del 50% [≥{threshold} chars]):")
    if recent_monograph:
        print("    ℹ️ Regulador Monográfico activo: Hubo monográfico en los últimos 3 días (bonus en pausa para alternancia temática).")

    scored = []
    for a, t_len in candidates:
        src = (a.get('source') or '').lower().strip()
        # Baremo 1: Base de longitud (1.0 a 1.4)
        len_ratio = min(1.0, t_len / max_len)
        base_score = 1.0 + (len_ratio - 0.5) * 0.8

        # Baremo 2: Factor de rotación
        rot_factor = get_rotation_factor(src, history)

        # Baremo 3: Bonus de cadencia
        cadence_bonus = SOURCE_CADENCE_WEIGHT.get(src, 1.2)

        # Baremo 4: Oportunidad Monográfica
        mono_match, mono_mode, mono_author = find_monographic_counterpart(a, DB_PATH)
        mono_bonus = 1.0
        mono_desc = "sin mono"
        if mono_match and not recent_monograph:
            if mono_mode == 'monografico_cruzado':
                mono_bonus = 1.40
                mono_desc = f"★ MONO-CRUZADO ({mono_author} en {mono_match.get('source', '').upper()})"
            elif mono_mode == 'monografico_mismo_medio':
                mono_bonus = 1.20
                mono_desc = f"★ MONO-MISMO-MEDIO ({mono_author})"
        elif mono_match and recent_monograph:
            mono_desc = f"mono-pausa ({mono_author})"

        total_score = base_score * rot_factor * cadence_bonus * mono_bonus
        scored.append((total_score, a, t_len, base_score, rot_factor, cadence_bonus, mono_bonus, mono_desc))

    scored.sort(key=lambda x: x[0], reverse=True)

    for sc, a, t_len, b_sc, r_fc, c_bn, m_bn, m_dsc in scored[:8]:
        src_name = a.get('source', '').upper()
        title = (a.get('title') or 'Sin título')[:38]
        days_ago = history.get(a.get('source', '').lower())
        rot_info = f"hace {days_ago}d" if days_ago else "fresco"
        print(f"    • [{src_name:10s}] {title:38s} | len:{t_len:5d} ({b_sc:.2f}) | rot:{r_fc:.2f} ({rot_info}) | cad:{c_bn:.2f} | {m_dsc} => SCORE: {sc:.3f}")

    winner = scored[0][1]
    return winner


def get_historical_counterpart(primary_article):
    """
    Busca en el archivo la contraparte histórica para el Linaje Visual:
      Nivel 1: Monográfico cruzado (mismo fotógrafo en otra revista).
      Nivel 2: Monográfico mismo medio (excepción: obra anterior diferente del autor).
      Nivel 3: Linaje conceptual y estético mediante sqlite-vec (o FTS5) en otra revista.
    """
    if not os.path.exists(DB_PATH) or not primary_article:
        return None, 'none'

    # Nivel 1 & 2: Intentar conexión monográfica de autor
    mono_match, mono_mode, mono_author = find_monographic_counterpart(primary_article, DB_PATH)
    if mono_match:
        mono_match['lineage_mode'] = mono_mode
        mono_match['author_name'] = mono_author
        return mono_match, mono_mode

    # Nivel 3: Búsqueda Semántica Vectorial en otra revista (sqlite-vec)
    try:
        import vector_search
        candidates = vector_search.find_visual_lineage(primary_article.get('id', 0), limit=2)
        if candidates:
            candidates[0]['lineage_mode'] = 'conceptual_vector'
            return candidates[0], 'conceptual_vector'
    except Exception:
        pass

    # Fallback por FTS5 en otra revista
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    title_words = re.findall(r'\b[a-zA-ZáéíóúÁÉÍÓÚñÑ]{4,}\b', (primary_article.get('title', '') + ' ' + (primary_article.get('summary') or '')).lower())
    stop_words = {'para', 'como', 'este', 'esta', 'sobre', 'desde', 'with', 'from', 'that', 'this', 'have', 'more', 'foto', 'photo'}
    filtered = [w for w in title_words if w not in stop_words][:5]

    counterparts = []
    if filtered:
        try:
            c.execute("""
                SELECT a.id, a.url, a.source, a.title, a.photographer, a.published_date, a.summary, a.full_text
                FROM articles_fts fts
                JOIN articles a ON a.id = fts.rowid
                WHERE articles_fts MATCH ? AND a.id != ? AND a.source != ?
                ORDER BY rank LIMIT 2;
            """, (' OR '.join(filtered), primary_article.get('id', 0), primary_article.get('source', '')))
            counterparts = [dict(r) for r in c.fetchall()]
        except Exception:
            pass

    if not counterparts:
        c.execute("""
            SELECT id, url, source, title, photographer, published_date, summary, full_text
            FROM articles
            WHERE id != ? AND source != ? AND summary != ''
            ORDER BY RANDOM() LIMIT 1;
        """, (primary_article.get('id', 0), primary_article.get('source', '')))
        counterparts = [dict(r) for r in c.fetchall()]

    conn.close()
    if counterparts:
        counterparts[0]['lineage_mode'] = 'conceptual_fts'
        return counterparts[0], 'conceptual_fts'
    return None, 'none'


def build_editorial_podcast_prompt(articles, primary, historical, episode_date, ep_num, museum_piece=None, facet_prompts=None):
    """Construye el prompt editorial para Roberto, Beatriz y Nicolás en 4 Actos."""
    d = episode_date or date.today()
    fecha_completa = fmt_fecha_completa_es(d)

    roberto_radar_block = (facet_prompts.get('roberto_radar') or '') if facet_prompts else ''
    beatriz_book_block = (facet_prompts.get('beatriz_book') or '') if facet_prompts else ''
    nicolas_lab_block = (facet_prompts.get('nicolas_lab') or '') if facet_prompts else ''

    # Agrupar titulares por medio / revista
    by_source = {}
    for a in articles:
        src = a.get('source', 'Otras fuentes').upper()
        if src not in by_source:
            by_source[src] = []
        by_source[src].append(a)

    headlines_by_source_text = []
    for src, items in by_source.items():
        headlines_by_source_text.append(f"📰 MEDIO: {src}")
        for item in items[:6]:
            autor = item.get('photographer') or 'Autor'
            tit = item.get('title', 'Sin título')
            sumario = (item.get('summary') or item.get('full_text', ''))[:450].replace('\n', ' ')
            headlines_by_source_text.append(f"  • {tit} (por {autor}): {sumario}")
        headlines_by_source_text.append("")

    headlines_block = "\n".join(headlines_by_source_text)

    hist_text = ""
    if historical:
        mode = historical.get('lineage_mode', 'conceptual_vector')
        author = historical.get('author_name') or historical.get('photographer') or primary.get('photographer') or 'el mismo autor'
        if mode == 'monografico_cruzado':
            hist_header = f"🌟 ENFOQUE MONOGRÁFICO ESPECIAL (MISMO AUTOR EN OTRA REVISTA: {author.upper()}):"
            hist_directive = f"⚠️ INSTRUCCIÓN EDITORIAL: Hoy es un episodio MONOGRÁFICO sobre {author}. En el Acto 2 no compares con otro fotógrafo, sino que analiza la trayectoria y evolución de {author} contrastando su obra de hoy ({primary.get('title')}) con su otra obra ({historical.get('title')}) publicada en {historical.get('source', '').upper()}."
        elif mode == 'monografico_mismo_medio':
            hist_header = f"🌟 ENFOQUE MONOGRÁFICO ESPECIAL (EVOLUCIÓN AUTORAL DE {author.upper()}):"
            hist_directive = f"⚠️ INSTRUCCIÓN EDITORIAL: Hoy es un episodio MONOGRÁFICO sobre {author}. En el Acto 2 profundiza en la evolución de su mirada comparando el proyecto de hoy con su trabajo anterior ({historical.get('title')})."
        else:
            hist_header = "PROYECTO HISTÓRICO DEL ARCHIVO (LINAJE VISUAL EN ARCHIVE.DB):"
            hist_directive = "En el Acto 2 conecta la obra de hoy con esta referencia histórica, explicando el diálogo estético y conceptual entre ambas miradas."

        hist_text = f"""
{hist_header}
{hist_directive}
- Título de referencia: {historical.get('title')}
- Medio/Revista de referencia: {historical.get('source', '').upper()}
- Autor/a: {historical.get('photographer') or author}
- Fecha original: {historical.get('published_date', 'Archivo')}
- Resumen/Esencia: {(historical.get('summary') or historical.get('full_text', ''))[:500]}
"""

    museum_text = ""
    inst_mention = historical.get('title') if historical else 'el archivo histórico'
    if museum_piece:
        inst = museum_piece.get('institution', 'Colección de Museo')
        m_tit = museum_piece.get('title', 'Obra patrimonial')
        m_aut = museum_piece.get('photographer', 'Autor histórico')
        m_fecha = museum_piece.get('date', 'Fondo histórico')
        m_tec = museum_piece.get('technique', '')
        m_notas = museum_piece.get('curatorial_notes', '')

        museum_text = f"""
🏛️ JOYA DEL ARCHIVO / LINAJE DE MUSEO ({inst.upper()}):
- Institución custodia: {inst}
- Obra patrimonial: {m_tit} ({m_fecha})
- Fotógrafo/a o artífice: {m_aut}
- Técnica / Fondo: {m_tec or 'Fondo fotográfico patrimonial'}
- Notas curatoriales del museo: {m_notas}

⚠️ INSTRUCCIÓN EDITORIAL PARA BEATRIZ (LINAJE DE MUSEO):
En el Acto 2, Beatriz enriquece su análisis conectando la mirada del proyecto contemporáneo de hoy con esta joya histórica custodiada en {inst}. Cita expresamente la institución ({inst}) y a {m_aut} con '{m_tit}', mostrando a la audiencia cómo esta inquietud o técnica visual ya latía en las colecciones de los grandes centros y museos del mundo.
"""
        inst_mention = f"{inst} con '{m_tit}' de {m_aut}"

    return f"""Eres el equipo de redacción y locución de 'Punto de vista', el podcast diario de cultura visual y fotografía.
Equipo de locutores:
- ROBERTO (Conductor principal): Cercano, dinámico, culto, con excelente ritmo periodístico. Abre el podcast, repasa las noticias del día, presenta a los compañeros y hace el cierre.
- BEATRIZ (Especialista en Historia, Crítica y Cultura Visual): Lúcida, apasionada, ensayística pero extraordinariamente cercana, cálida y pedagógica. No habla para teóricos ni académicos de museo, sino para personas que aman hacer fotos y quieren educar su mirada, entender por qué una imagen funciona e inspirarse para sus propias tomas. Traduce las decisiones visuales complejas a lecciones fotográficas y emocionales tangibles, sin pedantería.
- NICOLÁS (Maestro de Taller y Disparador Creativo): Práctico, motivador, cómplice y con un punto gamberro y apasionado. Es quien baja toda la teoría al asfalto para sacudir al oyente y empujarlo a salir a fotografiar hoy mismo con retos estimulantes, frescos y atrevidos.

Fecha de hoy: {fecha_completa} (Episodio #{ep_num}).

MATERIAL DE LAS ÚLTIMAS 24 HORAS:
{headlines_block}

PROYECTO PROTAGONISTA DEL DÍA:
- Título: {primary.get('title')}
- Medio: {primary.get('source', '').upper()}
- Autor: {primary.get('photographer') or 'Autor/a reseñado/a'}
- Resumen/Texto completo: {(primary.get('summary') or primary.get('full_text', ''))[:1500]}

{hist_text}

{museum_text}

Debes estructurar tu respuesta EXACTAMENTE en TRES SECCIONES siguiendo esta plantilla obligatoria (sin añadir texto ni etiquetas antes de cada marcador):

[Título sugerente, poético y periodístico en español en una sola línea, sin comillas ni prefijos]
{TITLE_MARKER}
[Resumen editorial conciso en 3 párrafos para el feed y redes sociales destacando:
1. El panorama general de las noticias de hoy (Roberto).
2. El análisis del proyecto protagonista y su linaje histórico con los fondos de museo (Beatriz).
3. El reto creativo del día (Nicolás).]
{LOCUTABLE_MARKER}
[ROBERTO]
[Inicio directo del guion coral con el saludo de Roberto. Cada intervención empieza con [ROBERTO], [BEATRIZ] o [NICOLAS]. El paso entre Roberto y Beatriz, y entre Beatriz y Nicolás es continuo e inmediato, sin música ni pausas intermedias. La única pausa musical (---PAUSA---) se sitúa antes del Acto 4 de cierre.]

REGLAS EDITORIALES Y DE LOCUCIÓN (ESTRICTAS):
- FORMATO DE DIÁLOGO: Cada cambio de voz DEBE empezar exactamente en una línea nueva con [ROBERTO], [BEATRIZ] o [NICOLAS].
- TRANSICIONES CONTINUAS SIN MÚSICA: El paso entre Roberto y Beatriz, y entre Beatriz y Nicolás debe ser orgánico y directo en antena (sin insertar ---PAUSA--- ni cortinillas musicales entre ellos). Roberto llama a Beatriz, Beatriz responde de inmediato; Beatriz llama a Nicolás, Nicolás responde de inmediato.
- COLABORACIÓN Y TRANSICIONES: Los locutores deben interactuar con naturalidad, saludarse brevemente al darse paso y cerrar con fluidez radiofónica.
- RIGOR FACTUAL: NUNCA INVENTES DATOS. Todo se basa estrictamente en el material provisto.
- PUNTUACIÓN Y FLUIDEZ RADIOFÓNICA:
  * Oraciones continuas separadas por puntos y comas.
  * PROHIBIDO usar guiones largos (—), dos puntos (:), puntos suspensivos (...) o paréntesis (...).
- FONÉTICA:
  * Escribe "niusleter" o "niusleters" (nunca newsletter).
  * Escribe "el Magazine de arte online Colosal" (nunca Colossal).
  * Escribe "la revista Buum" (para Booooooom).
  * Escribe "el Ojo de la Fotografía, el O-D-L-P" (para ODLP).
- DIRECTRIZ COMUNITARIA Y CORREOS (ANA DE FOTONISTAS / FOTOLETER):
  * Si en las publicaciones o correos del día hay contenido de Fotonistas o de Ana:
    Menciónalo explícitamente en el repaso de Roberto o al inicio del bloque de Nicolás: "en el niusleter de Fotonistas, Ana nos deja una reflexión imperdible...".
    REGLA DE CERO SPOILERS: NO desveles el contenido ni destripes la carta. Solo presenta la idea o pregunta sugerente para crear intriga y expectación, invitando a la audiencia a suscribirse a su fotoleter.
- TRADUCCIÓN: Títulos de series/obras → traduce al español. Nombres propios → mantén original.

ESTRUCTURA DE LOS 4 ACTOS:

1. ACTO 1: APERTURA & REPASO A LA ACTUALIDAD ([ROBERTO])
   - Apertura de Roberto: "¡Hola, muy buenas! Bienvenidos a Punto de vista, tu dosis diaria de inspiración fotográfica. Hoy es {fecha_completa} y este es el episodio {ep_num}..."
   - Lanza una breve frase intrigante sobre el tema central que analizará luego Beatriz.
   - RECORRIDO DE NOTICIAS: Selecciona entre 6 y 10 noticias destacadas de distintas fuentes del material de las últimas 24 horas.
   - FORMATO PARA CADA NOTICIA:
     * Roberto redacta un bloque de locución completo, sustancial y ameno de aproximadamente 50 a 55 segundos de duración (~115 a 130 palabras por noticia). No un titular de dos líneas: debe explicar el contexto, el autor o protagonistas, la técnica o proyecto, y por qué es relevante hoy en la cultura fotográfica.
     * SEPARA cada noticia de la siguiente insertando en una línea propia la etiqueta de cortinilla:
       ---RAFAGA---
     * La siguiente noticia debe comenzar de nuevo con la etiqueta [ROBERTO] en una línea nueva.
{roberto_radar_block}
   - En la última noticia del bloque, Roberto concluye dando paso con complicidad y de forma directa a Beatriz (sin ráfaga entre ellos para mantener continuidad de antena): "...Y precisamente de esa conexión entre el tiempo, la memoria y la tierra vamos a hablar ahora; porque para profundizar en el gran proyecto de hoy y su diálogo con la historia, os dejo con Beatriz. ¡Hola, Beatriz!"

2. ACTO 2: TEMA CENTRAL, LINAJE VISUAL Y FOTOLIBROS ([BEATRIZ]) (~4 A 5 MINUTOS)
   - [BEATRIZ]: Responde inmediatamente a Roberto y a los oyentes con calidez y complicidad: "¡Hola Roberto! Muchas gracias y muy buenas a todos..."
   - Beatriz se adentra en el PROYECTO PROTAGONISTA del día con profundidad ensayística y sensorial, pero siempre cercana e inspiradora (~550 a 680 palabras).
   - RECURSOS RETÓRICOS Y VARIEDAD EDITORIAL (ESTRICTO):
     * PROHIBIDO usar fórmulas o muletillas repetitivas como "Porque ninguna mirada nace en el vacío" o frases hechas como "no busca el efectismo sino la pausa".
     * Varía la puerta de entrada a la obra: explora cómo la luz modela los volúmenes, la tensión del encuadre y el punto de vista, la empatía y la distancia física con el sujeto, o el juego entre el detalle cotidiano y la atmósfera general.
     * Haz que el oyente visualice la fotografía en su mente como si la tuviera delante y entienda qué decisiones del autor pueden inspirar su propia práctica fotográfica cotidiana.
   - CONEXIÓN CON EL LINAJE DE MUSEO ({inst_mention}):
     * Enlaza la obra de hoy con esta joya patrimonial de museo ({inst_mention}) desde el aprendizaje fotográfico: muestra cómo los grandes maestros históricos ya se enfrentaron a esa misma búsqueda de composición, geometría, emoción o luz que tenemos hoy al mirar por el visor. Cita expresamente la institución y la obra histórica con naturalidad.
{beatriz_book_block}
   - Al concluir, Beatriz da paso directo y enérgico a Nicolás para el reto práctico: "Y ahora, ¿cómo llevamos toda esta reflexión a la práctica en la calle? Nicolás ya tiene preparado el taller del día. ¡Adelante, Nicolás!"

3. ACTO 3: DISPARADOR CREATIVO (EL RETO DEL DÍA) ([NICOLAS]) (~1:15 A 1:30 MINUTOS)
   - [NICOLAS]: Entra inmediatamente recogiendo el testigo con energía, frescura y complicidad en antena (~170 a 200 palabras).
     * VARIEDAD DE ENTRADA: Varía su saludo según su carácter espontáneo y entusiasta (evita empezar siempre con "¡Gracias compañeros! Qué gran análisis..."). Ejemplos: "¡Oído cocina, Beatriz! Menudo festín visual nos acabas de servir...", "¡Qué delicia de viaje, Beatriz! Pero aquí no nos quedamos en la teoría...", "¡Tomo el testigo con la cámara al hombro! Dejemos las pantallas y vamos al lío...", etc.
   - INSPIRACIÓN EN LAS HISTORIAS DEL DÍA:
     * Nicolás conecta el reto de hoy directamente con el estilo, la técnica, el dilema o la actitud de alguno de los fotógrafos o noticias comentadas hoy por Roberto o Beatriz (la audacia callejera y cercanía de Frank Horvat, la geometría de Stieglitz, la complicidad humana de Lecomte, el humor ácido de Parr o Goldberger, la energía de Klein, o la atmósfera del proyecto protagonista).
   - EL RETO FOTOGRÁFICO DE HOY (ANTIRREPETICIÓN Y RETOS ATREVIDOS):
     * PROHIBIDO repetir siempre "buscar texturas en paredes desgastadas o sombras en el suelo".
     * Diseña un reto práctico con una restricción creativa clara y motivante.
     * Alterna periódicamente con retos atrevidos, descarados o gamberros de fotografía activa:
       - El reto de la proximidad física (obligarse a entrar a un metro de distancia del sujeto).
       - Disparar desde la cintura sin mirar por el visor (cazar el ritmo espontáneo de la calle).
       - La caza del absurdo cotidiano o la ironía visual (yuxtaponer carteles, reflejos o gestos involuntarios).
       - El destello a pleno sol (usar el flash en la calle para congelar contrastes agresivos).
       - La regla de los 5 segundos (llegar a una esquina y disparar antes de 5 segundos confiando en el primer instinto).
       - El retrato espontáneo (pedir un retrato rápido a un desconocido con una sonrisa y una sola pregunta).
   - LA PREGUNTA PREVIA AL DISPARO:
     * Cierra el reto con una pregunta detonante que el fotógrafo debe hacerse antes de apretar el obturador.
   ---PAUSA---

4. ACTO 4: CIERRE Y DESPEDIDA ([ROBERTO] & [BEATRIZ]) (~45 SEGUNDOS)
   - [ROBERTO]: "Fantástico reto el de Nicolás para hoy."
   - [BEATRIZ]: Añade una última reflexión inspiradora invitando a salir a mirar el mundo.
   - [ROBERTO]: Cierra despidiendo el episodio: "Cargad baterías o carretes, y nos escuchamos mañana. ¡Buenas fotos!"

DURACIÓN TOTAL ESTIMADA: ~1600 a 2200 palabras (~13 a 17 minutos de emisión con ráfagas musicales de 6 segundos entre noticias)."""


def parse_summary(summary):
    podcast_title = ''
    resumen = ''
    locutable = summary
    remaining = summary

    if TITLE_MARKER in remaining:
        pre, post = remaining.split(TITLE_MARKER, 1)
        podcast_title = pre.strip()
        remaining = post

    if LOCUTABLE_MARKER in remaining:
        # Usamos rsplit para que locutable sea siempre lo que va tras el ÚLTIMO marcador
        loc_parts = remaining.rsplit(LOCUTABLE_MARKER, 1)
        locutable = loc_parts[1].strip()
        resumen_candidate = loc_parts[0].strip()
        if not resumen:
            resumen = resumen_candidate
    else:
        resumen = remaining.strip()

    # Si locutable todavía contiene texto huérfano antes del primer locutor [ROBERTO|BEATRIZ|NICOLAS|CLARA]
    speaker_match = re.search(r'\[(ROBERTO|BEATRIZ|NICOLAS|CLARA)\]', locutable, re.IGNORECASE)
    if speaker_match:
        preamble = locutable[:speaker_match.start()].strip()
        if preamble:
            # Si el resumen estaba vacío o solo tenía el título, recuperamos el preámbulo como resumen
            if not resumen or resumen == podcast_title:
                resumen = preamble
            locutable = locutable[speaker_match.start():].strip()

    if not podcast_title and resumen:
        for ln in resumen.split('\n'):
            ln = ln.strip()
            if not ln or re.match(r'^---+', ln) or re.match(r'^#\s*Podcast\b', ln, re.IGNORECASE):
                continue
            m_title = re.match(r'^(?:#+\s*)?(?:Título|Titulo):\s*(.+)', ln, re.IGNORECASE)
            if m_title:
                podcast_title = m_title.group(1).strip()
                break
            if not podcast_title:
                podcast_title = ln
                break

    # Limpiar prefijos residuales de título tipo '# Título:' o '**Título:**'
    podcast_title = re.sub(r'^(?:#+\s*)?(?:Título|Titulo):\s*', '', podcast_title, flags=re.IGNORECASE).strip()
    # Limpiar posibles marcadores residuales al inicio del resumen
    resumen = re.sub(r'^(?:---[A-Z_]+---\s*)+', '', resumen).strip()

    return podcast_title, resumen, locutable


def get_day_music(target_date=None):
    d = target_date or date.today()
    weekday = d.weekday()  # 0=Lunes, 6=Domingo
    day_patterns = [
        'day_0_lunes.mp3',
        'day_1_martes.mp3',
        'day_2_miercoles.mp3',
        'day_3_jueves.mp3',
        'day_4_viernes.mp3',
        'day_5_sabado.mp3',
        'day_6_domingo.mp3'
    ]
    track_name = day_patterns[weekday]
    track_path = os.path.join(DIR, 'assets', 'mp3', track_name)
    if os.path.exists(track_path):
        return track_path
    fallback = os.path.join(DIR, 'assets', 'mp3', 'bg_lofi.mp3')
    return fallback if os.path.exists(fallback) else None


def clean_text(t):
    # 1. Eliminar emojis y símbolos decorativos
    t = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF'
               r'\U0001F1E0-\U0001F1FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F'
               r'\U0001FA70-\U0001FAFF\u2702-\u27B0\u24C2-\U0001F251'
               r'\U0001F004\u2600-\u26FF\uFE0F]', '', t)
    # 2. Eliminar marcas markdown e HTML
    t = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', t)
    t = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', t)
    t = re.sub(r'<\/?[^>]+>', '', t)
    t = re.sub(r'\*\*(.+?)\*\*', r'\1', t)
    t = re.sub(r'\*(.+?)\*', r'\1', t)
    t = re.sub(r'[_*~`#]', '', t)

    # 3. Entidades HTML
    t = re.sub(r'&#8217;|&apos;', "'", t)
    t = re.sub(r'&#8211;|&#8212;|&mdash;|&ndash;', ' ', t)
    t = re.sub(r'&#\d+;', '', t)
    t = t.replace('\\', '')
    t = re.sub(r'\|', ' ', t)

    # 4. Suavizar signos que provocan pausas artificiales en Edge-TTS (AlvaroNeural):
    # IMPORTANTE: convertimos a ESPACIO, no a coma. La coma hace que el motor TTS
    # pause, cortando frases que en español son continuas. El espacio mantiene el flujo.
    # - Rayas y guiones largos aislados -> espacio
    t = re.sub(r'\s*[—–]\s*', ' ', t)
    t = re.sub(r'\s+-\s+', ' ', t)
    # - Puntos suspensivos -> punto simple (pausa larga innecesaria)
    t = re.sub(r'\.{2,}', '.', t)
    # - Dos puntos y punto y coma -> espacio (no coma: evitar pausa artificial)
    t = re.sub(r'[:;]', ' ', t)
    # - Paréntesis, corchetes, llaves y comillas tipográficas -> eliminados (protegiendo tags de locutor y pausa)
    valid_tags = ['[ROBERTO]', '[BEATRIZ]', '[NICOLAS]', '[PAUSA]', '---PAUSA---', '[RAFAGA]', '---RAFAGA---']
    for idx, tag in enumerate(valid_tags):
        t = re.sub(re.escape(tag), f'__TAG_{idx}__', t, flags=re.IGNORECASE)
    t = re.sub(r'[(){}\[\]"«»""]', '', t)
    for idx, tag in enumerate(valid_tags):
        t = t.replace(f'__TAG_{idx}__', tag)

    # 5. Normalizar puntuaciones repetidas y espacios
    t = re.sub(r',\s*,+', ',', t)
    t = re.sub(r'\.\s*\.+', '.', t)
    t = re.sub(r',\s*\.', '.', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def generate_audio(text, out_path, episode_date=None):
    bg_music = get_day_music(episode_date)
    tmp_dir = os.path.join(DIR, 'tmp_audio')
    os.makedirs(tmp_dir, exist_ok=True)

    clean = text
    clean = re.sub(r'\bnewsletters\b', 'niusleters', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\bnewsletter\b', 'niusleter', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\bcolossal\b', 'colosal', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\bbooooooom\b', 'buum', clean, flags=re.IGNORECASE)

    # Eliminar pausas o ráfagas intermedias entre Roberto -> Beatriz y Beatriz -> Nicolás para continuidad de antena
    clean = re.sub(r'(?:---\s*(?:PAUSA|RAFAGA)\s*---|\[\s*(?:PAUSA|RAFAGA)\s*\])\s*(?=\[(?:BEATRIZ|NICOL[AÁ]S)\])', '\n', clean, flags=re.IGNORECASE)

    raw_blocks = re.split(r'---PAUSA---|\[PAUSA\]|---RAFAGA---|\[RAFAGA\]', clean)
    blocks = [b.strip() for b in raw_blocks if b.strip()]

    if not blocks:
        blocks = [clean.strip()]

    print(f'  Generando locución ({TTS_VOICE}, rate={TTS_RATE}) en {len(blocks)} bloque(s)...')

    if not bg_music or not os.path.exists(bg_music):
        try:
            subprocess.run([
                'edge-tts',
                '--voice', TTS_VOICE,
                f'--rate={TTS_RATE}',
                '--text', clean,
                '--write-media', out_path
            ], check=True, capture_output=True, text=True, timeout=180)
            return True
        except Exception as e:
            print(f'  Error edge-tts: {e}')
            return False

    try:
        voice_files = []
        kokoro_instance = None
        if TTS_ENGINE == 'kokoro' and os.path.exists(KOKORO_ONNX) and os.path.exists(KOKORO_VOICES):
            try:
                import soundfile as sf
                from kokoro_onnx import Kokoro
                kokoro_instance = Kokoro(KOKORO_ONNX, KOKORO_VOICES)
                print(f'  🎙️ Usando motor Kokoro-82M con reparto coral (Roberto: {VOICE_CAST["ROBERTO"]}, Beatriz: {VOICE_CAST["BEATRIZ"]}, Nicolás: {VOICE_CAST["NICOLAS"]})...')
            except Exception as ek:
                print(f'  ⚠️ No se pudo inicializar Kokoro ({ek}), usando Edge-TTS...')

        for i, b in enumerate(blocks):
            wav_block = os.path.join(tmp_dir, f'v_{i}.wav')
            
            # Parsear los turnos de diálogo dentro del bloque: [ROBERTO], [BEATRIZ], [NICOLAS]
            dialogue_turns = []
            current_speaker = 'ROBERTO'
            pattern = re.compile(r'\[(ROBERTO|BEATRIZ|NICOL[AÁ]S)\]', re.IGNORECASE)
            
            splits = pattern.split(b)
            if len(splits) == 1:
                if splits[0].strip():
                    dialogue_turns.append((current_speaker, splits[0].strip()))
            else:
                # Si hay etiquetas de locutor en el bloque, descartamos splits[0]
                # para asegurar que ningún preámbulo, metadato o resumen huérfano sea locutado.
                for idx_s in range(1, len(splits), 2):
                    speaker_raw = splits[idx_s].upper()
                    speaker_tag = 'NICOLAS' if 'NICOL' in speaker_raw else speaker_raw
                    turn_text = splits[idx_s + 1].strip()
                    if turn_text:
                        dialogue_turns.append((speaker_tag, turn_text))

            turn_wavs = []
            for t_idx, (speaker, turn_txt) in enumerate(dialogue_turns):
                t_wav = os.path.join(tmp_dir, f'b_{i}_t_{t_idx}.wav')
                voice_id = VOICE_CAST.get(speaker, 'em_alex')
                synthesized = False

                if kokoro_instance:
                    try:
                        samples, sr = kokoro_instance.create(turn_txt, voice=voice_id, speed=1.0, lang="es")
                        sf.write(t_wav, samples, sr)
                        t_wav_44k = os.path.join(tmp_dir, f'b_{i}_t_{t_idx}_44k.wav')
                        subprocess.run(['ffmpeg', '-y', '-i', t_wav, '-ar', '44100', '-ac', '2', t_wav_44k], check=True, capture_output=True, timeout=60)
                        turn_wavs.append(t_wav_44k)
                        synthesized = True
                    except Exception as ex_k:
                        print(f'  ⚠️ Error Kokoro con {speaker} ({voice_id}): {ex_k}')

                if not synthesized:
                    fallback_voice = 'es-ES-ElviraNeural' if speaker == 'BEATRIZ' else ('es-ES-AlvaroNeural' if speaker == 'ROBERTO' else 'es-ES-ManuelNeural')
                    raw_mp3 = os.path.join(tmp_dir, f'b_{i}_t_{t_idx}_raw.mp3')
                    subprocess.run([
                        'edge-tts',
                        '--voice', fallback_voice,
                        f'--rate={TTS_RATE}',
                        '--text', turn_txt,
                        '--write-media', raw_mp3
                    ], check=True, capture_output=True, text=True, timeout=120)
                    subprocess.run([
                        'ffmpeg', '-y', '-i', raw_mp3,
                        '-ar', '44100', '-ac', '2', t_wav
                    ], check=True, capture_output=True, timeout=60)
                    turn_wavs.append(t_wav)

            # Concatenar turnos del bloque
            if len(turn_wavs) == 1:
                voice_files.append(turn_wavs[0])
            elif len(turn_wavs) > 1:
                concat_list = os.path.join(tmp_dir, f'concat_{i}.txt')
                with open(concat_list, 'w') as f_c:
                    for tw in turn_wavs:
                        f_c.write(f"file '{tw}'\n")
                subprocess.run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_list, '-c', 'copy', wav_block], check=True, capture_output=True, timeout=60)
                voice_files.append(wav_block)

        # 1. Intro musical (12s, fade in 1.5s, fade out 2.5s)
        intro_wav = os.path.join(tmp_dir, 'intro.wav')
        subprocess.run([
            'ffmpeg', '-y', '-ss', '00:00:00', '-i', bg_music, '-t', '12',
            '-af', 'afade=t=in:ss=0:d=1.5,afade=t=out:st=9.5:d=2.5,volume=0.30',
            '-ar', '44100', '-ac', '2', intro_wav
        ], check=True, capture_output=True, timeout=60)

        # 2. Interludio musical (6s, fade in 1.0s, fade out 1.8s)
        inter_wav = os.path.join(tmp_dir, 'inter.wav')
        subprocess.run([
            'ffmpeg', '-y', '-ss', '00:00:20', '-i', bg_music, '-t', '6',
            '-af', 'afade=t=in:ss=0:d=1.0,afade=t=out:st=4.2:d=1.8,volume=0.30',
            '-ar', '44100', '-ac', '2', inter_wav
        ], check=True, capture_output=True, timeout=60)

        # 3. Outro musical (12s, fade in 1.5s, fade out 3.5s)
        outro_wav = os.path.join(tmp_dir, 'outro.wav')
        subprocess.run([
            'ffmpeg', '-y', '-ss', '00:00:45', '-i', bg_music, '-t', '12',
            '-af', 'afade=t=in:ss=0:d=1.5,afade=t=out:st=8.5:d=3.5,volume=0.30',
            '-ar', '44100', '-ac', '2', outro_wav
        ], check=True, capture_output=True, timeout=60)

        # Ensamblar secuencia
        sequence = [intro_wav]
        for i, vf in enumerate(voice_files):
            sequence.append(vf)
            if i < len(voice_files) - 1:
                sequence.append(inter_wav)
        sequence.append(outro_wav)

        inputs = []
        filter_inputs = ''
        for idx, fpath in enumerate(sequence):
            inputs.extend(['-i', fpath])
            filter_inputs += f'[{idx}:a]'

        cmd = ['ffmpeg', '-y'] + inputs + [
            '-filter_complex', f'{filter_inputs}concat=n={len(sequence)}:v=0:a=1,loudnorm=I=-16:TP=-1.5:LRA=11[outa]',
            '-map', '[outa]',
            '-b:a', '192k',
            out_path
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=240)

        try:
            shutil.rmtree(tmp_dir)
        except Exception:
            pass

        return True

    except Exception as e:
        print(f'  ⚠️ Error al mezclar cortinillas: {e}. Fallback a audio directo...')
        try:
            subprocess.run([
                'edge-tts',
                '--voice', TTS_VOICE,
                f'--rate={TTS_RATE}',
                '--text', clean,
                '--write-media', out_path
            ], check=True, capture_output=True, text=True, timeout=180)
            return True
        except Exception as err:
            print(f'  Error fallback: {err}')
            return False


def tag_audio(audio_path, title):
    tmp = audio_path + '.tagged.mp3'
    try:
        subprocess.run([
            'ffmpeg', '-y', '-i', audio_path,
            '-metadata', 'title=' + title,
            '-metadata', 'artist=Punto de vista Podcast',
            '-metadata', 'album=Punto de vista Podcast',
            '-metadata', 'album_artist=Punto de vista Podcast',
            '-codec', 'copy',
            tmp,
        ], check=True, capture_output=True, text=True, timeout=60)
        os.replace(tmp, audio_path)
        return True
    except Exception as e:
        print(f'  ⚠️ No se pudo etiquetar el audio: {e}')
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        return False


def send_telegram(text, parse_mode='HTML'):
    if not TG_TOKEN or not TG_CHAT_ID:
        return None
    url = f'https://api.telegram.org/bot{TG_TOKEN}/sendMessage'
    try:
        resp = requests.post(url, json={
            'chat_id': TG_CHAT_ID,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': True
        }, timeout=30)
        return resp.json()
    except requests.RequestException as e:
        print(f'  Error Telegram: {e}')
        return None


def send_telegram_audio(audio_path, caption='', filename='podcast.mp3', cover_path=None, title='', performer='Punto de vista', duration=0):
    if not TG_TOKEN or not TG_CHAT_ID:
        return None
    url = f'https://api.telegram.org/bot{TG_TOKEN}/sendAudio'
    try:
        files = {'audio': (filename, open(audio_path, 'rb'), 'audio/mpeg')}
        if cover_path and os.path.exists(cover_path):
            files['thumbnail'] = ('cover.jpg', open(cover_path, 'rb'), 'image/jpeg')
        data = {'chat_id': TG_CHAT_ID}
        if caption:
            data['caption'] = caption
        if title:
            data['title'] = title
        if performer:
            data['performer'] = performer
        if duration:
            data['duration'] = int(duration)
        resp = requests.post(url, data=data, files=files, timeout=120)
        return resp.json()
    except requests.RequestException as e:
        print(f'  Error Telegram audio: {e}')
        return None


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    is_test = '--test' in sys.argv or os.environ.get('TEST_RUN') == '1'
    is_dry = '--dry-run' in sys.argv
    clean_args = [a for a in sys.argv[1:] if a not in ('--test', '--dry-run')]
    today = date.fromisoformat(clean_args[0]) if clean_args else date.today()
    ep_num = get_episode_number(today)
    test_tag = " [MODO PRUEBA]" if is_test else ""
    print(f'[{ts}] daily_podcast (Roberto - 4 Actos){test_tag} · {today} (Ep #{ep_num})')

    # 1. Recuperar artículos de la fecha
    articles = get_articles_for_day(today.isoformat())
    if not articles:
        podcast_file = find_latest_podcast(today)
        if podcast_file:
            print(f'  Leyendo artículos desde digest file: {podcast_file.name}')
            raw_text = podcast_file.read_text(encoding='utf-8')
            articles = [{'title': 'Digest ' + today.isoformat(), 'source': 'FOTO', 'summary': raw_text[:4000], 'full_text': raw_text}]

    if not articles:
        print(f'  ❌ No hay artículos para {today}')
        sys.exit(1)

    # 2. Identificar protagonista y linaje histórico con los 4 baremos editoriales
    primary = select_primary_article(articles, today, META_PATH)
    historical, lineage_mode = get_historical_counterpart(primary)
    is_monographic = lineage_mode in ('monografico_cruzado', 'monografico_mismo_medio')

    print(f"\n  🎯 Proyecto protagonista elegido: [{primary.get('source', '').upper()}] {primary.get('title')}")
    if historical:
        print(f"  🧬 Linaje histórico ({lineage_mode}): [{historical.get('source', '').upper()}] {historical.get('title')}")

    # Búsqueda de Linaje de Museo / Archivo Internacional
    museum_piece = None
    try:
        keywords = []
        if primary.get('photographer'):
            keywords.append(primary.get('photographer'))
        title_words = re.findall(r'\b[a-zA-ZáéíóúÁÉÍÓÚñÑ]{4,}\b', primary.get('title', ''))
        keywords.extend(title_words[:3])
        museum_piece = get_museum_treasure(keywords=keywords)
        if museum_piece:
            print(f"  🏛️ Joya de Museo / Archivo: [{museum_piece.get('institution')}] {museum_piece.get('title')} ({museum_piece.get('photographer')})")
    except Exception as e:
        print(f"  ⚠️ No se pudo obtener pieza de museo: {e}")

    # Búsqueda de facetas especiales (Fotolibro, Laboratorio/Química, Convocatorias/Becas)
    facets = analyze_daily_facets(articles, primary=primary)
    facet_prompts = build_editorial_facet_prompts(facets)
    if facets.get('call'):
        print(f"  🎯 Convocatoria / Beca detectada: [{facets['call'].get('award_or_grant')}] {facets['call'].get('title')}")
    if facets.get('book'):
        print(f"  📖 Fotolibro detectado: [{facets['book'].get('publisher')}] {facets['book'].get('title')}")
    if facets.get('lab'):
        print(f"  🧪 Laboratorio / Química detectada: {facets['lab'].get('matched_terms')} - {facets['lab'].get('title')}")

    # 3. Construir prompt y llamar a Gemini
    prompt = build_editorial_podcast_prompt(
        articles, primary, historical, today, ep_num,
        museum_piece=museum_piece, facet_prompts=facet_prompts
    )
    if is_dry:
        print("\n--- PROMPT PREVIEW (--dry-run) ---")
        lines = prompt.splitlines()
        for idx, l in enumerate(lines):
            if any(k in l for k in ['🏛️', 'JOYA DEL ARCHIVO', 'LINAJE DE MUSEO', 'ACTO 2:', 'PROYECTO PROTAGONISTA', '🎯 RADAR', '📖 ENFOQUE FOTOLIBRO', '🧪 RINCÓN DE LABORATORIO']):
                print(f"  {l}")
                for sub in lines[idx+1:idx+9]:
                    if sub.strip().startswith(('1.', '2.', '3.', '4.', 'Debes estructurar')):
                        break
                    print(f"    {sub}")
        print("--- FIN PROMPT PREVIEW ---")
        return
    print('  Enviando prompt editorial a Gemini...')
    summary = gemini_request(prompt)

    if not summary:
        print('  ❌ No se obtuvo respuesta de Gemini.')
        sys.exit(1)

    podcast_title, resumen, locutable = parse_summary(summary)

    # 4. Guardar guiones para trazabilidad
    guion_filename = f'podcast-{today.isoformat()}-test.guion.txt' if is_test else f'podcast-{today.isoformat()}.guion.txt'
    guion_path = os.path.join(OUT_DIR, guion_filename)
    locutable_path = os.path.join(OUT_DIR, f'digest-{today.isoformat()}.locutable.txt')
    try:
        header = f"# Podcast Diario · {today.isoformat()} (Ep #{ep_num}){test_tag}\n# Título: {podcast_title}\n# Enfoque: {lineage_mode}\n\n"
        with open(guion_path, 'w', encoding='utf-8') as f:
            f.write(header + locutable)
        if not is_test:
            with open(locutable_path, 'w', encoding='utf-8') as f:
                f.write(header + locutable)
        print(f'  ✅ Guion guardado en: {guion_path}')
    except Exception as e:
        print(f'  ⚠️ Error guardando guion: {e}')

    # 5. Generar audio
    clean_text_audio = clean_text(locutable)
    if not clean_text_audio:
        print('  ❌ No hay texto locutable para audio')
        sys.exit(1)

    os.makedirs(PODCAST_DIR, exist_ok=True)
    audio_filename = f'podcast-{today.isoformat()}-test.mp3' if is_test else f'podcast-{today.isoformat()}.mp3'
    audio_path = os.path.join(PODCAST_DIR, audio_filename)

    if generate_audio(clean_text_audio, audio_path, today):
        size = os.path.getsize(audio_path)
        print(f'  ✅ Audio generado ({size/1024:.0f} KB)')

        # Duración con ffprobe
        duration = 0
        try:
            probe = subprocess.run(
                ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', audio_path],
                capture_output=True, text=True, timeout=30
            )
            if probe.returncode == 0:
                duration = int(float(json.loads(probe.stdout)['format']['duration']))
        except Exception:
            duration = 0

        # Portada e imágenes
        day_image = ''
        img_path = os.path.join(OUT_DIR, f'digest-{today.isoformat()}.image')
        if os.path.exists(img_path):
            try:
                with open(img_path, encoding='utf-8') as f:
                    day_image = f.read().strip()
            except Exception:
                day_image = ''

        images = []
        images_path = os.path.join(OUT_DIR, f'digest-{today.isoformat()}.images.json')
        if os.path.exists(images_path):
            try:
                with open(images_path, encoding='utf-8') as f:
                    images = json.load(f)
            except Exception:
                images = []

        images = [img for img in images if img != day_image]
        if not day_image and images:
            day_image = random.choice(images)

        if not is_test:
            # Actualizar metadata
            meta = []
            if os.path.exists(META_PATH):
                try:
                    with open(META_PATH, encoding='utf-8') as f:
                        meta = json.load(f)
                except Exception:
                    meta = []
            meta = [m for m in meta if m.get('date') != today.isoformat()]
            entry = {
                'date': today.isoformat(),
                'description': resumen,
                'image': day_image,
                'images': images,
                'podcast_title': podcast_title,
                'primary_source': primary.get('source', ''),
                'primary_title': primary.get('title', ''),
                'monographic': is_monographic,
                'lineage_mode': lineage_mode,
                'historical_source': historical.get('source', '') if historical else '',
                'historical_title': historical.get('title', '') if historical else '',
                'museum_piece': {
                    'institution': museum_piece.get('institution', ''),
                    'title': museum_piece.get('title', ''),
                    'photographer': museum_piece.get('photographer', ''),
                    'date': museum_piece.get('date', ''),
                    'technique': museum_piece.get('technique', ''),
                    'curatorial_notes': museum_piece.get('curatorial_notes', ''),
                    'image_url': museum_piece.get('image_url', ''),
                    'museum_url': museum_piece.get('museum_url', ''),
                } if museum_piece else None,
                'facets': {
                    'book': facets.get('book'),
                    'lab': facets.get('lab'),
                    'call': facets.get('call'),
                },
                'size': size,
                'duration': duration,
            }
            meta.append(entry)
            with open(META_PATH, 'w', encoding='utf-8') as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
            print(f'  ✅ Meta del podcast actualizado ({len(meta)} episodios, {duration}s, monográfico={is_monographic})')

            tag_title = clean_text(podcast_title) if podcast_title else f'Podcast {today.isoformat()}'
            tag_audio(audio_path, tag_title)

            if day_image:
                print('  Generando portada del episodio...')
                try:
                    subprocess.run([
                        sys.executable, os.path.join(DIR, 'make_podcast_cover.py'),
                        today.isoformat(), day_image
                    ], check=True, capture_output=True, text=True, timeout=60)
                    print('  ✅ Portada generada')
                except Exception as e:
                    print(f'  ⚠️ Error generando portada: {e}')

            # Telegram
            if os.environ.get('SKIP_TELEGRAM'):
                print('  SKIP_TELEGRAM=1, omitiendo Telegram')
            else:
                caption = f'🎙️ {fmt_fecha_es(today)}\n{clean_text(podcast_title)}'
                audio_filename_tg = f'Punto de vista - {today.isoformat()}.mp3'
                cover_file = os.path.join(DIR, f'podcast-cover-{today.isoformat()}.jpg')
                if not os.path.exists(cover_file):
                    cover_file = os.path.join(DIR, 'assets', 'covers', f'podcast-cover-{today.isoformat()}.jpg')
                send_telegram_audio(
                    audio_path,
                    caption=caption,
                    filename=audio_filename_tg,
                    cover_path=cover_file,
                    title=clean_text(podcast_title),
                    performer='Punto de vista',
                    duration=duration
                )
                print('  ✅ Audio enviado a Telegram')
        else:
            tag_title = f'[PRUEBA] {clean_text(podcast_title)}'
            tag_audio(audio_path, tag_title)
            print(f'\n🎉 [MODO PRUEBA] Episodio de prueba generado exitosamente:')
            print(f'  📁 Audio: {audio_path}')
            print(f'  ⏱️ Duración total: {duration}s ({duration // 60} min {duration % 60} seg)')
            print(f'  📝 Guion: {guion_path}')
            print(f'  ℹ️ No se ha modificado podcast_meta.json ni podcast.xml, ni se ha enviado a Telegram.')
    else:
        print('  ❌ Error al generar audio')
        sys.exit(1)


if __name__ == '__main__':
    main()
