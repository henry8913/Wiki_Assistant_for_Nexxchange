import os

from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: str = "") -> str:
    """Read an env var, falling back to the default when empty or missing."""
    return os.getenv(name, "").strip() or default


# ---------------------------------------------------------------------------
# OpenCode (Console API) - provider principale per LLM e visione
# ---------------------------------------------------------------------------
OPENCODE_API_KEY: str = _env("OPENCODE_API_KEY")
OPENCODE_MODEL: str = _env("OPENCODE_MODEL", "deepseek-v4.1-flash")

# Piano Go: https://opencode.ai/inference/go/openai/v1
# Piano pay-as-you-go: https://opencode.ai/inference/openai/v1
OPENCODE_BASE_URL: str = _env(
    "OPENCODE_BASE_URL", "https://opencode.ai/inference/go/openai/v1"
)

# Header obbligatorio sul piano Go: serve a instradare la conversazione e a
# riusare la prompt cache. Deve essere stabile tra le richieste.
OPENCODE_SESSION_ID: str = _env("OPENCODE_SESSION_ID", "ses_wiki_assistant_golfsuite")

# Il piano Go si aspetta traffico "coding agent": serve un user agent proprio
# invece di quello generico della libreria HTTP.
OPENCODE_USER_AGENT: str = _env("OPENCODE_USER_AGENT", "wiki-assistant/1.0")

# Modello per la descrizione delle immagini del wiki (vision).
# Claude Haiku è molto più rapido di DeepSeek su questo compito.
VISION_MODEL: str = _env("VISION_MODEL", "claude-haiku-5-5")

# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------
# fastembed = modello locale, nessuna API esterna (default)
# openrouter = embedding remoto (solo fallback)
EMBEDDING_PROVIDER: str = _env("EMBEDDING_PROVIDER", "fastembed")
EMBEDDING_MODEL: str = _env(
    "EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)
EMBEDDING_DIMENSIONS: int = int(_env("EMBEDDING_DIMENSIONS", "384"))

# ---------------------------------------------------------------------------
# OpenRouter (opzionale: usato solo come fallback per le embeddings)
# ---------------------------------------------------------------------------
OPENROUTER_API_KEY: str = _env("OPENROUTER_API_KEY")
OPENROUTER_MODEL: str = _env("OPENROUTER_MODEL", "openai/gpt-4o")
OPENROUTER_BASE_URL: str = _env("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# ---------------------------------------------------------------------------
# Wiki / Confluence
# ---------------------------------------------------------------------------
WIKI_BASE_URL: str = _env("WIKI_BASE_URL")
WIKI_SPACES: list[str] = [
    s.strip() for s in _env("WIKI_SPACES", "GOLIT").split(",") if s.strip()
]
WIKI_EMAIL: str = _env("WIKI_EMAIL")
WIKI_API_TOKEN: str = _env("WIKI_API_TOKEN")

# ---------------------------------------------------------------------------
# Database (PostgreSQL with pgvector)
# ---------------------------------------------------------------------------
DATABASE_URL: str = _env(
    "DATABASE_URL", "postgresql+psycopg://ai:ai@localhost:5532/ai"
)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
APP_ENV: str = _env("APP_ENV", "development")
HOST: str = _env("HOST", "0.0.0.0")
PORT: int = int(_env("PORT", "7777"))
