#!/bin/bash
set -e

DIR="/opt/v0l0v/apps/puntodevista"
cd "$DIR"

FECHA_LOG=$(date '+%Y-%m-%d %H:%M:%S')
echo "========================================"
echo "[$FECHA_LOG] Arrancando ejecución diaria de Punto de Vista"
echo "========================================"

# 1. Asegurar repositorio actualizado
git pull --rebase origin main || true

# 2. Generar Digest Diario
echo "[1/4] Generando digest diario..."
./venv/bin/python3 daily_digest.py

# 3. Actualizar cachés estáticos
echo "[2/4] Actualizando cachés de artículos..."
./venv/bin/python3 update_static_data.py --keep-lomo || true

# 4. Generar Podcast y publicar a Telegram
echo "[3/4] Generando podcast y enviando a Telegram..."
./venv/bin/python3 daily_podcast.py

# 5. Publicar en GitHub Releases y regenerar feed RSS
echo "[4/4] Publicando Release y actualizando Feed RSS..."
DATE=$(date +%F)
MP3="podcast/podcast-${DATE}.mp3"
COVER="podcast-cover-${DATE}.jpg"

if [ -f "$MP3" ]; then
  gh release upload episodios "$MP3" --clobber 2>/dev/null || echo "Aviso: Release upload ignorado si gh no está autenticado"
fi

if [ -f "$COVER" ]; then
  gh release upload episodios "$COVER" --clobber 2>/dev/null || true
elif [ -f "podcast-cover-${DATE}.png" ]; then
  gh release upload episodios "podcast-cover-${DATE}.png" --clobber 2>/dev/null || true
fi

./venv/bin/python3 generate_podcast_feed.py

# 6. Sincronizar cambios a GitHub
git add resumenes podcast_meta.json podcast.xml *.json 2>/dev/null || true
git commit -m "chore: daily digest & podcast $(date +%F) [vps]" || echo "Nada que commitear"

for i in 1 2 3; do
  git pull --rebase origin main || true
  git push origin main && break || sleep 5
done

FECHA_FIN=$(date '+%Y-%m-%d %H:%M:%S')
echo "[$FECHA_FIN] Proceso diario completado con éxito."
