#!/usr/bin/env python3
"""
photo_enricher.py — Analizador y Clasificador de Facetas de Valor Fotográfico:
1. Fotolibros (Editoriales independientes, encuadernación, objeto físico).
2. Laboratorio y Alquimia (Procesos químicos, emulsiones, películas, cuarto oscuro).
3. Radar de Convocatorias y Becas (Open calls, premios, residencias, plazos).
"""

import re

# Editoriales de fotolibro reconocidas
PHOTOBOOK_PUBLISHERS = [
    'mack', 'aperture', 'steidl', 'loose joints', 'deadbeat club', 'dalpine',
    'chose commune', 'kehrer', 'twin palms', 'atelier exb', 'xavier barral',
    'void', 'phree', 'editorial rm', 'tbw books', 'dewi lewis', 'gost books',
    'kominek', 'overlapse', 'witty books', 'trespasser', 'stanley/barker',
    'hartmann projects', 'ceiba editions', 'fuego books', 'ediciones anomalas',
    'silvia book', 'the velvet cell', 'kaunas photography', 'akina books'
]

# Premios, festivales y becas reconocidas
AWARDS_AND_GRANTS = [
    'carmignac', 'leica oskar barnack', 'loba', 'world press photo',
    'sony world photography', 'photoespaña', 'photoespana', 'arles',
    'rencontres d\'arles', 'foam paul huf', 'w. eugene smith grant',
    'dorothea lange', 'inge morath', 'henri cartier-bresson',
    'aperture portfolio prize', 'cortona on the move', 'unseen amsterdam',
    'landskrona', 'bjp international photography award', 'portrait of humanity',
    'openwalls arles', 'guggenheim', 'pulitzer', 'taylor wessing',
    'deutsche börse', 'deutsche borse', 'kraszna-krausz', 'prix pictet'
]

# Procesos químicos y técnicas de laboratorio
LAB_CHEMISTRY_TERMS = [
    'pyro', '510 pyro', 'rodinal', 'd-76', 'xtol', 'hc-110', 'c-41', 'e-6',
    'cianotipia', 'cyanotype', 'colodion', 'colodión', 'wet plate', 'mordancage',
    'mordançage', 'tintype', 'ambrotype', 'platino paladio', 'platinum palladium',
    'goma bicromatada', 'gum bichromate', 'papel baritado', 'baryta',
    'gelatin silver', 'gelatina de plata', 'bromoil', 'heliografia',
    'revelador', 'revelado', 'cuarto oscuro', 'darkroom', 'enlarger', 'ampliadora',
    'lomochrome', 'tri-x', 'hp5', 'delta 3200', 't-max', 'pan f', 'cinestill',
    'fomapan', 'provia', 'velvia', 'portra', 'kodachrome', 'cross processing',
    'push pull', 'forzado de pelicula', 'grano tabular', 'contact sheet', 'hoja de contacto'
]


def detect_photobook(article):
    """Detecta si un artículo trata sobre un fotolibro y extrae pistas editoriales."""
    if not article:
        return None
    
    text = f"{article.get('title', '')} {article.get('summary', '')} {article.get('full_text', '')}".lower()
    
    # Comprobar si menciona explícitamente fotolibro o publicación
    book_signals = ['photobook', 'photo book', 'fotolibro', 'monograph', 'monografía', 'published by', 'hardcover', 'softcover', 'clothbound', 'zine']
    has_signal = any(re.search(r'\b' + re.escape(sig) + r'\b', text) for sig in book_signals)
    
    matched_publisher = None
    for pub in PHOTOBOOK_PUBLISHERS:
        if re.search(r'\b' + re.escape(pub) + r'\b', text):
            matched_publisher = pub.title()
            break

    if has_signal or matched_publisher:
        return {
            'is_book': True,
            'publisher': matched_publisher or 'Editorial independiente',
            'title': article.get('title', ''),
            'photographer': article.get('photographer', ''),
            'source': article.get('source', '')
        }
    return None


def detect_lab_chemistry(article):
    """Detecta si un artículo trata sobre laboratorio, película, química o técnicas artesanales."""
    if not article:
        return None

    text = f"{article.get('title', '')} {article.get('summary', '')} {article.get('full_text', '')}".lower()
    
    matched_terms = []
    for term in LAB_CHEMISTRY_TERMS:
        if re.search(r'\b' + re.escape(term) + r'\b', text):
            matched_terms.append(term)

    if matched_terms:
        return {
            'is_lab': True,
            'matched_terms': matched_terms[:4],
            'title': article.get('title', ''),
            'photographer': article.get('photographer', ''),
            'source': article.get('source', '')
        }
    return None


