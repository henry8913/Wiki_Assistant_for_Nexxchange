#!/usr/bin/env bash
set -euo pipefail

if [ "${1:-}" != "python" ] || [ "${2:-}" != "-m" ] || [ "${3:-}" != "wiki_assistant.main" ]; then
    if [ $# -eq 0 ]; then
        echo "=== Wiki Assistant - Avvio Bot ==="
    else
        exec "$@"
    fi
fi

echo "Avvio del bot..."
exec python -m wiki_assistant.main
