#!/bin/bash
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# Asegurar TMPDIR ejecutable para phonemizer / libespeak-ng en VPS
export TMPDIR="$DIR/tmp_audio"
mkdir -p "$TMPDIR"

echo "=========================================="
echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] Inicio Diario Punto de Vista ==="
echo "=========================================="

echo ">> 1. Generando Digest Diario..."
python3 daily_digest.py || echo "⚠️ Warning: daily_digest reporto advertencia"

echo ">> 2. Actualizando datos estaticos..."
python3 update_static_data.py --keep-lomo || echo "⚠️ Warning: update_static_data reporto advertencia"

echo ">> 3. Generando Podcast Diario con Kokoro-82M..."
python3 daily_podcast.py || echo "⚠️ Warning: daily_podcast reporto advertencia"

echo ">> 4. Regenerando Feed RSS..."
python3 generate_podcast_feed.py || echo "⚠️ Warning: generate_podcast_feed reporto advertencia"

echo ">> 5. Sincronizando respaldo con GitHub..."
git add resumenes/ podcast_meta.json podcast.xml assets/covers/ archive.db 2>/dev/null || true
git commit -m "chore(auto): daily update $(date +%F)" || echo "Nada nuevo que commitear"
for i in 1 2 3; do
  git pull --rebase --autostash origin main 2>/dev/null || true
  git push origin main 2>/dev/null && echo "✅ Respaldo sincronizado con GitHub" && break || sleep 5
done

echo "=========================================="
echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] Finalizado ==="
echo "=========================================="