def detect_open_call(article):
    """Detecta si un artículo trata sobre una convocatoria abierta, premio, beca o festival."""
    if not article:
        return None

    text = f"{article.get('title', '')} {article.get('summary', '')} {article.get('full_text', '')}".lower()
    
    call_signals = ['open call', 'convocatoria', 'grant', 'beca', 'award', 'premio', 'contest', 'concurso', 'submission', 'deadline', 'plazo de inscripción', 'plazo de entrega', 'residency', 'residencia']
    has_signal = any(re.search(r'\b' + re.escape(sig) + r'\b', text) for sig in call_signals)

    matched_award = None
    for aw in AWARDS_AND_GRANTS:
        if re.search(r'\b' + re.escape(aw) + r'\b', text):
            matched_award = aw.title()
            break

    if matched_award or (has_signal and ('winner' in text or 'submit' in text or 'apply' in text or 'convocatoria' in text or 'deadline' in text)):
        return {
            'is_call': True,
            'award_or_grant': matched_award or 'Convocatoria internacional',
            'title': article.get('title', ''),
            'source': article.get('source', '')
        }
    return None


def analyze_daily_facets(articles, primary=None):
    """
    Analiza todos los artículos del día y el proyecto principal para extraer las 3 facetas:
    - Roberto: Radar de Convocatorias (si existe).
    - Beatriz: Enfoque Fotolibro (si el proyecto o noticia destacada es un libro).
    - Nicolás: Rincón de Laboratorio y Alquimia (si hay química/analógico).
    """
    facets = {
        'book': None,
        'lab': None,
        'call': None
    }

    # 1. Comprobar primero el protagonista para libro
    if primary:
        book_info = detect_photobook(primary)
        if book_info:
            facets['book'] = book_info

    # 2. Recorrer todos los artículos del día
    for art in articles:
        if not facets['book']:
            b = detect_photobook(art)
            if b:
                facets['book'] = b

        if not facets['lab']:
            l = detect_lab_chemistry(art)
            if l:
                facets['lab'] = l

        if not facets['call']:
            c = detect_open_call(art)
            if c:
                facets['call'] = c

    return facets


def build_editorial_facet_prompts(facets):
    """
    Genera los bloques de texto enriquecido listos para inyectar en las directrices de Roberto, Beatriz y Nicolás.
    """
    prompts = {
        'roberto_radar': '',
        'beatriz_book': '',
        'nicolas_lab': ''
    }

    if facets.get('call'):
        c = facets['call']
        prompts['roberto_radar'] = f"""
🎯 RADAR DE CONVOCATORIAS Y BECAS (SERVICIO PÚBLICO PARA FOTÓGRAFOS):
Entre las noticias del día se encuentra una oportunidad para creadores:
- Titular/Referencia: '{c.get('title')}' ({c.get('source')})
- Beca/Premio: {c.get('award_or_grant')}
👉 DIRECTRIZ PARA ROBERTO (ACTO 1):
En su repaso de actualidad, Roberto debe incluir un apunte claro de servicio público mencionando esta oportunidad para quienes tengan un proyecto documental o de autor que presentar.
"""

    if facets.get('book'):
        b = facets['book']
        prompts['beatriz_book'] = f"""
📖 ENFOQUE FOTOLIBRO COMO OBJETO ESCULTÓRICO:
El proyecto o publicación destacada tiene formato de fotolibro:
- Título: '{b.get('title')}'
- Editorial / Publicación: {b.get('publisher')}
👉 DIRECTRIZ PARA BEATRIZ (ACTO 2):
Beatriz debe dedicar un momento a reflexionar sobre el fotolibro como soporte: la cadencia de la secuencia, el diálogo entre páginas opuestas (dípticos), el peso del papel y por qué esta obra está concebida para ser sostenida en las manos y no consumida fugazmente en pantallas.
"""

    if facets.get('lab'):
        l = facets['lab']
        terms_str = ", ".join(l.get('matched_terms', []))
        prompts['nicolas_lab'] = f"""
🧪 RINCÓN DE LABORATORIO Y ALQUIMIA (TALLER PRÁCTICO):
Hoy contamos con una referencia analógica y química:
- Noticia/Técnica: '{l.get('title')}'
- Términos/Procesos detectados: {terms_str}
👉 DIRECTRIZ PARA NICOLÁS (ACTO 3):
Al presentar el taller y el reto práctico del día, Nicolás abre su intervención compartiendo un apunte cómplice para los amantes del laboratorio, el grano o el proceso analógico (rescatando el truco de diafragmado, emulsión o exposición a las sombras), antes de lanzar el reto a toda la audiencia.
"""

    return prompts


if __name__ == '__main__':
    # Test de detección sobre artículos reales
    import sqlite3
    con = sqlite3.connect('data/archive.db')
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT * FROM articles ORDER BY id DESC LIMIT 50").fetchall()
    
    print("Probando enriquecedor sobre los últimos 50 artículos:")
    b_count = l_count = c_count = 0
    for r in rows:
        art = dict(r)
        b = detect_photobook(art)
        l = detect_lab_chemistry(art)
        c = detect_open_call(art)
        if b:
            b_count += 1
            print(f"  📖 [LIBRO - {b['publisher']}]: {b['title'][:60]}")
        if l:
            l_count += 1
            print(f"  🧪 [LAB - {l['matched_terms']}]: {l['title'][:60]}")
        if c:
            c_count += 1
            print(f"  🎯 [CALL - {c['award_or_grant']}]: {c['title'][:60]}")

    print(f"\nResumen: {b_count} fotolibros, {l_count} lab/química, {c_count} convocatorias detectadas.")
