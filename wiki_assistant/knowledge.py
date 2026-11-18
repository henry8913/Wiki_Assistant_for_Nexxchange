from agno.knowledge.knowledge import Knowledge
from agno.vectordb.pgvector import PgVector, SearchType

from wiki_assistant.config import DATABASE_URL
from wiki_assistant.db import knowledge_contents_db
from wiki_assistant.embeddings import ensure_vector_table, get_embedder

_wiki_knowledge: Knowledge | None = None


def get_wiki_knowledge() -> Knowledge:
    global _wiki_knowledge
    if _wiki_knowledge is None:
        embedder = get_embedder()
        ensure_vector_table(expected_dimension=getattr(embedder, "dimensions", None) or 384)

        _wiki_knowledge = Knowledge(
            name="wiki_knowledge",
            # Fewer chunks = less context = faster answers (the default is 10,
            # which alone fills ~12k prompt tokens).
            max_results=4,
            vector_db=PgVector(
                db_url=DATABASE_URL,
                table_name="wiki_knowledge_vectors",
                search_type=SearchType.hybrid,
                embedder=embedder,
            ),
            contents_db=knowledge_contents_db,
        )
    return _wiki_knowledge
