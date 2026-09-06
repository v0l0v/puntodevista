#!/bin/bash
set -eo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# Lock anti-solapamiento de feeds
LOCK_FEEDS="$DIR/.feeds_runner.lock"
exec 201>"$LOCK_FEEDS"
if ! flock -n 201; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️ Actualización de feeds ya en ejecución. Omitiendo."
  exit 0
fi

# Si el runner diario está activo, no interferir
LOCK_DAILY="$DIR/.daily_runner.lock"
if [ -f "$LOCK_DAILY" ]; then
  exec 200<"$LOCK_DAILY"
  if ! flock -n 200; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ℹ️ Proceso diario en curso. Omitiendo feeds periódicos para evitar interferencias."
    exit 0
  fi
fi

if [ -f "$DIR/venv/bin/python3" ]; then
  PYTHON="$DIR/venv/bin/python3"
else
  PYTHON="python3"
fi

if ss -tulpn 2>/dev/null | grep -q ':40000 '; then
  export HTTPS_PROXY="socks5h://127.0.0.1:40000"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iniciando actualización periódica de feeds..."
$PYTHON update_lists.py

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Notificando novedades a Telegram..."
$PYTHON telegram_news.py

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Ciclo de feeds completado."
