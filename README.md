# Autonomous Research Agent

An AI-powered autonomous research assistant that discovers, analyzes, and summarizes academic papers using Retrieval-Augmented Generation (RAG). It combines context-aware semantic search over a live corpus of research papers with LLM-generated summaries and grounded question-answering, surfaced through an interactive dashboard.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
  - [1. Clone and environment variables](#1-clone-and-environment-variables)
  - [2. Backend — RAG engine](#2-backend--rag-engine)
  - [3. Backend — API layer](#3-backend--api-layer)
  - [4. Database](#4-database)
  - [5. Frontend](#5-frontend)
- [Running the Application](#running-the-application)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Environment Variables](#environment-variables)
- [Team & Work Division](#team--work-division)
- [Roadmap](#roadmap)
- [License](#license)

## Overview

Manually keeping up with new research is slow: finding relevant papers, reading them, and synthesizing findings across multiple sources takes hours per topic. The Autonomous Research Agent automates that workflow end to end:

1. **Discover** — fetches paper metadata from arXiv and Semantic Scholar for a given topic.
2. **Index** — parses, chunks, and embeds paper content into a FAISS vector store for semantic retrieval.
3. **Understand** — generates structured, AI-written summaries (Problem / Approach / Findings / Limitations) for any indexed paper.
4. **Answer** — answers free-form questions grounded in the indexed corpus, citing which papers support each claim.

All of this is exposed through a FastAPI backend and a React dashboard for real-time paper exploration.

## Features

- **Automated paper discovery** from arXiv and Semantic Scholar APIs
- **Context-aware semantic search** over indexed paper content (not just titles/abstracts)
- **Retrieval-Augmented Generation** for grounded, citation-aware question answering
- **AI-generated structured summaries**, cached per paper to avoid redundant LLM calls
- **Research history tracking** per user (searches, questions, summaries)
- **Interactive dashboard** for real-time paper exploration and insight generation
- **JWT-based authentication** for per-user history and saved research

## Tech Stack

| Layer | Technology |
|---|---|
| LLM inference | Groq API (Llama 3.3 70B) |
| RAG orchestration | LangChain |
| Vector search | FAISS |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`) |
| Backend API | FastAPI |
| Database | PostgreSQL + SQLAlchemy |
| Frontend | React (Vite) |
| Auth | JWT (python-jose, passlib/bcrypt) |

## Architecture

```
┌─────────────┐      ┌──────────────────┐      ┌───────────────────┐
│   React     │ ───▶ │   FastAPI (api)   │ ───▶ │  RAGService facade │
│  Dashboard  │ ◀─── │  routers + auth   │ ◀─── │   (rag_engine.api) │
└─────────────┘      └────────┬──────────┘      └─────────┬──────────┘
                               │                            │
                               ▼                            ▼
                      ┌─────────────────┐         ┌──────────────────────┐
                      │   PostgreSQL     │         │  Ingestion Pipeline   │
                      │ users / papers / │         │  fetch → parse →      │
                      │   query_logs     │         │  chunk → embed → index│
                      └─────────────────┘         └──────────┬────────────┘
                                                              ▼
                                                   ┌──────────────────────┐
                                                   │   FAISS Vector Store  │
                                                   │  + Groq LLM (chains)  │
                                                   └──────────────────────┘
```

The system is split into two independently testable halves:

- **`rag_engine/`** — a standalone Python package with no FastAPI/DB dependency. Handles fetching, parsing, chunking, embedding, indexing, retrieval, summarization, and Q&A. Exposes a single facade (`rag_engine.api.service.RAGService`) for the API layer to consume.
- **`api/`** — the FastAPI application: routing, auth, request/response validation, and PostgreSQL persistence. Calls into `RAGService` rather than touching RAG internals directly.

## Project Structure

```
autonomous-research-agent/
│
├── backend/
│   ├── rag_engine/                 # RAG core (fetch, parse, chunk, embed, retrieve, generate)
│   │   ├── ingestion/
│   │   │   ├── paper_fetcher.py    # arXiv / Semantic Scholar API calls
│   │   │   ├── pdf_parser.py       # PDF download + text extraction
│   │   │   └── chunker.py          # text splitting for embedding
│   │   ├── embeddings/
│   │   │   ├── embedder.py         # sentence-transformers wrapper
│   │   │   └── faiss_store.py      # FAISS index (add / search / persist)
│   │   ├── chains/
│   │   │   ├── retrieval_chain.py  # semantic search over the index
│   │   │   ├── summarization_chain.py
│   │   │   └── qa_chain.py         # RAG question answering
│   │   ├── llm/
│   │   │   └── groq_client.py      # Groq API wrapper with retries
│   │   ├── prompts/
│   │   │   └── templates.py        # all prompt templates
│   │   ├── api/                    # service-layer facade for the FastAPI app
│   │   │   ├── schemas.py          # dataclass I/O contracts
│   │   │   ├── ingest_pipeline.py  # orchestrates the full ingest flow
│   │   │   └── service.py          # RAGService — single entry point
│   │   └── requirements.txt
│   │
│   ├── api/                        # FastAPI application
│   │   ├── main.py                 # app entrypoint
│   │   ├── routers/
│   │   │   ├── search.py
│   │   │   ├── summary.py
│   │   │   ├── papers.py
│   │   │   └── history.py          # includes auth routes
│   │   ├── models/                 # SQLAlchemy models
│   │   │   ├── user.py
│   │   │   ├── paper.py
│   │   │   └── query_log.py
│   │   ├── schemas/
│   │   │   └── schemas.py          # Pydantic request/response models
│   │   ├── db/
│   │   │   ├── database.py         # engine, session, init_db
│   │   │   └── migrations/         # Alembic (TODO)
│   │   ├── core/
│   │   │   ├── config.py           # env-based settings
│   │   │   └── security.py         # password hashing + JWT
│   │   └── requirements.txt
│   │
│   ├── tests/                      # pytest suite (TODO)
│   └── .env                        # local environment variables (not committed)
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── SearchBar/
│   │   │   ├── PaperCard/
│   │   │   ├── InsightPanel/
│   │   │   └── SummaryView/
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   └── PaperDetail.jsx
│   │   ├── api/
│   │   │   └── client.js           # axios wrapper for the FastAPI backend
│   │   ├── hooks/
│   │   │   └── usePaperSearch.js
│   │   ├── context/
│   │   │   └── AppContext.jsx      # auth state
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── docs/                           # architecture notes, API contract (TODO)
├── .env.example
└── README.md
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- A [Groq API key](https://console.groq.com)
- ~500MB free disk space (embedding model + FAISS index)

## Setup

### 1. Clone and environment variables

```bash
git clone <repo-url>
cd autonomous-research-agent
cp .env.example backend/.env
```

Fill in `backend/.env` — see [Environment Variables](#environment-variables) for the full list.

### 2. Backend — RAG engine

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r rag_engine/requirements.txt
```

Verify it works standalone before wiring up the API:

```bash
python -m rag_engine.llm.groq_client       # tests the Groq connection
python -m rag_engine.embeddings.embedder    # downloads and tests the embedding model
```

### 3. Backend — API layer

```bash
pip install -r api/requirements.txt
```

### 4. Database

```bash
createdb research_agent
python -c "from api.db.database import init_db; init_db()"
```

This creates the `users`, `papers`, and `query_logs` tables. `init_db()` also runs automatically on API startup.

### 5. Frontend

```bash
cd ../frontend
npm install
```

## Running the Application

**Backend:**
```bash
cd backend
uvicorn api.main:app --reload --port 8000
```
API docs available at `http://localhost:8000/docs` (Swagger UI).

**Frontend:**
```bash
cd frontend
npm run dev
```
App available at `http://localhost:5173`.

**Populate the index** (run at least once before searching):
```bash
cd backend
python -m rag_engine.api.ingest_pipeline
```

## API Reference

All routes are prefixed with `/api`. Authenticated routes require an `Authorization: Bearer <token>` header obtained from `/api/auth/login`.

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | `/` | Health check | No |
| POST | `/api/auth/register` | Create a new user | No |
| POST | `/api/auth/login` | Log in, returns a JWT | No |
| GET | `/api/papers` | List indexed papers (paginated) | No |
| GET | `/api/papers/{id}` | Get a single paper's metadata | No |
| POST | `/api/papers` | Persist paper metadata | Yes |
| DELETE | `/api/papers/{id}` | Remove a paper | Yes |
| POST | `/api/search` | Semantic search over the indexed corpus | Yes |
| POST | `/api/summary` | Generate/fetch a cached AI summary for a paper | Yes |
| POST | `/api/summary/ask` | Ask a RAG-grounded question (optionally scoped to one paper) | Yes |
| GET | `/api/history` | Get the current user's research history | Yes |
| DELETE | `/api/history/{id}` | Delete a history entry | Yes |

Full request/response schemas are documented interactively at `/docs`.

## Testing

Test the RAG engine and API independently before integrating with the frontend — see each module's `if __name__ == "__main__":` block for standalone runs:

```bash
# RAG engine, layer by layer
python -m rag_engine.ingestion.paper_fetcher
python -m rag_engine.embeddings.embedder
python -m rag_engine.llm.groq_client
python -m rag_engine.api.ingest_pipeline
python -m rag_engine.api.service

# API, via Swagger UI or curl once the server is running
curl http://localhost:8000/

# Automated regression tests
pytest backend/tests/ -v
```

## Environment Variables

| Variable | Description | Example |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@localhost:5432/research_agent` |
| `SECRET_KEY` | Secret used to sign JWTs | a long random string |
| `GROQ_API_KEY` | API key for Groq LLM calls | `gsk_...` |
| `FAISS_INDEX_PATH` | File path prefix for the FAISS index | `data/faiss_index` |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins | `http://localhost:5173` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT expiry window | `60` |
| `DEBUG` | Enables verbose logging / SQL echo | `true` |
| `VITE_API_BASE_URL` | Backend URL used by the frontend | `http://localhost:8000` |

See `.env.example` for a ready-to-copy template.

## Team & Work Division

| Member | Ownership |
|---|---|
| **Member 1** | RAG engine: paper ingestion, chunking, embeddings, FAISS indexing, LangChain retrieval/summarization/QA chains, Groq integration |
| **Member 2** | FastAPI backend (routing, auth, PostgreSQL models), React frontend (dashboard, components, API client) |

## Roadmap

- [ ] Alembic migrations for schema versioning
- [ ] pytest suite with isolated test database
- [ ] Dockerfile + docker-compose for one-command setup
- [ ] Background job queue for ingestion (instead of synchronous requests)
- [ ] Pagination/streaming for long LLM responses

## License

Add your license here (e.g., MIT).