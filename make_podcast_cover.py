import os
import shutil
import sys
import urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

DIR = os.path.dirname(os.path.abspath(__file__))
LOGO = os.path.join(DIR, 'assets', 'logos', 'logoFpdv.png')
SIZE = 1400
BG = '#0a0a0a'
ACCENT = (255, 1, 0)


def make_glow(size):
    gs = 320
    glow = Image.new('RGBA', (gs, gs), (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
    c = gs / 2
    r_max = gs / 2
    for i in range(40, 0, -1):
        r = r_max * i / 40
        alpha = int(26 * (1 - i / 40))
        d.ellipse([c - r, c - r, c + r, c + r], fill=ACCENT + (alpha,))
    glow = glow.filter(ImageFilter.GaussianBlur(30))
    return glow.resize((size, size), Image.LANCZOS)


def download_image(url, cache_dir):
    cache_dir.mkdir(parents=True, exist_ok=True)
    fname = url.split('/')[-1].split('?')[0]
    if not fname or '.' not in fname:
        fname = 'day_image.jpg'
    path = cache_dir / fname
    if not path.exists():
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'
            })
            with urllib.request.urlopen(req, timeout=30) as resp:
                with open(path, 'wb') as f:
                    f.write(resp.read())
        except Exception as e:
            print(f'  Error descargando imagen: {e}')
            return None
    return path


def create_cover(day_image_path, date_str, out_path, subtitle=None):
    img = Image.new('RGBA', (SIZE, SIZE), BG)

    if day_image_path and os.path.exists(day_image_path):
        try:
            day_img = Image.open(day_image_path).convert('RGBA')
            w, h = day_img.size
            s = min(w, h)
            left = (w - s) // 2
            top = (h - s) // 2
            day_img = day_img.crop((left, top, left + s, top + s))
            day_img = day_img.resize((SIZE, SIZE), Image.LANCZOS)

            dark_overlay = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 180))
            day_img = Image.alpha_composite(day_img, dark_overlay)

            img.alpha_composite(day_img)
        except Exception as e:
            print(f'  Error procesando imagen del día: {e}')

    img.alpha_composite(make_glow(SIZE))

    if os.path.exists(LOGO):
        logo = Image.open(LOGO).convert('RGBA')
        logo_size = 400
        logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
        img.alpha_composite(logo, ((SIZE - logo_size) // 2, (SIZE - logo_size) // 2 - 80))

    draw = ImageDraw.Draw(img)
    try:
        font_title = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 52)
        font_sub = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 32)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    title = 'Punto de vista'
    if not subtitle:
        subtitle = f'Podcast diario · {date_str}'

    title_w = draw.textlength(title, font=font_title)
    sub_w = draw.textlength(subtitle, font=font_sub)

    y_center = SIZE // 2 + 120
    draw.text(((SIZE - title_w) // 2, y_center), title, font=font_title, fill=(255, 255, 255, 255))
    draw.text(((SIZE - sub_w) // 2, y_center + 60), subtitle, font=font_sub, fill=(200, 200, 200, 255))

    img = img.convert('RGB')
    img.save(out_path, format='JPEG', quality=85, optimize=True)
    print(f'Portada generada: {out_path} ({img.size[0]}x{img.size[1]})')


def main():
    if len(sys.argv) < 2:
        print('Uso: python make_podcast_cover.py <YYYY-MM-DD> [image_url]')
        sys.exit(1)

    date_str = sys.argv[1]
    image_url = sys.argv[2] if len(sys.argv) > 2 else None

    cache_dir = Path(DIR) / '.cover_cache'
    day_image_path = None

    if image_url:
        print(f'  Descargando imagen del día: {image_url[:80]}...')
        day_image_path = download_image(image_url, cache_dir)

    out_name = f'podcast-cover-{date_str}.jpg'
    out_path = os.path.join(DIR, out_name)

    subtitle = sys.argv[3] if len(sys.argv) > 3 else None
    create_cover(day_image_path, date_str, out_path, subtitle)

    # Copiar también a podcast/ y assets/covers/ para disponibilidad estática y feeds
    podcast_dir = os.path.join(DIR, 'podcast')
    os.makedirs(podcast_dir, exist_ok=True)
    podcast_cover_path = os.path.join(podcast_dir, out_name)
    try:
        shutil.copy2(out_path, podcast_cover_path)
    except Exception:
        pass

    assets_covers_dir = os.path.join(DIR, 'assets', 'covers')
    os.makedirs(assets_covers_dir, exist_ok=True)
    assets_cover_path = os.path.join(assets_covers_dir, out_name)
    try:
        shutil.copy2(out_path, assets_cover_path)
        print(f'Copia estática guardada en: {assets_cover_path}')
    except Exception as e:
        print(f'  ⚠️ Error al copiar a assets/covers: {e}')


if __name__ == '__main__':
    main()