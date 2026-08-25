#!/usr/bin/env python3
"""
catalog_tags.py — Motor de Catalogación Curatorial y Etiquetado Taxonómico (39 Etiquetas Controladas).
Asigna entre 2 y 3 etiquetas hiperespecíficas y representativas a cada obra en archive.db y feeds.json.
"""

import json
import os
import re
import sqlite3
import html
import collections

DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DIR, 'archive.db')
FEEDS_PATH = os.path.join(DIR, 'feeds.json')

TAG_DEFINITIONS = {
    # ── GÉNEROS Y TEMÁTICAS NUCLEARES ──
    '#calle': r'\b(?:street|calle|calles|peaton(?:es)?|transeunte(?:s)?|candid|flaneur|decisive\s+moment|sidewalk|street\s+photograph(?:y|er)|city\s+streets?|urban\s+scene)\b',
    '#retrato': r'\b(?:portrait(?:s|ure|ed)?|retrato(?:s)?|face(?:s)?|rostro(?:s)?|mirada(?:s)?|self-portrait|autorretrato|pose|headshot|portraitist)\b',
    '#cuerpo': r'\b(?:body|bodies|cuerpo(?:s)?|nude|desnudo(?:s)?|skin|piel|gesture|gesto(?:s)?|flesh|figura|figure|human\s+form)\b',
    '#paisaje': r'\b(?:landscape(?:s)?|paisaje(?:s)?|horizon(?:te)?|mountain(?:s)?|montaña(?:s)?|desert(?:o)?|geography|territorio|valley|valle|scenery|wilderness)\b',
    '#marina': r'\b(?:ocean|sea|mar|surf|surfing|surfer|beach|playa|coast|costa|waves|olas|underwater|submarina|litoral|marino|marina|shore)\b',
    '#naturaleza': r'\b(?:nature|naturaleza|forest|bosque|trees|árboles|flora|botanical|botánica|plants?|plantas?|garden|jardín)\b',
    '#fauna': r'\b(?:wildlife|fauna|animal(?:s|es)?|birds?|aves?|pájaro(?:s)?|insects?|insectos?|macro|fungi|mushrooms?|creatures?)\b',
    '#arquitectura': r'\b(?:architecture|arquitectura|building(?:s)?|edificio(?:s)?|brutalis(?:m|ta)|facade|fachada|concrete|hormigón|structure|skyscraper|interior(?:s)?)\b',
    '#espacio-urbano': r'\b(?:city|ciudad|urban|urbano|metropolis|metrópoli|barrio|neighborhood|tokyo|london|new\s+york|berlin|asfalto|urbanism|suburb)\b',
    '#moda': r'\b(?:fashion|moda|clothing|vestuario|textile|textil|runway|apparel|style|estilismo|garment|editorial\s+de\s+moda|couture)\b',
    '#música': r'\b(?:music|música|musician(?:s)?|músico(?:s)?|concert(?:s)?|concierto(?:s)?|band|banda|festival|sound|sonido|record|vinilo|jazz|rock)\b',
    '#deporte': r'\b(?:sport(?:s)?|deporte(?:s)?|athlete(?:s)?|atleta(?:s)?|football|fútbol|basketball|boxing|boxeo|olympic|skate(?:r|boarding)?)\b',
    '#astronomía': r'\b(?:astronomy|astronomía|cosmos|sun|sol|solar|eclipse|stars|estrellas|moon|luna|space|espacio|telescope|galaxy|nebula|cosmic)\b',
    '#viaje': r'\b(?:journey|travel|traveler|viaje|viajar|road\s+trip|train|tren|railway|railroad|station|estación|transit|tránsito|wanderlust|route|ruta|itinerary|voyage)\b',

    # ── DIMENSIONES HUMANAS, SOCIALES Y CONCEPTUALES ──
    '#intimidad': r'\b(?:intimacy|intimidad|domestic|doméstico|home|hogar|house|casa|room|habitación|quietude|quietud|daily\s+life|vida\s+cotidiana)\b',
    '#familia': r'\b(?:family|familia|parents|padres|mother|madre|father|padre|childhood|infancia|children|niños|generations|hijos|heritage)\b',
    '#memoria': r'\b(?:memory|memoria|grief|duelo|loss|pérdida|nostalgia|melancolía|remember|recuerdo(?:s)?|past|pasado|loneliness|soledad|absence|ausencia)\b',
    '#identidad': r'\b(?:identity|identidad|gender|género|queer|trans|transgender|lgbtq|belonging|pertenencia|self|roots|raíces)\b',
    '#comunidad': r'\b(?:community|comunidad|collective|colectivo|neighborhood|vecindario|indigenous|indígena|tradition|tradición|cultural|gathering)\b',
    '#sociedad': r'\b(?:society|sociedad|social|protest|protesta|activism|activismo|democracy|democracia|politics|política|rights|derechos|struggle)\b',
    '#trabajo': r'\b(?:labor|labour|trabajo|trabajadores|workers|industry|industria|factory|fábrica|craft|artesanal|oficio|working\s+class)\b',
    '#subcultura': r'\b(?:subculture|subcultura|underground|punk|graffiti|rave|youth\s+culture|tribus?\s+urbanas?|counterculture|fringe)\b',
    '#medioambiente': r'\b(?:climate|clima|environment|medioambiente|ecology|ecología|pollution|contaminación|glacier|glaciar|anthropocene|earth)\b',

    # ── ESTÉTICAS Y ATMÓSFERAS ──
    '#nocturna': r'\b(?:night|nocturn(?:a|o)|darkness|oscuridad|neon|neón|shadows?|sombras?|midnight|madrugada|twilight|crepúsculo|atardecer)\b',
    '#color': r'\b(?:color|colour|cromatismo|palette|paleta|vibrant|saturated|saturación|kodachrome|lomochrome|technicolor|hues?)\b',
    '#blanco-y-negro': r'\b(?:black\s+and\s+white|b&w|blanco\s+y\s+negro|monochrome|monocromo|grayscale|monochromatic|silver\s+gelatin|bw)\b',
    '#claroscuro': r'\b(?:chiaroscuro|claroscuro|high\s+contrast|contraste|silueta(?:s)?|silhouettes?|light\s+and\s+shadow|luz\s+y\s+sombra)\b',
    '#minimalismo': r'\b(?:minimalis(?:m|ta)|negative\s+space|espacio\s+negativo|simplicity|simplicidad|lines|líneas|geometry|geometría|pure\s+form|subtle)\b',
    '#experimental': r'\b(?:experimental|abstraction|abstracción|abstract|blur|desenfoque|double\s+exposure|doble\s+exposición|solarization|chemigram|collage|glitch|pinhole)\b',

    # ── MEDIO, FORMATO Y TÉCNICA ──
    '#analógico': r'\b(?:analogue|analog|film|película|pelicula|darkroom|emulsion|emulsión|grain|grano|lomography|pinhole|estenopeica)\b',
    '#35mm': r'\b(?:35mm|135\s+film|compact\s+camera|point\s+and\s+shoot|rangefinder|telemétrica)\b',
    '#formato-medio': r'\b(?:120\s+film|medium\s+format|formato\s+medio|6x6|6x7|645|hasselblad|rolleiflex|mamiya|pentax\s+67)\b',
    '#cámaras-y-equipo': r'\b(?:camera\s+review|lens\s+review|shutter|slr|tlr|nikon|canon|leica|olympus|pentax|fujifilm|kodak|ilford|lens|cámara)\b',
    '#técnica-y-proceso': r'\b(?:technique|técnica|process|proceso|developer|revelado|chemistry|química|exposure|exposición|scanning|escaneado|lab)\b',

    # ── CURADURÍA, DIFUSIÓN Y FORMATO EDITORIAL ──
    '#fotolibro': r'\b(?:photobook|photo\s+book|fotolibro|monograph|monografía|publishing|editorial|publication|publicación|zine|fanzine|book)\b',
    '#documental': r'\b(?:documentar(?:y|io)|reportage|reportaje|essay|ensayo|chronicle|crónica|testimony|testimonio|documenting)\b',
    '#entrevista': r'\b(?:interview|entrevista|conversation|conversación|talk|in\s+conversation|q&a|charla|dialogue|profile)\b',
    '#exposición': r'\b(?:exhibition|exposición|gallery|galería|museum|museo|retrospective|retrospectiva|biennial|bienal|show)\b',
    '#fotografía-histórica': r'\b(?:vintage|historical|19th\s+century|20th\s+century|siglo\s+xix|siglo\s+xx|archive|archivo|masters?|maestro(?:s)?|collection|colección|pioneer)\b'
}


