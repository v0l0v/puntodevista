#!/usr/bin/env python3
"""
daily_lineage_digest.py — Generador de la Píldora Diaria de Linaje Visual y Disparador Creativo.
Estructura en 3 Actos:
 1. La Mirada de Hoy (Proyecto destacado de la jornada)
 2. El Linaje Visual (Conexión dialéctica con 1-2 proyectos históricos de archive.db)
 3. El Disparador Creativo (Propuesta práctica y técnica para el fotógrafo/oyente)
"""

import json
import os
import re
import sqlite3
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(DIR, 'resumenes')
DB_PATH = os.path.join(DIR, 'archive.db')
CONFIG_PATH = os.path.join(DIR, 'config.json')

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

def gemini_generate(prompt, max_tokens=4096, temperature=0.7):
    if not GEMINI_KEY:
        print("⚠️ No hay GEMINI_KEY configurada. Se usará modo sintético básico.")
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
            with urllib.request.urlopen(req, timeout=90) as resp:
                res = json.loads(resp.read().decode('utf-8'))
                return res['candidates'][0]['content']['parts'][0]['text'].strip()
        except Exception as e:
            time.sleep(2 * (attempt + 1))
            if attempt == 2:
                print(f"Error llamando a Gemini: {e}")
                return None
    return None

def get_articles_for_day(target_date_str=None):
    """Obtiene los artículos de la fecha dada (o los más recientes en la base de datos)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if target_date_str:
        c.execute("""
            SELECT id, url, source, title, photographer, published_date, summary, full_text, image_url
            FROM articles
            WHERE published_date = ? OR created_at LIKE ?
            ORDER BY id DESC
        """, (target_date_str, f'{target_date_str}%'))
        rows = [dict(r) for r in c.fetchall()]
        if rows:
            conn.close()
            return rows

    # Fallback: tomar los artículos más recientes de la BD
    c.execute("""
        SELECT id, url, source, title, photographer, published_date, summary, full_text, image_url
        FROM articles
        ORDER BY published_date DESC, id DESC
        LIMIT 15
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

import vector_search

def find_historical_connections(current_article, limit=3):
    """Busca en el archivo proyectos anteriores que dialoguen temáticamente con el artículo actual usando sqlite-vec."""
    if not current_article or not current_article.get('id'):
        return []
    
    # Búsqueda de Linaje Visual mediante sqlite-vec
    try:
        candidates = vector_search.find_visual_lineage(current_article['id'], limit=limit)
        if candidates and len(candidates) >= 1:
            return candidates
    except Exception as e:
        print(f"⚠️ Error en linaje vectorial: {e}")
        candidates = []

    # Fallback Semántico o Híbrido con texto del artículo
    text_sample = f"{current_article.get('title', '')} {current_article.get('summary', '')}".strip()
    if text_sample:
        try:
            sem_matches = vector_search.search_semantic(text_sample, limit=limit * 2)
            filtered = [m for m in sem_matches if m.get('id') != current_article.get('id') and m.get('source') != current_article.get('source')]
            if filtered:
                return filtered[:limit]
        except Exception:
            pass

    return candidates


