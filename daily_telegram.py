import json
import os
import random
import re
import subprocess
import sys
import time
import urllib.request
from datetime import date, datetime
from pathlib import Path

import requests

DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(DIR, 'resumenes')
PODCAST_DIR = os.path.join(DIR, 'podcast')
META_PATH = os.path.join(DIR, 'podcast_meta.json')

CONFIG = {}
try:
    CONFIG = json.load(open(os.path.join(DIR, 'config.json')))
except Exception:
    pass


def _cfg(key):
    return os.environ.get(key) or CONFIG.get(key)


TG_TOKEN = _cfg('TG_TOKEN')
TG_CHAT_ID = _cfg('TG_CHAT_ID')
GEMINI_KEY = _cfg('GEMINI_KEY')
GEMINI_MODEL = 'gemini-3.5-flash'
GEMINI_URL = f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_KEY}'

MAX_RETRIES = 5
RETRY_DELAY = 15


def find_latest_podcast(target_date=None):
    files = sorted(Path(OUT_DIR).glob('*.podcast.md'), reverse=True)
    if target_date:
        for f in files:
            if target_date.isoformat() in f.name:
                return f
        return None
    return files[0] if files else None


def gemini_request(prompt):
    body = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {
            'temperature': 0.7,
            'maxOutputTokens': 8192,
        }
    }
    data = json.dumps(body).encode()
    req = urllib.request.Request(GEMINI_URL, data=data,
                                 headers={'Content-Type': 'application/json'},
                                 method='POST')
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read())
            text = result['candidates'][0]['content']['parts'][0]['text']
            return text.strip()
        except urllib.error.HTTPError as e:
            err = e.read().decode()
            retryable = (
                e.code >= 500
                or 'quota' in err.lower()
                or 'RESOURCE_EXHAUSTED' in err
                or 'UNAVAILABLE' in err
            )
            if retryable and attempt < MAX_RETRIES - 1:
                wait = RETRY_DELAY * (attempt + 1)
                if 'quota' in err.lower() or 'RESOURCE_EXHAUSTED' in err:
                    reason = 'Cuota excedida'
                else:
                    reason = f'Error {e.code}'
                print(f'  {reason}, reintentando en {wait}s...')
                time.sleep(wait)
                continue
            print(f'  Error API: {err[:300]}')
            return None
        except (urllib.error.URLError, json.JSONDecodeError, KeyError) as e:
            print(f'  Error: {e}')
            return None
    print('  Se agotaron los reintentos.')
    return None


def send_telegram(text, parse_mode='HTML'):
    url = f'https://api.telegram.org/bot{TG_TOKEN}/sendMessage'
    try:
        resp = requests.post(url, json={
            'chat_id': TG_CHAT_ID,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': True
        }, timeout=30)
        return resp.json()
    except requests.RequestException as e:
        print(f'  Error Telegram: {e}')
        return None


def send_telegram_audio(audio_path, caption='', filename='podcast.mp3'):
    url = f'https://api.telegram.org/bot{TG_TOKEN}/sendAudio'
    try:
        with open(audio_path, 'rb') as f:
            files = {'audio': (filename, f, 'audio/mpeg')}
            data = {'chat_id': TG_CHAT_ID}
            if caption:
                data['caption'] = caption
            resp = requests.post(url, data=data, files=files, timeout=120)
            return resp.json()
    except requests.RequestException as e:
        print(f'  Error Telegram audio: {e}')
        return None


def generate_audio(text, out_path):
    try:
        subprocess.run([
            'edge-tts',
            '--voice', 'es-ES-ElviraNeural',
            '--text', text,
            '--write-media', out_path
        ], check=True, capture_output=True, text=True, timeout=120)
        return True
    except subprocess.CalledProcessError as e:
        print(f'  Error edge-tts: {e.stderr[:300]}')
        return False
    except FileNotFoundError:
        print('  edge-tts no instalado')
        return False


def tag_audio(audio_path, title):
    tmp = audio_path + '.tagged.mp3'
    try:
        subprocess.run([
            'ffmpeg', '-y', '-i', audio_path,
            '-metadata', 'title=' + title,
            '-metadata', 'artist=Punto de vista Podcast',
            '-metadata', 'album=Punto de vista Podcast',
            '-metadata', 'album_artist=Punto de vista Podcast',
            '-codec', 'copy',
            tmp,
        ], check=True, capture_output=True, text=True, timeout=60)
        os.replace(tmp, audio_path)
        return True
    except Exception as e:
        print(f'  ⚠️ No se pudo etiquetar el audio: {e}')
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        return False


