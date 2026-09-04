#!/bin/bash
set -e

DIR="/opt/v0l0v/apps/puntodevista"
cd "$DIR"

# Función de alerta en caso de fallo
on_error() {
  local exit_code=$?
  local line_no=$1
  echo "❌ Error en línea $line_no (código de salida: $exit_code)"
  ./venv/bin/python3 send_alert.py "Falló la ejecución diaria de PDV en la línea $line_no (código: $exit_code)" || true
}
trap 'on_error $LINENO' ERR

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

# 5. Regenerar feed RSS (servido directamente por el VPS)
echo "[4/4] Actualizando Feed RSS..."
./venv/bin/python3 generate_podcast_feed.py

FECHA_FIN=$(date '+%Y-%m-%d %H:%M:%S')
echo "[$FECHA_FIN] Proceso diario completado con éxito 100% autónomo en el VPS."
