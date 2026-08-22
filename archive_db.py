#!/usr/bin/env python3
"""
archive_db.py — Gestor de Base de Datos SQLite con Full-Text Search (FTS5)
para el archivo histórico de Punto de vista (artículos, fotógrafos, podcasts).
"""

import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(DIR, 'archive.db')


def get_connection(db_path=DEFAULT_DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path=DEFAULT_DB_PATH):
    """Crea las tablas relacionales y virtuales FTS5 con triggers de sincronización."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        # 1. Tabla de Artículos
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            photographer TEXT,
            published_date TEXT,
            summary TEXT,
            full_text TEXT,
            image_url TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_date ON articles(published_date);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_photographer ON articles(photographer);")

        # 2. Tabla virtual FTS5 para Artículos
        cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
            title,
            photographer,
            source,
            summary,
            full_text,
            content='articles',
            content_rowid='id'
        );
        """)

        # Triggers de sincronización FTS5 para artículos
        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS articles_ai AFTER INSERT ON articles BEGIN
            INSERT INTO articles_fts(rowid, title, photographer, source, summary, full_text)
            VALUES (new.id, new.title, new.photographer, new.source, new.summary, new.full_text);
        END;
        """)

        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS articles_ad AFTER DELETE ON articles BEGIN
            INSERT INTO articles_fts(articles_fts, rowid, title, photographer, source, summary, full_text)
            VALUES ('delete', old.id, old.title, old.photographer, old.source, old.summary, old.full_text);
        END;
        """)

        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS articles_au AFTER UPDATE ON articles BEGIN
            INSERT INTO articles_fts(articles_fts, rowid, title, photographer, source, summary, full_text)
            VALUES ('delete', old.id, old.title, old.photographer, old.source, old.summary, old.full_text);
            INSERT INTO articles_fts(rowid, title, photographer, source, summary, full_text)
            VALUES (new.id, new.title, new.photographer, new.source, new.summary, new.full_text);
        END;
        """)

        # 3. Tabla de Podcasts / Episodios
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS podcasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE NOT NULL,
            title TEXT,
            description TEXT,
            locutable_text TEXT,
            duration INTEGER DEFAULT 0,
            audio_url TEXT,
            image_url TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        """)

        # 4. Tabla virtual FTS5 para Podcasts
        cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS podcasts_fts USING fts5(
            date,
            title,
            description,
            locutable_text,
            content='podcasts',
            content_rowid='id'
        );
        """)

        # Triggers de sincronización FTS5 para podcasts
        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS podcasts_ai AFTER INSERT ON podcasts BEGIN
            INSERT INTO podcasts_fts(rowid, date, title, description, locutable_text)
            VALUES (new.id, new.date, new.title, new.description, new.locutable_text);
        END;
        """)

        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS podcasts_ad AFTER DELETE ON podcasts BEGIN
            INSERT INTO podcasts_fts(podcasts_fts, rowid, date, title, description, locutable_text)
            VALUES ('delete', old.id, old.date, old.title, old.description, old.locutable_text);
        END;
        """)

        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS podcasts_au AFTER UPDATE ON podcasts BEGIN
            INSERT INTO podcasts_fts(podcasts_fts, rowid, date, title, description, locutable_text)
            VALUES ('delete', old.id, old.date, old.title, old.description, old.locutable_text);
            INSERT INTO podcasts_fts(rowid, date, title, description, locutable_text)
            VALUES (new.id, new.date, new.title, new.description, new.locutable_text);
        END;
        """)

        conn.commit()


