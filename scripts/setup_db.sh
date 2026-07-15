#!/usr/bin/env bash
set -euo pipefail

DB_NAME="${1:-ai}"
DB_USER="${2:-ai}"
DB_PASS="${3:-ai}"
DB_HOST="${4:-localhost}"
DB_PORT="${5:-5432}"

if ! command -v psql &> /dev/null; then
    echo "ERRORE: psql non trovato. Installa PostgreSQL prima:"
    echo "  brew install postgresql@16"
    echo "  brew services start postgresql@16"
    exit 1
fi

echo "Creating database '$DB_NAME' with user '$DB_USER'..."

psql -h "$DB_HOST" -p "$DB_PORT" -U postgres <<SQL
CREATE DATABASE "$DB_NAME";
CREATE USER "$DB_USER" WITH PASSWORD '$DB_PASS';
GRANT ALL PRIVILEGES ON DATABASE "$DB_NAME" TO "$DB_USER";
\c "$DB_NAME"
CREATE EXTENSION IF NOT EXISTS vector;
GRANT ALL ON SCHEMA public TO "$DB_USER";
SQL

echo ""
echo "Database '$DB_NAME' ready with pgvector extension."
echo ""
echo "Connessione: postgresql+psycopg://$DB_USER:$DB_PASS@$DB_HOST:$DB_PORT/$DB_NAME"
