# Wiki Assistant per Nexxchange GolfSuite

Assistente AI per il manuale GolfSuite, basato su Agno + OpenRouter + pgvector. Accessibile via **widget web**.

**Cosa fa:**
- Risponde a domande sul manuale cercando nella wiki Confluence
- **Ragiona** sul contenuto — non copia e incolla, ma sintetizza e spiega con logica
- Alla fine di ogni risposta mostra il **link alla pagina esatta**
- **Memoria persistente** — ricorda le conversazioni precedenti (PostgreSQL)
- **Descrizione immagini del wiki** — durante l'indicizzazione, ogni immagine viene descritta da un modello AI e resa ricercabile
- **Output con immagini** — può restituire immagini nella risposta se utile
- Conosce il sito aziendale Nexxchange (https://www.nexxchange.com) come contesto
- Supporta più lingue

---

## Quick Start con Docker

### 1. Prepara le chiavi API

| Cosa ti serve | Dove prenderlo |
|---|---|
| OpenRouter API key | https://openrouter.ai/keys |
| API token Atlassian | https://id.atlassian.com/manage/api-tokens |

### 2. Configura

```bash
cp .env.example .env
# Modifica .env con le tue chiavi
```

### 3. Avvia tutto

```bash
docker compose up -d
```

Avvia automaticamente: **PostgreSQL** e **il bot**.

### 4. Ingerisci il wiki (una volta sola)

```bash
docker compose run --rm bot python -m wiki_assistant.ingest.run_ingest
```

### 5. (Opzionale) Ingerisci il sito Nexxchange

```bash
docker compose run --rm bot python -m wiki_assistant.ingest.run_ingest_website
```

---

## Accesso

### Widget web (pagina intera)
```
https://wiki-assistant.henrydev.it/chat
```

Chat a pagina intera con sfondo brand Nexxchange.

### Widget fluttuante (consigliato)
Pulsante in basso a destra, si apre la chat senza coprire la pagina.

Inserisci in una pagina HTML:

```html
<div id="ws-chat-widget"></div>
<script src="https://wiki-assistant.henrydev.it/static/widget.js"></script>
```

---

## Comandi Docker

```bash
# Log del bot
docker compose logs -f bot

# Ricostruisci (dopo modifiche al codice)
docker compose up --build -d

# Ingerisci spazi specifici
docker compose run --rm bot python -m wiki_assistant.ingest.run_ingest --spaces "GOLIT"

# Ingerisci sito Nexxchange
docker compose run --rm bot python -m wiki_assistant.ingest.run_ingest_website

# Ferma tutto
docker compose down

# Ferma tutto e cancella il database
docker compose down -v
```
