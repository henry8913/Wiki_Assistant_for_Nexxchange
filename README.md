<p align="center">
  <img src="IMG/1a.png" alt="Wiki Assistant" width="100%">
</p>

<h1 align="center">Wiki Assistant — Nexxchange GolfSuite</h1>

<p align="center">
  Domande sul manuale GolfSuite? Parla con Wiki Assistant.
</p>

<p align="center">
  <a href="https://wiki-assistant.henrydev.it/chat">🌐 Provalo ora</a>
</p>

---

## Cosa fa

- **Cerca nel wiki Confluence** e risponde con parole tue
- Mostra il **link alla pagina esatta** come fonte
- **Memoria persistente** — ricorda le conversazioni
- Supporta **immagini** — descrizioni automatiche delle immagini del wiki
- Conosce il **sito aziendale Nexxchange** come contesto
- Multi-lingua

---

## Stack

<p align="center">
  Agno · OpenRouter · pgvector · FastAPI · PostgreSQL · Docker
</p>

---

## Quick Start con Docker

### 1. Prepara le chiavi

| Cosa ti serve | Dove prenderlo |
|---|---|
| OpenRouter API key | [openrouter.ai/keys](https://openrouter.ai/keys) |
| API token Atlassian | [id.atlassian.com/manage/api-tokens](https://id.atlassian.com/manage/api-tokens) |

### 2. Configura

```bash
cp .env.example .env
# Modifica .env con le tue chiavi
```

### 3. Avvia

```bash
docker compose up -d
```

### 4. Ingerisci il wiki

```bash
docker compose run --rm bot python -m wiki_assistant.ingest.run_ingest
```

### 5. (Opzionale) Ingerisci il sito Nexxchange

```bash
docker compose run --rm bot python -m wiki_assistant.ingest.run_ingest_website
```

---

## Accesso

### Widget web — [wiki-assistant.henrydev.it/chat](https://wiki-assistant.henrydev.it/chat)
Chat a pagina intera con sfondo brand Nexxchange.

### Widget fluttuante
Pulsante in basso a destra, si apre senza coprire la pagina.

```html
<div id="ws-chat-widget"></div>
<script src="https://wiki-assistant.henrydev.it/static/widget.js"></script>
```

---

## Comandi Docker

```bash
# Log
docker compose logs -f bot

# Ricostruisci
docker compose up --build -d

# Ingerisci spazi specifici
docker compose run --rm bot python -m wiki_assistant.ingest.run_ingest --spaces "GOLIT"

# Ingerisci sito
docker compose run --rm bot python -m wiki_assistant.ingest.run_ingest_website

# Ferma tutto
docker compose down

# Ferma e cancella db
docker compose down -v
```
