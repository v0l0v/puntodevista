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
RETOS_PATH = get_data_path('retos_historicos.json')
DB_PATH = get_db_path()
from config import get_telegram_creds, get_llm_config, ensure_warp_proxy
from museum_archive import get_museum_treasure
from photo_enricher import analyze_daily_facets, build_editorial_facet_prompts
from phonetic_adapter import adapt_text_phonetics

ensure_warp_proxy()
TG_TOKEN, TG_CHAT_ID = get_telegram_creds()
LLM_BASE_URL, LLM_API_KEY, LLM_MODEL = get_llm_config()

TTS_ENGINE = os.environ.get('TTS_ENGINE', 'kokoro')
TTS_VOICE = os.environ.get('TTS_VOICE', 'es-ES-AlvaroNeural')
TTS_RATE = os.environ.get('TTS_RATE', '-3%')

# Trío de locutores de Punto de Vista
VOICE_CAST = {
    'ROBERTO': 'em_alex',    # Conductor único de Punto de Vista (noticias y reto)
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


def llm_request(prompt, system_instruction=None):
    """
    Realiza una petición de chat completion a un proveedor compatible con OpenAI
    (llama-server local, OpenRouter, Groq, DeepSeek u OpenAI directo).
    Garantiza estricto seguimiento de formato separando reglas en system prompt.
    """
    base_url, api_key, model_name = get_llm_config()
    print(f"  🤖 Solicitando guion al LLM ({model_name}) en {base_url}...")

    is_direct = any(x in base_url for x in ['127.0.0.1', 'localhost', '100.', '192.168.', '10.'])
    system_content = system_instruction or (
        "Eres el guionista y productor ejecutivo de 'Punto de Vista', el podcast diario de alta cultura fotográfica.\n"
        "Debes estructurar tu respuesta EXACTAMENTE en TRES SECCIONES siguiendo los marcadores obligatorios:\n"
        f"[Título del episodio en una sola línea]\n{TITLE_MARKER}\n"
        f"[Resumen conciso en 3 párrafos]\n{LOCUTABLE_MARKER}\n"
        "[Guion para locutar con los tres locutores: [ROBERTO], [BEATRIZ] y [NICOLAS]]\n\n"
        "REGLAS CRÍTICAS DE DIÁLOGO:\n"
        "1. Cada intervención locutable debe comenzar estrictamente en línea nueva con su etiqueta canónica: [ROBERTO], [BEATRIZ] o [NICOLAS].\n"
        "2. PROHIBIDO usar markdown en las etiquetas de los locutores (nunca escribas **[BEATRIZ]**: ni _[BEATRIZ]_ ni BEATRIZ:).\n"
        "3. PROHIBIDO usar triples guiones en los nombres de locutores (nunca escribas ---BEATRIZ--- ni ---NICOLAS---).\n"
        "4. Los triples guiones se reservan exclusivamente para ---TITLE---, ---LOCUTABLE---, ---RAFAGA--- y ---PAUSA---.\n"
        "5. Los tres personajes deben intervenir obligatoriamente con textos sustanciales y estilo radiofónico natural y fluido."
    )

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": prompt}
    ]

    from openai import OpenAI
    try:
        import httpx2 as httpx_mod
    except ImportError:
        try:
            import httpx as httpx_mod
        except ImportError:
            httpx_mod = None

    for attempt in range(MAX_RETRIES):
        try:
            http_client = httpx_mod.Client(trust_env=False) if (is_direct and httpx_mod) else None
            client = OpenAI(
                base_url=base_url,
                api_key=api_key,
                http_client=http_client,
                timeout=900.0
            )

            resp = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.6,
                max_tokens=4096
            )
            content = resp.choices[0].message.content
            if content and content.strip():
                print(f"  ✅ Respuesta recibida exitosamente de {model_name}")
                return content.strip()
        except Exception as e:
            print(f"  Error en petición a {model_name} (intento {attempt + 1}/{MAX_RETRIES}): {e}")
            time.sleep(RETRY_DELAY)

    print("  ❌ Se agotaron todos los reintentos con el proveedor LLM.")
    return None

# Alias para compatibilidad
gemini_request = llm_request


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



