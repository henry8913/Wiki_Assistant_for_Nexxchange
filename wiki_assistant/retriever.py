"""Retrieval con boost lessicale per la knowledge base del wiki.

La ricerca vettoriale da sola sbaglia sulle domande che contengono un termine
raro (es. "Platzhalter"): il termine pesa poco nell'embedding e il documento
giusto finisce dietro a pagine che parlano genericamente dell'argomento.

Il retriever quindi unisce due segnali:
1. la ricerca ibrida (vettoriale + full-text) della Knowledge base Agno;
2. una ricerca lessicale esatta sui termini "rari" della domanda.
"""

import re

from sqlalchemy import text

from wiki_assistant.config import DATABASE_URL
from wiki_assistant.embeddings import VECTOR_TABLE

STOPWORDS = {
    # italiano
    "come", "cosa", "sono", "dove", "quando", "perche", "perché", "quale", "quali",
    "questo", "questa", "questi", "queste", "quello", "quella", "della", "dello",
    "delle", "degli", "della", "nella", "nello", "nelle", "negli", "sulla", "sullo",
    "sulle", "sugli", "dalla", "dallo", "dalle", "dagli", "posso", "devo", "vorrei",
    "fare", "faccio", "creare", "creo", "usare", "uso", "serve", "significa",
    "funziona", "funzionano", "esempio", "esempi", "aiuto", "spiegami", "aiutami",
    "sapere", "voglio", "dovrei", "sicuro", "grazie", "ciao", "allora", "anche",
    # inglese
    "what", "which", "where", "when", "how", "does", "this", "that", "there",
    "with", "from", "about", "into", "please", "thanks",
}

TERM_PATTERN = re.compile(r"[^\W\d_][\w\-]{4,}", re.UNICODE)


def _query_terms(query: str) -> list[str]:
    terms = set()
    for raw in TERM_PATTERN.findall(query):
        term = raw.lower()
        if term not in STOPWORDS:
            terms.add(term)
    return sorted(terms)


def _lexical_docs(terms: list[str], limit: int, db_url: str = DATABASE_URL):
    """Rows of the vector table containing the rarest terms of the query."""
    if not terms:
        return []

    engine = __import__("sqlalchemy").create_engine(db_url)
    try:
        with engine.connect() as conn:
            schema = conn.execute(
                text(
                    "SELECT table_schema FROM information_schema.tables "
                    "WHERE table_name = :t LIMIT 1"
                ),
                {"t": VECTOR_TABLE},
            ).scalar()
            if not schema:
                return []
            table = f'"{schema}"."{VECTOR_TABLE}"'

            conditions = " OR ".join(f"content ILIKE :t{i}" for i in range(len(terms)))
            params = {f"t{i}": f"%{t}%" for i, t in enumerate(terms)}
            params["limit"] = 400
            rows = conn.execute(
                text(
                    f"SELECT name, content, meta_data, content_hash FROM {table} "
                    f"WHERE {conditions} LIMIT :limit"
                ),
                params,
            ).fetchall()
    finally:
        engine.dispose()

    scored = []
    for name, content, meta_data, content_hash in rows:
        haystack = (content or "").lower()
        hits = sum(1 for t in terms if t in haystack)
        if hits:
            scored.append((hits, name, content, meta_data, content_hash))
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[:limit]


def wiki_retriever(agent=None, query: str = "", num_documents: int | None = None, **kwargs):
    """Return the wiki documents most relevant to ``query``."""
    from wiki_assistant.knowledge import get_wiki_knowledge

    limit = num_documents or 6
    kb = get_wiki_knowledge()

    results = []
    seen = set()

    def add(doc_dict):
        key = (doc_dict.get("content") or "")[:200]
        if key and key not in seen:
            seen.add(key)
            results.append(doc_dict)

    # 1. hybrid search
    try:
        for doc in kb.search(query, max_results=max(limit, 8)):
            add(
                {
                    "name": doc.name,
                    "content": doc.content,
                    "meta_data": doc.meta_data or {},
                }
            )
    except Exception as exc:
        print(f"  (retrieval error: {exc})")

    # 2. lexical boost for rare terms
    for _hits, name, content, meta_data, _hash in _lexical_docs(_query_terms(query), limit):
        add({"name": name, "content": content, "meta_data": meta_data or {}})

    return results[: limit + 2]
