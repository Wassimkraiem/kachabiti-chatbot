# Kachabiti Chatbot

Async FastAPI scaffold for a Retrieval-Augmented Generation chatbot with:

- Clean architecture layers for API, application, domain, and infrastructure
- Document ingestion for `txt`, `pdf`, and `csv`
- Semantic retrieval through Qdrant
- LangChain-based OpenAI embeddings and chat generation
- Structured logging, dependency injection, and Pydantic settings

## Project Layout

```text
app/
  api/               FastAPI routes, request/response schemas, middleware
  application/       Use-case services for ingestion, retrieval, and chat
  core/              Settings, DI container, logging bootstrap
  domain/            Entities, protocols, and domain errors
  infrastructure/    Qdrant/LangChain adapters, parsers, repositories, storage
tests/               API and unit tests
```

## Run

```bash
python -m uvicorn app.main:app --reload
```

The app expects `QDRANT_URL` to point to an existing Qdrant instance. Set it in `.env` or your shell before starting.

## Run With Docker

1. Create your env file:

```bash
cp .env.example .env
```

2. Set `OPENAI_API_KEY` in `.env`.

3. Set `QDRANT_URL` in `.env` to your hosted Qdrant endpoint and, if required by your cluster, `QDRANT_API_KEY`.

Example:

```bash
QDRANT_URL=https://your-cluster-url:6333
QDRANT_API_KEY=your-qdrant-api-key
```

4. Start the app:

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000` and the Swagger UI at `http://localhost:8000/docs`.
The Docker app service mounts `./app` into the container and runs with reload enabled, so Python code changes under `app/` restart the server automatically.
The collection viewer is available at `http://localhost:8000/viewer`.
The Qdrant documents endpoint is available at `http://localhost:8000/api/v1/qdrant/documents`.

The compose stack includes only:

- `app`: the FastAPI service

Persistent data is stored in a Docker volume for the application files. Qdrant data lives in your hosted Qdrant instance.

## LangSmith Prompt Workflow

The app can trace LangChain runs to LangSmith and can optionally pull its chat prompt from LangSmith instead of using the in-code default.

Add these settings to `.env`:

```bash
APP_ENV=development
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=kachabiti-chatbot
LANGSMITH_LOCAL_PROJECT=kachabiti-chatbot-local
LANGSMITH_STAGING_PROJECT=kachabiti-chatbot-staging
LANGSMITH_PROMPT_NAME=kachabiti-chat
LANGSMITH_PROMPT_TAG=latest
```

Tracing projects are resolved by `APP_ENV`:

- `development`, `dev`, and `local` use `LANGSMITH_LOCAL_PROJECT` when set, otherwise `${LANGSMITH_PROJECT}-local`
- `staging` uses `LANGSMITH_STAGING_PROJECT` when set, otherwise `${LANGSMITH_PROJECT}-staging`
- any other environment uses `LANGSMITH_PROJECT`

Push the current default prompt into LangSmith:

```bash
python scripts/push_langsmith_prompt.py --name kachabiti-chat
```

After that, open the prompt in the LangSmith Playground, edit it there, and save a new commit. The app will pull the prompt named by `LANGSMITH_PROMPT_NAME`, using the commit tag or hash in `LANGSMITH_PROMPT_TAG`.

If `LANGSMITH_PROMPT_NAME` is not set or the prompt cannot be loaded, the app falls back to the in-code prompt.

## Import A Q/A CSV Into Qdrant

If you have a CSV with `question` and `answer` columns, you can import it directly into the configured Qdrant collection:

```bash
python scripts/ingest_qa_csv.py path/to/faq.csv
```

Optional flags:

```bash
python scripts/ingest_qa_csv.py path/to/faq.csv --question-column prompt --answer-column response --document-name faq-import.csv
```

Each CSV row is stored as a single chunk in this format:

```text
Question: ...
Answer: ...
```

The importer also writes local document and job metadata so the imported file appears in the viewer at `http://localhost:8000/viewer`.

## Environment

Set these environment variables before starting the service:

```bash
export OPENAI_API_KEY=...
export QDRANT_URL=https://your-cluster-url:6333
export QDRANT_API_KEY=...  # if required by your cluster
```

Optional settings are defined in [app/core/settings.py](/home/wassim/kachabiti-chatbot/app/core/settings.py).

For browser clients, CORS can be configured with these optional env vars:

```bash
export CORS_ALLOW_ORIGINS=http://localhost:3000,https://app.example.com
export CORS_ALLOW_CREDENTIALS=true
export CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,OPTIONS
export CORS_ALLOW_HEADERS=Authorization,Content-Type
export CORS_EXPOSE_HEADERS=X-Request-ID,X-Process-Time
export CORS_MAX_AGE=600
```

`CORS_ALLOW_ORIGINS` also accepts a JSON array. If no origin is configured, CORS middleware stays disabled.

## Design Notes

- Ingestion is asynchronous from the API caller's perspective. The upload endpoint creates document and job records, then schedules processing in the background.
- Provider boundaries are explicit. `EmbeddingProvider`, `ChatModelProvider`, and `VectorStoreRepository` can be replaced without changing application services.
- Metadata persistence uses local JSON-backed repositories for a runnable scaffold. This keeps the project self-contained while preserving repository boundaries for later migration to PostgreSQL or another durable store.
- CSV files are normalized into row-based text chunks to support retrieval-oriented Q&A without adding a full tabular query layer.

## Extension Paths

- Replace the background task runner with Celery, RQ, Dramatiq, or a workflow engine.
- Add authentication and tenant scoping by extending metadata filters and collection or payload strategies.
- Add streaming chat and WebSocket support by introducing a streaming chat provider interface and separate transport handlers.
- Swap Qdrant/OpenAI by implementing the existing domain protocols in new infrastructure adapters.
