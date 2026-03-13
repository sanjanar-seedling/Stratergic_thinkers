# Seedlings - AI Co-Founder for the Mind

## Architecture Overview

A deeply personalized AI agent that serves as a strategic thinking partner for founders. Unlike standard productivity tools, this system focuses on **improving the quality of founder thinking, not the quantity of output**.

## System Components

### 1. Frictionless Ingestion Layer ("Ears" and "Eyes")

Multi-modal input capture system:

- **Email Ingestion** (`workers/email_ingestion/`)
  - IMAP-based email processing
  - Auto-detection of event types (reflection, decision, weekly review)
  - Metadata extraction (tags, priority, context)

- **Voice Transcription** (`workers/voice_transcription/`)
  - OpenAI Whisper API integration
  - Local Whisper model support
  - Automatic event type detection from transcription

- **Slack/Discord** (`workers/slack_discord/`)
  - Webhook-based ingestion
  - Signature verification
  - Real-time event streaming

- **Google Workspace** (`workers/google_workspace/`)
  - Calendar integration for time allocation tracking
  - Gmail integration (planned)
  - OAuth 2.0 authentication

**Event Schema**: All inputs are normalized to `FounderEvent` format:
```python
{
    "id": "unique-id",
    "source": "email|slack|discord|voice|web|google_calendar",
    "event_type": "reflection|decision_record|weekly_review|time_allocation",
    "text": "content",
    "context": {"source-specific metadata"},
    "created_at": "ISO 8601 timestamp"
}
```

### 2. Cognitive Analysis Engines ("Brain")

Specialized AI microservices for analytical processing:

#### Pattern Recognition Engine (`backend/app/services/pattern_recognition.py`)
- **Decision Framework Detection**: Identifies recurring choice frameworks (first principles, pros/cons, reversible decisions)
- **Cognitive Bias Detection**: Flags sunk cost fallacy, confirmation bias, analysis paralysis, over-optimization
- **Avoidance Detection**: Spots topics mentioned frequently but never acted upon
- **Decision Velocity Tracking**: Monitors if decision-making is speeding up or slowing down

#### State & Drift Tracking (`backend/app/services/state_tracking.py`)
- **Emotional State Detection**: Correlates emotional state with decision quality
- **Time Allocation Drift**: Compares stated priorities vs. actual time spent (from calendar data)
- **Volatility Scoring**: Measures emotional stability over time
- **Context Switching**: Tracks frequency of topic changes

#### RAG Pipeline (`backend/app/services/rag_pipeline.py`)
- **Strategic Framework Library**: Curated mental models from founder literature
- **Semantic Search**: Context-aware framework recommendations
- **Application Tracking**: Monitors which frameworks lead to better outcomes
- **Frameworks Included**:
  - First Principles Thinking
  - Reversible vs. Irreversible Decisions (Jeff Bezos)
  - Regret Minimization Framework
  - Eisenhower Matrix
  - Jobs to Be Done
  - Working Backwards (Amazon)
  - Pre-Mortem Analysis
  - Opportunity Cost

### 3. Active Sparring Partner ("Voice")

#### Intervention Engine (`backend/app/services/intervention.py`)

Intelligent reflection prompts triggered by:

1. **Pattern-Triggered**
   - Cognitive bias detection → Socratic questioning
   - Avoidance patterns → "What's the real blocker?"

2. **Time-Based**
   - Weekly review reminders
   - Decision follow-ups (7 days after major decisions)

3. **Context-Aware**
   - Post-decision reflection
   - Framework application suggestions

4. **Drift-Triggered**
   - Time allocation mismatches
   - Priority vs. execution gaps

**Intervention Types**:
- **Clarifying**: "What's the minimum info needed to decide?"
- **Challenging**: "If you started fresh today, would you still choose this?"
- **Integrating**: "What shifted in your strategy since last week?"

**Respects User Preferences**:
- Quiet hours (no interventions during sleep/focus time)
- Pause mode (disable during high-stress sprints)
- Priority thresholds (only high-priority interventions)
- Max interventions per day

### 4. Zero-Trust Security Architecture ("Vault")

#### End-to-End Encryption (`backend/app/core/encryption.py`)
- **Hybrid Encryption**: RSA-4096 for key exchange, AES-256-GCM for data
- **Client-Side Encryption**: Data encrypted before leaving device
- **Key Derivation**: PBKDF2 with 600,000 iterations (OWASP standard)
- **Data Anonymization**: PII detection and pseudonymization for AI processing

#### Privacy Controls (`backend/app/core/privacy.py`)
- **Privacy Zones**: Topics off-limits for AI processing
  - `no_storage`: Never store (e.g., personal health)
  - `reflection_only`: Store but don't process with AI (e.g., family)
- **Data Retention Policies**:
  - Auto-delete after N days
  - Archive old data to cold storage
  - Keep insights only (delete raw text)
- **Consent Management**: Granular consent for AI processing, model training, third-party integrations
- **GDPR Compliance**: Full data export and right to erasure

### 5. Event-Driven Architecture