def clean_text(text):
    if not text:
        return ''
    t = re.sub(r'<[^>]+>', ' ', text)
    t = re.sub(r'http\S+', '', t)
    return html.unescape(t).lower()


def extract_tags(title, summary, full_text, source=None, photographer=None, max_tags=3):
    t_clean = clean_text(title)
    s_clean = clean_text(summary)
    f_clean = clean_text((full_text or '')[:1200])
    src_clean = (source or '').lower()

    scores = {}
    for tag, pat in TAG_DEFINITIONS.items():
        score = 0
        rx = re.compile(pat, re.IGNORECASE)
        if rx.search(t_clean): score += 10
        if rx.search(s_clean): score += 5
        if rx.search(f_clean): score += 2

        if tag == '#analógico' and src_clean in ['35mmc', 'emulsive', 'lomography', 'shootitwithfilm', 'kosmofoto']:
            score += 4
        if tag == '#35mm' and ('35mm' in t_clean or src_clean == '35mmc'):
            score += 6
        if tag == '#cámaras-y-equipo' and ('review' in t_clean or 'lens' in t_clean or 'camera' in t_clean):
            score += 7
        if tag == '#fotolibro' and ('book' in t_clean or src_clean == 'swan'):
            score += 7
        if tag == '#entrevista' and ('interview' in t_clean or 'conversation' in t_clean):
            score += 8
        if tag == '#exposición' and ('exhibition' in t_clean or 'show' in t_clean):
            score += 6

        if score >= 3:
            scores[tag] = score

    sorted_tags = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    assigned = [t[0] for t in sorted_tags[:max_tags]]

    # Si tiene menos de 2, buscar el mejor encaje en el texto completo
    if len(assigned) < 2:
        for tag, pat in TAG_DEFINITIONS.items():
            if tag not in assigned:
                rx = re.compile(pat, re.IGNORECASE)
                if rx.search(f_clean):
                    assigned.append(tag)
                    if len(assigned) >= 2:
                        break

    if len(assigned) < 2:
        assigned.append('#documental')

    return assigned[:max_tags]


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

    print(f"Catalogando {len(rows)} artículos en archive.db con taxonomía ampliada (39 categorías)...")
    article_tags_map = {}
    stats = collections.Counter()

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
            stats[t] += 1

    conn.commit()
    conn.close()
    print("✓ Base de datos archive.db actualizada con éxito.")

    # Sincronizar feeds.json consolidado
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

    print(f"\n--- Distribución de las {len(stats)} Categorías en el Archivo ({len(rows)} Obras) ---")
    for tag, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(rows)) * 100
        print(f"  {tag:24}: {count:3d} obras ({pct:4.1f}%)")


if __name__ == '__main__':
    tag_all_articles()
