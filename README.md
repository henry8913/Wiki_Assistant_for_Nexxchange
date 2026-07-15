# Wiki Assistant per Nexxchange GolfSuite

Assistente AI per il manuale GolfSuite, basato su Agno + OpenRouter. Accessibile via **Telegram** e **widget web** per Confluence/sito.

**Cosa fa:**
- Risponde a domande sul manuale cercando nella wiki Confluence
- **Ragiona** sul contenuto — non copia e incolla, ma sintetizza e spiega con logica
- Alla fine di ogni risposta mostra il **link alla pagina esatta**
- **Memoria persistente** — ricorda le conversazioni precedenti (PostgreSQL)
- **Analisi immagini** — se gli mandi uno screenshot, lo analizza e lo collega al manuale
- **Descrizione immagini del wiki** — durante l'indicizzazione, ogni immagine viene descritta da un modello AI e resa ricercabile
- **Output con immagini** — può restituire immagini nella risposta se utile
- Supporta più lingue

---

## Quick Start con Docker

### 1. Prepara le chiavi API

| Cosa ti serve | Dove prenderlo |
|---|---|
| Token Telegram | `@BotFather` su Telegram → `/newbot` |
| OpenRouter API key | https://openrouter.ai/keys |
| API token Atlassian | https://id.atlassian.com/manage/api-tokens |
| ngrok token | https://dashboard.ngrok.com/get-started/your-authtoken |

### 2. Configura

```bash
cp .env.example .env
# Modifica .env con le tue chiavi
```

### 3. Avvia tutto

```bash
docker compose up -d
```

Avvia automaticamente: **PostgreSQL**, **ngrok** (tunnel HTTPS), **il bot** (si registra da solo su Telegram).

### 4. Ingerisci il wiki (una volta sola)

```bash
docker compose run --rm bot python -m wiki_assistant.ingest.run_ingest
```

---

## Accessi

### Telegram
Cerca il tuo bot su Telegram e parlaci. Il webhook si registra automaticamente all'avvio.

### Widget web (pagina intera)
```
https://<ngrok-url>.ngrok-free.dev/chat
```
Chat a pagina intera con sfondo brand Nexxchange.

### Widget fluttuante per Confluence (consigliato)
Pulsante in basso a destra, si apre la chat senza coprire la pagina.

In Confluence, modifica la pagina → inserisci **HTML Macro** → incolla:

```html
<div id="ws-chat-widget"></div>
<script src="https://<ngrok-url>.ngrok-free.dev/static/widget.js"></script>
```

**Attenzione:** l'URL ngrok cambia se riavvi Docker senza lo stesso `NGROK_AUTHTOKEN`.

---

## Comandi Docker

```bash
# Log del bot
docker compose logs -f bot

# Vedi URL ngrok
docker compose logs ngrok | grep "started tunnel"

# Ricostruisci (dopo modifiche al codice)
docker compose build bot && docker compose up -d

# Ingerisci spazi specifici
docker compose run --rm bot python -m wiki_assistant.ingest.run_ingest --spaces "GOLIT"

# Ferma tutto
docker compose down

# Ferma tutto e cancella il database
docker compose down -v
```

---
