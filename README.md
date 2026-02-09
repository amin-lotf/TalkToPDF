![Docker Pulls](https://img.shields.io/docker/pulls/aminook/talktopdf)
# TalkToPDF

Self-hosted RAG system for precise Q&A over PDFs using hybrid retrieval and streaming responses.

## What You Can Do in 60 Seconds

- Upload a PDF via Streamlit UI and create a project
- Index PDFs asynchronously with structure-aware extraction and embeddings
- Ask questions and receive streaming answers with source citations
- Manage multiple chats per project with full conversation history
- Use REST API endpoints for programmatic integration

## Features

- Grobid-based PDF extraction preserving document structure (paragraphs, sections, figures)
- Hybrid retrieval combining pgvector similarity search and PostgreSQL full-text search
- Multi-query rewriting for better semantic matching across conversation context
- Configurable LLM-based reranking before final answer generation
- Streaming OpenAI chat responses with token usage tracking
- JWT authentication
- Async SQLAlchemy with unit-of-work pattern and dependency injection
- Multiprocess indexing with cancellation support

## Architecture at a Glance

FastAPI backend serves REST API at `/api/v1` with auth, projects, indexing, chat, and reply endpoints. Streamlit frontend runs alongside. The `talk` entrypoint starts both the FastAPI backend (8000) and Streamlit UI (8501).
. Indexing spawns separate processes that call Grobid to convert PDF to TEI XML, chunk normalized text blocks, embed via OpenAI, and persist to PostgreSQL with pgvector and tsvector GIN indexes. Retrieval flow: rewrite user query with chat history, embed query, search vector and FTS indexes in parallel, merge results with configurable weights, optionally rerank, then stream LLM reply with citations. Files stored on local filesystem under `FILE_STORAGE_DIR`.

## Tech Stack

- **Backend**: FastAPI, Pydantic Settings, async SQLAlchemy 2.0, python-jose JWT, uvicorn
- **AI**: LangChain OpenAI (embeddings, chat, reranking), tiktoken
- **Storage**: PostgreSQL with pgvector extension, tsvector GIN indexes, filesystem for uploads
- **PDF Processing**: Grobid TEI extraction, custom block chunker with overlap
- **Frontend**: Streamlit multipage app
- **Deployment**: Docker Compose, uv package manager with lockfile

## Quickstart with Docker Compose

Use the prebuilt image from Docker Hub:

```bash
# 1. Create .env.docker with your OpenAI API key
cp .env.docker.example .env.docker
# Edit .env.docker and set OPENAI_API_KEY=sk-...

# 2. Start all services (app, PostgreSQL with pgvector, Grobid)
docker compose -f docker-compose.yaml  up -d

# 3. Access the services
# Streamlit UI: http://localhost:8501
# FastAPI docs: http://localhost:8000/docs
# Health check: http://localhost:8000/health
```

The compose file uses `aminook/talktopdf:0.1.0` from Docker Hub. PostgreSQL data persists in the `pgdata` volume.

## Development with Docker Compose

Build from source and run with hot reload:

```bash
# 1. Create .env.docker
cp .env.docker.example .env.docker
# Edit and set OPENAI_API_KEY

# 2. Build and start dev environment
docker compose -f docker-compose-dev.yml up --build

# 3. Run tests inside container
docker compose -f docker-compose-dev.yml exec app pytest

# 4. Access Grobid directly (exposed on host)
# http://localhost:8070
```

The dev compose builds from your local checkout, enables FastAPI reload, and includes health checks.

## Configuration

All settings load from environment variables via Pydantic. Required:

- `OPENAI_API_KEY`: OpenAI API key for embeddings, chat, reranking, query rewriting
- `SQLALCHEMY_DATABASE_URL`: Async PostgreSQL connection string (postgresql+asyncpg://...)

Optional (defaults in `src/talk_to_pdf/backend/app/core/const.py`):

- `JWT_SECRET_KEY`: Secret for signing JWT tokens (default: "change-me")
- `JWT_ALGORITHM`: JWT algorithm (default: "HS256")
- `FILE_STORAGE_DIR`: Local directory for uploaded PDFs and artifacts (default: "tmpstorage")
- `GROBID_URL`: Grobid service endpoint (default: "http://grobid:8070")
- `EMBED_MODEL`: OpenAI embedding model (default: "text-embedding-3-small")
- `EMBED_BATCH_SIZE`: Batch size for embedding requests (default: 16)
- `CHUNKER_MAX_CHARS`: Max characters per chunk (default: 3000)
- `CHUNKER_OVERLAP`: Overlap between chunks (default: 500)
- `REPLY_MODEL`: OpenAI chat model (default: "gpt-4o-mini")
- `REPLY_TEMPERATURE`: Temperature for reply generation (default: 0.2)
- `QUERY_REWRITER_MODEL`: Model for query rewriting (default: "gpt-4o-mini")
- `QUERY_REWRITER_MAX_TURN`: Max conversation turns for rewriting (default: 6)
- `RERANKER_MODEL`: Model for reranking chunks (default: "gpt-4o-mini")
- `RETRIEVAL_MERGER_WEIGHT_VEC`: Vector search weight (default: 0.65)
- `RETRIEVAL_MERGER_WEIGHT_FTS`: Full-text search weight (default: 0.35)
- `MAX_TOP_K`: Max chunks from initial retrieval (default: 20)
- `MAX_TOP_N`: Max chunks after reranking (default: 5)
- `API_BASE_URL`: Frontend API endpoint (default: "http://127.0.0.1:8000/api/v1")

See `.env.example` for local development and `.env.docker.example` for Docker Compose.

## For Clients and Freelancing

This project demonstrates production-grade RAG architecture suitable for custom deployments. Typical paid extensions:

1. **Multi-document Projects**: Support multiple PDFs per project with cross-document retrieval and citation tracking
2. **S3-Compatible Storage**: Replace filesystem storage with MinIO/S3 for scalable cloud deployments
3. **OAuth Integration**: Add OAuth2 providers (Google, Microsoft) alongside JWT for enterprise SSO
4. **Alternative LLM Providers**: Integrate Anthropic Claude, Azure OpenAI, or local models (Ollama, vLLM) with provider abstraction
5. **Observability and Metrics**: Add OpenTelemetry tracing, Prometheus metrics for latency/costs, structured logging with correlation IDs


Common client use cases:

- **Legal/Compliance Teams**: Search contract libraries, policy documents, and regulatory filings with audit trails
- **Research Organizations**: Query academic papers, technical reports, and internal documentation with citation preservation
- **Customer Support**: Build knowledge base chatbots over product manuals, troubleshooting guides, and FAQ documents

This repository serves as a strong starting point for production RAG systems and can be adapted to client-specific constraints, data sources, and deployment environments.
