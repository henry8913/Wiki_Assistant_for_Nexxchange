#!/usr/bin/env bash
set -euo pipefail

# Se è un comando diverso dal bot (es. run_ingest), eseguilo direttamente
if [ "${1:-}" != "python" ] || [ "${2:-}" != "-m" ] || [ "${3:-}" != "wiki_assistant.main" ]; then
    # Se non c'è nessun comando, parte il bot
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

# Aspetta che ngrok sia pronto
echo "In attesa di ngrok..."
for i in $(seq 1 30); do
    if curl -sf http://ngrok:4040/api/tunnels > /dev/null 2>&1; then
        echo "ngrok pronto!"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "WARN: ngrok non raggiungibile, avvio comunque il bot"
    fi
    sleep 2
done

# Recupera URL pubblico da ngrok e registra webhook
NGROK_URL=""
if curl -sf http://ngrok:4040/api/tunnels -o /tmp/tunnels.json 2>/dev/null; then
    NGROK_URL=$(python3 -c "
import json
data = json.load(open('/tmp/tunnels.json'))
for t in data.get('tunnels', []):
    if t.get('proto') == 'https':
        print(t['public_url'])
        break
" 2>/dev/null || echo "")
fi

if [ -n "$NGROK_URL" ]; then
    WEBHOOK_URL="${NGROK_URL}/telegram/webhook"
    echo "Registrazione webhook: $WEBHOOK_URL"
    if [ -n "${TELEGRAM_WEBHOOK_SECRET_TOKEN:-}" ]; then
        RESPONSE=$(curl -sf "https://api.telegram.org/bot${TELEGRAM_TOKEN}/setWebhook?url=${WEBHOOK_URL}&secret_token=${TELEGRAM_WEBHOOK_SECRET_TOKEN}" 2>&1 || echo "")
    else
        RESPONSE=$(curl -sf "https://api.telegram.org/bot${TELEGRAM_TOKEN}/setWebhook?url=${WEBHOOK_URL}" 2>&1 || echo "")
    fi
    echo "Risposta Telegram: $RESPONSE"
else
    echo "WARN: ngrok non disponibile. Per registrare il webhook manualmente:"
    echo "  1. Avvia ngrok: ngrok http 7777"
    echo "  2. Prendi l'URL https://xxxx.ngrok-free.app"
    echo "  3. Esegui:"
    echo "     curl \"https://api.telegram.org/bot${TELEGRAM_TOKEN}/setWebhook?url=https://xxxx.ngrok-free.app/telegram/webhook\""
    echo ""
    echo "Oppure verifica lo stato:"
    echo "  curl \"https://api.telegram.org/bot${TELEGRAM_TOKEN}/getWebhookInfo\""
fi

echo "Avvio del bot..."
exec python -m wiki_assistant.main
