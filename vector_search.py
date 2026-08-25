#!/usr/bin/env python3
"""
vector_search.py — Módulo de Búsqueda Semántica Vectorial con sqlite-vec y Gemini Embeddings.
Permite vectorizar artículos y podcasts e indexarlos en archive.db para descubrir linajes visuales,
atmósferas estéticas, proyectos conceptualmente afines y búsquedas híbridas (vectorial + FTS5).
"""

import json
import os
import sqlite3
import struct
import sys
import time
import urllib.request
import sqlite_vec

DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DIR, 'archive.db')
CONFIG_PATH = os.path.join(DIR, 'config.json')

CONFIG = {}
if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            CONFIG = json.load(f)
    except Exception:
        pass

GEMINI_KEY = os.environ.get('GEMINI_KEY') or CONFIG.get('GEMINI_KEY')
EMBEDDING_MODEL = 'gemini-embedding-001'
EMBED_DIM = 3072


def get_connection(db_path=DB_PATH):
    """Crea una conexión SQLite con la extensión sqlite-vec cargada."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    return conn


def init_vector_tables(db_path=DB_PATH):
    """Crea las tablas virtuales de vectores vec0 si no existen."""
    with get_connection(db_path) as conn:
        conn.execute(f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS articles_vec USING vec0(
            embedding float[{EMBED_DIM}]
        );
        """)
        conn.execute(f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS podcasts_vec USING vec0(
            embedding float[{EMBED_DIM}]
        );
        """)
        conn.commit()


def get_embedding(text):
    """Obtiene el vector de 3072 dimensiones desde la API de Gemini."""
    if not GEMINI_KEY:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{EMBEDDING_MODEL}:embedContent?key={GEMINI_KEY}"
    body = {
        'content': {'parts': [{'text': text[:2500]}]}
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                return data.get('embedding', {}).get('values')
        except Exception:
            time.sleep(1 * (attempt + 1))
    return None


def serialize_vector(vector):
    """Empaqueta una lista de floats en un buffer binario para sqlite-vec."""
    return struct.pack(f'{len(vector)}f', *vector)


def index_missing_embeddings(db_path=DB_PATH, batch_limit=None):
    """Genera embeddings para todos los artículos que aún no estén vectorizados."""
    init_vector_tables(db_path)

    with get_connection(db_path) as conn:
        sql = """
        SELECT a.id, a.title, a.photographer, a.source, a.summary
        FROM articles a
        LEFT JOIN articles_vec v ON a.id = v.rowid
        WHERE v.rowid IS NULL
        """
        if batch_limit:
            sql += f" LIMIT {int(batch_limit)}"

        pending = [dict(r) for r in conn.execute(sql).fetchall()]

        if not pending:
            print("✨ Todos los artículos ya están vectorizados en sqlite-vec.")
            return 0

        print(f"🧠 Vectorizando {len(pending)} artículos pendientes con sqlite-vec...")
        count = 0
        for item in pending:
            context = f"Título: {item['title']}. Fotógrafo: {item.get('photographer') or 'Autor'}. Medio: {item['source']}. Descripción: {item.get('summary') or ''}"
            vec = get_embedding(context)
            if vec:
                serialized = serialize_vector(vec)
                conn.execute(
                    "INSERT OR REPLACE INTO articles_vec(rowid, embedding) VALUES (?, ?)",
                    (item['id'], serialized)
                )
                count += 1
                if count % 15 == 0 or count == len(pending):
                    conn.commit()
                    print(f"  ✓ {count}/{len(pending)} artículos vectorizados...")
            time.sleep(0.08)

        conn.commit()
        print(f"🎉 {count} artículos indexados vectorialmente en archive.db.")
        return count


def index_missing_podcasts(db_path=DB_PATH):
    """Genera embeddings para episodios del podcast pendientes."""
    init_vector_tables(db_path)

    with get_connection(db_path) as conn:
        sql = """
        SELECT p.id, p.date, p.title, p.description, p.locutable_text
        FROM podcasts p
        LEFT JOIN podcasts_vec v ON p.id = v.rowid
        WHERE v.rowid IS NULL
        """
        pending = [dict(r) for r in conn.execute(sql).fetchall()]
        if not pending:
            return 0

        count = 0
        for item in pending:
            context = f"Podcast {item['date']}: {item['title']}. {item.get('description', '')}. {item.get('locutable_text', '')[:1000]}"
            vec = get_embedding(context)
            if vec:
                serialized = serialize_vector(vec)
                conn.execute(
                    "INSERT OR REPLACE INTO podcasts_vec(rowid, embedding) VALUES (?, ?)",
                    (item['id'], serialized)
                )
                count += 1
            time.sleep(0.08)

        conn.commit()
        if count > 0:
            print(f"🎙️ {count} podcasts vectorizados en sqlite-vec.")
        return count


def search_semantic(query_text, limit=10, source=None, db_path=DB_PATH):
    """Búsqueda conceptual por significado estético y emocional en sqlite-vec."""
    init_vector_tables(db_path)
    vec = get_embedding(query_text)
    if not vec:
        return []

    serialized = serialize_vector(vec)
    k_val = max(30, limit * 3) if source else limit

    with get_connection(db_path) as conn:
        if source:
            sql = """
            SELECT
                a.id,
                a.url,
                a.title,
                a.photographer,
                a.source,
                a.published_date,
                a.summary,
                a.image_url,
                v.distance,
                ROUND(MAX(0.0, 1.0 - (v.distance / 2.0)), 4) as score
            FROM articles_vec v
            JOIN articles a ON a.id = v.rowid
            WHERE v.embedding MATCH ? AND k = ? AND a.source = ?
            ORDER BY v.distance ASC
            LIMIT ?;
            """
            rows = [dict(r) for r in conn.execute(sql, (serialized, k_val, source, limit)).fetchall()]
        else:
            sql = """
            SELECT
                a.id,
                a.url,
                a.title,
                a.photographer,
                a.source,
                a.published_date,
                a.summary,
                a.image_url,
                v.distance,
                ROUND(MAX(0.0, 1.0 - (v.distance / 2.0)), 4) as score
            FROM articles_vec v
            JOIN articles a ON a.id = v.rowid
            WHERE v.embedding MATCH ? AND k = ?
            ORDER BY v.distance ASC;
            """
            rows = [dict(r) for r in conn.execute(sql, (serialized, limit)).fetchall()]
        return rows


def find_visual_lineage(primary_article_id, limit=3, db_path=DB_PATH):
    """
    Encuentra las joyas históricas más afines conceptualmente para el Linaje Visual
    utilizando similitud de vectores en sqlite-vec.
    """
    init_vector_tables(db_path)
    with get_connection(db_path) as conn:
        cur = conn.execute("SELECT embedding FROM articles_vec WHERE rowid = ?", (primary_article_id,))
        row = cur.fetchone()

        if not row or not row['embedding']:
            # Intentar generar embedding del artículo al vuelo
            art_cur = conn.execute("SELECT id, title, photographer, source, summary FROM articles WHERE id = ?", (primary_article_id,))
            art = art_cur.fetchone()
            if not art:
                return []
            ctx = f"Título: {art['title']}. Fotógrafo: {art['photographer'] or 'Autor'}. Medio: {art['source']}. Descripción: {art['summary'] or ''}"
            vec = get_embedding(ctx)
            if not vec:
                return []
            serialized = serialize_vector(vec)
            conn.execute("INSERT OR REPLACE INTO articles_vec(rowid, embedding) VALUES (?, ?)", (primary_article_id, serialized))
            conn.commit()
            target_vec = serialized
        else:
            target_vec = row['embedding']

        # Extraer fuente para evitar endogamia visual
        cur_art = conn.execute("SELECT source FROM articles WHERE id = ?", (primary_article_id,)).fetchone()
        src = cur_art['source'] if cur_art else ''

        # Buscar vecinos más cercanos con k suficiente para filtrar la misma fuente y el mismo artículo
        k_val = max(25, limit * 6)
        sql = """
        SELECT
            a.id,
            a.url,
            a.title,
            a.photographer,
            a.source,
            a.published_date,
            a.summary,
            a.image_url,
            v.distance,
            ROUND(MAX(0.0, 1.0 - (v.distance / 2.0)), 4) as similarity
        FROM articles_vec v
        JOIN articles a ON a.id = v.rowid
        WHERE v.embedding MATCH ? AND k = ?
        ORDER BY v.distance ASC;
        """
        raw_matches = [dict(r) for r in conn.execute(sql, (target_vec, k_val)).fetchall()]

        filtered = []
        for item in raw_matches:
            if item['id'] == primary_article_id:
                continue
            if src and item['source'] == src:
                continue
            filtered.append(item)
            if len(filtered) >= limit:
                break

        return filtered


def search_hybrid(query_text, limit=10, db_path=DB_PATH):
    """
    Búsqueda Híbrida: Combina Búsqueda Semántica Vectorial (sqlite-vec)
    con Búsqueda de Texto Completo FTS5 usando Reciprocal Rank Fusion (RRF).
    """
    vector_results = search_semantic(query_text, limit=limit * 2, db_path=db_path)

    fts_results = []
    with get_connection(db_path) as conn:
        clean_q = ' '.join([f'"{w}"' if any(c in w for c in ':-+*') else w for w in query_text.split() if w])
        if clean_q:
            try:
                sql_fts = """
                SELECT a.id, a.url, a.title, a.photographer, a.source, a.published_date, a.summary, a.image_url,
                       bm25(articles_fts) as rank
                FROM articles_fts fts
                JOIN articles a ON a.id = fts.rowid
                WHERE articles_fts MATCH ?
                ORDER BY rank
                LIMIT ?;
                """
                fts_results = [dict(r) for r in conn.execute(sql_fts, (clean_q, limit * 2)).fetchall()]
            except Exception:
                pass

    if not vector_results and not fts_results:
        return []

    # Reciprocal Rank Fusion (RRF)
    scores = {}
    articles_map = {}

    for rank, doc in enumerate(vector_results, start=1):
        doc_id = doc['id']
        scores[doc_id] = scores.get(doc_id, 0.0) + (1.0 / (60 + rank)) * 1.5  # Peso vectorial
        articles_map[doc_id] = doc

    for rank, doc in enumerate(fts_results, start=1):
        doc_id = doc['id']
        scores[doc_id] = scores.get(doc_id, 0.0) + (1.0 / (60 + rank))
        if doc_id not in articles_map:
            articles_map[doc_id] = doc

    sorted_ids = sorted(scores.keys(), key=lambda i: scores[i], reverse=True)
    results = []
    for doc_id in sorted_ids[:limit]:
        item = articles_map[doc_id]
        item['rrf_score'] = round(scores[doc_id], 4)
        results.append(item)

    return results


def search_podcasts_semantic(query_text, limit=5, db_path=DB_PATH):
    """Búsqueda semántica en episodios del podcast con sqlite-vec."""
    init_vector_tables(db_path)
    vec = get_embedding(query_text)
    if not vec:
        return []

    serialized = serialize_vector(vec)
    with get_connection(db_path) as conn:
        sql = """
        SELECT
            p.id,
            p.date,
            p.title,
            p.description,
            p.duration,
            p.audio_url,
            p.image_url,
            v.distance,
            ROUND(MAX(0.0, 1.0 - (v.distance / 2.0)), 4) as score
        FROM podcasts_vec v
        JOIN podcasts p ON p.id = v.rowid
        WHERE v.embedding MATCH ? AND k = ?
        ORDER BY v.distance ASC;
        """
        return [dict(r) for r in conn.execute(sql, (serialized, limit)).fetchall()]


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'index':
        index_missing_embeddings()
        index_missing_podcasts()
    elif len(sys.argv) > 1 and sys.argv[1] == 'search':
        q = ' '.join(sys.argv[2:])
        results = search_hybrid(q)
        print(f"\n🔍 Resultados Híbridos (sqlite-vec + FTS5) para: '{q}'\n")
        for r in results:
            sim = f" (Score: {r.get('score') or r.get('rrf_score')})"
            print(f"- [{r['source'].upper()}] {r['title']}{sim}")
            print(f"  Fotógrafo: {r.get('photographer') or 'N/A'} · {r.get('published_date', '')}")
            print(f"  {r.get('summary', '')[:140]}...\n")
    elif len(sys.argv) > 1 and sys.argv[1] == 'lineage':
        aid = int(sys.argv[2])
        lineage = find_visual_lineage(aid)
        print(f"\n✨ Linaje Visual sqlite-vec para artículo ID {aid}:\n")
        for r in lineage:
            print(f"- [{r['source'].upper()}] {r['title']} (Similitud: {r.get('similarity')})")
            print(f"  {r.get('summary', '')[:120]}...\n")
    else:
        print("Uso:")
        print("  python vector_search.py index")
        print("  python vector_search.py search <concepto>")
        print("  python vector_search.py lineage <article_id>")
