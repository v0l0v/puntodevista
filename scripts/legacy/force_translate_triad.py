import os
import json
import urllib.request
import re
import time

DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG = json.load(open(os.path.join(DIR, 'config.json'))) if os.path.exists(os.path.join(DIR, 'config.json')) else {}
GEMINI_KEY = os.environ.get('GEMINI_KEY') or CONFIG.get('GEMINI_KEY')
GEMINI_MODEL = 'gemini-3.5-flash'
GEMINI_URL = f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_KEY}'

def call_gemini(prompt):
    body = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {'temperature': 0.1, 'maxOutputTokens': 2048}
    }
    req = urllib.request.Request(GEMINI_URL, data=json.dumps(body).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            return res['candidates'][0]['content']['parts'][0]['text'].strip()
    except Exception as e:
        return None

def translate_str(text, is_html=False):
    if not text or len(text.strip()) < 3:
        return text
    chunk = text[:2500] if is_html else text
    if is_html:
        prompt = f"Traduce este contenido HTML de fotografía al español manteniendo intactas todas las etiquetas HTML (img, a, figure, p):\n\n{chunk}"
    else:
        prompt = f"Traduce al español únicamente el siguiente titular o resumen fotográfico (sin comillas, sin explicaciones):\n\n{chunk}"
    res = call_gemini(prompt)
    if res:
        res = re.sub(r'^```html\s*', '', res, flags=re.IGNORECASE)
        res = re.sub(r'\s*```$', '', res).strip()
        res = re.sub(r'^["\']|["\']$', '', res).strip()
        return res
    return text

triad = ['colossal.json', 'odlp.json', 'shootitwithfilm.json']

for fname in triad:
    fpath = os.path.join(DIR, fname)
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    items = data.get('items', [])
    print(f"Traduciendo {fname} ({len(items[:8])} artículos)...")
    for it in items[:8]:
        if isinstance(it, dict):
            # Título
            t_orig = it.get('title', '')
            if t_orig:
                it['title'] = translate_str(t_orig)
            # Excerpt
            e_orig = it.get('excerpt', '')
            if e_orig:
                it['excerpt'] = translate_str(e_orig)
            # Content
            c_orig = it.get('content', '')
            if c_orig and len(c_orig) > 20:
                it['content'] = translate_str(c_orig, is_html=True)
    with open(fpath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"✅ {fname} guardado con traducciones en español.")

# Reflejar en feeds.json
with open(os.path.join(DIR, 'feeds.json'), 'r', encoding='utf-8') as f:
    f_data = json.load(f)

for fname in triad:
    src_id = fname.replace('.json', '')
    sub_data = json.load(open(os.path.join(DIR, fname), encoding='utf-8'))
    sub_items = sub_data.get('items', [])
    for it in f_data.get('items', []):
        if it.get('_source') == src_id:
            m = next((s for s in sub_items if (s.get('link') or s.get('title')) == (it.get('link') or it.get('title'))), None)
            if m:
                it['title'] = m.get('title')
                if m.get('excerpt'):
                    it['excerpt'] = m.get('excerpt')
                if m.get('content'):
                    it['content'] = m.get('content')

with open(os.path.join(DIR, 'feeds.json'), 'w', encoding='utf-8') as f:
    json.dump(f_data, f, ensure_ascii=False)

print("🎉 feeds.json actualizado con Colossal, ODLP y Shoot It With Film.")
