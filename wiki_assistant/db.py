from agno.db.postgres import PostgresDb

from wiki_assistant.config import DATABASE_URL

session_db = PostgresDb(
    db_url=DATABASE_URL,
    id="wiki_sessions",
    session_table="wiki_sessions",
)

knowledge_contents_db = PostgresDb(
    db_url=DATABASE_URL,
    id="wiki_knowledge_contents",
    knowledge_table="wiki_knowledge_contents",
)
