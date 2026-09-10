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
    - Beatriz:
      * is_primary_book: True si el proyecto principal es en sí mismo un fotolibro.
      * primary_book: metadatos del libro protagonista (si aplica).
      * other_books: lista de fotolibros y novedades editoriales detectadas en las noticias secundarias.
    - Nicolás: Rincón de Laboratorio y Alquimia (si hay química/analógico).
    """
    facets = {
        'is_primary_book': False,
        'primary_book': None,
        'other_books': [],
        'lab': None,
        'call': None
    }

    # 1. Comprobar primero si el PROYECTO PRINCIPAL es un fotolibro real
    if primary:
        p_book = detect_photobook(primary)
        if p_book:
            facets['is_primary_book'] = True
            facets['primary_book'] = p_book

    primary_id = primary.get('id') if primary else None
    primary_title = (primary.get('title') or '').strip().lower() if primary else ''

    # 2. Recorrer el resto de artículos del día para novedades de fotolibros, laboratorio y convocatorias
    for art in articles:
        art_title = (art.get('title') or '').strip().lower()
        is_same_as_primary = (primary_id and art.get('id') == primary_id) or (primary_title and art_title == primary_title)

        if not is_same_as_primary:
            b = detect_photobook(art)
            if b and len(facets['other_books']) < 3:
                # Evitar títulos repetidos
                if not any(ob.get('title') == b.get('title') for ob in facets['other_books']):
                    facets['other_books'].append(b)

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

    if facets.get('is_primary_book') and facets.get('primary_book'):
        b = facets['primary_book']
        prompts['beatriz_book'] = f"""
📖 EL PROYECTO PRINCIPAL DE HOY ES UN FOTOLIBRO:
La obra protagonista tiene formato físico de fotolibro:
- Título de la publicación: '{b.get('title')}'
- Editorial / Publicación: {b.get('publisher')}
👉 DIRECTRIZ EDITORIAL PARA BEATRIZ (ACTO 2):
Como la obra principal está concebida en formato de libro, reflexiona sobre cómo la secuenciación de páginas, el diálogo en dípticos y la elección de materiales potencian la narrativa visual del autor, invitando a la audiencia a comprender el libro como la culminación de un proyecto fotográfico.
"""
    elif facets.get('other_books'):
        books_list = facets['other_books']
        books_desc = []
        for bk in books_list:
            autor_str = f" de {bk.get('photographer')}" if bk.get('photographer') else ""
            books_desc.append(f"  • '{bk.get('title')}'{autor_str} (editado por {bk.get('publisher')}, vía {bk.get('source', '').upper()})")
        books_text = "\n".join(books_desc)

        prompts['beatriz_book'] = f"""
📚 EL RADAR DE FOTOLIBROS DE BEATRIZ (NOVEDADES EDITORIALES DEL DÍA):
El proyecto principal NO es un fotolibro (es una serie, exposición o ensayo visual), por lo que NO debes forzar la metáfora del libro sobre él.
Sin embargo, hoy han visto la luz estas interesantes novedades editoriales en la actualidad:
{books_text}

👉 DIRECTRIZ EDITORIAL PARA BEATRIZ (BLOQUE ESPECIAL AL FINAL DEL ACTO 2):
Tras haber analizado el proyecto protagonista y su linaje con la joya de museo, Beatriz abre una ventana motivante y fresca de recomendación editorial (~45 a 55 segundos) antes de dar paso a Nicolás:
Por ejemplo: "Y antes de irnos al taller con Nicolás, quiero abrir un momento la estantería de fotolibros, porque hoy tenemos novedades editoriales que merece la pena seguir de cerca..."
Presenta estas publicaciones de manera entusiasta e inspiradora para personas que hacen fotos: ¿qué lecciones de ritmo, edición, selección de imágenes o coherencia temática podemos aprender de estos fotolibros para aplicarlas a nuestros propios proyectos?
"""

    # La píldora artificial de laboratorio para Nicolás queda desactivada por directriz editorial
    prompts['nicolas_lab'] = ''

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