def upsert_article(conn, item):
    """Inserta o actualiza un artículo."""
    url = (item.get('url') or item.get('link') or '').strip()
    if not url:
        return False

    source = (item.get('source') or item.get('_source') or 'general').strip()
    title = (item.get('title') or '').strip()
    photographer = item.get('photographer') or (', '.join(item['photographers']) if item.get('photographers') else None)
    published_date = str(item.get('published_date') or item.get('date') or item.get('isoDate') or '')[:10]
    summary = (item.get('summary') or item.get('excerpt') or '').strip()
    full_text = (item.get('full_text') or item.get('content') or summary).strip()
    image_url = (item.get('image_url') or item.get('image') or item.get('thumbnail') or '').strip()

    sql = """
    INSERT INTO articles (url, source, title, photographer, published_date, summary, full_text, image_url)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(url) DO UPDATE SET
        source = excluded.source,
        title = excluded.title,
        photographer = COALESCE(excluded.photographer, articles.photographer),
        published_date = COALESCE(NULLIF(excluded.published_date, ''), articles.published_date),
        summary = COALESCE(NULLIF(excluded.summary, ''), articles.summary),
        full_text = COALESCE(NULLIF(excluded.full_text, ''), articles.full_text),
        image_url = COALESCE(NULLIF(excluded.image_url, ''), articles.image_url);
    """
    conn.execute(sql, (url, source, title, photographer, published_date, summary, full_text, image_url))
    return True


def upsert_podcast(conn, item):
    """Inserta o actualiza un episodio de podcast."""
    ep_date = str(item.get('date') or '')[:10]
    if not ep_date:
        return False

    title = item.get('title') or item.get('podcast_title') or f'Episodio · {ep_date}'
    description = item.get('description') or ''
    locutable_text = item.get('locutable_text') or ''
    duration = int(item.get('duration') or 0)
    audio_url = item.get('audio_url') or item.get('link') or f'https://github.com/v0l0v/puntodevista/releases/download/episodios/podcast-{ep_date}.mp3'
    image_url = item.get('image_url') or item.get('image') or ''

    sql = """
    INSERT INTO podcasts (date, title, description, locutable_text, duration, audio_url, image_url)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(date) DO UPDATE SET
        title = excluded.title,
        description = excluded.description,
        locutable_text = COALESCE(NULLIF(excluded.locutable_text, ''), podcasts.locutable_text),
        duration = excluded.duration,
        audio_url = excluded.audio_url,
        image_url = COALESCE(NULLIF(excluded.image_url, ''), podcasts.image_url);
    """
    conn.execute(sql, (ep_date, title, description, locutable_text, duration, audio_url, image_url))
    return True


def search_articles(query, limit=20, db_path=DEFAULT_DB_PATH):
    """Búsqueda full-text sobre artículos con ranking BM25 y snippets contextuales."""
    with get_connection(db_path) as conn:
        # Sanitizar consulta simple
        clean_q = ' '.join([f'"{w}"' if any(c in w for c in ':-+*') else w for w in query.split() if w])
        if not clean_q:
            return []

        sql = """
        SELECT
            a.id,
            a.url,
            a.source,
            a.title,
            a.photographer,
            a.published_date,
            a.image_url,
            snippet(articles_fts, 4, '<b>', '</b>', '…', 24) as snippet_full,
            snippet(articles_fts, 3, '<b>', '</b>', '…', 24) as snippet_summary,
            bm25(articles_fts) as rank
        FROM articles_fts fts
        JOIN articles a ON a.id = fts.rowid
        WHERE articles_fts MATCH ?
        ORDER BY rank
        LIMIT ?;
        """
        try:
            cur = conn.execute(sql, (clean_q, limit))
            return [dict(row) for row in cur.fetchall()]
        except sqlite3.OperationalError:
            fallback_sql = """
            SELECT id, url, source, title, photographer, published_date, image_url, summary
            FROM articles
            WHERE title LIKE ? OR summary LIKE ? OR full_text LIKE ? OR photographer LIKE ?
            ORDER BY published_date DESC
            LIMIT ?;
            """
            pattern = f'%{query}%'
            cur = conn.execute(fallback_sql, (pattern, pattern, pattern, pattern, limit))
            return [dict(row) for row in cur.fetchall()]


