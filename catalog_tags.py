#!/usr/bin/env python3
"""
catalog_tags.py — Motor de Catalogación Curatorial y Etiquetado Taxonómico (Máx. 3 tags por obra).
Asigna hasta 3 etiquetas representativas a cada artículo en archive.db y sincroniza feeds.json.
"""

import json
import os
import re
import sqlite3
import html

DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DIR, 'archive.db')
FEEDS_PATH = os.path.join(DIR, 'feeds.json')

TAG_PATTERNS = {
    '#calle': [
        r'\b(?:street|calle|calles|peaton(?:es)?|transeunte(?:s)?|candid|flaneur|decisive\s+moment|sidewalk)\b',
        r'\b(?:pure\s+street|street\s+photograph(?:y|er))\b'
    ],
    '#retrato': [
        r'\b(?:portrait(?:s|ure)?|retrato(?:s)?|face(?:s)?|rostro(?:s)?|mirada(?:s)?|self-portrait|autorretrato|pose|body|cuerpo|nude|desnudo)\b'
    ],
    '#paisaje': [
        r'\b(?:landscape(?:s)?|paisaje(?:s)?|horizon(?:te)?|mountain(?:s)?|montaña(?:s)?|desert(?:o)?|geography|territorio|valley|scenery)\b'
    ],
    '#documental': [
        r'\b(?:documentar(?:y|io)|reportage|reportaje|essay|ensayo|chronicle|crónica|testimony|testimonio|archives?|historia|historical)\b'
    ],
    '#analógico': [
        r'\b(?:analogue|analog|film|pelicula|película|35mm|120|medium\s+format|formato\s+medio|large\s+format|darkroom|emulsion|emulsión|grain|grano|lomography|pinhole|estenopeica|kodak|ilford|leica|silver\s+gelatin)\b'
    ],
    '#arquitectura': [
        r'\b(?:architecture|arquitectura|building(?:s)?|edificio(?:s)?|brutalis(?:m|ta)|facade|fachada|concrete|hormigón|structure|urbanism|urbanismo|skyscraper|interior(?:s)?)\b'
    ],
    '#marina': [
        r'\b(?:ocean|sea|mar|surf|surfing|surfer|beach|playa|coast|costa|waves|olas|underwater|submarina|litoral|marino|marina)\b'
    ],
    '#nocturna': [
        r'\b(?:night|nocturn(?:a|o)|darkness|oscuridad|neon|neón|shadows?|sombras?|midnight|madrugada|twilight|crepúsculo|claroscuro|chiaroscuro)\b'
    ],
    '#subcultura': [
        r'\b(?:subculture|subcultura|underground|punk|skate(?:r|boarding)?|graffiti|queer|lgbtq|trans|rave|youth\s+culture|tribus?\s+urbanas?|counterculture)\b'
    ],
    '#intimidad': [
        r'\b(?:intimacy|intimidad|domestic|doméstico|family|familia|home|hogar|memory|memoria|grief|duelo|loss|pérdida|diary|diario|childhood|infancia|loneliness|soledad)\b'
    ],
    '#viaje': [
        r'\b(?:journey|travel|viaje|viajar|road\s+trip|train|tren|railway|railroad|station|estación|transit|tránsito|wanderlust|expedition|route|ruta|itinerary)\b'
    ],
    '#color': [
        r'\b(?:color|colour|cromatismo|palette|paleta|vibrant|saturated|saturación|kodachrome|lomochrome|technicolor|pastel|neon\s+color)\b'
    ],
    '#blanco-y-negro': [
        r'\b(?:black\s+and\s+white|b&w|blanco\s+y\s+negro|monochrome|monocromo|grayscale|monochromatic)\b'
    ],
    '#experimental': [
        r'\b(?:experimental|abstraction|abstracción|abstract|blur|desenfoque|double\s+exposure|doble\s+exposición|solarization|chemigram|collage|glitch|distortion)\b'
    ],
    '#fauna': [
        r'\b(?:wildlife|fauna|animal(?:s|es)?|birds?|aves?|pájaro(?:s)?|insects?|insectos?|macro|flora|botanical|botánica|fungi|mushrooms?)\b'
    ],
    '#astronomía': [
        r'\b(?:astronomy|astronomía|cosmos|sun|sol|solar|eclipse|stars|estrellas|moon|luna|space|espacio|telescope|galaxy|nebula)\b'
    ],
    '#fotolibro': [
        r'\b(?:photobook|photo\s+book|fotolibro|monograph|monografía|publishing|editorial|publication|publicación|zine|fanzine)\b'
    ],
    '#sociedad': [
        r'\b(?:society|sociedad|social|protest|protesta|activism|activismo|democracy|democracia|politics|política|labor|trabajadores|community|comunidad)\b'
    ],
    '#minimalismo': [
        r'\b(?:minimalis(?:m|ta)|negative\s+space|espacio\s+negativo|simplicity|simplicidad|lines|líneas|geometry|geometría|pure\s+form)\b'
    ],
    '#moda': [
        r'\b(?:fashion|moda|clothing|vestuario|textile|textil|runway|apparel|model|outfit|style|estilismo)\b'
    ]
}


