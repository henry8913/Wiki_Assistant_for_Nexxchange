"""Retrieval con boost lessicale per la knowledge base del wiki.

La ricerca vettoriale da sola sbaglia sulle domande che contengono un termine
raro (es. "Platzhalter"): il termine pesa poco nell'embedding e il documento
giusto finisce dietro a pagine che parlano genericamente dell'argomento.

Il retriever quindi unisce due segnali:
1. la ricerca ibrida (vettoriale + full-text) della Knowledge base Agno;
2. una ricerca lessicale esatta sui soli termini *rari* della domanda, cioè
   quelli che compaiono in pochi chunk (un termine comune come "fattura" non
   aggiunge nulla e porterebbe solo rumore).
"""

import re

from sqlalchemy import create_engine, text

from wiki_assistant.config import DATABASE_URL
from wiki_assistant.embeddings import VECTOR_TABLE

STOPWORDS = {
    "come", "cosa", "sono", "dove", "quando", "perche", "perché", "quale", "quali",
    "questo", "questa", "questi", "queste", "quello", "quella", "della", "dello",
    "delle", "degli", "nella", "nello", "nelle", "negli", "sulla", "sullo",
    "sulle", "sugli", "dalla", "dallo", "dalle", "dagli", "posso", "devo", "vorrei",
    "fare", "faccio", "creare", "creo", "usare", "uso", "serve", "significa",
    "funziona", "funzionano", "esempio", "esempi", "aiuto", "spiegami", "aiutami",
    "sapere", "voglio", "dovrei", "sicuro", "grazie", "ciao", "allora", "anche",
    "what", "which", "where", "when", "how", "does", "this", "that", "there",
    "with", "from", "about", "into", "please", "thanks",
}

TERM_PATTERN = re.compile(r"[^\W\d_][\w\-]{4,}", re.UNICODE)

# A term is "rare" when it appears in at most this share of the chunks.
RARE_SHARE = 0.02
RARE_MIN = 3


def _query_terms(query: str) -> list[str]:
    terms = [
        raw.lower()
        for raw in TERM_PATTERN.findall(query)
        if raw.lower() not in STOPWORDS
    ]
    return list(dict.fromkeys(terms))


def _table_name(conn) -> str | None:
    schema = conn.execute(
        text(
            "SELECT table_schema FROM information_schema.tables "
            "WHERE table_name = :t LIMIT 1"
        ),
        {"t": VECTOR_TABLE},
    ).scalar()
    return f'"{schema}"."{VECTOR_TABLE}"' if schema else None


def _lexical_docs(terms: list[str], limit: int, db_url: str = DATABASE_URL):
    """Chunks that contain the rare terms of the query, best match first."""
    if not terms:
        return []

    engine = create_engine(db_url)
    try:
        with engine.connect() as conn:
            table = _table_name(conn)
            if not table:
                return []

            total = conn.execute(text(f"SELECT count(*) FROM {table}")).scalar() or 0
            if not total:
                return []

            params = {f"t{i}": f"%{t}%" for i, t in enumerate(terms)}
            counting = ", ".join(
                f"count(*) FILTER (WHERE content ILIKE :t{i})" for i in range(len(terms))
            )
            counts = conn.execute(text(f"SELECT {counting} FROM {table}"), params).fetchone()

            threshold = max(RARE_MIN, int(total * RARE_SHARE))
            rare = [t for t, c in zip(terms, counts) if 0 < (c or 0) <= threshold]
            if not rare:
                return []

            conditions = " OR ".join(f"content ILIKE :t{i}" for i in range(len(rare)))
            rare_params = {f"t{i}": f"%{t}%" for i, t in enumerate(rare)}
            rare_params["limit"] = 200
            rows = conn.execute(
                text(
                    f"SELECT name, content, meta_data FROM {table} "
                    f"WHERE {conditions} LIMIT :limit"
                ),
                rare_params,
            ).fetchall()
    finally:
        engine.dispose()

    scored = []
    for name, content, meta_data in rows:
        haystack = (content or "").lower()
        hits = sum(1 for t in rare if t in haystack)
        if hits:
            scored.append((hits, name, content, meta_data))
    scored.sort(key=lambda item: item[0], reverse=True)

    return [
        {"name": name, "content": content, "meta_data": meta_data or {}}
        for _hits, name, content, meta_data in scored[:limit]
    ]


def wiki_retriever(agent=None, query: str = "", num_documents: int | None = None, **kwargs):
    """Return the wiki documents most relevant to ``query``."""
    from wiki_assistant.knowledge import get_wiki_knowledge

    limit = num_documents or 6
    kb = get_wiki_knowledge()

    # Exact matches on rare terms are the most informative: keep them first.
    results = []
    seen = set()

    def add(doc_dict):
        key = (doc_dict.get("content") or "")[:200]
        if key and key not in seen:
            seen.add(key)
            results.append(doc_dict)

    for doc in _lexical_docs(_query_terms(query), 3):
        add(doc)

    try:
        for doc in kb.search(query, max_results=max(limit, 8)):
            add({"name": doc.name, "content": doc.content, "meta_data": doc.meta_data or {}})
    except Exception as exc:
        print(f"  (retrieval error: {exc})")

    return results[: limit + 2]
