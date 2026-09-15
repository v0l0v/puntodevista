#!/bin/bash
# scripts/vps_auto_pull.sh — Script ejecutable por cron en el VPS (ej. cada 10 min)
# Comprueba si hay commits nuevos en GitHub y los descarga automáticamente.

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$DIR" || exit 1

git fetch origin main > /dev/null 2>&1
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" != "$REMOTE" ]; then
    echo "[$(date -Iseconds)] 🔄 Nuevos commits en GitHub. Sincronizando VPS..."
    git pull --autostash --rebase origin main
    echo "[$(date -Iseconds)] ✅ VPS actualizado."
fi