def extract_tags(title, summary, full_text, source=None, photographer=None, max_tags=3):
    t_clean = html.unescape(title or '').lower()
    s_clean = html.unescape(summary or '').lower()
    f_clean = html.unescape((full_text or '')[:1200]).lower()
    src_clean = (source or '').lower()

    tag_scores = {}

    for tag, patterns in TAG_PATTERNS.items():
        score = 0
        for pat in patterns:
            if re.search(pat, t_clean):
                score += 10
            if re.search(pat, s_clean):
                score += 5
            if re.search(pat, f_clean):
                score += 2

        if tag == '#analógico' and src_clean in ['35mmc', 'emulsive', 'lomography', 'shootitwithfilm', 'kosmofoto']:
            score += 4
        elif tag == '#calle' and ('street' in t_clean or 'pure street' in t_clean):
            score += 6
        elif tag == '#marina' and ('ocean' in t_clean or 'sea' in t_clean or 'surf' in t_clean):
            score += 6
        elif tag == '#fotolibro' and ('book' in t_clean or 'swan' in src_clean):
            score += 5

        if score >= 4:
            tag_scores[tag] = score

    if not tag_scores:
        if any(w in t_clean for w in ['interview', 'conversation', 'talk', 'charla', 'profile']):
            tag_scores['#documental'] = 5
            tag_scores['#retrato'] = 4
        elif any(w in t_clean for w in ['series', 'project', 'show', 'exhibition']):
            tag_scores['#documental'] = 4
        else:
            tag_scores['#documental'] = 3

    sorted_tags = sorted(tag_scores.items(), key=lambda x: x[1], reverse=True)
    return [t[0] for t in sorted_tags[:max_tags]]


def ensure_tags_column(conn):
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(articles)")
    cols = [col[1] for col in cursor.fetchall()]
    if 'tags' not in cols:
        print("Creando columna 'tags' en la tabla articles...")
        cursor.execute("ALTER TABLE articles ADD COLUMN tags TEXT")
        conn.commit()


def tag_all_articles():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    ensure_tags_column(conn)

    cursor = conn.cursor()
    cursor.execute("SELECT id, url, source, title, photographer, summary, full_text FROM articles")
    rows = cursor.fetchall()

    print(f"Catalogando {len(rows)} artículos en archive.db...")
    article_tags_map = {}
    stats = {}

    for r in rows:
        tags = extract_tags(
            title=r['title'],
            summary=r['summary'],
            full_text=r['full_text'],
            source=r['source'],
            photographer=r['photographer'],
            max_tags=3
        )
        tags_json = json.dumps(tags, ensure_ascii=False)
        cursor.execute("UPDATE articles SET tags = ? WHERE id = ?", (tags_json, r['id']))
        article_tags_map[r['id']] = tags
        article_tags_map[r['url']] = tags
        if r['title']:
            article_tags_map[r['title'].strip()] = tags

        for t in tags:
            stats[t] = stats.get(t, 0) + 1

    conn.commit()
    conn.close()
    print("✓ Base de datos archive.db actualizada con éxito.")

    if os.path.exists(FEEDS_PATH):
        try:
            with open(FEEDS_PATH, 'r', encoding='utf-8') as f:
                feeds_data = json.load(f)

            updated_count = 0
            for item in feeds_data.get('items', []):
                tags = article_tags_map.get(item.get('_id')) or \
                       article_tags_map.get(item.get('link')) or \
                       article_tags_map.get(item.get('title', '').strip()) or \
                       extract_tags(
                           title=item.get('title'),
                           summary=item.get('excerpt') or item.get('summary'),
                           full_text=item.get('content'),
                           source=item.get('_source'),
                           max_tags=3
                       )
                item['tags'] = tags
                updated_count += 1

            with open(FEEDS_PATH, 'w', encoding='utf-8') as f:
                json.dump(feeds_data, f, ensure_ascii=False, indent=2)
            print(f"✓ feeds.json actualizado con tags en {updated_count} artículos.")
        except Exception as e:
            print(f"Error sincronizando feeds.json: {e}")

    print("\n--- Distribución de Etiquetas en el Archivo ---")
    for tag, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
        print(f"  {tag:18}: {count:3d} obras")


if __name__ == '__main__':
    tag_all_articles()