**Redis Streams** for event processing:
```
Ingestion Workers → Redis Stream → Event Processor → Analysis Engines → Interventions
```

**Consumer Groups**: Multiple processors can scale horizontally

**Event Flow**:
1. Worker receives input (email, voice, Slack, etc.)
2. Normalizes to `FounderEvent` schema
3. Pushes to Redis Stream (`seedlings:events`)
4. Event Processor validates and enriches
5. Triggers cognitive analysis pipelines
6. Stores in PostgreSQL
7. Generates interventions if patterns detected

## Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL (with asyncpg)
- **Cache/Queue**: Redis (with Streams)
- **LLM Provider**: Swappable (Groq for default cloud inference, OpenAI for production, Ollama for local/air-gapped)
- **Encryption**: `cryptography` library
- **Authentication**: JWT tokens

### Frontend
- **Framework**: React
- **State Management**: Context API
- **UI Components**: Custom component library

### Infrastructure
- **Storage**: MinIO (S3-compatible) for file uploads
- **Deployment**: Docker + Docker Compose
- **CI/CD**: GitHub Actions

## Privacy Guarantees

1. **Military-Grade Encryption**: AES-256-GCM with RSA-4096 key exchange
2. **Zero-Knowledge Architecture**: Server never sees plaintext (optional mode)
3. **Local Processing**: Ollama support for on-device AI
4. **No Third-Party Access**: Data never leaves your infrastructure
5. **No Model Training**: Founder data never used for training without explicit consent
6. **Complete Control**: Export all data, delete anytime

## Getting Started

### Prerequisites
```bash
# Install dependencies
pip install -r backend/requirements.txt
npm install --prefix frontend

# Start infrastructure
docker-compose up -d postgres redis minio

# (Optional) Start Ollama for local LLM
ollama serve
ollama pull tinyllama
ollama pull nomic-embed-text
```

### Configuration

Create `.env` file:
```bash
# Database
DATABASE_URL=postgresql+asyncpg://seedlings:seedlings_dev_2024@localhost:5432/seedlings

# Redis
REDIS_URL=redis://localhost:6379

# LLM Provider ("ollama" or "openai")
LLM_PROVIDER=groq  # "groq", "openai", or "ollama"
GROQ_API_KEY=      # Required if using Groq (default)
OPENAI_API_KEY=    # Required if using OpenAI

# Security
SECRET_KEY=your-secret-key-here

# OAuth (optional)
SLACK_CLIENT_ID=
SLACK_CLIENT_SECRET=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
```

### Run Services

```bash
# Backend API
cd backend
uvicorn app.main:app --reload

# Frontend
cd frontend
npm run dev

# Workers (in separate terminals)
python workers/email_ingestion/worker.py
python workers/voice_transcription/worker.py
python workers/slack_discord/worker.py

# Event Processor
python backend/app/services/event_processor.py
```

## API Endpoints

### Authentication
- `POST /api/auth/signup` - Create account
- `POST /api/auth/login` - Get JWT token
- `GET /api/auth/me` - Get current user profile

### Events
- `POST /api/events` - Submit new event (web interface)
- `GET /api/events` - List user events
- `GET /api/events/{id}` - Get event details

### Insights (Planned — not yet implemented in API layer)
- `GET /api/insights/patterns` - Get detected patterns
- `GET /api/insights/biases` - Get cognitive biases
- `GET /api/insights/drift` - Get time allocation drift

### Interventions (Planned — not yet implemented in API layer)
- `GET /api/interventions` - Get pending interventions
- `POST /api/interventions/{id}/respond` - Respond to intervention

### Dashboard
- `GET /api/dashboard/stats` - Get decision metrics
- `GET /api/dashboard/biases` - Get detected biases
- `GET /api/dashboard/growth` - Get growth trajectory

### Privacy
- `GET /api/privacy/export` - Export all data
- `DELETE /api/privacy/data` - Delete all data

## Roadmap

### Phase 1: MVP (Current)
- [x] Multi-modal ingestion (email, voice, Slack, Discord)
- [x] Pattern recognition engine
- [x] State tracking engine
- [x] RAG pipeline with framework library
- [x] Intervention engine
- [x] End-to-end encryption
- [x] Privacy controls

### Phase 2: Intelligence
- [ ] Judgment quality scorecard (predicted vs. actual outcomes)
- [ ] Longitudinal insights (quarterly syntheses)
- [ ] Calibration tracking (confidence vs. accuracy)
- [ ] Framework effectiveness tracking

### Phase 3: Personalization
- [ ] LoRA fine-tuning on founder's writing style
- [ ] Personalized framework recommendations
- [ ] Adaptive intervention timing
- [ ] Custom cognitive bias detection

### Phase 4: Collaboration
- [ ] Co-founder sync (shared insights, different privacy zones)
- [ ] Advisor integration (selective sharing)
- [ ] Team alignment tracking

## Contributing

This is a student project. Contributions welcome!

## License

MIT License

## Acknowledgments

Inspired by:
- Jeff Bezos' decision-making frameworks
- Ray Dalio's Principles
- Shane Parrish's mental models
- Y Combinator startup wisdom