SOURCE_NORMALIZATION = {
    'odlp': "L'Œil de la Photographie",
    "l'œil de la photographie": "L'Œil de la Photographie",
    "loeil": "L'Œil de la Photographie",
    '1854': 'British Journal of Photography (1854)',
    'british journal of photography (1854)': 'British Journal of Photography (1854)',
    'blind': 'Blind Magazine',
    'blind magazine': 'Blind Magazine',
    'lomography': 'Lomography Magazine',
    'lomography magazine': 'Lomography Magazine',
    'clavoardiendo': 'Clavoardiendo Magazine',
    'clavoardiendo magazine': 'Clavoardiendo Magazine',
    'booooooom': 'Booooooom',
    '35mmc': '35mmc',
    "ain't-bad": "Ain't-Bad",
    'aintbad': "Ain't-Bad",
    'shootitwithfilm': 'Shoot It With Film',
    'shoot it with film': 'Shoot It With Film',
    'emulsive': 'EMULSIVE',
    'aperture': 'Aperture',
    'magnum': 'Magnum Photos',
    'magnum photos': 'Magnum Photos',
    'asx': 'American Suburb X (ASX)',
    'casualphotophile': 'Casual Photophile',
    'phroom': 'Phroom Magazine',
    'c41': 'C41 Magazine',
    'featureshoot': 'Feature Shoot',
    'lensculture': 'LensCulture',
    'tpj': 'The Photographic Journal',
    'the photographic journal': 'The Photographic Journal',
    'colossal': 'Colossal',
    'fotonistas': 'Fotonistas / Fotoleter'
}


def is_newsletter_item(item):
    """Detecta si un artículo corresponde a un newsletter o correo recibido."""
    src = (item.get('source') or '').lower()
    tit = (item.get('title') or '').lower()
    txt = (item.get('full_text') or item.get('summary') or '').lower()
    return ('newsletter' in src or 'email' in src or 'fotonistas' in src or 'fotoleter' in src or
            'fotonistas' in tit or 'fotonistas' in txt[:350])

def normalize_source_name(raw_source):
    if not raw_source:
        return 'Otras publicaciones'
    clean = raw_source.strip().lower()
    return SOURCE_NORMALIZATION.get(clean, raw_source.strip())