def search_podcasts(query, limit=10, db_path=DEFAULT_DB_PATH):
    """Búsqueda full-text sobre episodios del podcast."""
    with get_connection(db_path) as conn:
        clean_q = ' '.join([f'"{w}"' if any(c in w for c in ':-+*') else w for w in query.split() if w])
        if not clean_q:
            return []

        sql = """
        SELECT
            p.id,
            p.date,
            p.title,
            p.duration,
            p.audio_url,
            p.image_url,
            snippet(podcasts_fts, 2, '<b>', '</b>', '…', 24) as snippet_desc,
            snippet(podcasts_fts, 3, '<b>', '</b>', '…', 24) as snippet_locutable,
            bm25(podcasts_fts) as rank
        FROM podcasts_fts fts
        JOIN podcasts p ON p.id = fts.rowid
        WHERE podcasts_fts MATCH ?
        ORDER BY rank
        LIMIT ?;
        """
        try:
            cur = conn.execute(sql, (clean_q, limit))
            return [dict(row) for row in cur.fetchall()]
        except sqlite3.OperationalError:
            fallback_sql = """
            SELECT id, date, title, duration, audio_url, image_url, description
            FROM podcasts
            WHERE title LIKE ? OR description LIKE ? OR locutable_text LIKE ?
            ORDER BY date DESC
            LIMIT ?;
            """
            pattern = f'%{query}%'
            cur = conn.execute(fallback_sql, (pattern, pattern, pattern, limit))
            return [dict(row) for row in cur.fetchall()]


def get_stats(db_path=DEFAULT_DB_PATH):
    """Estadísticas globales de la base de datos."""
    with get_connection(db_path) as conn:
        total_articles = conn.execute("SELECT COUNT(*) FROM articles;").fetchone()[0]
        total_podcasts = conn.execute("SELECT COUNT(*) FROM podcasts;").fetchone()[0]
        sources = conn.execute("SELECT source, COUNT(*) as count FROM articles GROUP BY source ORDER BY count DESC;").fetchall()
        date_range = conn.execute("SELECT MIN(published_date), MAX(published_date) FROM articles WHERE published_date != '';").fetchone()
        return {
            'total_articles': total_articles,
            'total_podcasts': total_podcasts,
            'sources': {row['source']: row['count'] for row in sources},
            'min_date': date_range[0] if date_range else None,
            'max_date': date_range[1] if date_range else None
        }


def main():
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python archive_db.py init")
        print("  python archive_db.py stats")
        print("  python archive_db.py search <termino>")
        print("  python archive_db.py search-podcast <termino>")
        sys.exit(0)

    cmd = sys.argv[1]
    init_db()

    if cmd == 'init':
        print(f"Base de datos inicializada en {DEFAULT_DB_PATH}")
    elif cmd == 'stats':
        stats = get_stats()
        print(f"\n📊 Estadísticas del Archivo Histórico ({DEFAULT_DB_PATH}):")
        print(f"  • Total Artículos: {stats['total_articles']}")
        print(f"  • Total Podcasts:  {stats['total_podcasts']}")
        print(f"  • Rango Fechas:    {stats['min_date']} a {stats['max_date']}")
        print("  • Desglose por fuente:")
        for src, cnt in stats['sources'].items():
            print(f"    - {src:20s}: {cnt:4d} artículos")
    elif cmd == 'search':
        q = ' '.join(sys.argv[2:])
        results = search_articles(q)
        print(f"\n🔍 Resultados para '{q}' ({len(results)} encontrados):")
        for r in results:
            photo = f" (Fotógrafo: {r['photographer']})" if r.get('photographer') else ""
            print(f"\n[{r['source'].upper()}] {r['title']}{photo} · {r.get('published_date', '')}")
            print(f"  URL: {r['url']}")
            snip = r.get('snippet_summary') or r.get('snippet_full') or r.get('summary', '')
            if snip:
                print(f"  Texto: {snip}")
    elif cmd == 'search-podcast':
        q = ' '.join(sys.argv[2:])
        results = search_podcasts(q)
        print(f"\n🎙️ Podcasts encontrados para '{q}' ({len(results)}):")
        for r in results:
            print(f"\n[PODCAST {r['date']}] {r['title']}")
            print(f"  Audio: {r['audio_url']}")
            snip = r.get('snippet_desc') or r.get('snippet_locutable') or r.get('description', '')
            if snip:
                print(f"  Fragmento: {snip}")


if __name__ == '__main__':
    main()