def clean_text(t):
    t = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF'
               r'\U0001F1E0-\U0001F1FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F'
               r'\U0001FA70-\U0001FAFF\u2702-\u27B0\u24C2-\U0001F251'
               r'\U0001F004\u2600-\u26FF\uFE0F]', '', t)
    t = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', t)
    t = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', t)
    t = re.sub(r'<\/?[^>]+>', '', t)
    t = re.sub(r'\*\*(.+?)\*\*', r'\1', t)
    t = re.sub(r'\*(.+?)\*', r'\1', t)
    t = re.sub(r'[_*~`]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    t = re.sub(r'&#8217;', "'", t)
    t = re.sub(r'&#8211;', '–', t)
    t = re.sub(r'&#\d+;', '', t)
    t = t.replace('\\', '')
    t = re.sub(r'\|', ', ', t)
    return t


def clean_caption(t, title=''):
    t = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', t)
    t = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', t)
    t = re.sub(r'<\/?[^>]+>', '', t)
    t = re.sub(r'\*\*(.+?)\*\*', r'\1', t)
    t = re.sub(r'\*(.+?)\*', r'\1', t)
    t = re.sub(r'[_~`]', '', t)
    t = re.sub(r'&#8217;', "'", t)
    t = re.sub(r'&#8211;', '–', t)
    t = re.sub(r'&#\d+;', '', t)
    t = t.replace('\\', '')
    t = re.sub(r'^---+\s*[A-ZÁÉÍÓÚÑ]+\s*---*\s*$', '', t, flags=re.M)
    lines = [re.sub(r'\s+', ' ', ln).strip() for ln in t.split('\n')]
    out = []
    blank = False
    for ln in lines:
        if ln:
            out.append(ln)
            blank = False
        elif not blank:
            out.append('')
            blank = True
    t = '\n'.join(out).strip()
    if title:
        t = re.sub(r'^\s*' + re.escape(title) + r'\s*(?:[—\-–]\s*)?', '', t, count=1)
    return t


def parse_summary(summary):
    podcast_title = ''
    resumen = ''
    locutable = summary
    remaining = summary
    if TITLE_MARKER in summary:
        pre, post = summary.split(TITLE_MARKER, 1)
        podcast_title = pre.strip()
        remaining = post
    loc_parts = remaining.split(LOCUTABLE_MARKER, 1)
    if len(loc_parts) == 2:
        locutable = loc_parts[1].strip()
        resumen = loc_parts[0].strip()
    else:
        resumen = remaining.strip()
    if not podcast_title and resumen:
        for ln in resumen.split('\n'):
            ln = ln.strip()
            if not ln:
                continue
            if re.match(r'^---+', ln):
                continue
            podcast_title = ln
            break
    return podcast_title, resumen, locutable



TITLE_MARKER = '---TITLE---'
LOCUTABLE_MARKER = '---LOCUTABLE---'

MESES_ES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
            'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']

def fmt_fecha_es(d):
    return f'{d.day} de {MESES_ES[d.month - 1]} de {d.year}'

def build_summary_prompt(podcast_content):
    today = date.today().isoformat()
    return f"""Hoy es {today}. A continuación tienes el texto completo de varios artículos de fotografía de distintas fuentes.

{podcast_content}

Escribe tu respuesta en TRES secciones separadas por estas líneas exactas:
{TITLE_MARKER}
{LOCUTABLE_MARKER}

PRIMERA SECCIÓN - Título creativo en español para el episodio. Solo el título, sin explicaciones ni notas.

SEGUNDA SECCIÓN - Resúmenes para redes sociales (formato exacto):
- Sin introducciones, sin títulos de programa, sin despedidas, sin notas.
- Por cada artículo: título en negrita **Título** y debajo 2-3 frases de resumen atractivas en español.
- Tono ameno e inspirador, como para redes sociales.

TERCERA SECCIÓN (solo el texto locutable para el audio del podcast):
REGLAS ESTRICTAS:
- SOLO TEXTO PARA LEER EN VOZ ALTA. Nada de markdown, asteriscos, corchetes, etiquetas como "Título:", "Fotógrafo:", "Fuente:", viñetas, guiones, etc.
- Títulos de obras, exposiciones, series, libros, películas: TRADÚCELOS al español natural ("Paisajes etéreos", no "Ethereal Landscapes"). Si no tienes traducción oficial, adapta el significado.
- Nombres propios de personas/lugares: MANTÉN el original.
- Estructura de programa de radio:
  1. APERTURA obligatoria: "¡Hola, muy buenas! Bienvenidos a Punto de vista, tu dosis diaria de inspiración fotográfica. Hoy es [fecha en español, ej: 9 de agosto de 2026]."
  2. BLOQUES POR FUENTE: Para cada fuente que tenga artículos, haz una transición natural → "En Colossal hoy..." / "En Lomography Magazine encontramos..." / "Y en Shoot It With Film..." → narra cada artículo en 2-3 frases con tono cercano, como contándole a un amigo. Une artículos de la misma fuente con fluidez.
  3. TRANSICIONES entre fuentes: "Y siguiendo con...", "También en...", "Cambiamos de tercio hacia...", "Para cerrar esta ronda...".
  4. CIERRE obligatorio: "Y hasta aquí la inspiración de hoy. ¡Nos escuchamos mañana con más fotografía!"
- Duración objetivo: 3-4 minutos de locución (~400-600 palabras).
- Ritmo: frases cortas, respiradas, lenguaje oral (contracciones, "vamos a ver", "fíjate", "resulta que")."""


