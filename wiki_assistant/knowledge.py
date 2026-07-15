from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.pgvector import PgVector, SearchType

from wiki_assistant.config import DATABASE_URL, OPENROUTER_API_KEY, OPENROUTER_BASE_URL
from wiki_assistant.db import knowledge_contents_db

_wiki_knowledge: Knowledge | None = None


def get_wiki_knowledge() -> Knowledge:
    global _wiki_knowledge
    if _wiki_knowledge is None:
        _wiki_knowledge = Knowledge(
            name="wiki_knowledge",
            vector_db=PgVector(
                db_url=DATABASE_URL,
                table_name="wiki_knowledge_vectors",
                search_type=SearchType.hybrid,
                embedder=OpenAIEmbedder(
                    id="openai/text-embedding-3-small",
                    api_key=OPENROUTER_API_KEY,
                    base_url=OPENROUTER_BASE_URL,
                ),
            ),
            contents_db=knowledge_contents_db,
        )
    return _wiki_knowledge
