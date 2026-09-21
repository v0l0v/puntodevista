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
    if [ -d "$DIR/.git/rebase-merge" ] || [ -d "$DIR/.git/rebase-apply" ]; then
        echo "[$(date -Iseconds)] ⚠️ Rebase previo incompleto detectado. Abortando..."
        git rebase --abort 2>/dev/null || true
    fi

    if ! git pull --autostash --rebase origin main; then
        echo "[$(date -Iseconds)] 🚨 Conflicto en git pull. Abortando rebase inmediatamente..."
        git rebase --abort 2>/dev/null || true
        PYTHON="$DIR/venv/bin/python3"
        [ ! -f "$PYTHON" ] && PYTHON="python3"
        $PYTHON "$DIR/send_alert.py" "Conflicto en vps_auto_pull.sh en el VPS. Se abortó el rebase automáticamente para evitar bloqueo." 2>/dev/null || true
        exit 1
    fi
    echo "[$(date -Iseconds)] ✅ VPS actualizado."
fi

