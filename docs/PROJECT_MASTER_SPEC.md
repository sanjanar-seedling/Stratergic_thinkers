# PROJECT MASTER SPECIFICATION

**System**: Seedlings — AI Co-Founder for the Mind
**Version**: 0.1.0 (MVP)
**Last Verified Against Code**: 2026-03-13
**Classification**: Internal Technical Reference — Senior Lead Architect

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Technical Stack](#2-technical-stack)
3. [OAuth Architecture](#3-oauth-architecture)
4. [Data Privacy & Security](#4-data-privacy--security)
5. [Strategic Logic — AI Analysis Engine](#5-strategic-logic--ai-analysis-engine)
6. [API Route Map](#6-api-route-map)
7. [Database Schema](#7-database-schema)
8. [Workers Layer](#8-workers-layer)
9. [Frontend Architecture](#9-frontend-architecture)
10. [Infrastructure](#10-infrastructure)
11. [Known Gaps & Technical Debt](#11-known-gaps--technical-debt)

---

## 1. Executive Summary

Seedlings is a deeply personalized AI agent that serves as a strategic thinking partner for startup founders. Unlike standard productivity tools, this system focuses on **improving the quality of founder thinking, not the quantity of output**.

The architecture is organized around five system metaphors:

| Metaphor | Function | Code Location |
|----------|----------|---------------|
| **Ears** | Multi-modal ingestion — email, voice, Slack, Discord, Google Calendar, Gmail | `workers/` |
| **Eyes** | Document/image ingestion via OCR and file uploads | `workers/ocr/` |
| **Brain** | Cognitive analysis engines — pattern recognition, bias detection, state tracking, RAG | `backend/app/services/` |
| **Voice** | Active sparring partner — adversarial challenges, interventions, Socratic questioning | `backend/app/services/adversarial_sparring.py`, `inference_router.py` |
| **Vault** | Zero-trust security — E2E encryption, PII stripping, privacy zones, GDPR compliance | `backend/app/core/encryption.py`, `privacy.py`, `middleware/pii_stripper.py` |

**Core Loop**: Founder generates text (journal, voice memo, Slack message, email) → PII-scrubbed and encrypted → published to Redis Stream → consumed by cognitive engines → patterns and biases detected → interventions generated → founder reflections improve over time → judgment quality tracked against actual outcomes.

**Target Users**: Early-stage startup founders (solo or co-founding teams) who want to build self-awareness around their decision-making patterns, cognitive biases, and time allocation drift.

---

## 2. Technical Stack

### 2.1 Frontend

Source: `frontend/package.json`

| Dependency | Version | Rationale |
|---|---|---|
| React | 19.2.0 | Concurrent rendering for real-time sparring UI; Suspense for data fetching |
| React DOM | 19.2.0 | DOM renderer paired with React 19 |
| TypeScript | 5.9.3 | Static type safety across the API boundary; enforced via `tsconfig.json` strict mode |
| Vite | 7.3.1 | Native ESM bundler; sub-second HMR; plugin ecosystem for Tailwind and SSL |
| Tailwind CSS | 4.2.1 | Utility-first CSS with v4's CSS-native configuration; glassmorphism theme |
| react-router-dom | 7.13.1 | Client-side routing; 7 protected routes + 3 public routes |
| Radix UI | Various (`@radix-ui/react-*`) | Headless, accessible primitives: dialog, dropdown-menu, tabs, tooltip, avatar, label, progress, switch, select, separator, toggle, scroll-area |
| recharts | 3.8.0 | Composable React charting: area charts (growth trajectory), bar charts (bias frequency), radar charts (thinking profile) |
| axios | 1.13.6 | HTTP client with request interceptor (JWT injection) and response interceptor (401 → redirect to login) |
| lucide-react | 0.577.0 | Tree-shakeable SVG icon set |
| class-variance-authority | latest | Component variant management (button variants: primary, outline, ghost, destructive) |
| clsx + tailwind-merge | latest | Conditional class composition without Tailwind conflicts |
| @vitejs/plugin-basic-ssl | 2.2.0 | Self-signed HTTPS certificates for localhost; required for OAuth redirect URIs |
| @vitejs/plugin-react | 5.1.1 | React Fast Refresh via Vite |
| ESLint | 9.39.1 | Linting with TypeScript and React rules |

### 2.2 Backend

Source: `backend/requirements.txt`

| Dependency | Version Constraint | Rationale |
|---|---|---|
| FastAPI | >=0.115.0 | Async-first Python web framework; auto-generated OpenAPI/Swagger docs; Pydantic v2 integration |
| uvicorn[standard] | >=0.32.0 | ASGI server with libuv event loop for production performance |
| SQLAlchemy[asyncio] | >=2.0.0 | Async ORM with declarative model definitions; 2.0 API with native async session management |
| asyncpg | >=0.30.0 | Fastest PostgreSQL async driver for Python; C extension for protocol parsing |
| pgvector | >=0.3.0 | PostgreSQL vector similarity search; enables cosine distance queries for RAG pipeline |
| redis | >=5.0.0 | Async Redis client; used for Streams (event pipeline), caching, rate limiting, session storage |
| presidio-analyzer | >=2.2.0 | Microsoft PII detection engine; NER-based entity recognition |
| presidio-anonymizer | >=2.2.0 | PII anonymization companion; operator-based replacement |
| spacy | >=3.7.0 | NLP backbone for Presidio; provides `en_core_web_lg` model for entity recognition |
| langchain | >=0.3.0 | Text splitting (`RecursiveCharacterTextSplitter`), LLM chain abstractions |
| langchain-openai | >=0.2.0 | OpenAI-specific LangChain integration; `ChatOpenAI` for pattern analysis |
| langchain-community | >=0.3.0 | Community integrations for LangChain |
| openai | >=1.50.0 | Official OpenAI SDK; used for Whisper transcription and GPT-4o-mini chat |
| python-jose[cryptography] | >=3.3.0 | JWT token creation and verification; HS256 algorithm |
| passlib | 1.7.4 | Password hashing framework; wraps bcrypt |
| bcrypt | 4.0.1 | bcrypt hashing with `$2b$` identifier |
| httpx | >=0.27.0 | Async HTTP client; used for OAuth token exchange and third-party API calls |
| pydantic | >=2.0.0 | Data validation; request/response schemas |
| pydantic-settings | >=2.0.0 | Environment variable loading with type coercion; `.env` file support |
| python-multipart | >=0.0.9 | Multipart form data parsing; required for file uploads (audio transcription) |
| apscheduler | >=3.10.0 | Background task scheduling (planned for periodic pattern analysis) |
| cryptography | (transitive) | RSA-4096 key generation, AES-256-GCM encryption, PBKDF2 key derivation |

**Testing & Quality** (dev dependencies):
- pytest 8.0.0, pytest-asyncio 0.23.5, pytest-cov 4.1.0
- black 24.1.1, isort 5.13.2, mypy 1.8.0, flake8 7.0.0
- bandit 1.7.6 (security linting)

### 2.3 Infrastructure

Source: `docker-compose.yml`

| Service | Image | Port | Purpose |
|---|---|---|---|
| PostgreSQL 16 | `pgvector/pgvector:pg16` | 5432 | Primary data store with pgvector extension for semantic search |
| Redis 7 | `redis:7-alpine` | 6379 | Event streaming (Redis Streams), caching, rate limiting, session storage |
| MinIO | `minio/minio:latest` | 9000 (API), 9001 (Console) | S3-compatible object storage for audio files and document uploads |

### 2.4 LLM Providers

Source: `backend/app/core/config.py`, `backend/app/core/llm_provider.py`

| Provider | Chat Model | Embedding Model | Transcription Model | Use Case |
|---|---|---|---|---|
| **Groq** (default) | llama-3.3-70b-versatile | N/A (falls back to Ollama) | whisper-large-v3-turbo | Production inference via Groq Cloud; OpenAI-compatible API at `https://api.groq.com/openai/v1` |
| **OpenAI** | gpt-4o-mini | text-embedding-3-small | whisper-1 | Cloud inference with full embedding support |
| **Ollama** | tinyllama | nomic-embed-text | N/A | Local/air-gapped fallback; zero data egress; base URL `http://localhost:11434` |

Selection is controlled by `LLM_PROVIDER` environment variable. Factory function `get_llm_provider()` in `llm_provider.py:203-227` returns a singleton instance.

---

## 3. OAuth Architecture

Source: `backend/app/api/integrations.py`

### 3.1 Supported Services & Scopes

| Service | Authorization URL | Token URL | Scopes | Special Handling |
|---|---|---|---|---|
| Slack | `https://slack.com/oauth/v2/authorize` | `https://slack.com/api/oauth.v2.access` | `channels:history,chat:write,groups:history,im:history` | Token URL returns `{"ok": false, "error": "..."}` with HTTP 200 on failure; must check `ok` field (line 205-209) |
| Discord | `https://discord.com/api/oauth2/authorize` | `https://discord.com/api/oauth2/token` | `identify guilds messages.read` | Standard OAuth2 code exchange |
| Google Calendar | `https://accounts.google.com/o/oauth2/v2/auth` | `https://oauth2.googleapis.com/token` | `https://www.googleapis.com/auth/calendar.readonly` | Adds `access_type=offline` and `prompt=consent` for refresh token (line 151-153) |
| Gmail | `https://accounts.google.com/o/oauth2/v2/auth` | `https://oauth2.googleapis.com/token` | `https://www.googleapis.com/auth/gmail.readonly` | Same Google OAuth with different scope; shares `GOOGLE_CLIENT_ID` |

### 3.2 OAuth Flow (Step-by-Step)

```
Frontend                        Backend                         Provider
   │                               │                               │
   │  GET /integrations/{svc}/     │                               │
   │  auth-url                     │                               │
   │──────────────────────────────>│                               │
   │                               │  Build URL with:              │
   │                               │  client_id, redirect_uri,     │
   │                               │  response_type=code, scope,   │
   │                               │  state={service_name}         │
   │  {"auth_url": "https://..."}  │                               │
   │<──────────────────────────────│                               │
   │                               │                               │
   │  window.location.href =       │                               │
   │  auth_url                     │                               │
   │──────────────────────────────────────────────────────────────>│
   │                               │                               │
   │                               │    User authorizes app        │
   │                               │                               │
   │  Redirect to                  │                               │
   │  /oauth/callback?code=X&      │                               │
   │  state={service}              │                               │
   │<──────────────────────────────────────────────────────────────│
   │                               │                               │
   │  POST /integrations/{svc}/    │                               │
   │  callback  {code: "X"}        │                               │
   │──────────────────────────────>│                               │
   │                               │  POST token_url with:         │
   │                               │  client_id, client_secret,    │
   │                               │  code, redirect_uri,          │
   │                               │  grant_type=authorization_code│
   │                               │──────────────────────────────>│
   │                               │                               │
   │                               │  {access_token, refresh_token}│
   │                               │<──────────────────────────────│
   │                               │                               │
   │                               │  Store in _integrations list  │
   │  {"status": "connected"}      │  (IN-MEMORY)                  │
   │<──────────────────────────────│                               │
```

### 3.3 Token Storage (Current Implementation)

**Location**: `integrations.py:24`
```python
_integrations: list[dict] = []
```

Tokens are stored as **plaintext strings in an in-memory Python list**. Storage structure per entry:
```python
{
    "user_id": str,           # From JWT
    "service": str,           # "slack" | "discord" | "google" | "gmail"
    "access_token": str,      # Plaintext OAuth access token
    "refresh_token": str,     # Plaintext refresh token (Google only)
    "scopes": str,            # Granted scopes
    "connected_at": str,      # ISO 8601 timestamp
}
```

**CRITICAL GAP**: The `infra/init.sql` defines a `seedlings.integrations` table (line 74-85) with `access_token_encrypted` and `refresh_token_encrypted` columns intended for encrypted persistent storage. The API code does not use this table. **Tokens are lost on every server restart.**

### 3.4 Data Sync Pipeline

`POST /api/integrations/sync` (line 257-332) fetches data from all connected services:

| Service | API Endpoints Called | Data Extracted | Limits |
|---|---|---|---|
| Slack | `conversations.list` (types=im), `conversations.history` | DM message text | 3 channels, 5 msgs/channel, min 10 chars |
| Discord | `/users/@me/channels`, `/channels/{id}/messages` | DM message content | 3 channels, 5 msgs/channel, min 10 chars |
| Gmail | `gmail/v1/users/me/messages` (list + get) | Subject + snippet | 10 emails, inbox, newer_than:7d |
| Google Calendar | `calendar/v3/calendars/primary/events` | Event summary | 20 events, last 7 days |

All fetched text is PII-scrubbed via `full_scrub()` before being stored as `FounderEvent` records and published to Redis Stream `seedlings:events`.

---

## 4. Data Privacy & Security

### 4.1 Encryption Architecture

#### Server-Side Encryption (E2E)

Source: `backend/app/core/encryption.py`

| Layer | Algorithm | Parameters | Purpose |
|---|---|---|---|
| Key Exchange | RSA-4096 | Public exponent 65537 | Asymmetric keypair per user; public key stored in DB, private key stays on client |
| Data Encryption | AES-256-GCM | 12-byte random nonce | Symmetric encryption of event text; produces `{ciphertext, nonce, tag}` (all base64) |
| Key Derivation | PBKDF2-HMAC-SHA256 | 600,000 iterations, 16-byte salt, 32-byte output | Derives encryption key from user password (OWASP recommended iteration count) |

`E2EEncryption` class methods:
- `generate_user_keypair()` → `(private_pem: bytes, public_pem: bytes)` — RSA-4096
- `derive_key_from_password(password, salt?)` → `(key: bytes, salt: bytes)` — PBKDF2
- `encrypt_data(plaintext, key)` → `{ciphertext, nonce, tag}` — AES-256-GCM
- `decrypt_data(encrypted_data, key)` → `plaintext` — AES-256-GCM verification + decryption
- `encrypt_for_storage(data, user_password)` → `{encrypted_data, salt}` — convenience wrapper
- `decrypt_from_storage(stored_data, user_password)` → `plaintext` — convenience wrapper

#### Client-Side Encryption

Source: `frontend/src/services/encryption.ts`

| Parameter | Value |
|---|---|
| Algorithm | AES-GCM via Web Crypto API |
| Key Length | 256 bits |
| IV Length | 12 bytes (random per encryption) |
| Salt Length | 16 bytes (random per encryption) |
| Key Derivation | PBKDF2 with 100,000 iterations |

When the user submits a journal entry with encryption enabled:
1. Frontend encrypts text using `encryptText(plaintext, passphrase)`
2. Sends `{text: ciphertext, encrypted: true, iv: base64, salt: base64}` to backend
3. Backend skips PII stripping when `encrypted=true` (line 48 of `routes.py`: `if not event.encrypted`)
4. Ciphertext stored as-is; only the user with the passphrase can decrypt

#### JWT Authentication

Source: `backend/app/core/security.py`

| Parameter | Value |
|---|---|
| Algorithm | HS256 (HMAC SHA-256) |
| Signing Key | `settings.secret_key` (default: `dev-secret-key-change-in-production`) |
| Expiry | 24 hours (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`, default 1440) |
| Payload | `{sub: user_id, email: email, exp: datetime, iat: datetime}` |

#### Password Storage

| Parameter | Value |
|---|---|
| Algorithm | bcrypt |
| Version | `$2b$` identifier |
| Library | passlib 1.7.4 CryptContext |

### 4.2 PII Stripping Pipeline

Source: `backend/app/middleware/pii_stripper.py`

#### Detection Layer

**Primary**: Microsoft Presidio `AnalyzerEngine` (lazy-loaded singleton)

Detected entities:
| Entity Type | Numbered Placeholder | Example |
|---|---|---|
| PERSON | Yes (`<PERSON_1>`, `<PERSON_2>`, ...) | "John Smith" → `<PERSON_1>` |
| ORGANIZATION | Yes (`<ORGANIZATION_1>`, ...) | "Acme Corp" → `<ORGANIZATION_1>` |
| LOCATION | Yes (`<LOCATION_1>`, ...) | "San Francisco" → `<LOCATION_1>` |
| PHONE_NUMBER | No (`<PHONE_NUMBER>`) | "555-123-4567" → `<PHONE_NUMBER>` |
| EMAIL_ADDRESS | No (`<EMAIL_ADDRESS>`) | "john@acme.com" → `<EMAIL_ADDRESS>` |
| CREDIT_CARD | No (`<CREDIT_CARD>`) | "4111-1111-1111-1111" → `<CREDIT_CARD>` |
| IBAN_CODE | No (`<IBAN_CODE>`) | — |
| US_SSN | No (`<US_SSN>`) | "123-45-6789" → `<US_SSN>` |
| NRP | No (`<NRP>`) | Nationality, Religion, Political group |

**Fallback**: Regex-based stripping (`_regex_strip_pii`, lines 43-86) when Presidio is unavailable:
- Email: `\b[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}\b`
- Phone: Multiple US format patterns
- SSN: `\d{3}-\d{2}-\d{4}`
- Credit Card: 16-digit patterns with optional separators
- Names: 2-4 consecutive capitalized words (heuristic)

#### Financial Figure Stripping

Source: `strip_financial_figures()`, lines 170-194

Dollar amounts are replaced with ranges to prevent financial intelligence leakage:

| Input Range | Output |
|---|---|
| < $1,000 | `<$1K` |
| $1,000 – $9,999 | `$1K-$10K` |
| $10,000 – $99,999 | `$10K-$100K` |
| $100,000 – $999,999 | `$100K-$1M` |
| $1,000,000 – $9,999,999 | `$1M-$10M` |
| >= $10,000,000 | `$10M+` |

#### Full Pipeline

```python
def full_scrub(text: str) -> str:
    scrubbed = strip_pii(text)         # Presidio or regex
    scrubbed = strip_financial_figures(scrubbed)  # Dollar ranges
    return scrubbed
```

Applied at:
- `POST /api/events` — event text (unless `encrypted=true`)
- `POST /api/decisions` — rationale field
- `POST /api/integrations/sync` — all fetched integration texts

### 4.3 Privacy Controls

Source: `backend/app/core/privacy.py`

#### Privacy Zones

User-defined topic boundaries:
| Mode | Behavior |
|---|---|
| `reflection_only` | Store event but skip AI processing (e.g., family, relationships) |
| `no_storage` | Never store the event at all (e.g., personal health) |

Detection: Keyword matching against user-configured `PrivacyZone.keywords` list.

#### Intervention Preferences

| Setting | Type | Default | Description |
|---|---|---|---|
| `enabled` | bool | `True` | Master toggle for AI interventions |
| `pause_until` | ISO timestamp | `None` | Temporary pause (e.g., during high-stress sprint) |
| `quiet_hours_start` | int (0-23) | `None` | Start of quiet window |
| `quiet_hours_end` | int (0-23) | `None` | End of quiet window |
| `max_per_day` | int | 3 | Maximum interventions per day |
| `priority_threshold` | string | `"medium"` | Minimum priority to trigger (`"low"`, `"medium"`, `"high"`) |

#### Data Retention Policy

| Setting | Type | Default | Description |
|---|---|---|---|
| `auto_delete_after_days` | int | `None` | Auto-delete events after N days |
| `archive_after_days` | int | 365 | Move to cold storage after N days |
| `keep_insights_only` | bool | `False` | Delete raw text after retention, preserve patterns and insights |

#### Consent Management

4 granular consent purposes:
1. `ai_processing` — Allow AI analysis of events
2. `model_training` — Allow use of data for model fine-tuning
3. `third_party_integrations` — Allow third-party service connections
4. `analytics` — Allow usage analytics collection

#### GDPR Right to Erasure

`delete_user_data(user_id, db_session)` performs cascading deletes in order:
1. `event_patterns` (association table)
2. `framework_applications`
3. `interventions`
4. `decision_outcomes`
5. `patterns`
6. `founder_events`
7. `users`

Returns per-table deletion counts for audit trail.

### 4.4 Additional Security Measures

| Measure | Implementation | Source |
|---|---|---|
| CORS | Allowed origins: `localhost:5173`, `localhost:3000`; all methods/headers; credentials enabled | `main.py:45-51` |
| Rate Limiting | Redis sliding window; default 60 requests/60 seconds | `redis_client.py:68-78` |
| Data Anonymization | `DataAnonymization` class: regex-based pseudonymization of emails and phones | `encryption.py` |
| Audit Logging | `AuditLog` class: in-memory audit trail with user_id, action, resource, timestamp | `encryption.py` |
| Non-root Docker | `useradd -m -u 1000 appuser` in Dockerfile | `backend/Dockerfile` |
| Health Checks | Docker HEALTHCHECK every 30s; FastAPI `/health` endpoint | `backend/Dockerfile`, `routes.py:37` |

---

## 5. Strategic Logic — AI Analysis Engine

### 5.1 Pattern Recognition Engine

Source: `backend/app/services/pattern_engine.py`

**Class**: `PatternEngine` (singleton: `pattern_engine`)

**Analysis Window**: 7-day rolling window of founder events

**LLM Integration**: LangChain `ChatOpenAI` with `gpt-4o-mini` at temperature 0.2

**Detected Patterns**:
| Pattern | Detection Method |
|---|---|
| Anchoring Bias | LLM analysis of event text for fixation on initial data points |
| Confirmation Bias | LLM detection of selective evidence gathering |
| Sunk Cost Fallacy | LLM identification of past-investment-driven decisions |
| Optimism Bias | LLM detection of unrealistic positive expectations |
| Recency Bias | LLM detection of overweighting recent events |
| Survivorship Bias | LLM detection of ignoring failures/non-survivors |
| Avoidance Behavior | Heuristic bigram frequency analysis with action-word exclusion |
| Over-Optimization | LLM detection of perfectionism blocking execution |

**Analysis Prompt** (line 18-39): Structured prompt requesting JSON output `[{bias_type, description, severity}]` with calendar context injection for cross-referencing stated vs. actual behavior.

**Avoidance Detection** (`detect_avoidance`, line 95-120): Pure heuristic — counts bigram frequency in entries that lack action words (`decided`, `will`, `done`, `completed`, `shipped`, `launched`, `hired`, `fired`). Topics mentioned >= `threshold` times (default 3) without associated actions are flagged.

### 5.2 Adversarial Sparring

Source: `backend/app/services/adversarial_sparring.py`

**Class**: `AdversarialSparring` (singleton: `adversarial_sparring`)

**Trigger Conditions** (`should_trigger`, line 38-51):
1. `confidence_score >= 0.8 AND len(alternatives) == 0` — High confidence with zero alternatives
2. `confidence_score >= 0.9` — Very high confidence regardless of alternatives

**System Prompt**: `"You are a tough but fair board member. You challenge founders to think harder. Be direct, specific, and concise. Never repeat instructions."`

**Challenge Generation** (`generate_challenge`, line 53-77):
- Formats decision title, rationale, confidence %, and alternatives into structured prompt
- Requests: ONE blind spot, name any cognitive bias, ask ONE sharp question
- Temperature: 0.7 (higher creativity for adversarial responses)
- Uses swappable `LLMProvider` (not LangChain)

**Multi-Turn Sparring** (`continue_sparring`, line 79-103):
- Takes conversation history string + latest user message
- Prompt: "acknowledge their point, then find the next weak link"
- Maintains adversarial posture across turns

### 5.3 State & Drift Tracking

Source: `backend/app/services/state_tracking.py`

**Class**: `StateTrackingEngine`

**Emotional State Detection** (line 84-112):

5 emotional states with keyword lists:
| State | Keywords |
|---|---|
| `confident` | confident, certain, clear, sure, convinced, momentum |
| `anxious` | worried, anxious, nervous, uncertain, stressed, overwhelmed |
| `frustrated` | frustrated, stuck, blocked, annoyed, irritated |
| `excited` | excited, energized, pumped, thrilled, motivated |
| `burned_out` | exhausted, drained, tired, burned out, depleted |

Intensity formula: `min(len(keyword_matches) / 3, 1.0)`

**Emotional Volatility** (line 154-168): Measures state-change frequency across timeline: `min(changes / len(timeline), 1.0)`. Range: 0.0 (stable) to 1.0 (highly volatile).

**Time Allocation Drift** (line 170-215):
- Inputs: `stated_priorities` dict and `actual_time` dict (each category sums to 1.0)
- Drift = `actual - stated` per category
- Severity thresholds: `>=0.4` high, `>=0.25` medium, `>=0.2` low
- Generates actionable recommendations per drift (line 217-238)

**Emotion-Decision Correlation** (line 240-273): Maps emotional state at time of decision to decision events for retrospective analysis.

### 5.4 RAG Pipeline

Source: `backend/app/services/rag_pipeline.py`

**Class**: `RAGPipeline` (singleton: `rag_pipeline`)

**Text Chunking** (line 32-52):
- LangChain `RecursiveCharacterTextSplitter`
- Chunk size: 1000 characters, overlap: 200 characters
- Separators: `["\n\n", "\n", ". ", " ", ""]`
- Fallback: Simple sliding-window chunking if LangChain unavailable

**Embedding Generation**: Delegates to swappable `LLMProvider.embed()` method

**Similarity Search** (line 58-89):
- pgvector cosine distance operator: `<=>`
- Query: `1 - (embedding <=> query_vec) AS similarity`
- Table: `seedlings.knowledge_chunks`
- Default limit: 5 results

**Document Ingestion** (line 91-125): Chunks → embeds → stores in pgvector with `gen_random_uuid()` IDs

**Framework Recommendation** (line 127-170):
- LLM generates framework suggestions for a decision context
- Cross-references against built-in framework library
- Falls back to top-3 built-in frameworks if no match

**Built-in Strategic Framework Library** (line 175-248):

| Framework | Source | Category |
|---|---|---|
| First Principles Thinking | Elon Musk / Aristotle | decision_making |
| Reversible vs. Irreversible Decisions | Jeff Bezos / Amazon | decision_making |
| Regret Minimization Framework | Jeff Bezos | decision_making |
| Pre-Mortem Analysis | Gary Klein | decision_making |
| Eisenhower Matrix | Dwight D. Eisenhower | execution |
| Opportunity Cost | Economics | decision_making |
| Inversion | Charlie Munger | strategy |
| Jobs to Be Done | Clayton Christensen | strategy |

### 5.5 Inference Router

Source: `backend/app/services/inference_router.py`

**Class**: `InferenceRouter` (singleton: `inference_router`)

Classifies each `FounderEvent` into one of 4 response categories and generates the appropriate response:

| Category | Trigger | Response Strategy |
|---|---|---|
| `rag_query` | Founder wrestling with strategic decision | Retrieve relevant frameworks via RAG similarity search |
| `clarifying_question` | Vague or surface-level reflection | Generate Socratic question (under 30 words) challenging unstated assumptions |
| `pattern_alert` | Signals of cognitive bias or avoidance | Direct bias identification with constructive feedback (under 100 words) |
| `acknowledgment` | Thoughtful, complete reflection | Simple receipt: "Noted. This reflection has been added to your growth journal." |

Classification temperature: 0.1 (deterministic). Response temperature: 0.3 (controlled creativity).

### 5.6 Judgment Tracker

Source: `backend/app/services/judgment_tracker.py`

**Class**: `JudgmentTracker` (requires `AsyncSession` DB dependency)

**Decision Outcome Lifecycle**:
1. `create_decision_outcome()` — Records predicted outcome, confidence, impact, frameworks applied, and sets follow-up date (default: 30 days)
2. `record_actual_outcome()` — Records what actually happened; calculates `was_correct` and `calibration_error = |confidence - accuracy|`
3. `get_pending_followups()` — Returns decisions past their follow-up date without recorded outcomes

**Judgment Metrics** (`calculate_judgment_metrics`, line 153-239):
| Metric | Formula |
|---|---|
| Accuracy Rate | `correct_predictions / decisions_with_outcomes` |
| Average Confidence | Mean of all `confidence_level` values |
| Calibration Score | `1.0 - mean(calibration_errors)` — how well confidence matches actual accuracy |
| Improvement Trend | Split outcomes into halves; compare accuracy: `>+10%` = improving, `<-10%` = declining, else stable |

**Framework Effectiveness Analysis**: Groups outcomes by `frameworks_applied` array; calculates per-framework accuracy rate.

**Impact Analysis**: Accuracy segmented by `predicted_impact` level (high/medium/low).

---

## 6. API Route Map

All routes verified against source code as of 2026-03-13.

### 6.1 Authentication (`/api/auth`)

Source: `backend/app/api/auth.py`

| Method | Path | Auth | Request Body | Response | Notes |
|---|---|---|---|---|---|
| POST | `/api/auth/signup` | No | `{email, password, display_name?}` | `{access_token, token_type, user}` | 201 Created; password min 6 chars; email unique |
| POST | `/api/auth/login` | No | `{email, password}` | `{access_token, token_type, user}` | 200 OK; bcrypt verification |
| GET | `/api/auth/me` | Bearer JWT | — | `{id, email, display_name, created_at}` | Returns token data if user not in memory |

### 6.2 Events (`/api`)

Source: `backend/app/api/routes.py`

| Method | Path | Auth | Request Body | Response | Notes |
|---|---|---|---|---|---|
| POST | `/api/events` | Bearer JWT | `{source, event_type, text, encrypted?, context?}` | `FounderEventResponse` | PII scrubbed unless `encrypted=true`; publishes to Redis |
| GET | `/api/events` | Bearer JWT | Query: `limit=20, offset=0` | `list[dict]` | Paginated, newest first |

### 6.3 Decisions (`/api`)

| Method | Path | Auth | Request Body | Response | Notes |
|---|---|---|---|---|---|
| POST | `/api/decisions` | Bearer JWT | `{title, rationale, expected_outcome, expected_outcome_date?, confidence_score, alternatives?}` | `DecisionResponse` | Rationale PII-scrubbed |
| GET | `/api/decisions` | Bearer JWT | Query: `status?` | `list[dict]` | Optional status filter (pending/resolved/revised) |
| PUT | `/api/decisions/{id}/resolve` | Bearer JWT | `{actual_outcome, outcome_score}` | `dict` | Sets status to "resolved" |

### 6.4 Transcription (`/api`)

| Method | Path | Auth | Request Body | Response | Notes |
|---|---|---|---|---|---|
| POST | `/api/transcribe` | No | `multipart/form-data: audio, language?` | `{text, duration_seconds}` | Fallback chain: Groq → OpenAI → stub |

### 6.5 Adversarial Sparring (`/api`)

| Method | Path | Auth | Request Body | Response | Notes |
|---|---|---|---|---|---|
| POST | `/api/sparring/{decision_id}` | Bearer JWT | — | `{decision_id, challenge}` | Generates initial adversarial challenge |
| POST | `/api/sparring/{decision_id}/continue` | Bearer JWT | `{conversation_history, user_message}` | `{decision_id, response}` | Multi-turn sparring continuation |

### 6.6 Dashboard (`/api`)

| Method | Path | Auth | Response | Notes |
|---|---|---|---|---|
| GET | `/api/dashboard/stats` | Bearer JWT | `{total_decisions, avg_accuracy, biases_caught, open_decisions}` | Real-time from in-memory stores |
| GET | `/api/dashboard/biases` | Bearer JWT | `list[dict]` | Returns detected biases for user |
| GET | `/api/dashboard/growth` | Bearer JWT | `list[{month, confidence, accuracy, reflection_count}]` | Last 6 months bucketed data |

### 6.7 Privacy (`/api`)

| Method | Path | Auth | Response | Notes |
|---|---|---|---|---|
| GET | `/api/privacy/export` | Bearer JWT | `{user_id, exported_at, events, decisions, biases}` | Full JSON data export |
| DELETE | `/api/privacy/data` | Bearer JWT | `{status: "deleted", user_id}` | Deletes all user data from memory stores |

### 6.8 Integrations (`/api/integrations`)

| Method | Path | Auth | Request Body | Response | Notes |
|---|---|---|---|---|---|
| GET | `/api/integrations/status` | Bearer JWT | — | `list[IntegrationStatus]` | Status for all 4 services |
| GET | `/api/integrations/{service}/auth-url` | Bearer JWT | — | `{auth_url}` | Generates OAuth authorization URL |
| POST | `/api/integrations/{service}/callback` | Bearer JWT | `{code}` | `{status, service}` | Exchanges code for tokens |
| DELETE | `/api/integrations/{service}` | Bearer JWT | — | `{status, service}` | Disconnects integration |
| POST | `/api/integrations/sync` | Bearer JWT | — | `{status, events_created, services_synced, errors}` | Syncs data from all connected services |

### 6.9 Health

| Method | Path | Auth | Response |
|---|---|---|---|
| GET | `/health` | No | `{status: "ok", service: "seedlings-api", version: "0.1.0"}` |
| GET | `/` | No | Service info with docs link |

---

## 7. Database Schema

### 7.1 Deployed Schema (init.sql)

Source: `infra/init.sql`

Extensions: `pgvector`

| Table | Primary Key | Key Columns | Indexes |
|---|---|---|---|
| `seedlings.users` | UUID (gen_random_uuid) | email (unique), password_hash, display_name, is_active, encrypted_key_hash | — |
| `seedlings.founder_events` | UUID | user_id (FK→users CASCADE), source, event_type, scrubbed_text, context (JSONB), embedding (vector(1536)) | user_id, created_at, IVFFlat(embedding, cosine, lists=100) |
| `seedlings.decisions` | UUID | user_id (FK), event_id (FK→founder_events), title, rationale, alternatives (JSONB), expected_outcome, confidence_score (decimal 3,2), outcome_score, status | user_id, status |
| `seedlings.bias_detections` | UUID | user_id (FK), event_id (FK), bias_type, description, severity, acknowledged | user_id |
| `seedlings.knowledge_chunks` | UUID | source_title, source_author, chunk_text, chunk_index, embedding (vector(1536)), metadata (JSONB) | IVFFlat(embedding, cosine, lists=100) |
| `seedlings.integrations` | UUID | user_id (FK, UNIQUE with service), service, access_token_encrypted, refresh_token_encrypted, scopes, external_user_id, expires_at | user_id |

### 7.2 Aspirational Schema (models.py)

Source: `backend/app/models.py`

Additional tables NOT in init.sql:

| Table | Purpose | Key Columns |
|---|---|---|
| `seedlings.patterns` | Detected cognitive patterns | pattern_type (enum), name, confidence (float), frequency, pattern_data (JSON) |
| `seedlings.event_patterns` | M2M: events ↔ patterns | event_id, pattern_id (composite PK) |
| `seedlings.interventions` | AI-generated reflection prompts | trigger_type (enum), prompt_type, question, priority, status (enum), response_text |
| `seedlings.decision_outcomes` | Judgment quality tracking | predicted/actual outcome, confidence_level, calibration_error, was_correct, frameworks_applied (JSON) |
| `seedlings.frameworks` | Strategic framework library | name (unique), category, when_to_use, example, embedding (JSON), times_recommended/applied |
| `seedlings.framework_applications` | Framework usage tracking | user_id, framework_id, decision_event_id, application_notes, was_helpful |

### 7.3 Schema Drift Notes

| Divergence | init.sql | models.py |
|---|---|---|
| Users columns | `encrypted_key_hash`, `display_name`, `is_active` | `encryption_salt`, `public_key`, `privacy_settings` (JSON), `intervention_preferences` (JSON) |
| Events text field | `scrubbed_text` | `encrypted_text` + `encryption_nonce` + `encryption_tag` + `anonymized_text` |
| Events embedding | `vector(1536)` (pgvector native) | JSON (Python list) |
| Integration tokens | `access_token_encrypted` (persistent) | In-memory `_integrations` list (volatile) |

---

## 8. Workers Layer

All workers normalize input to the `FounderEvent` schema and publish to Redis Stream `seedlings:events`.

### 8.1 Voice Transcription Worker

Source: `workers/voice_transcription/worker.py`

**Class**: `VoiceTranscriptionWorker`

| Provider | Model | API Endpoint |
|---|---|---|
| Groq (default) | whisper-large-v3-turbo | `https://api.groq.com/openai/v1/audio/transcriptions` |
| OpenAI | whisper-1 | `https://api.openai.com/v1/audio/transcriptions` |
| Local | openai-whisper (pip) | Local inference |

**Event Type Auto-Detection** (keyword matching on transcript):
- "decided" / "choosing" / "decision" → `decision_record`
- "weekly" / "review" / "last week" → `weekly_review`
- Default → `reflection`

### 8.2 Email Ingestion Worker

Source: `workers/email_ingestion/worker.py`

**Class**: `EmailIngestionWorker`

- Protocol: IMAP (default server: `imap.gmail.com`)
- Searches for `UNSEEN` emails; marks as read after processing
- Metadata extraction from email body:
  - Hashtags: `#fundraising #product` → `tags` array
  - Priority: `[HIGH]`, `[URGENT]`, `[LOW]` → `priority` field
  - Context: `@context: board meeting` → `context` field
  - Subject prefix: `[DECISION]`, `[WEEKLY]`, `[REFLECTION]` → event type

### 8.3 Slack/Discord Webhook Worker

Source: `workers/slack_discord/worker.py`

**Framework**: Standalone FastAPI app (webhook server)

| Webhook | Verification | Event Extraction |
|---|---|---|
| Slack (`POST /webhook/slack`) | HMAC-SHA256 via `X-Slack-Request-Timestamp` + `X-Slack-Signature` + `SLACK_SIGNING_SECRET` | `client_msg_id`, `text`, `channel`, `user`, `ts` |
| Discord (`POST /webhook/discord`) | Ping verification (type=1) | `id`, `content`, `author`, `channel_id` |

All events created with `event_type="reflection"`.

### 8.4 Google Workspace Worker

Source: `workers/google_workspace/worker.py`

- **Calendar**: Fetches events via Google Calendar API; categorizes by summary keywords into: engineering, fundraising, management, sales, strategy, reflection
- **Gmail**: Fetches email snippets via Gmail API
- **Time Allocation**: Compares calendar-derived time allocation against stated priorities

### 8.5 OCR Worker

Source: `workers/ocr/worker.py`

- **PDF**: `pypdf` for text extraction
- **Images**: Tesseract (`pytesseract`) for OCR
- **Storage**: Uploads to MinIO S3 bucket (`seedlings-uploads`)

---

## 9. Frontend Architecture

Source: `frontend/src/`

### 9.1 Routing

| Route | Page Component | Auth Required | Description |
|---|---|---|---|
| `/login` | LoginPage | No | Email/password login |
| `/signup` | SignupPage | No | Registration with display name |
| `/oauth/callback` | OAuthCallbackPage | No | OAuth redirect handler; extracts `code` and `state` from URL |
| `/` | JournalPage | Yes | Default; write tab (encrypted journal) + voice memo tab |
| `/decisions` | DecisionsPage | Yes | Create, view, resolve decisions; confidence tracking |
| `/sparring` | SparringPage | Yes | Multi-turn adversarial sparring with Devil's Advocate persona |
| `/dashboard` | DashboardPage | Yes | KPI cards, growth trajectory chart, bias frequency bar chart, thinking profile radar |
| `/privacy` | PrivacyPage | Yes | Privacy zones, processing preferences, data export/delete |
| `/settings` | SettingsPage | Yes | Profile, integration connections (Slack/Discord/Google/Gmail), notification preferences |

### 9.2 State Management

- **Authentication**: React Context API (`AuthContext.tsx`)
  - Token stored in `localStorage` as `"seedlings_token"`
  - On mount: validates token via `GET /api/auth/me`
  - On 401: clears token, redirects to `/login`
- **Application State**: Component-level `useState` hooks (no Redux/Zustand)
- **API Client**: Axios instance with base URL `/api` (proxied to `http://localhost:8000` via Vite)

### 9.3 Key Components

| Component | Location | Purpose |
|---|---|---|
| Sidebar | `components/Sidebar.tsx` | Navigation (6 routes), user info, theme toggle, encryption indicator |
| VoiceMemo | `components/VoiceMemo.tsx` | MediaRecorder API; supports webm/opus, webm, ogg/opus, mp4; sends to `/transcribe` |
| ReflectionToggle | `components/ReflectionToggle.tsx` | Toggle between local-only processing and encrypted server submission |
| ThemeProvider | `components/ThemeProvider.tsx` | Dark/light mode via React context |
| UI Library | `components/ui/` | Radix + CVA: button, card, input, label, textarea, switch, tabs, tooltip, progress |

---

## 10. Infrastructure

### 10.1 Docker Compose Services

Source: `docker-compose.yml`

```
PostgreSQL 16 (pgvector)          Redis 7 Alpine              MinIO
├─ Port: 5432                     ├─ Port: 6379               ├─ Port: 9000 (API)
├─ DB: seedlings                  ├─ appendonly: yes           ├─ Port: 9001 (Console)
├─ User: seedlings                ├─ Health: redis-cli ping    ├─ User: seedlings
├─ Init: infra/init.sql           └─ Volume: redis-data        └─ Volume: minio-data
├─ Health: pg_isready
└─ Volume: postgres-data
```

### 10.2 CI/CD

Source: `.github/workflows/`

| Workflow | Trigger | Jobs |
|---|---|---|
| `ci.yml` | Push to main/develop, PRs | Backend lint (Ruff), Mypy type check, frontend TS check + build, Docker Compose validation |
| `cd.yml` | Push to main, tags `v*` | Build backend/frontend images, deploy to `ghcr.io` |
| `ci-cd.yml` | Push to main/master/develop, PRs | pytest, frontend-test, code-quality (Black, isort, Mypy, Flake8), security-scan (Safety, Bandit), Docker build |

### 10.3 Makefile Targets

Source: `Makefile`

| Target | Description |
|---|---|
| `make dev` | Start infra + backend + frontend |
| `make infra` | Start Docker services |
| `make install` | Install all dependencies (backend venv + frontend npm) |
| `make build-frontend` | Production build |
| `make lint` | Run all linters |
| `make test` | Run pytest |
| `make clean` | Remove build artifacts |
| `make status` | Show running services and ports |

---

## 11. Known Gaps & Technical Debt

### Critical

| Issue | Description | Impact | Location |
|---|---|---|---|
| **In-Memory Data Stores** | All API data (`_users`, `_events`, `_decisions`, `_biases`, `_integrations`) stored in Python lists/dicts | All data lost on server restart | `auth.py:21`, `routes.py:30-32`, `integrations.py:24` |
| **OAuth Tokens Not Encrypted** | Access tokens stored as plaintext strings in memory | Token exposure if memory dumped; no persistence | `integrations.py:225-232` |
| **No Token Refresh** | No mechanism to refresh expired OAuth tokens | Integrations break after token expiry | `integrations.py` |
| **Schema Drift** | `models.py` defines 6 tables not present in `init.sql`; column differences in shared tables | ORM models cannot be used against deployed schema | `models.py` vs `init.sql` |

### High

| Issue | Description | Location |
|---|---|---|
| **Weak Password Requirements** | Minimum 6 characters; no complexity requirements | `auth.py:66` |
| **Default Secret Key** | `dev-secret-key-change-in-production` hardcoded as default | `config.py` |
| **No CSRF Protection** | No CSRF tokens for state-changing requests | `main.py` |
| **Transcribe Endpoint Unauthenticated** | `POST /transcribe` has no auth dependency | `routes.py:134-135` |

### Medium

| Issue | Description | Location |
|---|---|---|
| **Insights/Interventions Endpoints Missing** | `ARCHITECTURE.md` documents these routes but they have no implementation in the API layer | `ARCHITECTURE.md:246-254` |
| **Pattern Engine Uses LangChain** | Pattern engine hardcodes `ChatOpenAI(model="gpt-4o-mini")` instead of using swappable `LLMProvider` | `pattern_engine.py:48` |
| **Redis Connection Not Validated** | Redis publish failures are silently caught; no retry or circuit breaker | `routes.py:68-69` |
| **Groq Embeddings Fallback** | Groq provider falls back to Ollama for embeddings; fails if Ollama not running | `llm_provider.py:175-195` |

### Documentation Discrepancies (Fixed)

| Document | Error | Correction |
|---|---|---|
| `ARCHITECTURE.md:238` | `POST /api/auth/register` | Actual: `POST /api/auth/signup` |
| `ARCHITECTURE.md:258` | `POST /api/privacy/export` | Actual: `GET /api/privacy/export` |
| `ARCHITECTURE.md:259` | `DELETE /api/privacy/delete` | Actual: `DELETE /api/privacy/data` |
| `docs/architecture.md:24` | `aya-expanse:8b` as Ollama model | Actual default: `tinyllama` (config.py) |
| `ARCHITECTURE.md:201` | Default LLM provider is Ollama | Actual default: `groq` (config.py:30) |