def generate_lineage_digest(target_date_str=None):
    """Genera la píldora diaria de linaje visual y propuesta creativa."""
    today_str = target_date_str or date.today().isoformat()
    recent = get_articles_for_day(today_str)
    if not recent:
        print("No se encontraron artículos para analizar.")
        return None

    primary = max(recent, key=lambda a: len(a.get('summary') or a.get('full_text') or ''))
    connections = find_historical_connections(primary, limit=2)

    prompt = f"""
Eres un respetado crítico, curador fotográfico y mentor de artistas visuales para la plataforma 'Punto de vista'.
Tu objetivo es crear la píldora editorial del día ({today_str}) con un rigor intelectual y visual de máximo nivel (similar al tono de Aperture, Foam Magazine o British Journal of Photography, pero en un español cálido, directo e inspirador).

EL PROYECTO PRINCIPAL DE HOY:
- Título: {primary['title']}
- Fotógrafo/Autor: {primary.get('photographer') or 'Autor/a reseñado/a'}
- Medio/Revista: {primary['source'].upper()} ({primary.get('published_date', today_str)})
- URL: {primary['url']}
- Resumen/Texto: {primary.get('summary') or primary.get('full_text', '')[:1000]}

LOS PROYECTOS HISTÓRICOS DE REFERENCIA DEL ARCHIVO:
{json.dumps([{
    'title': c['title'],
    'author': c.get('photographer') or 'No especificado',
    'source': c['source'].upper(),
    'date': c.get('published_date', 'Archivo'),
    'url': c['url'],
    'summary': c.get('summary', '')[:400]
} for c in connections], ensure_ascii=False, indent=2)}

Debes redactar la entrega siguiendo ESTRICTAMENTE esta estructura en 3 Actos:

# 🎙️ PUNTO DE VISTA · DIÁLOGO & LINAJE VISUAL // {today_str}

## 1. LA MIRADA DE HOY // [Título del Proyecto de Hoy]
(Análisis crítico del proyecto de hoy: ¿Qué premisa aborda? ¿Cómo construye su lenguaje visual (luz, atmósfera, composición, color o blanco y negro, escala)? Explica la relevancia estética o conceptual sin limitarte a resumir la nota de prensa).

## 2. EL LINAJE VISUAL // Resonancias en el Archivo
(Conecta el proyecto de hoy con los proyectos históricos proporcionados. Explica el hilo conductor o la contraposición dialéctica: ¿Cómo continúa, subvierte o dialoga este autor con lo que ya vimos en las otras publicaciones? Cita expresamente las fuentes y autores con sus enlaces).

## 3. EL DISPARADOR CREATIVO // Tu Propuesta Práctica
(Una propuesta/ejercicio práctico, técnico o conceptual muy concreto para que el fotógrafo/oyente tome su cámara o revise su obra hoy. Proponle un reto visual tangible de encuadre, iluminación, uso del tiempo, enfoque o narrativa cotidiana basado en lo aprendido en los actos anteriores).

---
Escribe en un tono brillante, apasionado por la fotografía autoral y sin clichés vacíos.
"""

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Generando Píldora de Linaje con IA (Gemini 3.5 Flash)...")
    content_md = gemini_generate(prompt)

    if not content_md:
        content_md = f"""# 🎙️ PUNTO DE VISTA · DIÁLOGO & LINAJE VISUAL // {today_str}

## 1. LA MIRADA DE HOY // {primary['title']}
*Publicado en [{primary['source'].upper()}]({primary['url']})*
{primary.get('summary') or 'Análisis del proyecto contemporáneo destacado de la jornada.'}

## 2. EL LINAJE VISUAL // Resonancias en el Archivo
Este trabajo conecta con las obras rescatadas de nuestro fondo histórico:
"""
        for c in connections:
            content_md += f"\n- **[{c['title']}]({c['url']})** ({c['source'].upper()}, {c.get('published_date', '')}): {c.get('summary', '')[:200]}..."

        content_md += f"""

## 3. EL DISPARADOR CREATIVO // Tu Propuesta Práctica
**Ejercicio del día:** Busca hoy en tu entorno cotidiano una escena donde la luz y las sombras definan la geometría del espacio antes que el propio sujeto. Experimenta con subexponer medio paso y aislar un fragmento arquitectónico o íntimo.
"""

    os.makedirs(OUT_DIR, exist_ok=True)
    md_filename = os.path.join(OUT_DIR, f'linaje-{today_str}.md')
    html_filename = os.path.join(OUT_DIR, f'linaje-{today_str}.html')

    with open(md_filename, 'w', encoding='utf-8') as f:
        f.write(content_md)

    html_body = render_markdown_to_html(content_md)
    html_doc = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Punto de vista · Linaje Visual ({today_str})</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,600;0,700;1,400&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {{ --bg: #0f1115; --card: #181b22; --text: #e6edf3; --text-muted: #8b949e; --accent: #ff3333; --border: #30363d; }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); line-height: 1.7; padding: 2rem 1rem; }}
    .container {{ max-width: 760px; margin: 0 auto; background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 2.5rem; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
    h1 {{ font-family: 'Playfair Display', serif; font-size: 1.8rem; color: #fff; margin-bottom: 1.5rem; border-bottom: 2px solid var(--accent); padding-bottom: 0.8rem; }}
    h2 {{ font-family: 'Playfair Display', serif; font-size: 1.3rem; color: var(--accent); margin: 2rem 0 1rem; }}
    p {{ margin-bottom: 1.2rem; color: #c9d1d9; font-size: 1.05rem; }}
    blockquote {{ border-left: 3px solid var(--accent); padding: 0.8rem 1.2rem; margin: 1.5rem 0; background: rgba(255,51,51,0.05); font-style: italic; color: #f0f6fc; }}
    ul, ol {{ margin: 1rem 0 1.5rem 1.5rem; color: #c9d1d9; }}
    li {{ margin-bottom: 0.5rem; }}
    a {{ color: #58a6ff; text-decoration: none; border-bottom: 1px dotted #58a6ff; }}
    a:hover {{ color: #79c0ff; border-bottom-style: solid; }}
    .footer-nav {{ margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid var(--border); display: flex; justify-content: space-between; font-size: 0.9rem; color: var(--text-muted); }}
  </style>
</head>
<body>
  <div class="container">
    {html_body}
    <div class="footer-nav">
      <a href="../index.html">← Volver al feed general</a>
      <span>Punto de vista · Inteligencia Visual</span>
    </div>
  </div>
</body>
</html>"""

    with open(html_filename, 'w', encoding='utf-8') as f:
        f.write(html_doc)

    print(f"✅ Píldora de Linaje generada con éxito:\n  • Markdown: {md_filename}\n  • HTML: {html_filename}")
    return md_filename

def render_markdown_to_html(md):
    h = md
    h = re.sub(r'^# (.+)$', r'<h1>\1</h1>', h, flags=re.M)
    h = re.sub(r'^## (.+)$', r'<h2>\1</h2>', h, flags=re.M)
    h = re.sub(r'^### (.+)$', r'<h3>\1</h3>', h, flags=re.M)
    h = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', h)
    h = re.sub(r'\*(.+?)\*', r'<em>\1</em>', h)
    h = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2" target="_blank" rel="noopener">\1</a>', h)
    h = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', h, flags=re.M)
    h = re.sub(r'^---$', r'<hr>', h, flags=re.M)

    paragraphs = []
    for block in h.split('\n\n'):
        b = block.strip()
        if not b:
            continue
        if b.startswith('<h') or b.startswith('<blockquote') or b.startswith('<hr'):
            paragraphs.append(b)
        elif b.startswith('- '):
            items = '\n'.join([f'<li>{line[2:]}</li>' for line in b.split('\n') if line.startswith('- ')])
            paragraphs.append(f'<ul>{items}</ul>')
        else:
            paragraphs.append(f'<p>{b}</p>')

    return '\n'.join(paragraphs)

def main():
    target = sys.argv[1] if len(sys.argv) > 1 else None
    generate_lineage_digest(target)

if __name__ == '__main__':
    main()
