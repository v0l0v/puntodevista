#!/bin/bash
# cron_runner.sh — Delegado canónico a run_daily.sh (SSOT)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$DIR/run_daily.sh" "$@"
