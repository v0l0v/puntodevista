import os
import json
import glob
import urllib.request
import re
import time

DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG = json.load(open(os.path.join(DIR, 'config.json'))) if os.path.exists(os.path.join(DIR, 'config.json')) else {}
GEMINI_KEY = os.environ.get('GEMINI_KEY') or CONFIG.get('GEMINI_KEY')
GEMINI_MODEL = 'gemini-3-flash-preview'
GEMINI_URL = f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_KEY}'

CACHE_FILE = os.path.join(DIR, 'translations_cache.json')
_CACHE = {}
if os.path.exists(CACHE_FILE):
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            _CACHE = json.load(f)
    except Exception:
        pass

def save_cache():
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(_CACHE, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def call_gemini(prompt):
    body = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {'temperature': 0.1, 'maxOutputTokens': 4096}
    }
    req = urllib.request.Request(GEMINI_URL, data=json.dumps(body).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                res = json.loads(resp.read().decode('utf-8'))
                return res['candidates'][0]['content']['parts'][0]['text'].strip()
        except Exception:
            time.sleep(2 * (attempt + 1))
    return None

def translate_str(text, is_html=False):
    if not text or len(text.strip()) < 3:
        return text
    h = str(hash(text))
    if h in _CACHE and not _CACHE[h].startswith("La traducción") and not "1." in _CACHE[h]:
        return _CACHE[h]

    chunk = text[:2500] if is_html else text
    if is_html:
        prompt = f"Eres un editor fotográfico. Traduce este texto HTML al español conservando intactas todas las etiquetas (img, a, figure, p). Devuelve ÚNICAMENTE el HTML traducido:\n\n{chunk}"
    else:
        prompt = f"Traduce al español únicamente el siguiente titular o texto fotográfico. Devuelve EXCLUSIVAMENTE la frase traducida sin notas, sin opciones ni comillas:\n\n{chunk}"

    res = call_gemini(prompt)
    if res:
        res = re.sub(r'^```html\s*', '', res, flags=re.IGNORECASE)
        res = re.sub(r'\s*```$', '', res).strip()
        res = re.sub(r'^["\']|["\']$', '', res).strip()
        if "1." in res and "\n" in res:
            res = res.split('\n')[0].replace('1.', '').strip()
        _CACHE[h] = res
        save_cache()
        return res
    return text

target_sources = ['colossal.json', 'odlp.json', 'shootitwithfilm.json', 'lomography.json', '35mmc.json', 'c41.json', 'swan.json', 'tpj.json', 'booooooom.json', 'lensculture.json', 'magnum.json', 'huck.json', 'phroom.json']

print(f"--- TRADUCIENDO TODAS LAS FUENTES CON GEMINI-3-FLASH-PREVIEW ---")

for sname in target_sources:
    fpath = os.path.join(DIR, sname)
    if not os.path.exists(fpath):
        continue
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            d = json.load(f)
        items = d.get('items', []) if isinstance(d, dict) else (d if isinstance(d, list) else [])
        if not items:
            continue
        print(f"Traduciendo {sname} ({len(items[:10])} artículos)...")
        for it in items[:10]:
            if isinstance(it, dict):
                it['title'] = translate_str(it.get('title', ''))
                if it.get('excerpt'):
                    it['excerpt'] = translate_str(it.get('excerpt', ''))
                if it.get('content') and len(it['content']) > 20:
                    it['content'] = translate_str(it.get('content', ''), is_html=True)
        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False)
        print(f"✅ {sname} traducido y guardado.")
    except Exception as e:
        print(f"⚠️ Error en {sname}: {e}")

# Sincronizar feeds.json
try:
    with open(os.path.join(DIR, 'feeds.json'), 'r', encoding='utf-8') as f:
        f_data = json.load(f)
    for it in f_data.get('items', []):
        if isinstance(it, dict):
            t_orig = it.get('title', '')
            h = str(hash(t_orig))
            if h in _CACHE:
                it['title'] = _CACHE[h]
            if it.get('excerpt'):
                he = str(hash(it['excerpt']))
                if he in _CACHE:
                    it['excerpt'] = _CACHE[he]
            if it.get('content'):
                hc = str(hash(it['content']))
                if hc in _CACHE:
                    it['content'] = _CACHE[hc]
    with open(os.path.join(DIR, 'feeds.json'), 'w', encoding='utf-8') as f:
        json.dump(f_data, f, ensure_ascii=False)
    print("✅ feeds.json sincronizado.")
except Exception as e:
    print(f"⚠️ Error feeds.json: {e}")

print("🎉 Proceso finalizado.")