def load_historical_challenges():
    """Carga la lista histórica de retos fotográficos propuestos para evitar repeticiones."""
    if os.path.exists(RETOS_PATH):
        try:
            with open(RETOS_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Error cargando {RETOS_PATH}: {e}")
    return []

def save_historical_challenge(date_str, ep_num, challenge_text):
    """Guarda el nuevo reto propuesto en el archivo histórico persistente."""
    if not challenge_text:
        return
    retos = load_historical_challenges()
    retos = [r for r in retos if r.get('date') != date_str]
    retos.append({
        'date': date_str,
        'episode': ep_num,
        'theme': challenge_text[:120].replace('\n', ' ').strip(),
        'challenge': challenge_text.strip()
    })
    try:
        with open(RETOS_PATH, 'w', encoding='utf-8') as f:
            json.dump(retos, f, ensure_ascii=False, indent=2)
        print(f"  ✅ Reto registrado en {RETOS_PATH} (total acumulado: {len(retos)} retos)")
    except Exception as e:
        print(f"  ⚠️ Error guardando reto en {RETOS_PATH}: {e}")

def extract_challenge_text(locutable):
    """Extrae el reto propuesto por Roberto en el bloque de cierre."""
    blocks = re.split(r'---RAFAGA---|\[RAFAGA\]|---PAUSA---|\[PAUSA\]', locutable)
    if not blocks:
        return ""
    last_block = blocks[-1]
    match = re.search(r'(?:reto|desaf[íi]o)[^\n.]*?[.:]\s*([^\n]+(?:\n[^\n]+){1,3})', last_block, re.IGNORECASE)
    if match:
        return match.group(0).strip()
    return last_block[-450:].strip()

def build_editorial_podcast_prompt(articles, primary, historical, episode_date, ep_num, museum_piece=None, facet_prompts=None):
    """Construye el prompt editorial para ROBERTO:
    - Apertura con gancho de 3 proyectos destacados.
    - Noticias agrupadas por medio: 30 a 45 segundos dedicados a CADA noticia.
    - Ráfaga musical de 6 segundos entre medio y medio.
    - Niusleters recibidos SIEMPRE en la última posición (referencia explícita a Fotonistas).
    - Ráfaga musical de 6 segundos tras el niusleter.
    - Cierre y Reto Fotográfico Inédito (antirrepetición estricta con registro histórico)."""
    d = episode_date or date.today()
    fecha_completa = fmt_fecha_completa_es(d)

    # 1. Separar medios editoriales tradicionales de los niusleters recibidos
    editorial_by_source = {}
    newsletter_items = []

    for a in articles:
        if is_newsletter_item(a):
            newsletter_items.append(a)
        else:
            src_norm = normalize_source_name(a.get('source'))
            editorial_by_source.setdefault(src_norm, []).append(a)

    # 2. Seleccionar 3 proyectos de 3 medios distintos para la expectación inicial
    teaser_candidates = []
    for src_name, items in editorial_by_source.items():
        chosen = next((it for it in items if it.get('photographer') and len(it.get('title', '')) > 10), items[0] if items else None)
        if chosen:
            teaser_candidates.append(chosen)
    teaser_projects = teaser_candidates[:3]

    teaser_lines = []
    for idx, p in enumerate(teaser_projects, 1):
        aut = p.get('photographer') or 'Autor/a'
        tit = p.get('title', 'Sin título')
        src = normalize_source_name(p.get('source'))
        teaser_lines.append(f"  {idx}. En {src}: '{tit}' de {aut}")
    teaser_block = "\n".join(teaser_lines)

    # 3. Formatear medios agrupados con instrucción estricta de 30/45s por noticia
    sources_text = []
    for src_name, items in sorted(editorial_by_source.items(), key=lambda x: len(x[1]), reverse=True):
        count = len(items)
        sources_text.append(f"📰 MEDIO EDITORIAL: {src_name.upper()} ({count} noticia{'s' if count>1 else ''})")
        sources_text.append(f"  [PAUTA ESTRICTA: Roberto debe dedicar aproximadamente 30 a 45 segundos a CADA UNA de las {count} noticias de este medio (~70-100 palabras por noticia). Si tiene una noticia, le dedica 30-45s; si tiene varias (como en ODLP u otras), le dedica 30-45s a cada una de ellas de forma sustancial]")
        for it in items[:6]:  # hasta 6 noticias por medio
            tit = it.get('title', 'Sin título')
            aut = it.get('photographer') or 'Autor/a'
            sumario = (it.get('summary') or it.get('full_text', ''))[:350].replace('\n', ' ')
            sources_text.append(f"  • {tit} (por {aut}): {sumario}")
        sources_text.append("")

    sources_block = "\n".join(sources_text)

    # 4. Formatear el bloque de niusleters recibidos (siempre al final de las noticias)
    newsletters_text = []
    if newsletter_items:
        newsletters_text.append("📬 SECCIÓN DE NIUSLETERS RECIBIDOS (ÚLTIMA POSICIÓN DE NOTICIAS):")
        newsletters_text.append("  [PAUTA ESTRICTA: Roberto revisa el buzón de correo. Debe hacer referencia explícita a 'Fotonistas' (Ana de Fotonistas) o al nombre del niusleter recibido. Le dedica 30 a 45 segundos (~70-95 palabras) comentando la reflexión o idea de la carta sin spoilers, con intriga para invitar a suscribirse. Tras este bloque va una ráfaga musical hacia el cierre y reto]")
        for nl in newsletter_items[:2]:
            tit = nl.get('title', 'Correo de la comunidad')
            sumario = (nl.get('summary') or nl.get('full_text', ''))[:450].replace('\n', ' ')
            newsletters_text.append(f"  • Remitente: Fotonistas (Ana) - Título/Asunto: '{tit}' -> {sumario}")
    else:
        newsletters_text.append("📬 SECCIÓN DE NIUSLETERS RECIBIDOS:")
        newsletters_text.append("  (Hoy no se han recibido correos ni niusleters en el buzón; pasar directamente al Cierre y Reto)")

    newsletters_block = "\n".join(newsletters_text)

    # 5. Histórico de retos pasados para antirrepetición
    past_retos = load_historical_challenges()
    retos_negros = []
    for r in past_retos[-20:]:
        retos_negros.append(f"  ❌ [{r.get('date')}] {r.get('theme', '')}: {r.get('challenge', '')[:90]}...")
    retos_negros_block = "\n".join(retos_negros) if retos_negros else "  (Ninguno registrado todavía)"

    return f"""Eres ROBERTO, el único conductor y locutor del podcast 'Punto de vista', el espacio diario de actualidad, cultura fotográfica y mirada de autor.
Tu tono es cercano, dinámico, culto, con excelente ritmo periodístico y pasión por la fotografía.

Fecha de hoy: {fecha_completa} (Episodio #{ep_num}).

MATERIAL DE LAS ÚLTIMAS 24 HORAS AGRUPADO POR MEDIO:
{sources_block}

{newsletters_block}

TRES PROYECTOS SELECCIONADOS PARA EL GANCHO DE EXPECTACIÓN INICIAL:
{teaser_block}

HISTÓRICO DE RETOS PASADOS (LISTA NEGRA - PROHIBIDO REPETIR O PARAFRASEAR):
{retos_negros_block}

DIRECTRICES GENERALES DE ESTILO Y LOCUCIÓN:
- LOCUTOR ÚNICO: Todo el podcast lo presenta y locuta exclusivamente [ROBERTO]. No introduzcas a ningún otro locutor.
- DURACIÓN POR NOTICIA: A CADA NOTICIA que menciones debes dedicarle aproximadamente 30 a 45 segundos (~70 a 100 palabras por noticia). Aunque un medio (como ODLP) tenga muchas noticias, le dedicas 30/45 segundos a cada una de ellas con buen ritmo y desarrollo.
- SEPARADORES MUSICALES (6 SEGUNDOS DE SINTONÍA): Entre medio y medio debes insertar estrictamente en una línea independiente la etiqueta:
---RAFAGA---
Esto inserta una ráfaga musical de 6 segundos entre los medios para dar dinamismo a la emisión.
- POSICIÓN DE LOS NIUSLETERS: La sección de niusleters recibidos va SIEMPRE en la última posición del recorrido de actualidad, justo después de todos los medios editoriales y antes del cierre. En ella debes hacer siempre referencia explícita a 'Fotonistas' (Ana de Fotonistas) o al nombre del niusleter recibido.
- TRAS EL NIUSLETER: Inserta una etiqueta ---RAFAGA--- (6 segundos de música) y da paso a la fase final de Cierre y Reto.
- FONÉTICA Y ADAPTACIÓN EN EL LOCUTABLE:
  * Escribe "niusleter" o "niusleters" (nunca newsletter).
  * Escribe "el Magazine online Colosal" (para Colossal).
  * Escribe "la revista Buum" (para Booooooom).
  * Escribe "el Ojo de la Fotografía, el O-D-L-P" (para ODLP).
  * Si un nombre propio en inglés es difícil o engañoso para la síntesis de voz, adapta su fonética amigable en castellano (ej: "Macari", "Clain", "Ápercher", "Táiler").

ESTRUCTURA OBLIGATORIA DEL GUION:

Debes estructurar tu respuesta EXACTAMENTE en TRES SECCIONES siguiendo esta plantilla:

[Título sugerente, periodístico y atractivo del episodio en una sola línea, sin comillas]
{TITLE_MARKER}
[Resumen editorial conciso en 2 o 3 párrafos para la web, feed RSS y Telegram destacando el panorama de noticias de hoy y el reto fotográfico propuesto]
{LOCUTABLE_MARKER}
[ROBERTO]
¡Hola, muy buenas! Bienvenidos a Punto de vista, tu dosis diaria de actualidad y cultura fotográfica. Hoy es {fecha_completa} y este es el episodio #{ep_num}...
[Roberto saluda y crea levemente expectación nombrando de manera introductoria y atractiva los 3 proyectos destacados seleccionados, invitando a quedarse a escuchar el recorrido completo. Cierra la apertura con una frase enérgica hacia la música.]

---RAFAGA---

[ROBERTO]
[Roberto aborda el primer medio editorial. Dedica 30 a 45 segundos a CADA noticia que trata en este medio.]

---RAFAGA---

[ROBERTO]
[Roberto pasa al segundo medio editorial, dedicando 30 a 45 segundos a cada noticia...]

---RAFAGA---

[Continuar con un bloque [ROBERTO] y separador ---RAFAGA--- para cada medio presente]

---RAFAGA---

[ROBERTO]
[SECCIÓN DE NIUSLETERS (ÚLTIMA POSICIÓN DE NOTICIAS): Roberto abre el buzón de niusleters recibidos. Hace referencia explícita a Fotonistas (o al nombre del niusleter recibido). Comenta la idea durante 30 a 45 segundos sin spoilers para abrir el apetito.]

---RAFAGA---

[ROBERTO]
Y hasta aquí nuestro recorrido por las noticias y las páginas que hoy marcan el pulso de la fotografía...
[Roberto se despide cordialmente hasta el día de mañana]
[Roberto propone el RETO FOTOGRÁFICO DEL DÍA:
 - Extrae la idea de las noticias tratadas hoy o de su amplio conocimiento fotográfico.
 - OBLIGATORIO: El reto debe ser COMPLETAMENTE INÉDITO. No repitas ninguno de los temas de la lista negra de días anteriores.
 - Plantea una restricción creativa tangible y motivadora para salir a disparar hoy.
 - Formula una pregunta detonante antes de presionar el obturador: "Antes de disparar, pregúntate..."]
Cargad baterías o carretes, y nos escuchamos mañana. ¡Buenas fotos!
"""

def normalize_speaker_tags(text):
    """Normaliza de forma exhaustiva cualquier variación en el marcado de locutores
    (por ejemplo: ---BEATRIZ---, **[BEATRIZ]**, BEATRIZ:, [NICOLÁS], etc.)
    al estándar canónico de emisión: [ROBERTO], [BEATRIZ], [NICOLAS]."""
    if not text:
        return text

    def _sub_speaker(m):
        raw = m.group('speaker').upper()
        speaker = 'NICOLAS' if 'NICOL' in raw else raw
        rest = m.group('rest').strip() if 'rest' in m.groupdict() and m.group('rest') else ''
        if rest:
            return f'\n[{speaker}]\n{rest}'
        return f'\n[{speaker}]\n'

    # 1. Etiquetas con guiones: ---BEATRIZ--- o ---NICOLAS--- o ---ROBERTO---
    text = re.sub(r'(?mi)^[ \t]*---+\s*(?P<speaker>ROBERTO|BEATRIZ|NICOL[AÁ]S|CLARA)\s*---+[ \t]*(?P<rest>.*)$', _sub_speaker, text)
    # 2. Etiquetas con corchetes (con o sin markdown/dos puntos): **[BEATRIZ]**, [BEATRIZ]:, etc.
    text = re.sub(r'(?mi)^[ \t]*(?:\*{1,2}|_{1,2})?\[\s*(?P<speaker>ROBERTO|BEATRIZ|NICOL[AÁ]S|CLARA)\s*\](?:\*{1,2}|_{1,2}|:)?[ \t]*(?P<rest>.*)$', _sub_speaker, text)
    # 3. Etiquetas con dos puntos al inicio de línea: BEATRIZ:, **BEATRIZ:**
    text = re.sub(r'(?mi)^[ \t]*(?:\*{1,2}|_{1,2})?(?P<speaker>ROBERTO|BEATRIZ|NICOL[AÁ]S|CLARA)(?:\*{1,2}|_{1,2})?:[ \t]*(?P<rest>.*)$', _sub_speaker, text)
    # 4. Nombre solo en una línea: BEATRIZ
    text = re.sub(r'(?mi)^[ \t]*(?:\*{1,2}|_{1,2})?(?P<speaker>ROBERTO|BEATRIZ|NICOL[AÁ]S|CLARA)(?:\*{1,2}|_{1,2})?[ \t]*$', _sub_speaker, text)

    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


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

    locutable = normalize_speaker_tags(locutable)

    # Si locutable todavía contiene texto huérfano antes del primer locutor [ROBERTO|BEATRIZ|NICOLAS|CLARA]
    speaker_match = re.search(r'\[(ROBERTO|BEATRIZ|NICOLAS|CLARA)\]', locutable, re.IGNORECASE)
    if speaker_match:
        preamble = locutable[:speaker_match.start()].strip()
        if preamble:
            # Si el resumen estaba vacío o solo tenía el título, recuperamos el preámbulo como resumen
            if not resumen or resumen == podcast_title:
                resumen = preamble
            locutable = locutable[speaker_match.start():].strip()

    locutable = normalize_speaker_tags(locutable)

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


def validate_podcast_script(locutable, expected_speakers=None):
    """Quality Gate: Valida que el guion contenga las intervenciones de Roberto,
    las ráfagas de separación entre medios y la propuesta del reto fotográfico."""
    clean = normalize_speaker_tags(locutable)
    pattern = re.compile(r'\[ROBERTO\]', re.IGNORECASE)
    turns = [t.strip() for t in pattern.split(clean) if t.strip()]

    errors = []
    if not turns:
        errors.append("No se encontró ninguna intervención del locutor [ROBERTO].")

    rafagas = re.findall(r'---RAFAGA---|\[RAFAGA\]', clean)
    if len(rafagas) < 2:
        errors.append(f"Se requieren separadores ---RAFAGA--- entre medios (detectados: {len(rafagas)}).")

    has_reto = bool(re.search(r'\b(?:reto|desaf[íi]o|taller)\b', clean, re.IGNORECASE))
    if not has_reto:
        errors.append("El bloque final debe incluir la propuesta del reto fotográfico del día.")

    total_len = sum(len(t) for t in turns)
    if total_len < 900:
        errors.append(f"El texto locutable es demasiado corto ({total_len} caracteres).")

    is_valid = len(errors) == 0
    return is_valid, errors, {'ROBERTO': turns}

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
    t = normalize_speaker_tags(t)
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

    clean = normalize_speaker_tags(text)
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
                turn_spoken = adapt_text_phonetics(clean_text(turn_txt))
                synthesized = False

                if kokoro_instance:
                    try:
                        samples, sr = kokoro_instance.create(turn_spoken, voice=voice_id, speed=1.0, lang="es")
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
                        '--text', turn_spoken,
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

    # 3. Construir prompt y llamar al LLM (llama-server local / OpenAI-compatible)
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
    max_attempts = 2
    summary = None
    podcast_title, resumen, locutable = '', '', ''
    validation_errors = []

    for attempt in range(1, max_attempts + 1):
        if attempt == 1:
            print('  Enviando prompt editorial al LLM...')
            summary = llm_request(prompt)
        else:
            print(f'  🔄 Reintento {attempt}/{max_attempts}: Re-solicitando guion al LLM con corrección de reparto coral...')
            correction_note = (
                f"\n\n⚠️ CORRECCIÓN OBLIGATORIA DE FORMATO (EL INTENTO ANTERIOR FUE RECHAZADO):\n"
                f"La respuesta previa fue rechazada por los siguientes fallos:\n"
                + "\n".join(f"  * {err}" for err in validation_errors) +
                "\n\nINSTRUCCIONES ESTRICTAS:\n"
                "- Todo el texto locutable debe ser narrado exclusivamente por [ROBERTO].\n"
                "- Cada intervención debe comenzar estrictamente con la etiqueta [ROBERTO] en una línea nueva.\n"
                "- Separa cada medio editorial con una línea independiente que contenga: ---RAFAGA---\n"
                "- Al principio debes incluir el gancho de 3 proyectos destacados creando expectación.\n"
                "- Al final debes proponer un reto fotográfico inédito (sin repetir la lista negra) y la pregunta detonante antes de disparar."
            )
            summary = llm_request(prompt + correction_note)

        if not summary:
            print('  ❌ No se obtuvo respuesta del proveedor LLM.')
            if attempt == max_attempts:
                sys.exit(1)
            continue

        podcast_title, resumen, locutable = parse_summary(summary)
        is_valid, validation_errors, speaker_turns = validate_podcast_script(locutable)

        if is_valid:
            spk_info = ", ".join(f"{k} ({len(v)} turnos, {sum(len(t) for t in v)} caracteres)" for k, v in sorted(speaker_turns.items()))
            print(f'  ✅ Quality Gate de locución superado: {spk_info}')
            break
        else:
            print(f'  ⚠️ Quality Gate falló en intento {attempt}/{max_attempts}:')
            for err in validation_errors:
                print(f'     - {err}')
            if attempt == max_attempts:
                print('  ❌ ERROR FATAL: El guion no cumple con los requisitos del reparto coral tras agotar los reintentos.')
                sys.exit(1)

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

    challenge_snippet = extract_challenge_text(locutable)
    if not is_test:
        save_historical_challenge(today.isoformat(), ep_num, challenge_snippet)

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
                    'book': facets.get('primary_book') or (facets.get('other_books')[0] if facets.get('other_books') else None),
                    'other_books': facets.get('other_books', []),
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
