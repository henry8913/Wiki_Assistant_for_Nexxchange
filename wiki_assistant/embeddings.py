"""Embeddings e compatibilità dello schema pgvector.

Le embedding possono essere locali (FastEmbed, nessuna API esterna) o
remote (OpenRouter, usato solo come fallback).

Se cambia il modello di embedding cambia anche la dimensione dei vettori:
una tabella pgvector ha una dimensione fissa, quindi la tabella va
ricreata e il contenuto re-indicizzato.
"""

from agno.knowledge.embedder.base import Embedder
from sqlalchemy import create_engine, text

from wiki_assistant.config import (
    DATABASE_URL,
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL,
    EMBEDDING_PROVIDER,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
)

VECTOR_TABLE = "wiki_knowledge_vectors"

_embedder: Embedder | None = None


def get_embedder() -> Embedder:
    """Return the configured embedder (local by default)."""
    global _embedder
    if _embedder is None:
        if EMBEDDING_PROVIDER == "openrouter":
            from agno.knowledge.embedder.openai import OpenAIEmbedder

            _embedder = OpenAIEmbedder(
                id="openai/text-embedding-3-small",
                api_key=OPENROUTER_API_KEY,
                base_url=OPENROUTER_BASE_URL,
                dimensions=1536,
            )
        else:
            from agno.knowledge.embedder.fastembed import FastEmbedEmbedder

            _embedder = FastEmbedEmbedder(
                id=EMBEDDING_MODEL,
                dimensions=EMBEDDING_DIMENSIONS,
            )
    return _embedder


def current_vector_dimension(db_url: str = DATABASE_URL, table_name: str = VECTOR_TABLE) -> int | None:
    """Return the dimension of the vector column, or None if the table is missing."""
    engine = create_engine(db_url)
    try:
        with engine.connect() as conn:
            schema = conn.execute(
                text(
                    "SELECT table_schema FROM information_schema.tables "
                    "WHERE table_name = :t LIMIT 1"
                ),
                {"t": table_name},
            ).scalar()
            if not schema:
                return None

            column_type = conn.execute(
                text(
                    "SELECT format_type(a.atttypid, a.atttypmod) "
                    "FROM pg_attribute a "
                    "WHERE a.attrelid = to_regclass(:qualified) "
                    "AND a.attname = 'embedding' AND a.attnum > 0 AND NOT a.attisdropped"
                ),
                {"qualified": f'"{schema}"."{table_name}"'},
            ).scalar()
            if not column_type:
                return None

            # 'vector(384)' -> 384
            dimension = column_type.split("(")[-1].split(")")[0]
            return int(dimension)
    finally:
        engine.dispose()


def ensure_vector_table(
    db_url: str = DATABASE_URL,
    table_name: str = VECTOR_TABLE,
    expected_dimension: int = EMBEDDING_DIMENSIONS,
) -> None:
    """Drop the vectors table when it was built for a different embedding size.

    pgvector stores a fixed dimension per column: keeping the old table would
    make every insert fail, so the table is recreated and the knowledge base
    re-ingested.
    """
    try:
        current = current_vector_dimension(db_url, table_name)
    except Exception as exc:
        print(f"⚠️  Controllo dimensione vettoriale saltato: {exc}")
        return

    if current is None or current == expected_dimension:
        return

    print(
        f"🔄 Dimensione embedding cambiata ({current} → {expected_dimension}): "
        f"ricreo la tabella '{table_name}'. Serve re-ingestare il contenuto."
    )

    engine = create_engine(db_url)
    try:
        with engine.connect() as conn:
            schema = conn.execute(
                text(
                    "SELECT table_schema FROM information_schema.tables "
                    "WHERE table_name = :t LIMIT 1"
                ),
                {"t": table_name},
            ).scalar()
            if schema:
                conn.execute(text(f'DROP TABLE IF EXISTS "{schema}"."{table_name}" CASCADE'))
                conn.commit()
    finally:
        engine.dispose()
