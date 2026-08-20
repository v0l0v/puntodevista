import json
import os
import random
import re
import shutil
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


def get_day_music(target_date=None):
    d = target_date or date.today()
    weekday = d.weekday()  # 0=Lunes, 6=Domingo
    day_patterns = [
        'day_0_lunes.mp3',
        'day_1_martes.mp3',
        'day_2_miercoles.mp3',
        'day_3_jueves.mp3',
        'day_4_viernes.mp3',
        'day_5_sabado.mp3',
        'day_6_domingo.mp3'
    ]
    track_name = day_patterns[weekday]
    track_path = os.path.join(DIR, 'assets', 'mp3', track_name)
    if os.path.exists(track_path):
        return track_path
    # Fallback si no existe la pista del día
    fallback = os.path.join(DIR, 'assets', 'mp3', 'bg_lofi.mp3')
    return fallback if os.path.exists(fallback) else None


TTS_VOICE = os.environ.get('TTS_VOICE', 'es-ES-ElviraNeural')
TTS_RATE = os.environ.get('TTS_RATE', '-4%')


def generate_audio(text, out_path, episode_date=None):
    bg_music = get_day_music(episode_date)
    tmp_dir = os.path.join(DIR, 'tmp_audio')
    os.makedirs(tmp_dir, exist_ok=True)

    # Fonetizar palabras comunes en inglés que suenan mal en el lector español
    clean = text
    clean = re.sub(r'\bnewsletters\b', 'niusleters', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\bnewsletter\b', 'niusleter', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\bcolossal\b', 'colosal', clean, flags=re.IGNORECASE)

    # Dividir el texto en bloques usando el marcador ---PAUSA--- o dobles saltos de línea
    raw_blocks = re.split(r'---PAUSA---|\[PAUSA\]', clean)
    blocks = [b.strip() for b in raw_blocks if b.strip()]

    if not blocks:
        blocks = [clean.strip()]

    print(f'  Generando locución ({TTS_VOICE}, rate={TTS_RATE}) en {len(blocks)} bloque(s)...')

    # Si no hay música de fondo disponible, generar en un solo archivo directo
    if not bg_music or len(blocks) == 1 and not os.path.exists(bg_music):
        try:
            subprocess.run([
                'edge-tts',
                '--voice', TTS_VOICE,
                f'--rate={TTS_RATE}',
                '--text', clean,
                '--write-media', out_path
            ], check=True, capture_output=True, text=True, timeout=120)
            return True
        except Exception as e:
            print(f'  Error edge-tts: {e}')
            return False

    try:
        voice_files = []
        for i, b in enumerate(blocks):
            raw_mp3 = os.path.join(tmp_dir, f'v_raw_{i}.mp3')
            wav_out = os.path.join(tmp_dir, f'v_{i}.wav')
            subprocess.run([
                'edge-tts',
                '--voice', TTS_VOICE,
                f'--rate={TTS_RATE}',
                '--text', b,
                '--write-media', raw_mp3
            ], check=True, capture_output=True, text=True, timeout=120)
            subprocess.run([
                'ffmpeg', '-y', '-i', raw_mp3,
                '-ar', '44100', '-ac', '2', wav_out
            ], check=True, capture_output=True, timeout=60)
            voice_files.append(wav_out)

        # 1. Intro musical de 12 segundos (fade in 1.5s, fade out 2.5s)
        intro_wav = os.path.join(tmp_dir, 'intro.wav')
        subprocess.run([
            'ffmpeg', '-y', '-ss', '00:00:00', '-i', bg_music, '-t', '12',
            '-af', 'afade=t=in:ss=0:d=1.5,afade=t=out:st=9.5:d=2.5,volume=0.30',
            '-ar', '44100', '-ac', '2', intro_wav
        ], check=True, capture_output=True, timeout=60)

        # 2. Interludio musical de 6 segundos (fade in 1.0s, fade out 1.8s)
        inter_wav = os.path.join(tmp_dir, 'inter.wav')
        subprocess.run([
            'ffmpeg', '-y', '-ss', '00:00:20', '-i', bg_music, '-t', '6',
            '-af', 'afade=t=in:ss=0:d=1.0,afade=t=out:st=4.2:d=1.8,volume=0.30',
            '-ar', '44100', '-ac', '2', inter_wav
        ], check=True, capture_output=True, timeout=60)

        # 3. Outro musical de 12 segundos (fade in 1.5s, fade out 3.5s)
        outro_wav = os.path.join(tmp_dir, 'outro.wav')
        subprocess.run([
            'ffmpeg', '-y', '-ss', '00:00:45', '-i', bg_music, '-t', '12',
            '-af', 'afade=t=in:ss=0:d=1.5,afade=t=out:st=8.5:d=3.5,volume=0.30',
            '-ar', '44100', '-ac', '2', outro_wav
        ], check=True, capture_output=True, timeout=60)

        # Ensamblar secuencia completa
        sequence = [intro_wav]
        for i, vf in enumerate(voice_files):
            sequence.append(vf)
            if i < len(voice_files) - 1:
                sequence.append(inter_wav)
        sequence.append(outro_wav)

        inputs = []
        filter_inputs = ''
        for idx, fpath in enumerate(sequence):
            inputs.extend(['-i', fpath])
            filter_inputs += f'[{idx}:a]'

        cmd = ['ffmpeg', '-y'] + inputs + [
            '-filter_complex', f'{filter_inputs}concat=n={len(sequence)}:v=0:a=1[outa]',
            '-map', '[outa]',
            '-b:a', '192k',
            out_path
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=180)

        # Limpiar temporales
        try:
            shutil.rmtree(tmp_dir)
        except Exception:
            pass

        return True

    except Exception as e:
        print(f'  ⚠️ Error al mezclar cortinillas: {e}. Fallback a audio plano...')
        try:
            subprocess.run([
                'edge-tts',
                '--voice', TTS_VOICE,
                f'--rate={TTS_RATE}',
                '--text', clean,
                '--write-media', out_path
            ], check=True, capture_output=True, text=True, timeout=120)
            return True
        except Exception as err:
            print(f'  Error fallback: {err}')
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

