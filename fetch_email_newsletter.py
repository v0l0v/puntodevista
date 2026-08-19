"""
fetch_email_newsletter.py
Recupera correos etiquetados en Gmail (label: fotopodcast) del día de hoy
y los convierte al formato estándar de artículo del podcast.

Requiere en config.json:
  "email": {
    "address":      "tu@gmail.com",
    "app_password": "xxxx xxxx xxxx xxxx"
  }

La App Password se genera en:
  https://myaccount.google.com/apppasswords
"""

import email
import imaplib
import json
import os
import re
from datetime import date, datetime, timezone, timedelta
from email.header import decode_header
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser

GMAIL_IMAP = 'imap.gmail.com'
GMAIL_LABEL = 'Fotopodcast'

DIR = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_config():
    with open(os.path.join(DIR, 'config.json'), encoding='utf-8') as f:
        return json.load(f)


def _decode_str(value):
    """Decodifica cabeceras MIME (pueden venir codificadas en base64/qp)."""
    if value is None:
        return ''
    parts = decode_header(value)
    result = []
    for chunk, enc in parts:
        if isinstance(chunk, bytes):
            result.append(chunk.decode(enc or 'utf-8', errors='replace'))
        else:
            result.append(chunk)
    return ''.join(result)


class _HTMLToText(HTMLParser):
    """Parser mínimo que extrae texto legible de un HTML de email."""

    SKIP_TAGS = {'style', 'script', 'head', 'title'}

    def __init__(self):
        super().__init__()
        self._skip = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self._skip += 1
        if tag in ('br', 'p', 'div', 'tr', 'h1', 'h2', 'h3', 'h4', 'li'):
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS:
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)

    def get_text(self):
        raw = ''.join(self.parts)
        # Colapsar líneas en blanco múltiples
        raw = re.sub(r'\n{3,}', '\n\n', raw)
        return raw.strip()


def _html_to_text(html: str) -> str:
    parser = _HTMLToText()
    parser.feed(html)
    return parser.get_text()


def _extract_body(msg) -> str:
    """Extrae el cuerpo de texto del mensaje (prefiere text/plain, si no text/html)."""
    plain = None
    html = None

    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = part.get('Content-Disposition', '')
            if 'attachment' in cd:
                continue
            charset = part.get_content_charset() or 'utf-8'
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            decoded = payload.decode(charset, errors='replace')
            if ct == 'text/plain' and plain is None:
                plain = decoded
            elif ct == 'text/html' and html is None:
                html = decoded
    else:
        ct = msg.get_content_type()
        charset = msg.get_content_charset() or 'utf-8'
        payload = msg.get_payload(decode=True)
        if payload:
            decoded = payload.decode(charset, errors='replace')
            if ct == 'text/plain':
                plain = decoded
            elif ct == 'text/html':
                html = decoded

    if html:
        return _html_to_text(html)
    if plain:
        return plain.strip()
    return ''


def _msg_date(msg) -> date | None:
    """Parsea la fecha del mensaje y devuelve un objeto date."""
    raw = msg.get('Date', '')
    if not raw:
        return None
    try:
        dt = email.utils.parsedate_to_datetime(raw)
        # Normalizar a fecha local (sin zona horaria para comparar)
        return dt.astimezone().date()
    except Exception:
        return None


def _summary(text: str, max_chars: int = 400) -> str:
    """Devuelve las primeras frases del texto hasta max_chars."""
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    last = max(cut.rfind('. '), cut.rfind('.\n'))
    if last > 100:
        return cut[:last + 1].strip()
    return cut.rstrip() + '…'


# ---------------------------------------------------------------------------
# Función principal pública
# ---------------------------------------------------------------------------

def fetch_email_newsletters(target_date: date | None = None, hours: int = 24) -> list[dict]:
    """
    Devuelve una lista de artículos en formato estándar del podcast,
    obtenidos de los correos con label 'fotopodcast' en Gmail de las últimas `hours` horas
    o del día indicado.

    Formato de cada artículo:
      { title, link, photographer, photographers, summary, full_text,
        image, images, source }
    """
    if target_date is None:
        target_date = date.today()

    cfg = _load_config()
    email_cfg = cfg.get('email')
    if not email_cfg:
        print('  [email] No hay configuración de email en config.json — saltando.')
        return []

    address = email_cfg.get('address', '')
    app_password = email_cfg.get('app_password', '')
    if not address or not app_password:
        print('  [email] Faltan "address" o "app_password" en config.json → saltando.')
        return []

    articles = []

    try:
        mail = imaplib.IMAP4_SSL(GMAIL_IMAP)
        mail.login(address, app_password)

        # En Gmail los labels son carpetas IMAP
        status, _ = mail.select(f'"{GMAIL_LABEL}"', readonly=True)
        if status != 'OK':
            print(f'  [email] No se pudo abrir el label "{GMAIL_LABEL}". '
                  f'¿Existe la etiqueta en Gmail?')
            mail.logout()
            return []

        # Buscar correos desde ayer para cubrir las últimas 24h
        since_date = target_date - timedelta(days=1)
        since_str = since_date.strftime('%d-%b-%Y')
        status, data = mail.search(None, f'(SINCE {since_str})')
        if status != 'OK' or not data or not data[0]:
            # Fallback a búsqueda del día exacto
            date_str = target_date.strftime('%d-%b-%Y')
            status, data = mail.search(None, f'(ON {date_str})')
            if status != 'OK' or not data or not data[0]:
                print(f'  [email] Sin correos con label "{GMAIL_LABEL}" para las últimas 24h.')
                mail.logout()
                return []

        msg_ids = data[0].split()
        print(f'  [email] {len(msg_ids)} correo(s) candidato(s) con label "{GMAIL_LABEL}".')

        cutoff_utc = datetime.now(timezone.utc) - timedelta(hours=hours)

        for mid in msg_ids:
            status, raw = mail.fetch(mid, '(RFC822)')
            if status != 'OK':
                continue
            msg = email.message_from_bytes(raw[0][1])

            # Comprobar si está dentro de las últimas `hours` horas
            date_header = msg.get('Date')
            if date_header:
                try:
                    msg_dt = parsedate_to_datetime(date_header)
                    if msg_dt.tzinfo is None:
                        msg_dt = msg_dt.replace(tzinfo=timezone.utc)
                    if msg_dt < cutoff_utc:
                        continue
                except Exception:
                    pass

            subject = _decode_str(msg.get('Subject', '(sin asunto)'))
            sender = _decode_str(msg.get('From', ''))
            body = _extract_body(msg)

            if not body:
                print(f'    → [vacío] {subject[:60]}')
                continue

            print(f'    → {subject[:70]}')

            articles.append({
                'title': subject,
                'link': '',                      # email no tiene URL canónica
                'photographer': None,
                'photographers': None,
                'summary': _summary(body),
                'full_text': body,
                'image': '',
                'images': [],
                'source': f'Newsletter · {sender.split("<")[0].strip()}',
            })

        mail.logout()

    except imaplib.IMAP4.error as e:
        print(f'  [email] Error IMAP: {e}')
    except Exception as e:
        print(f'  [email] Error inesperado: {e}')

    return articles
