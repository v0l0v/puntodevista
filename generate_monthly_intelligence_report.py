#!/usr/bin/env python3
"""
generate_monthly_intelligence_report.py
Genera el Informe Mensual de Inteligencia Visual y Tendencias Globales
utilizando Gemini 3.5 Flash mediante curl directo de alta velocidad.
"""

import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from datetime import date, datetime
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

def gemini_generate(prompt, max_tokens=8192, temperature=0.6):
    if not GEMINI_KEY:
        print("⚠️ No hay GEMINI_KEY configurada.", flush=True)
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_KEY}"
    body = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {
            'temperature': temperature,
            'maxOutputTokens': max_tokens,
        }
    }
    
    cmd = [
        'curl', '-s', '-m', '120',
        '-X', 'POST',
        '-H', 'Content-Type: application/json',
        '-d', json.dumps(body),
        url
    ]

    for attempt in range(3):
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Enviando prompt a {GEMINI_MODEL} (Intento {attempt+1})...", flush=True)
            res_str = subprocess.check_output(cmd).decode('utf-8')
            res = json.loads(res_str)
            if 'candidates' in res and len(res['candidates']) > 0:
                text = res['candidates'][0]['content']['parts'][0]['text'].strip()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Respuesta recibida con éxito ({len(text)} caracteres).", flush=True)
                return text
            else:
                err = res.get('error', {}).get('message', 'Error desconocido')
                print(f"⚠️ Error API Gemini: {err}", flush=True)
        except Exception as e:
            print(f"⚠️ Excepción en intento {attempt+1}: {e}", flush=True)
        time.sleep(3 * (attempt + 1))

    return None

