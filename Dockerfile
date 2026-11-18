FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Pre-download the local embedding model into the image, so the container
# never needs to fetch it at runtime.
ENV FASTEMBED_CACHE_PATH=/app/.fastembed_cache
RUN python -c "from fastembed import TextEmbedding; list(TextEmbedding(model_name='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2').embed(['warm up']))"

EXPOSE 7777

FROM base AS bot
ENTRYPOINT ["/app/entrypoint.sh"]

FROM base AS ingest
CMD ["python", "-m", "wiki_assistant.ingest.run_ingest"]
