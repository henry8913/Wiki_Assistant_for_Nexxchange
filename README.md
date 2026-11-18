<h1 align="center">Wiki Assistant — Nexxchange GolfSuite</h1>

Wiki Assistant è un assistente AI che risponde a qualsiasi domanda sul manuale **GolfSuite** di Nexxchange. Scrivi una domanda in linguaggio naturale, lui cerca nelle pagine Confluence e restituisce la risposta più pertinente spiegata con parole sue, citando sempre la fonte esatta con link. Parla italiano, inglese e altre lingue, ricorda le conversazioni precedenti e conosce anche il sito aziendale Nexxchange per contesto extra. Funziona dal browser — niente installazione, niente plugin.

<p align="center">
  <img src="IMG/1a.png" alt="Wiki Assistant" width="100%">
</p>

<p align="center">
  <a href="https://wiki-assistant.henrydev.it/chat" style="display:inline-block;padding:12px 28px;background:#79CAF7;color:#fff;border-radius:40px;text-decoration:none;font-weight:600;font-size:18px">🌐 Provalo ora</a>
</p>

---

## Indice

- [🏗️ Architettura](#architettura)
- [🛠️ Stack tecnologico](#stack-tecnologico)
- [📁 Struttura del progetto](#struttura-del-progetto)
- [🤖 Come funziona](#come-funziona)
- [🔑 Variabili d'ambiente](#variabili-dambiente)
- [🐳 Setup con Docker](#setup-con-docker)
- [💻 Sviluppo locale](#sviluppo-locale)
- [🌐 Accesso](#accesso)
- [🚀 Deploy automatico](#deploy-automatico)
- [⚙️ Comandi Docker](#comandi-docker)

---

## 🏗️ Architettura

Wiki Assistant implementa una pipeline **RAG (Retrieval-Augmented Generation)**:

```
Confluence Wiki ─┐
PDF locali      ├──>  Chunking  ──>  Embedding  ──>  pgvector (PostgreSQL)
Sito Nexxchange ─┘                                        │
                       ┌──────────────────────────────────┘
                       │
User  ──>  Chat UI  ──>  FastAPI  ──>  Agno Agent  ──>  Retrieval  ──>  LLM (OpenRouter)  ──>  Risposta + Fonti
```

1. **Indicizzazione**: un unico comando raccoglie le pagine Confluence, i PDF in `wiki_update/` e il sito Nexxchange, li suddivide in chunk e li vettorizza in PostgreSQL con pgvector.
2. **Ricerca**: quando un utente fa una domanda, il sistema cerca i chunk più simili semanticamente nel database.
3. **Generazione**: l'Agno Agent passa i chunk recuperati come contesto al LLM, che genera una risposta citando le fonti.

Ogni fonte è tracciata con la sua versione/fingerprint: alla riesecuzione vengono aggiornati **solo** i documenti cambiati, senza duplicati né re-embedding inutile.

---

## 🛠️ Stack tecnologico

| Componente | Tecnologia | Ruolo |
|---|---|---|
| Framework AI | [Agno](https://github.com/agno-agi/agno) | Orchestra agente, knowledge base e sessioni |
| LLM | [OpenRouter](https://openrouter.ai) (DeepSeek, GPT, Claude, ecc.) | Generazione risposte |
| Embedding | `text-embedding-3-small` via OpenRouter | Vettorizzazione chunk |
| Database | PostgreSQL 16 + [pgvector](https://github.com/pgvector/pgvector) | Ricerca semantica vettoriale |
| Backend | [FastAPI](https://fastapi.tiangolo.com/) | API REST e serving pagine |
| Frontend | HTML / CSS / JS vanilla | Chat widget e pagina intera |
| PDF | [pypdf](https://pypi.org/project/pypdf/) | Estrazione testo dai PDF locali |
| Container | [Docker](https://www.docker.com/) + Docker Compose | Ambiente isolato |
| Deploy | [GitHub Actions](https://github.com/features/actions) | Auto-deploy su push |
| Server | Oracle Linux, Nginx Proxy Manager | Hosting produzione |

---

## 📁 Struttura del progetto

```
wiki_assistant/
├── agent.py                  # Configurazione Agno Agent (prompt, modello)
├── main.py                   # Entrypoint FastAPI, routing, static files
├── config.py                 # Variabili d'ambiente e costanti
├── knowledge.py              # Knowledge base Agno + pgvector
├── db.py                     # Connessioni PostgreSQL (sessioni + knowledge)
├── utils.py                  # Utility (formattazione fonti, troncamento)
├── ingest/
│   ├── confluence.py         # Crawler pagine Confluence
│   ├── image_descriptor.py   # Descrizione immagini via vision LLM
│   ├── image_handler.py      # Download e gestione immagini
│   ├── local_docs.py         # Ingestion PDF locali da wiki_update/
│   ├── run_ingest.py         # Script principale: Confluence + PDF + sito
│   └── run_ingest_website.py # Crawler sito Nexxchange
├── static/
│   ├── chat.html             # Pagina chat full-screen
│   ├── widget.js             # Widget chat fluttuante
│   └── widget.css            # Stili chat (widget + full-page)

.github/workflows/
└── deploy.yml                # GitHub Actions deploy

docker-compose.yml            # Servizi bot + db
Dockerfile                    # Multi-stage: base, bot, ingest
entrypoint.sh                 # Entrypoint container bot
.env.example                  # Template variabili d'ambiente
```

---

## 🤖 Come funziona

### Agente (agent.py)

L'agente è configurato con:
- Modello LLM da OpenRouter (configurabile via `OPENROUTER_MODEL`)
- Knowledge base collegata al vettoriale
- Cronologia conversazione (ultimi 5 scambi)
- Prompt di sistema in italiano: istruzioni su come rispondere, citare le fonti, dare esempi, nessun LaTeX

### Knowledge base (knowledge.py)

La knowledge base usa:
- **PgVector** come vettoriale
- **Hybrid search** (combinazione di similarità vettoriale e full-text search)
- **OpenAI-compatible embedder** (`text-embedding-3-small`) via OpenRouter
- Tabella `knowledge_contents` per i metadati dei documenti

### Ingestion (run_ingest.py)

Un solo comando ingestion raccoglie **tutte** le fonti:

1. **Confluence** — si connette via API (Basic Auth), scansiona gli spazi configurati (`WIKI_SPACES`), estrae il testo di ogni pagina e ne genera le descrizioni delle immagini (via vision LLM). Gli spazi inesistenti/non accessibili vengono saltati con un warning.
2. **PDF locali** — legge tutti i `*.pdf` presenti in `wiki_update/` (vedi sotto), un file per ogni documentazione che ti viene passata.
3. **Sito Nexxchange** — crawler BFS su `https://www.nexxchange.com` (max 30 pagine), saltabile con `--no-website`.

Ogni fonte salva la propria **versione/fingerprint** nei metadati, quindi una nuova esecuzione:

- salta i documenti invariati (`up to date`)
- cancella i vecchi chunk e reinserisce quelli cambiati
- aggiunge i nuovi file

### 📄 Documentazione PDF locale (`wiki_update/`)

Metti qui qualsiasi PDF che vuoi rendere disponibile all'assistente:

```
wiki_update/
├── Guida_addebiti_soci_v23.pdf
├── Migrazione_club_Nexxchange.pdf
├── Modelli_di_fattura_Nexxchange.pdf
└── Stagioni_Nexxchange.pdf
```

La cartella è montata nel container (`./wiki_update:/app/wiki_update:ro`), quindi puoi **aggiungere o sostituire PDF senza ricostruire l'immagine**: basta rilanciare l'ingestion. Un file con lo stesso nome e contenuto diverso viene riconosciuto come aggiornato e sostituito automaticamente.

---

## 🔑 Variabili d'ambiente

| Variabile | Obbligatoria | Descrizione |
|---|---|---|
| `OPENROUTER_API_KEY` | ✅ | Chiave API da [openrouter.ai/keys](https://openrouter.ai/keys) |
| `OPENROUTER_MODEL` | ✅ | Modello LLM (es. `deepseek/deepseek-v4-flash`) |
| `WIKI_BASE_URL` | ✅ | URL base Confluence (es. `https://nexxchange.atlassian.net/wiki`) |
| `WIKI_SPACES` | ✅ | Chiavi spazi separati da virgola (es. `GOLIT,GOLFR`) |
| `WIKI_EMAIL` | ✅ | Email account Atlassian |
| `WIKI_API_TOKEN` | ✅ | API token da [id.atlassian.com/manage/api-tokens](https://id.atlassian.com/manage/api-tokens) |
| `DATABASE_URL` | ✅ | URI PostgreSQL (es. `postgresql+psycopg://ai:ai@db:5432/ai`) |
| `APP_ENV` | ❌ | `production` o `development` |
| `HOST` | ❌ | Host di ascolto (default `0.0.0.0`) |
| `PORT` | ❌ | Porta di ascolto (default `7777`) |

---

## 🐳 Setup con Docker

**Prerequisiti:** Docker e Docker Compose installati.

### 1. Prepara le chiavi

| Cosa ti serve | Dove prenderlo |
|---|---|
| OpenRouter API key | [openrouter.ai/keys](https://openrouter.ai/keys) |
| API token Atlassian | [id.atlassian.com/manage/api-tokens](https://id.atlassian.com/manage/api-tokens) |

### 2. Configura

```bash
cp .env.example .env
# Apri .env e inserisci le tue chiavi
```

### 3. Avvia

```bash
docker compose up -d
```

### 4. Ingerisci tutto (Confluence + PDF locali + sito)

```bash
docker compose run --rm bot python -m wiki_assistant.ingest.run_ingest
```

Un solo comando addestra l'assistente su tutte le fonti. Alla riesecuzione aggiorna solo ciò che è cambiato. Per forzare la re-indicizzazione completa:

```bash
docker compose run --rm bot python -m wiki_assistant.ingest.run_ingest --force
```

L'applicazione sarà disponibile su `http://localhost:7777/chat`.

---

## 💻 Sviluppo locale

**Prerequisiti:** Python 3.12+, PostgreSQL con pgvector.

### 1. Clona e configura

```bash
git clone https://github.com/henry8913/Wiki_Assistant_for_Nexxchange.git
cd Wiki_Assistant_for_Nexxchange
cp .env.example .env
# Modifica DATABASE_URL per il tuo PostgreSQL locale:
# DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/nome_db
```

### 2. Installa dipendenze

```bash
pip install -r requirements.txt
```

### 3. Avvia

```bash
python -m wiki_assistant.main
```

### 4. Ingerisci dati

```bash
python -m wiki_assistant.ingest.run_ingest
```

---

## 🌐 Accesso

### Chat a pagina intera — [wiki-assistant.henrydev.it/chat](https://wiki-assistant.henrydev.it/chat)

La versione principale: una pagina web con sfondo brand Nexxchange, ideale per l'uso quotidiano.

### Widget fluttuante

Aggiungi il pulsante chat su qualsiasi sito web. Incolla queste due righe nel HTML della pagina:

```html
<div id="ws-chat-widget"></div>
<script src="https://wiki-assistant.henrydev.it/static/widget.js"></script>
```

Il widget appare in basso a destra e si apre senza coprire il contenuto della pagina.

---

## 🚀 Deploy automatico

A ogni push sul branch `main`, GitHub Actions esegue il deploy sul server di produzione:

```yaml
# .github/workflows/deploy.yml
- Connessione SSH al server (158.180.235.83)
- git pull origin main
- docker compose up --build -d
```

Il server è un Oracle Linux con Nginx Proxy Manager che fa da reverse proxy per `wiki-assistant.henrydev.it`.

---

## ⚙️ Comandi Docker

```bash
# Log in tempo reale
docker compose logs -f bot

# Ricostruisci i container dopo modifiche al codice
docker compose up --build -d

# Ingestion completa: Confluence + PDF in wiki_update/ + sito Nexxchange
# (aggiorna solo ciò che è cambiato)
docker compose run --rm bot python -m wiki_assistant.ingest.run_ingest

# Ingestion forzata: re-indicizza tutto da zero
docker compose run --rm bot python -m wiki_assistant.ingest.run_ingest --force

# Solo Confluence + PDF, senza il sito aziendale
docker compose run --rm bot python -m wiki_assistant.ingest.run_ingest --no-website

# Ingerisci solo spazi specifici del wiki (salta sito)
docker compose run --rm bot python -m wiki_assistant.ingest.run_ingest --spaces "GOLIT"

# Ingerisci solo i PDF locali
docker compose run --rm bot python -c "from wiki_assistant.ingest.local_docs import ingest_local_pdfs; ingest_local_pdfs()"

# Terminale interattivo nel container bot
docker compose run --rm bot bash

# Ferma tutto
docker compose down

# Ferma e cancella il database (perde i dati)
docker compose down -v
```
---

<p align="center">
  <img src="IMG/3a.jpeg" alt="banner" width="100%">
</p>

<div style="display:flex;justify-content:space-between;align-items:center">
  <div>
    <a href="https://nexxchange.atlassian.net/wiki">Confluence Wiki</a> ·
    <a href="https://www.nexxchange.com">Nexxchange.com</a><br>
    <small>Wiki Assistant per Nexxchange GolfSuite</small>
  </div>
  <img src="IMG/2a.png" alt="footer" width="25%">
</div>
