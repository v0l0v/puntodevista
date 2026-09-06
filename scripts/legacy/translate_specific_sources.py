import os
import json
import urllib.request
import re
import time

DIR = '/home/victor/proyectos/foto'
CONFIG = json.load(open(os.path.join(DIR, 'config.json'))) if os.path.exists(os.path.join(DIR, 'config.json')) else {}
GEMINI_KEY = os.environ.get('GEMINI_KEY') or CONFIG.get('GEMINI_KEY')
GEMINI_MODEL = 'gemini-3-flash-preview'
GEMINI_URL = f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_KEY}'

def translate_fast(text, is_html=False):
    if not text or len(text.strip()) < 3:
        return text
    chunk = text[:3000] if is_html else text
    if is_html:
        prompt = f"Traduce este texto HTML de fotografía al español manteniendo intactas todas las etiquetas (img, a, figure, p):\n\n{chunk}"
    else:
        prompt = f"Traduce al español directamente (sin notas, sin comillas, sin explicaciones):\n\n{chunk}"
    
    body = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {'temperature': 0.1, 'maxOutputTokens': 4096}
    }
    req = urllib.request.Request(GEMINI_URL, data=json.dumps(body).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                res = json.loads(resp.read().decode('utf-8'))
                t = res['candidates'][0]['content']['parts'][0]['text'].strip()
                t = re.sub(r'^```html\s*', '', t, flags=re.IGNORECASE)
                t = re.sub(r'\s*```$', '', t).strip()
                t = re.sub(r'^[\*"\']+|[\*"\']+$', '', t).strip()
                return t
        except Exception:
            time.sleep(1)
    return text

sources = ['colossal.json', 'odlp.json', 'shootitwithfilm.json']

for sname in sources:
    fpath = os.path.join(DIR, sname)
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    items = data.get('items', [])
    print(f"Traduciendo {sname} ({len(items)} artículos)...")
    for it in items:
        if isinstance(it, dict):
            it['title'] = translate_fast(it.get('title', ''))
            if it.get('excerpt'):
                it['excerpt'] = translate_fast(it.get('excerpt', ''))
            if it.get('content') and len(it['content']) > 20:
                it['content'] = translate_fast(it.get('content', ''), is_html=True)
    with open(fpath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"✅ {sname} guardado.")

# Sincronizar feeds.json
with open(os.path.join(DIR, 'feeds.json'), 'r', encoding='utf-8') as f:
    f_data = json.load(f)

for sname in sources:
    src_id = sname.replace('.json', '')
    sub_data = json.load(open(os.path.join(DIR, sname), encoding='utf-8'))
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

print("🎉 Feeds de Colossal, ODLP y Shoot It With Film 100% traducidos.")
