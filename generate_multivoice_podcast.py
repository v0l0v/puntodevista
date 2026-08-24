#!/usr/bin/env python3
"""
generate_multivoice_podcast.py — Generador de Podcast Multi-Voz para Punto de vista
Reparto:
 - ROBERTO (es-ES-AlvaroNeural): Conductor, radar de titulares y moderador.
 - BEATRIZ (es-ES-ElviraNeural): Crítica curatorial, análisis del linaje visual y diálogo.
 - CLARA (es-ES-XimenaNeural): Mentora de taller, disparador creativo y reto técnico.
"""

import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(DIR, 'resumenes')
PODCAST_DIR = os.path.join(DIR, 'podcast')
DB_PATH = os.path.join(DIR, 'archive.db')
CONFIG_PATH = os.path.join(DIR, 'config.json')

VOICES = {
    'ROBERTO': {'voice': 'es-ES-AlvaroNeural', 'rate': '-2%'},
    'BEATRIZ': {'voice': 'es-ES-ElviraNeural', 'rate': '-4%'},
    'CLARA':   {'voice': 'es-ES-XimenaNeural', 'rate': '-3%'}
}

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

CONFIG = load_config()
GEMINI_KEY = os.environ.get('GEMINI_KEY') or CONFIG.get('GEMINI_KEY')
GEMINI_MODEL = 'gemini-3.5-flash'
GEMINI_URL = f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_KEY}'

