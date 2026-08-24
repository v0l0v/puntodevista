#!/usr/bin/env python3
"""
weekly_trends_observatory.py — Observatorio Semanal de Tendencias e Inteligencia Editorial.
Procesa el histórico de los últimos 7 días de archive.db (o rango personalizado)
y genera un dossier curatorial profundo con:
 1. 3 Macro-Tendencias estéticas y conceptuales detectadas en múltiples plataformas.
 2. Radar de Voces y Fotógrafos Emergentes a seguir.
 3. Insights de Mercado Cultural para Editores y Directores de Arte.
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

def gemini_generate(prompt, max_tokens=8192, temperature=0.7):
    if not GEMINI_KEY:
        print("⚠️ No hay GEMINI_KEY configurada.")
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
                print(f"Error llamando a Gemini: {e}")
                return None
    return None

def get_weekly_dataset(days=7, end_date_str=None):
    """Obtiene artículos de los últimos N días."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Si hay fechas en la BD, buscamos en los últimos N días o los últimos 60 artículos más recientes
    c.execute("""
        SELECT id, url, source, title, photographer, published_date, summary, full_text, image_url
        FROM articles
        ORDER BY published_date DESC, id DESC
        LIMIT 80;
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def generate_weekly_report(days=7):
    today = date.today()
    week_num = today.isocalendar()[1]
    year = today.year
    report_id = f"{year}-W{week_num:02d}"

    articles = get_weekly_dataset(days=days)
    if not articles:
        print("No hay suficientes artículos para generar el informe semanal.")
        return None

    # Preparar el corpus sintético para el prompt
    sources_summary = {}
    articles_payload = []
    for a in articles:
        src = a['source']
        sources_summary[src] = sources_summary.get(src, 0) + 1
        articles_payload.append({
            'source': src.upper(),
            'title': a['title'],
            'author': a.get('photographer') or 'Autor/a reseñado/a',
            'date': a.get('published_date', ''),
            'url': a['url'],
            'summary': (a.get('summary') or a.get('full_text', ''))[:350]
        })

    prompt = f"""
Eres el Director de Investigación Curatorial y Crítica Visual del 'Observatorio Punto de Vista'.
Analiza el siguiente corpus de {len(articles_payload)} artículos y proyectos fotográficos publicados recientemente en {len(sources_summary)} revistas internacionales de referencia (LensCulture, Magnum Photos, Phroom, C41, Huck, Aint-Bad, Shoot It With Film, Lomography, etc.).

DISTRIBUCIÓN POR FUENTES:
{json.dumps(sources_summary, indent=2)}

MUESTRA DE PROYECTOS PUBLICADOS:
{json.dumps(articles_payload[:50], ensure_ascii=False, indent=2)}

TU TAREA:
Genera un INFORME DE INTELIGENCIA EDITORIAL Y TENDENCIAS GLOBALES DE LA FOTOGRAFÍA (Semana {report_id}) de altísimo nivel.
No hagas una lista de noticias ni resúmenes lineales. Debes encontrar los patrones invisibles que conectan revistas de diferentes países.

Estructura obligatoria en Markdown:

# 🌐 OBSERVATORIO PUNTO DE VISTA // DOSSIER DE INTELIGENCIA EDITORIAL
**Edición Semanal {report_id} · {today.strftime('%d de %B de %Y')}**
*Base de análisis: {len(articles_payload)} proyectos en {len(sources_summary)} cabeceras globales.*

---

## 1. LAS 3 MACRO-TENDENCIAS DE LA SEMANA
(Para cada tendencia:
- **Título Conceptual Evocador** (ej: *"La Ansiedad Doméstica y el Espacio Confinado"*, *"Tensión Matérica: El Grano contra el Algoritmo"*).
- **El Patrón Detectado:** Explica qué fenómeno cultural, estético o social está ocurriendo simultáneamente en varias revistas.
- **Proyectos Clave Cruzados:** Cita 2 o 3 proyectos específicos de la muestra con su medio, autor y enlace Markdown, explicando cómo cada uno aborda esa tendencia desde su propio ángulo.
- **Lectura Curatorial:** Qué significa esto para el estado actual del lenguaje fotográfico).

## 2. RADAR DE VOCES EMERGENTES // TALENT SCOUTING
(Destaca a 3-4 fotógrafos o colectivos que hayan publicado proyectos sobresalientes esta semana. Para cada uno, indica: nombre, medio donde se publicó, su enfoque singular y por qué los editores de arte deberían tenerlos en seguimiento).

## 3. INSIGHTS PARA DIRECTORES DE ARTE Y EDITORES
(2-3 conclusiones estratégicas: ¿Qué estéticas se están agotando? ¿Qué temas están encontrando nueva tracción entre coleccionistas y jurados de premios internacionales? ¿Hacia dónde se mueve la conversación visual?).

## 4. LA PREGUNTA DIALÉCTICA
(Una pregunta abierta de debate para la comunidad de fotógrafos y editores).

---
Escribe en un español impecable, culto, directo y con criterio curatorial profundo.
"""

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Generando Dossier Semanal con Gemini 3.5 Flash...")
    report_md = gemini_generate(prompt)

    if not report_md:
        print("Error generando informe con IA.")
        return None

    os.makedirs(OUT_DIR, exist_ok=True)
    md_file = os.path.join(OUT_DIR, f'tendencias-{report_id}.md')
    html_file = os.path.join(OUT_DIR, f'tendencias-{report_id}.html')

    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(report_md)

    html_body = render_markdown_to_html(report_md)
    html_doc = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Observatorio Punto de vista · Dossier {report_id}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,600;0,700;1,400&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{ --bg: #090a0f; --card: #13161f; --card-border: #242938; --text: #e2e8f0; --text-muted: #94a3b8; --accent: #ff2a2a; --gold: #f59e0b; }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); line-height: 1.75; padding: 2.5rem 1rem; }}
    .container {{ max-width: 860px; margin: 0 auto; background: var(--card); border: 1px solid var(--card-border); border-radius: 16px; padding: 3rem 3rem; box-shadow: 0 20px 40px rgba(0,0,0,0.6); }}
    .header-badge {{ display: inline-block; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 2px; color: var(--accent); font-weight: 700; margin-bottom: 0.8rem; }}
    h1 {{ font-family: 'Playfair Display', serif; font-size: 2.2rem; color: #fff; margin-bottom: 0.8rem; line-height: 1.25; }}
    h2 {{ font-family: 'Playfair Display', serif; font-size: 1.45rem; color: #fff; margin: 2.5rem 0 1.2rem; border-left: 3px solid var(--accent); padding-left: 0.8rem; }}
    h3 {{ font-family: 'Inter', sans-serif; font-size: 1.15rem; color: #f1f5f9; margin: 1.8rem 0 0.8rem; font-weight: 600; }}
    p {{ margin-bottom: 1.25rem; color: #cbd5e1; font-size: 1.05rem; }}
    strong {{ color: #fff; }}
    blockquote {{ border-left: 3px solid var(--gold); padding: 1rem 1.4rem; margin: 1.8rem 0; background: rgba(245, 158, 11, 0.05); font-style: italic; color: #f8fafc; border-radius: 0 8px 8px 0; }}
    ul, ol {{ margin: 1rem 0 1.5rem 1.8rem; color: #cbd5e1; }}
    li {{ margin-bottom: 0.6rem; }}
    a {{ color: #60a5fa; text-decoration: none; border-bottom: 1px solid rgba(96, 165, 250, 0.3); transition: all 0.2s; }}
    a:hover {{ color: #93c5fd; border-bottom-color: #93c5fd; }}
    hr {{ border: none; border-top: 1px solid var(--card-border); margin: 2.5rem 0; }}
    .footer-nav {{ margin-top: 3.5rem; padding-top: 1.5rem; border-top: 1px solid var(--card-border); display: flex; justify-content: space-between; font-size: 0.9rem; color: var(--text-muted); }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header-badge">● Intelligence Dossier</div>
    {html_body}
    <div class="footer-nav">
      <a href="../index.html">← Volver a Punto de vista</a>
      <span>Observatorio de Fotografía Contemporánea</span>
    </div>
  </div>
</body>
</html>"""

    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_doc)

    print(f"✅ Dossier Semanal de Tendencias generado:\n  • Markdown: {md_file}\n  • HTML: {html_file}")
    return md_file

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
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    generate_weekly_report(days)

if __name__ == '__main__':
    main()
