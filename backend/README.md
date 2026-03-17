# 🌱 Backend — Seedlings

> FastAPI backend providing the API layer, cognitive analysis engines, and zero-trust security.

## 📖 Overview

The Seedlings backend is an async Python API built on FastAPI that serves as the intelligence layer for the AI Co-Founder for the Mind. It provides authentication, LLM-powered cognitive analysis (via OpenAI or Ollama), PII-safe data handling with Presidio, and a suite of services for pattern recognition, adversarial sparring, and judgment tracking. All data flows through a PostgreSQL + pgvector store with Redis for event streaming and caching.

## 📁 Directory Structure

```
backend/
├── Dockerfile                          # Container build definition
├── .env.example                        # Environment variable template
├── requirements.txt                    # Python dependencies
├── app/
│   ├── main.py                         # FastAPI app entry point, CORS, lifespan
│   ├── models.py                       # SQLAlchemy ORM models
│   ├── schemas.py                      # Pydantic request/response schemas
│   ├── db_init.py                      # Database initialisation script
│   ├── api/
│   │   ├── auth.py                     # JWT authentication endpoints
│   │   ├── routes.py                   # Core API routes
│   │   ├── insights.py                 # Insight generation endpoints
│   │   └── integrations.py            # OAuth & third-party integrations
│   ├── core/
│   │   ├── config.py                   # Pydantic settings / env loading
│   │   ├── database.py                 # Async SQLAlchemy engine & sessions
│   │   ├── encryption.py              # Field-level encryption helpers
│   │   ├── llm_provider.py            # LLM abstraction (OpenAI / Ollama)
│   │   ├── privacy.py                 # Presidio PII detection & redaction
│   │   ├── redis_client.py            # Redis connection & stream helpers
│   │   └── security.py                # Password hashing, JWT creation
│   ├── middleware/
│   │   └── pii_stripper.py            # Request/response PII stripping middleware
│   └── services/
│       ├── adversarial_sparring.py    # Devil's-advocate challenge engine
│       ├── event_processor.py         # Redis stream event consumer
│       ├── feedback_loops.py          # Outcome-based feedback tracking
│       ├── inference_router.py        # Model routing logic
│       ├── intervention.py            # Real-time cognitive interventions
│       ├── judgment_tracker.py        # Decision quality scoring
│       ├── lora_personalizer.py       # Per-user LoRA adapter management
│       ├── lora_worker.py             # Background LoRA fine-tune worker
│       ├── pattern_engine.py          # Core pattern matching engine
│       ├── pattern_recognition.py     # Cognitive bias pattern detection
│       ├── personalized_router.py     # User-adaptive response routing
│       ├── rag_pipeline.py            # Retrieval-augmented generation pipeline
│       ├── state_aware_prompter.py    # Context-aware prompt construction
│       └── state_tracking.py          # Conversation & cognitive state tracking
└── tests/
    ├── conftest.py                     # Shared pytest fixtures
    ├── test_db_init.py                 # Database initialisation tests
    └── test_pattern_recognition.py     # Pattern recognition unit tests
```

## 🔑 Key Components

| Module | Key Class / Function | Purpose |
|---|---|---|
| `main.py` | `app`, `lifespan()` | FastAPI application factory with startup/shutdown lifecycle |
| `models.py` | ORM models | SQLAlchemy async models for users, decisions, patterns |
| `schemas.py` | Pydantic models | Request/response validation and serialisation |
| `api/auth.py` | `auth_router` | User registration, login, JWT token management |
| `api/routes.py` | `router` | Core CRUD and analysis endpoints |
| `api/integrations.py` | `integrations_router` | Slack, Google OAuth flows |
| `core/config.py` | `get_settings()` | Centralised app configuration from environment |
| `core/llm_provider.py` | LLM abstraction | Swap between OpenAI and Ollama without code changes |
| `core/privacy.py` | PII utilities | Presidio-powered detection and anonymisation |
| `core/security.py` | JWT / hashing | Password hashing (bcrypt) and token creation (python-jose) |
| `middleware/pii_stripper.py` | PII middleware | Strips personally identifiable information from API traffic |
| `services/pattern_recognition.py` | Pattern detector | Identifies cognitive biases in founder reasoning |
| `services/adversarial_sparring.py` | Sparring engine | Generates devil's-advocate challenges |
| `services/rag_pipeline.py` | RAG pipeline | Retrieval-augmented generation over user context |
| `services/judgment_tracker.py` | Judgment scorer | Tracks and scores decision quality over time |

## 📦 Dependencies

| Category | Packages |
|---|---|
| **Web Framework** | `fastapi`, `uvicorn[standard]`, `python-multipart`, `pydantic`, `pydantic-settings`, `httpx` |
| **Database** | `asyncpg`, `sqlalchemy[asyncio]`, `pgvector`, `redis` |
| **AI / LLM** | `langchain`, `langchain-openai`, `langchain-community`, `openai` |
| **Security & Privacy** | `python-jose[cryptography]`, `passlib`, `bcrypt`, `presidio-analyzer`, `presidio-anonymizer`, `spacy` |
| **Scheduling** | `apscheduler` |
| **Testing** | `pytest`, `pytest-asyncio`, `pytest-cov` |
| **Code Quality** | `black`, `isort`, `mypy`, `flake8`, `bandit` |

## 🚀 Getting Started

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Edit .env — set SECRET_KEY, DATABASE_URL, LLM_PROVIDER, etc.

# 4. Initialise the database (PostgreSQL + pgvector must be running)
python -m app.db_init

# 5. Start the development server
uvicorn app.main:app --reload --port 8000
```

| URL | Description |
|---|---|
| `http://localhost:8000` | API root |
| `http://localhost:8000/docs` | Swagger UI (interactive API docs) |
| `http://localhost:8000/redoc` | ReDoc (alternative API docs) |

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=term-missing

# Run a specific test file
pytest tests/test_pattern_recognition.py -v
```

## 📚 Related Documentation

- [Root README](../README.md) — Project overview and quickstart
- [ARCHITECTURE.md](../ARCHITECTURE.md) — System design and data-flow diagrams
- [SETUP_GUIDE.md](../SETUP_GUIDE.md) — Full local development setup
- [docs/](../docs/) — Additional design documents and ADRs
