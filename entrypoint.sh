#!/usr/bin/env bash
set -euo pipefail

if [ "${1:-}" != "python" ] || [ "${2:-}" != "-m" ] || [ "${3:-}" != "wiki_assistant.main" ]; then
    if [ $# -eq 0 ]; then
        echo "=== Wiki Assistant - Avvio Bot ==="
    else
        exec "$@"
    fi
fi

if [ -z "${TELEGRAM_TOKEN:-}" ]; then
    echo "ERRORE: TELEGRAM_TOKEN non impostato"
    exit 1
fi

WEBHOOK_URL="${WEBHOOK_DOMAIN:-http://localhost:7777}/telegram/webhook"
echo "Registrazione webhook Telegram: $WEBHOOK_URL"

if [ -n "${TELEGRAM_WEBHOOK_SECRET_TOKEN:-}" ]; then
    RESPONSE=$(curl -sf "https://api.telegram.org/bot${TELEGRAM_TOKEN}/setWebhook?url=${WEBHOOK_URL}&secret_token=${TELEGRAM_WEBHOOK_SECRET_TOKEN}" 2>&1 || echo "ERRORE")
else
    RESPONSE=$(curl -sf "https://api.telegram.org/bot${TELEGRAM_TOKEN}/setWebhook?url=${WEBHOOK_URL}" 2>&1 || echo "ERRORE")
fi
echo "Risposta Telegram: $RESPONSE"

echo "Avvio del bot..."
exec python -m wiki_assistant.main