def clean_for_gemini(text):
    """Limpia el texto para Gemini: quita markdown, etiquetas, deja solo contenido legible."""
    t = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)          # **negrita** → negrita
    t = re.sub(r'\*([^*]+)\*', r'\1', t)                # *cursiva* → cursiva
    t = re.sub(r'`([^`]+)`', r'\1', t)                  # `code` → code
    t = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', t)      # [link](url) → link
    t = re.sub(r'^#+\s*', '', t, flags=re.M)            # # encabezados
    t = re.sub(r'^(?:Fotógrafo|Fotógrafos|Fuente|Source):\s*.+$', '', t, flags=re.M)
    t = re.sub(r'\n{3,}', '\n\n', t)                    # múltiples saltos
    return t.strip()


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    today = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    print(f'[{ts}] daily_telegram · {today}')

    podcast_file = find_latest_podcast(today)
    if not podcast_file:
        print(f'  No hay archivo .podcast.md para {today}')
        return

    print(f'  Leyendo: {podcast_file.name}')
    content = podcast_file.read_text(encoding='utf-8')

    print('  Limpiando contenido para Gemini...')
    content = clean_for_gemini(content)

    print('  Enviando a Gemini...')
    prompt = build_summary_prompt(content)
    summary = gemini_request(prompt)

    if not summary:
        print('  No se obtuvo respuesta de Gemini.')
        return

    print(f'  Resumen generado ({len(summary)} chars)')

    podcast_title, resumen, locutable = parse_summary(summary)

    print('  Generando audio...')
    clean_text_audio = clean_text(locutable)
    if not clean_text_audio:
        print('  ❌ No hay texto locutable para audio')
        return
    os.makedirs(PODCAST_DIR, exist_ok=True)
    audio_path = os.path.join(PODCAST_DIR, f'podcast-{today.isoformat()}.mp3')
    if generate_audio(clean_text_audio, audio_path):
        size = os.path.getsize(audio_path)
        print(f'  Audio generado ({size/1024:.0f} KB)')

        description = clean_caption(resumen, clean_text(podcast_title))

        duration = 0
        try:
            probe = subprocess.run(
                ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', audio_path],
                capture_output=True, text=True, timeout=30)
            if probe.returncode == 0:
                duration = int(float(json.loads(probe.stdout)['format']['duration']))
        except Exception:
            duration = 0

        day_image = ''
        img_path = os.path.join(OUT_DIR, f'digest-{today.isoformat()}.image')
        if os.path.exists(img_path):
            try:
                with open(img_path, encoding='utf-8') as f:
                    day_image = f.read().strip()
            except Exception:
                day_image = ''
        images = []
        images_path = os.path.join(OUT_DIR, f'digest-{today.isoformat()}.images.json')
        if os.path.exists(images_path):
            try:
                with open(images_path, encoding='utf-8') as f:
                    images = json.load(f)
            except Exception:
                images = []
        images = [img for img in images if img != day_image]
        if not day_image and images:
            day_image = random.choice(images)
            print(f'  Sin imagen del día, usando aleatoria de la galería: {day_image[:70]}')
        meta = []
        if os.path.exists(META_PATH):
            try:
                with open(META_PATH, encoding='utf-8') as f:
                    meta = json.load(f)
            except Exception:
                meta = []
        meta = [m for m in meta if m.get('date') != today.isoformat()]
        entry = {
            'date': today.isoformat(),
            'description': description,
            'image': day_image,
            'images': images,
            'podcast_title': podcast_title,
            'size': size,
            'duration': duration,
        }
        meta.append(entry)
        with open(META_PATH, 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        print(f'  Meta del podcast actualizado ({len(meta)} episodios)')

        tag_title = clean_text(podcast_title) if podcast_title else f'Podcast {today.isoformat()}'
        if tag_audio(audio_path, tag_title):
            print('  Audio etiquetado (Punto de vista Podcast)')

        if day_image:
            print('  Generando portada del episodio...')
            try:
                subprocess.run([
                    sys.executable, os.path.join(DIR, 'make_podcast_cover.py'),
                    today.isoformat(), day_image
                ], check=True, capture_output=True, text=True, timeout=60)
                print('  Portada generada')
            except subprocess.CalledProcessError as e:
                print(f'  ⚠️ Error generando portada: {e.stderr[:200]}')
            except Exception as e:
                print(f'  ⚠️ Error generando portada: {e}')

        print('  Enviando audio a Telegram...')
        audio_caption = f'🎙️ {fmt_fecha_es(today)}'
        if podcast_title:
            audio_caption += f'\n{clean_text(podcast_title)}'
        if resumen:
            audio_caption += f'\n\n{clean_caption(resumen, clean_text(podcast_title))}'
        if len(audio_caption) > 1024:
            audio_caption = audio_caption[:1021] + '...'
        audio_filename = f'Punto de vista - {today.isoformat()}.mp3'
        result = send_telegram_audio(audio_path, audio_caption, audio_filename)
        if result and result.get('ok'):
            print('  ✅ Audio enviado')
        else:
            err = result.get('description', '?') if result else '?'
            print(f'  ❌ Error al enviar audio: {err}')
    else:
        print('  ❌ Error al generar audio')


if __name__ == '__main__':
    main()