DIAS_SEMANA_ES = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
MESES_ES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
            'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']

def fmt_fecha_es(d):
    return f'{d.day} de {MESES_ES[d.month - 1]} de {d.year}'

def fmt_fecha_completa_es(d):
    dia_sem = DIAS_SEMANA_ES[d.weekday()]
    return f'{dia_sem}, {d.day} de {MESES_ES[d.month - 1]} de {d.year}'

def get_episode_number(target_date, meta_path=META_PATH):
    try:
        if os.path.exists(meta_path):
            with open(meta_path, encoding='utf-8') as f:
                meta = json.load(f)
            dates = sorted(set(m.get('date') for m in meta if m.get('date')))
            target_iso = target_date.isoformat()
            if target_iso in dates:
                return dates.index(target_iso) + 1
            else:
                prior_dates = [d for d in dates if d < target_iso]
                return len(prior_dates) + 1
    except Exception:
        pass
    return 1

def build_summary_prompt(podcast_content, episode_date=None):
    d = episode_date or date.today()
    today_iso = d.isoformat()
    fecha_completa = fmt_fecha_completa_es(d)
    ep_num = get_episode_number(d)
    return f"""Hoy es {today_iso}. A continuación tienes el texto completo de varios artículos de fotografía de distintas fuentes (recopilados en las últimas 24 horas).

{podcast_content}

Escribe tu respuesta en TRES secciones separadas por estas líneas exactas:
{TITLE_MARKER}
{LOCUTABLE_MARKER}

PRIMERA SECCIÓN - Título creativo, sugerente y periodístico en español para el episodio (ej: "Entre el misterio de la noche y la magia del colodión húmedo"). Solo el título, sin explicaciones ni notas.

SEGUNDA SECCIÓN - Resúmenes completos y atractivos para la web y redes sociales (formato exacto):
- Sin introducciones, sin títulos de programa, sin despedidas, sin notas.
- Por cada artículo o fuente habitual:
  **Título del artículo**
  Resumen de 3-4 frases bien estructuradas:
  1. ¿Qué historia, tema o concepto visual aborda el proyecto?
  2. ¿Qué técnica, estética o proceso fotográfico se utiliza (medio formato, analógico, blanco y negro contrastado, luz natural, etc.)?
  3. ¿Cuál es el valor o reflexión artística que aporta al espectador/fotógrafo?
- CASO ESPECIAL - SI HAY NEWSLETTER DE FOTONISTAS (Ana Arbonés / Ana de Fotonistas / fotonistas.com):
  No hagas un resumen completo ni destripes la lección completa que Ana envía a sus suscriptores para no hacer competencia desleal. Da solo 2 frases picantes y sugerentes que generen "hype" e intriga sobre el tema que plantea hoy, e invita directamente a los lectores a suscribirse a su Fotoletter en fotonistas.com.

TERCERA SECCIÓN (solo el texto locutable para el audio del podcast):
REGLAS ESTRICTAS:
- SOLO TEXTO PARA LEER EN VOZ ALTA. Cero markdown, asteriscos, corchetes o encabezados como "Título:", "Fotógrafo:", etc.
- SEPARADORES MUSICALES: Coloca la línea exacta ---PAUSA--- justo después de la apertura, entre cada bloque temático/fuente, antes del bloque de newsletters y antes del cierre final.
- FONÉTICA: Escribe siempre "niusleter" o "niusleters" en lugar de "newsletter/s", y "el Magazine de arte online Colosal" en lugar de "Colossal", para que la voz en español los lea perfectamente natural.
- TRADUCCIÓN: Títulos de obras, exposiciones, series, libros: TRADÚCELOS al español natural y fluido ("Viaje nocturno", no "Night Journey"). Nombres propios de autores/ciudades: MANTÉN el original.
- ESTRUCTURA DE PROGRAMA DE RADIO FOTOGRÁFICO:
  1. APERTURA OBLIGATORIA (CON GANCHO Y HYPE INICIAL):
     - Saluda con calidez y sigue este esquema exacto:
       "¡Hola, muy buenas! Bienvenidos a Punto de vista, tu dosis diaria de inspiración fotográfica. Hoy es {fecha_completa} y este es el episodio {ep_num} de Punto de vista... y [GANCHO/HYPE: frase breve y sugerente levantando expectación sobre uno de los proyectos o noticias estrella del boletín de hoy, por ejemplo: 'tenemos un proyecto fascinante de X sobre Y que analizaremos en el episodio de hoy / hoy descubrimos la impresionante mirada de X sobre Y que desgranaremos a continuación...']."
     - Coloca inmediatamente la línea exacta ---PAUSA--- después de la apertura.
  2. NARRACIÓN DE HISTORIAS: No leas una lista seca de noticias. Conecta los artículos con transiciones naturales (ej: "Y de la luz del atardecer nos vamos al contraste radical de...", "Cambiando de tercio, en la revista Lomography encontramos...").
     En cada noticia, destaca no solo quién es el autor, sino cómo mira: la luz, el grano, el desenfoque, el soporte utilizado y qué lección visual podemos llevarnos hoy al coger la cámara.
     Separa cada bloque de fuente con ---PAUSA---.
  3. BLOQUE DE NIUSLETERS (TRATAMIENTO A ANA DE FOTONISTAS):
     Si hay correos en la sección de newsletters:
     - Si el correo es de Ana de Fotonistas (fotonistas.com / Ana Arbonés): Trátala con cercanía, naturalidad y complicidad (como a alguien habitual de la comunidad). NO hace falta presentarla, ni repetir su biografía ni profesión en cada episodio.
       * REGLA DE ORO: NO reveles toda la información ni destripes el contenido exclusivo de su correo.
       * Da solo unas pinceladas o una pequeña semilla de reflexión que abra el apetito y cree curiosidad ("hype") sobre el tema de su correo de hoy.
       * Invita de forma directa y natural a los oyentes a entrar en fotonistas.com y suscribirse a su Fotoletter diaria para leer sus reflexiones completas.
     - Si hay otros correos, coméntalos también de forma distendida.
     - Separa este bloque con ---PAUSA---.
  4. CIERRE inspirador: inventa una variante fresca de este mensaje: "Y hasta aquí la inspiración de hoy. No olvidéis visitar las webs y revistas originales y suscribiros a sus niusleters para apoyar su trabajo. Gracias por acompañarnos, por mantener viva la pasión por la imagen y por ayudarnos a mirar el mundo con más detalle. ¡Cargad baterías o carretes, y nos escuchamos mañana!"
- TONO Y RITMO: Muy humano, cercano, entusiasta y cómplice con la comunidad fotográfica. Usa frases respiradas y pausas naturales con puntos suspensivos ("...") o comas para dar calidez y ritmo radiofónico.
- Duración objetivo: 3-5 minutos de locución (~450-650 palabras)."""




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
    prompt = build_summary_prompt(content, today)
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
    if generate_audio(clean_text_audio, audio_path, today):
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
        if os.environ.get('SKIP_TELEGRAM'):
            print('  SKIP_TELEGRAM=1, no se envía a Telegram')
        else:
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
