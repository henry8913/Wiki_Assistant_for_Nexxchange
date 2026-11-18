import asyncio

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


def ensure_agno_schema() -> None:
    """Apply pending Agno schema migrations.

    Agno adds columns between releases (e.g. ``user_id``). A table created by
    an older version is considered invalid and the DB is then rejected with an
    "invalid schema" warning, so the sessions/knowledge metadata are not used.

    The migration is a no-op when the schema is already up to date.
    """
    from agno.db.migrations.manager import MigrationManager

    targets = [
        (session_db, None),
        (knowledge_contents_db, "knowledge"),
    ]

    for db, table_type in targets:
        try:
            asyncio.run(MigrationManager(db).up(table_type=table_type))
        except Exception as exc:
            print(f"⚠️  Schema migration non riuscita per '{db.id}': {exc}")


ensure_agno_schema()
