import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")

# OpenRouter base URL (default is https://openrouter.ai/api/v1)
# Can be overridden for custom endpoints
OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# Wiki / Confluence
WIKI_BASE_URL: str = os.getenv("WIKI_BASE_URL", "")
WIKI_SPACES: list[str] = [
    s.strip() for s in os.getenv("WIKI_SPACES", "GOLIT").split(",") if s.strip()
]
WIKI_EMAIL: str = os.getenv("WIKI_EMAIL", "")
WIKI_API_TOKEN: str = os.getenv("WIKI_API_TOKEN", "")

# Database (PostgreSQL with pgvector)
DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+psycopg://ai:ai@localhost:5532/ai")

# App
APP_ENV: str = os.getenv("APP_ENV", "development")
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "7777"))
