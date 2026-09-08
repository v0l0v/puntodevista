#!/bin/bash
set -eo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# 1. Protección contra ejecuciones solapadas (flock)
LOCK_FILE="$DIR/.daily_runner.lock"
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️ Proceso diario de Punto de Vista ya en ejecución. Saliendo sin solapar."
  exit 0
fi

# 2. Selección de entorno de ejecución Python
if [ -f "$DIR/venv/bin/python3" ]; then
  PYTHON="$DIR/venv/bin/python3"
else
  PYTHON="python3"
fi

# 3. Directorio temporal seguro y ejecutable para Kokoro / libespeak-ng
export TMPDIR="$DIR/tmp_audio"
mkdir -p "$TMPDIR"

# 4. Función de notificación en caso de error
on_error() {
  local exit_code=$?
  local line_no=$1
  echo "❌ Error en línea $line_no (código de salida: $exit_code)"
  $PYTHON send_alert.py "Falló la ejecución diaria de PDV en la línea $line_no (código: $exit_code)" || true
}
trap 'on_error $LINENO' ERR

FECHA_LOG=$(date '+%Y-%m-%d %H:%M:%S')
echo "=========================================================="
echo "=== [$FECHA_LOG] Arrancando ciclo diario Punto de Vista ==="
echo "=========================================================="

# 5. Enrutamiento SOCKS5 a través de WARP si está activo en el VPS
if ss -tulpn 2>/dev/null | grep -q ':40000 '; then
  export HTTPS_PROXY="socks5h://127.0.0.1:40000"
fi

# 6. Sincronización previa del repositorio
echo ">> [1/6] Sincronizando estado con GitHub..."
git pull --rebase --autostash origin main || true

# 7. Generar Digest Diario
echo ">> [2/6] Generando digest diario..."
$PYTHON daily_digest.py

# 8. Actualizar listas de feeds y cachés estáticos (todas las fuentes activas)
echo ">> [3/6] Actualizando feeds y cachés de artículos..."
$PYTHON update_lists.py || echo "⚠️ Advertencia en update_lists (continuando)"

# 8b. Saneamiento y traducción continua del archivo
echo ">> Saneando y traduciendo artículos pendientes del archivo..."
$PYTHON scripts/repair_all_translations.py --limit-per-source 8 --feeds-limit 20 || echo "⚠️ Advertencia en repair_all_translations (continuando)"

# 9. Generar Podcast con Kokoro TTS y publicar en Telegram
echo ">> [4/6] Generando podcast y publicando en Telegram..."
$PYTHON daily_podcast.py

# 10. Regenerar Feed RSS del Podcast
echo ">> [5/6] Actualizando feed RSS (podcast.xml)..."
$PYTHON generate_podcast_feed.py

# 11. Sincronizar archivo histórico SQLite (FTS5 + vectores sqlite-vec)
echo ">> [6/6] Indexando archivo histórico y vectores..."
$PYTHON sync_archive.py || echo "⚠️ Advertencia en sync_archive (continuando)"

# 12. Actualizar reporte de salud y observabilidad
echo ">> Actualizando métricas de observabilidad (health.json)..."
$PYTHON health_check.py || echo "⚠️ Advertencia en health_check (continuando)"

# 13. Respaldo y sincronización de estado hacia GitHub
echo ">> Sincronizando respaldo con GitHub..."
git add resumenes/ data/ podcast.xml assets/covers/ 2>/dev/null || true
git commit -m "chore(auto): daily update $(date +%F)" || echo "Nada nuevo que commitear"
for i in 1 2 3; do
  git pull --rebase --autostash origin main 2>/dev/null || true
  git push origin main 2>/dev/null && echo "✅ Respaldo sincronizado con GitHub" && break || sleep 5
done

FECHA_FIN=$(date '+%Y-%m-%d %H:%M:%S')
echo "=========================================================="
echo "=== [$FECHA_FIN] Proceso diario completado con éxito ==="
echo "=========================================================="