def gemini_generate(prompt, max_tokens=6000, temperature=0.7):
    if not GEMINI_KEY:
        return None
    body = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {
            'temperature': temperature,
            'maxOutputTokens': max_tokens,
        }
    }
    req = urllib.request.Request(
        GEMINI_URL,
        data=json.dumps(body).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                res = json.loads(resp.read().decode('utf-8'))
                return res['candidates'][0]['content']['parts'][0]['text'].strip()
        except Exception as e:
            time.sleep(2 * (attempt + 1))
            if attempt == 2:
                print(f"Error en Gemini: {e}")
                return None
    return None

def get_day_articles(target_date_str=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if target_date_str:
        c.execute("""
            SELECT id, url, source, title, photographer, published_date, summary, full_text
            FROM articles
            WHERE published_date = ? OR created_at LIKE ?
            ORDER BY id DESC
        """, (target_date_str, f'{target_date_str}%'))
        rows = [dict(r) for r in c.fetchall()]
        if rows:
            conn.close()
            return rows

    c.execute("""
        SELECT id, url, source, title, photographer, published_date, summary, full_text
        FROM articles
        ORDER BY published_date DESC, id DESC
        LIMIT 12
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_historical_counterpart(primary_article):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Buscar artículo afín en otra revista
    words = re.findall(r'\b[a-zA-ZáéíóúÁÉÍÓÚñÑ]{4,}\b', (primary_article['title'] + ' ' + (primary_article.get('summary') or '')).lower())
    stop_words = {'para', 'como', 'este', 'esta', 'sobre', 'desde', 'with', 'from', 'that', 'this', 'have', 'more'}
    filtered = [w for w in words if w not in stop_words][:5]

    counterparts = []
    if filtered:
        try:
            c.execute("""
                SELECT a.id, a.url, a.source, a.title, a.photographer, a.published_date, a.summary
                FROM articles_fts fts
                JOIN articles a ON a.id = fts.rowid
                WHERE articles_fts MATCH ? AND a.id != ? AND a.source != ?
                ORDER BY rank LIMIT 2;
            """, (' OR '.join(filtered), primary_article['id'], primary_article['source']))
            counterparts = [dict(r) for r in c.fetchall()]
        except Exception:
            pass

    if not counterparts:
        c.execute("""
            SELECT id, url, source, title, photographer, published_date, summary
            FROM articles
            WHERE id != ? AND source != ? AND summary != ''
            ORDER BY RANDOM() LIMIT 1;
        """, (primary_article['id'], primary_article['source']))
        counterparts = [dict(r) for r in c.fetchall()]

    conn.close()
    return counterparts[0] if counterparts else None

def generate_script(target_date_str=None):
    today_str = target_date_str or date.today().isoformat()
    articles = get_day_articles(today_str)
    if not articles:
        print("No hay artículos suficientes para generar el guion.")
        return None

    primary = max(articles, key=lambda a: len(a.get('summary') or a.get('full_text') or ''))
    historical = get_historical_counterpart(primary)

    # Preparar titulares rápidos
    headlines = []
    for a in articles[:6]:
        headlines.append(f"- [{a['source'].upper()}] {a['title']} ({a.get('photographer') or 'Autor reseñado'}): {(a.get('summary') or '')[:140]}")

    prompt = f"""
Eres el guionista principal del podcast diario 'Punto de vista' ({today_str}).
Debes escribir un guion de radio/podcast dinámico, elegante y muy natural para TRES VOCES:

REPARTO:
1. [ROBERTO]: Conductor principal. Enérgico, culto, ágil. Abre el programa, repasa los titulares del día en 90 segundos, modera y dialoga.
2. [BEATRIZ]: Crítica y Curadora. Reflexiva, con ojo analítico. Profundiza en el proyecto central de hoy y explica el 'Linaje Visual' conectándolo con el archivo histórico.
3. [CLARA]: Mentora y Fotógrafa de Taller. Práctica, inspiradora, directa. Entra hacia el final con el 'Disparador Creativo' (reto práctico con la cámara).

MATERIAL DEL DÍA:
Titulares recientes:
{chr(10).join(headlines)}

PROYECTO PROTAGONISTA DE HOY:
- Título: {primary['title']}
- Medio: {primary['source'].upper()}
- Autor: {primary.get('photographer') or 'Autor'}
- Resumen: {primary.get('summary') or primary.get('full_text', '')[:600]}

PROYECTO HISTÓRICO DEL ARCHIVO (LINAJE):
- Título: {historical['title'] if historical else 'Archivo Clásico'}
- Medio: {historical['source'].upper() if historical else 'C41 / LensCulture'}
- Autor: {historical.get('photographer') if historical else 'Referencia'}
- Resumen: {(historical.get('summary') if historical else '')[:400]}

ESTRUCTURA DEL GUION (Usa obligatoriamente las etiquetas de voz [ROBERTO], [BEATRIZ], [CLARA]):
- Acto 1 (Intro & Titulares): ROBERTO da la bienvenida, repasa 3 o 4 titulares breves de las cabeceras e introduce a BEATRIZ para el plato fuerte.
- Acto 2 (Foco Central & Diálogo de Linaje): Diálogo fluido y vivo entre ROBERTO y BEATRIZ analizando el proyecto de hoy y su conexión con el archivo. Beatriz aporta el contexto estético y dialéctico; Roberto hace preguntas perspicaces.
- Acto 3 (Disparador Creativo): Roberto y Beatriz dan paso a CLARA, quien propone un ejercicio técnico/conceptual muy concreto y tangible para que el oyente salga hoy a fotografiar.
- Cierre: Breve despedida coral.

REGLAS DE LOCUCIÓN:
- Escribe exactamente como se habla en la radio profesional española: natural, sin frases encorsetadas ni muletillas vacías.
- Las etiquetas de voz deben ir al inicio de cada intervención en una línea propia: [ROBERTO], [BEATRIZ] o [CLARA].
- No incluyas acotaciones entre paréntesis tipo (música alegre) ni indicaciones que no se deban leer.
- Duración estimada: ~800 a 1000 palabras en total (~6 a 7 minutos).
"""

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Redactando guion multi-voz con Gemini 3.5 Flash...")
    script_text = gemini_generate(prompt)

    if not script_text:
        print("Error generando guion.")
        return None

    os.makedirs(OUT_DIR, exist_ok=True)
    script_file = os.path.join(OUT_DIR, f'podcast-{today_str}.guion.txt')
    with open(script_file, 'w', encoding='utf-8') as f:
        f.write(script_text)

    print(f"✅ Guion guardado en: {script_file}")
    return script_text, script_file

def parse_dialogue(script_text):
    """Parsea el texto en bloques estructurados por personaje."""
    blocks = []
    current_speaker = 'ROBERTO'
    current_lines = []

    for line in script_text.split('\n'):
        l = line.strip()
        if not l:
            continue
        m = re.match(r'^\[(ROBERTO|BEATRIZ|CLARA)\]', l, re.IGNORECASE)
        if m:
            if current_lines:
                blocks.append((current_speaker, ' '.join(current_lines)))
                current_lines = []
            current_speaker = m.group(1).upper()
            content = l[m.end():].strip().lstrip(':').strip()
            if content:
                current_lines.append(content)
        else:
            current_lines.append(l)

    if current_lines:
        blocks.append((current_speaker, ' '.join(current_lines)))

    return blocks

def render_multivoice_audio(script_text, out_mp3_path):
    """Genera el audio multi-voz procesando cada bloque con su voz respectiva y concatenando."""
    blocks = parse_dialogue(script_text)
    if not blocks:
        print("No se encontraron bloques de diálogo.")
        return False

    tmp_dir = os.path.join(DIR, 'tmp_multivoice')
    os.makedirs(tmp_dir, exist_ok=True)

    print(f"🎙️ Generando locución multi-voz en {len(blocks)} intervenciones...")
    audio_segments = []

    for i, (speaker, text) in enumerate(blocks):
        voice_cfg = VOICES.get(speaker, VOICES['ROBERTO'])
        voice_name = voice_cfg['voice']
        rate = voice_cfg['rate']

        # Limpiar textos de marcas
        clean_text = re.sub(r'[*_#]', '', text)
        clean_text = re.sub(r'\bnewsletters\b', 'niusleters', clean_text, flags=re.IGNORECASE)
        clean_text = re.sub(r'\bnewsletter\b', 'niusleter', clean_text, flags=re.IGNORECASE)

        raw_mp3 = os.path.join(tmp_dir, f'seg_{i:03d}_{speaker}.mp3')
        wav_out = os.path.join(tmp_dir, f'seg_{i:03d}_{speaker}.wav')

        cmd = [
            'edge-tts',
            '--voice', voice_name,
            f'--rate={rate}',
            '--text', clean_text,
            '--write-media', raw_mp3
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=90)
            # Normalizar a WAV para concatenación limpia
            subprocess.run([
                'ffmpeg', '-y', '-i', raw_mp3,
                '-ar', '44100', '-ac', '2', wav_out
            ], check=True, capture_output=True, timeout=60)
            audio_segments.append(wav_out)
        except Exception as e:
            print(f"  ⚠️ Error en segmento {i} ({speaker}): {e}")

    if not audio_segments:
        print("Error: no se generaron segmentos de audio.")
        return False

    # Concatenar todos los fragmentos
    inputs = []
    filter_inputs = ''
    for idx, fpath in enumerate(audio_segments):
        inputs.extend(['-i', fpath])
        filter_inputs += f'[{idx}:a]'

    os.makedirs(os.path.dirname(out_mp3_path), exist_ok=True)
    concat_cmd = ['ffmpeg', '-y'] + inputs + [
        '-filter_complex', f'{filter_inputs}concat=n={len(audio_segments)}:v=0:a=1,loudnorm=I=-16:TP=-1.5:LRA=11[outa]',
        '-map', '[outa]',
        '-b:a', '192k',
        out_mp3_path
    ]

    print("🎧 Ensamblando y masterizando audio final con ffmpeg...")
    subprocess.run(concat_cmd, check=True, capture_output=True, timeout=180)

    # Limpiar temporales
    try:
        shutil.rmtree(tmp_dir)
    except Exception:
        pass

    print(f"🎉 Audio Multi-Voz generado con éxito en: {out_mp3_path}")
    return True

def main():
    target_date = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    script_data = generate_script(target_date)
    if not script_data:
        sys.exit(1)

    script_text, script_file = script_data
    out_mp3 = os.path.join(PODCAST_DIR, f'podcast-{target_date}.mp3')
    render_multivoice_audio(script_text, out_mp3)

if __name__ == '__main__':
    main()
