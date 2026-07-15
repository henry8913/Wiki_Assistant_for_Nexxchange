FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 7777

FROM base AS bot
ENTRYPOINT ["/app/entrypoint.sh"]

FROM base AS ingest
CMD ["python", "-m", "wiki_assistant.ingest.run_ingest"]