def get_monthly_dataset():
    """Obtiene una muestra de los artículos más representativos de archive.db."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
        SELECT id, url, source, title, photographer, published_date, summary, full_text, image_url
        FROM articles
        ORDER BY published_date DESC, id DESC
        LIMIT 90;
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def render_markdown_to_html(md_text):
    """Convierte Markdown enriquecido a HTML estructurado y elegante."""
    html = md_text

    # Escapar bloques de código antes
    html = re.sub(r'```(.*?)```', r'<pre><code>\1</code></pre>', html, flags=re.DOTALL)
    
    # Headers
    html = re.sub(r'^# (.*?)$', r'<h1 class="report-title">\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.*?)$', r'<h2 class="section-title">\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.*?)$', r'<h3 class="subsection-title">\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^#### (.*?)$', r'<h4 class="sub-subsection-title">\1</h4>', html, flags=re.MULTILINE)
    
    # Negritas y cursivas
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
    
    # Links
    html = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2" target="_blank" rel="noopener">\1</a>', html)
    
    # Blockquotes
    html = re.sub(r'^> (.*?)$', r'<blockquote class="report-quote"><p>\1</p></blockquote>', html, flags=re.MULTILINE)
    
    # Separadores
    html = re.sub(r'^---$', r'<hr class="divider">', html, flags=re.MULTILINE)
    
    # Listas
    lines = html.split('\n')
    out_lines = []
    in_list = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('* ') or stripped.startswith('- '):
            if not in_list:
                out_lines.append('<ul class="report-list">')
                in_list = True
            content = stripped[2:]
            out_lines.append(f'  <li>{content}</li>')
        else:
            if in_list:
                out_lines.append('</ul>')
                in_list = False
            if stripped and not stripped.startswith('<h') and not stripped.startswith('<blockquote') and not stripped.startswith('<hr') and not stripped.startswith('<pre') and not stripped.startswith('<ul'):
                out_lines.append(f'<p>{line}</p>')
            else:
                out_lines.append(line)
    if in_list:
        out_lines.append('</ul>')
        
    return '\n'.join(out_lines)

def generate_monthly_report():
    today = date.today()
    month_name = "Agosto 2026"
    report_id = f"{today.year}-{today.month:02d}"

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Recopilando datos de archive.db...", flush=True)
    articles = get_monthly_dataset()
    if not articles:
        print("❌ No hay artículos en la base de datos.", flush=True)
        return

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
Tu misión es redactar el **INFORME MENSUAL DE INTELIGENCIA VISUAL, TENDENCIAS GLOBALES Y MERCADO CULTURAL** correspondiente a **{month_name}**.

Este es un producto de análisis editorial y de mercado de **ALTO VALOR B2B**, dirigido a Directores de Arte, Agencias Creativas, Editores de Fotolibros, Galeristas y Diseñadores Estratégicos.

CORPUS ANALIZADO ({len(articles_payload)} proyectos de {len(sources_summary)} publicaciones internacionales):
DISTRIBUCIÓN POR FUENTES:
{json.dumps(sources_summary, indent=2)}

MUESTRA REPRESENTATIVA DEL CORPUS:
{json.dumps(articles_payload[:60], ensure_ascii=False, indent=2)}

---

### DIRECTRICES EDITORIALES OBLIGATORIAS:
1. **Extensión y profundidad:** Desarrolla un texto exhaustivo, riguroso, elocuente y con densidad teórica y práctica (equivalente a un dossier completo de 8 a 12 páginas).
2. **Criterio Curatorial:** No hagas un mero listado de enlaces. Conecta discursos filosóficos, sociológicos y estéticos contemporáneos con los proyectos reales analizados.
3. **Citas y Enlaces:** Cita explícitamente los proyectos, fotógrafos y publicaciones usando markdown [Título o Autor](URL).
4. **Español:** Tono culto, analítico, persuasivo y profesional.

---

### ESTRUCTURA REQUERIDA EN MARKDOWN:

# 🌐 OBSERVATORIO PUNTO DE VISTA // INFORME MENSUAL DE INTELIGENCIA VISUAL
**Edición Mensual · {month_name}**
*Dossier de Investigación Curatorial, Estéticas Emergentes y Prospectiva de Mercado*
*Metodología: Análisis cruzado de {len(articles_payload)} proyectos en {len(sources_summary)} cabeceras globales.*

---

## 1. RESUMEN EJECUTIVO (EXECUTIVE SUMMARY)
- Síntesis de los 3 grandes vectores que han definido la producción visual este mes.
- Mapa de tensiones: Dónde se está librando la batalla estética (ej. analógico vs. sintético, intimismo vs. documento geopolítico).
- Datos clave del radar (fuentes más influyentes y formatos dominantes).

---

## 2. LAS 4 MACRO-CORRIENTES ESTÉTICAS Y CONCEPTUALES DEL MES
(Para cada una de las 4 corrientes:
- **Título Conceptual:** Un nombre sugerente y categórico (ej: *"Arqueología del Afecto"*, *"Fricción Matérica frente a la IA"*).
- **El Fenómeno Cultural:** Análisis profundo de qué necesidad social, política o artística impulsa esta corriente.
- **Evidencias Empíricas Cruzadas:** Análisis detallado de 3 proyectos específicos de la muestra (con autor, medio y enlace Markdown) explicando cómo cada uno manifiesta esta corriente.
- **Implicaciones Estéticas y Técnicas:** Paletas cromáticas, ópticas, grano, soporte y sintaxis compositiva.
- **Veredicto Curatorial:** Proyección de impacto a 6-12 meses).

---

## 3. RADAR DE TALENTO DISRUPTIVO // SCOUTING DE CREADORES
(Fichas exhaustivas de 5-6 fotógrafos/as destacados del mes:
- **Nombre y Medio de Publicación**
- **Discurso y Singularidad Visual**
- **Por qué seguir su trayectoria (Key Takeaway para Agencias/Galerías)**)

---

## 4. ANÁLISIS DE MATERIALIDAD, SOPORTES Y TECNOLOGÍA
- El estado de la fotografía química / analógica (medio formato, half-frame, cianotipia, emulsiones experimentales).
- La reacción frente a la imagen sintética generada por IA: ¿cómo responden los creadores contemporáneos?
- El renacimiento del fotolibro y el ensayo híbrido (texto + imagen).

---

## 5. GUÍA PRÁCTICA DE APLICACIÓN PARA DIRECTORES DE ARTE Y EDITORES
- **3 Cosas que DEBES incorporar en tus próximos proyectos/campañas.**
- **3 Vicios o clichés visuales que están AGOTADOS y debes evitar.**
- **Oportunidades de commissioning y nuevos formatos.**

---

## 6. LA PREGUNTA DIALÉCTICA & CONCLUSIÓN
- Un ensayo breve de cierre con una pregunta dialéctica de calado para la comunidad creativa.

---
Escribe el documento completo con la máxima excelencia estilística y analítica.
"""

    report_md = gemini_generate(prompt, max_tokens=8192, temperature=0.6)

    if not report_md:
        print("❌ Error: No se pudo generar el informe.", flush=True)
        return

    os.makedirs(OUT_DIR, exist_ok=True)
    md_file = os.path.join(OUT_DIR, f'informe-mensual-{report_id}.md')
    html_file = os.path.join(OUT_DIR, f'informe-mensual-{report_id}.html')

    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(report_md)
    print(f"✅ Guardado Markdown en: {md_file}", flush=True)

    html_content = render_markdown_to_html(report_md)

    full_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Observatorio Punto de Vista · Informe Mensual {month_name}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@500;700;900&family=Plus+Jakarta+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #090a0f;
      --paper: #0e111a;
      --paper-elevated: #151a27;
      --border: #232a3d;
      --border-subtle: #1a2030;
      --text: #f1f5f9;
      --text-secondary: #94a3b8;
      --text-muted: #64748b;
      --accent: #ff3344;
      --accent-glow: rgba(255, 51, 68, 0.15);
      --gold: #eab308;
      --cyan: #06b6d4;
      --font-display: 'Cinzel', serif;
      --font-sans: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      background: var(--bg);
      color: var(--text);
      font-family: var(--font-sans);
      line-height: 1.8;
      font-size: 16px;
      padding: 0;
      margin: 0;
      -webkit-font-smoothing: antialiased;
    }}

    /* Print styling para exportar a PDF impecable */
    @media print {{
      body {{
        background: #ffffff !important;
        color: #111827 !important;
        font-size: 11pt;
        line-height: 1.6;
      }}
      .report-container {{
        max-width: 100% !important;
        padding: 0 !important;
        box-shadow: none !important;
      }}
      .no-print {{ display: none !important; }}
      .section-title {{
        page-break-before: always;
        color: #0f172a !important;
        border-bottom: 2px solid #0f172a !important;
      }}
      .report-quote {{
        background: #f8fafc !important;
        border-left: 4px solid #0f172a !important;
        color: #334155 !important;
      }}
      a {{ color: #0f172a !important; text-decoration: underline !important; }}
    }}

    .top-bar {{
      position: sticky;
      top: 0;
      background: rgba(9, 10, 15, 0.85);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border);
      padding: 1rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      z-index: 100;
    }}

    .brand-tag {{
      font-family: var(--font-mono);
      font-size: 0.75rem;
      letter-spacing: 0.15em;
      text-transform: uppercase;
      color: var(--accent);
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}

    .brand-tag::before {{
      content: '';
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--accent);
      box-shadow: 0 0 10px var(--accent);
    }}

    .btn-action {{
      background: var(--paper-elevated);
      color: var(--text);
      border: 1px solid var(--border);
      padding: 0.5rem 1rem;
      border-radius: 6px;
      font-family: var(--font-mono);
      font-size: 0.8rem;
      cursor: pointer;
      text-decoration: none;
      transition: all 0.2s ease;
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
    }}

    .btn-action:hover {{
      background: var(--accent);
      border-color: var(--accent);
      color: #fff;
    }}

    .report-container {{
      max-width: 880px;
      margin: 3rem auto 6rem;
      padding: 3rem 3.5rem;
      background: var(--paper);
      border: 1px solid var(--border);
      border-radius: 12px;
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
    }}

    /* Estilos Tipográficos */
    .report-title {{
      font-family: var(--font-display);
      font-size: 2.4rem;
      font-weight: 900;
      letter-spacing: 0.02em;
      line-height: 1.25;
      color: #ffffff;
      margin-bottom: 0.75rem;
      border-bottom: 1px solid var(--border);
      padding-bottom: 1.5rem;
    }}

    .section-title {{
      font-family: var(--font-display);
      font-size: 1.6rem;
      font-weight: 700;
      letter-spacing: 0.03em;
      color: #ffffff;
      margin: 3rem 0 1.25rem;
      padding-bottom: 0.6rem;
      border-bottom: 2px solid var(--border);
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}

    .subsection-title {{
      font-family: var(--font-sans);
      font-size: 1.25rem;
      font-weight: 700;
      color: var(--accent);
      margin: 2rem 0 0.75rem;
    }}

    .sub-subsection-title {{
      font-family: var(--font-sans);
      font-size: 1.05rem;
      font-weight: 600;
      color: #e2e8f0;
      margin: 1.25rem 0 0.5rem;
    }}

    p {{
      margin-bottom: 1.3rem;
      color: #cbd5e1;
      font-weight: 400;
      text-align: justify;
    }}

    strong {{
      color: #ffffff;
      font-weight: 600;
    }}

    em {{
      color: #94a3b8;
      font-style: italic;
    }}

    a {{
      color: var(--cyan);
      text-decoration: none;
      border-bottom: 1px solid rgba(6, 182, 212, 0.3);
      transition: all 0.2s ease;
    }}

    a:hover {{
      color: #38bdf8;
      border-bottom-color: #38bdf8;
    }}

    .report-quote {{
      margin: 2rem 0;
      padding: 1.5rem 2rem;
      background: var(--paper-elevated);
      border-left: 3px solid var(--accent);
      border-radius: 0 8px 8px 0;
      font-family: var(--font-sans);
      font-style: italic;
      color: #e2e8f0;
    }}

    .report-quote p {{
      margin-bottom: 0;
    }}

    .divider {{
      border: 0;
      height: 1px;
      background: linear-gradient(90deg, transparent, var(--border), transparent);
      margin: 2.5rem 0;
    }}

    .report-list {{
      margin: 1rem 0 1.5rem 1.5rem;
      color: #cbd5e1;
    }}

    .report-list li {{
      margin-bottom: 0.6rem;
      line-height: 1.7;
    }}
  </style>
</head>
<body>

  <div class="top-bar no-print">
    <div class="brand-tag">Punto de Vista · Intelligence Report</div>
    <div>
      <button class="btn-action" onclick="window.print()">🖨️ Exportar a PDF</button>
      <a class="btn-action" href="informe-mensual-{report_id}.md" download>⬇️ Descargar Markdown</a>
    </div>
  </div>

  <main class="report-container">
    {html_content}
  </main>

</body>
</html>
"""

    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(full_html)
    print(f"✅ Guardado HTML de alta fidelidad en: {html_file}", flush=True)
    print(f"🎉 ¡Informe Mensual completado con éxito!", flush=True)

if __name__ == '__main__':
    generate_monthly_report()
