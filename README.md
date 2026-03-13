# 🌱 Seedlings — AI Co-Founder for the Mind

An elite, zero-trust AI strategic thinking partner for founders. Built to improve the **quality** of founder thinking, not the quantity of output.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose

### 1. Start Infrastructure
```bash
docker-compose up -d
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python -m app.db_init
uvicorn app.main:app --reload
```
🔗 Backend: http://localhost:8000 | Docs: http://localhost:8000/docs

### 3. Frontend Setup
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```
🔗 Frontend: http://localhost:5173

### 4. (Optional) Local LLM with Ollama
```bash
ollama serve
ollama pull tinyllama
ollama pull nomic-embed-text
```

## 🧪 Testing

```bash
# Backend tests
cd backend && pytest -v

# Frontend tests
cd frontend && npm test

# E2E tests
npm run test:e2e

# Coverage
pytest --cov=app --cov-report=html
```

## 🏛️ Architecture

| Component | Technology |
|-----------|-----------|
| **Frontend** | React + TypeScript + shadcn/ui |
| **Backend** | FastAPI + SQLAlchemy + Pydantic |
| **LLM** | Swappable (Ollama/OpenAI) |
| **Message Broker** | Redis Streams |
| **Database** | PostgreSQL 15 |
| **Security** | E2E Encryption (AES-256-GCM) |

## ✨ Key Features

✅ **Multi-modal ingestion** (email, voice, Slack, Discord, calendar)
✅ **Pattern recognition** (cognitive biases, decision frameworks)
✅ **RAG pipeline** with strategic framework library
✅ **Intelligent interventions** with Socratic questioning
✅ **Judgment quality tracking** (predicted vs. actual outcomes)
✅ **LoRA personalization** for adaptive AI
✅ **Zero-trust security** (E2E encryption, privacy zones)

## 📚 Documentation

- [Architecture Guide](ARCHITECTURE.md) - Complete system documentation
- [API Reference](http://localhost:8000/docs) - Interactive API docs
- [Contributing](CONTRIBUTING.md) - Contribution guidelines

## 🛠️ Project Structure

```
student-project/
├── frontend/              # React + TypeScript
├── backend/               # FastAPI + SQLAlchemy
│   ├── app/
│   │   ├── api/           # API endpoints
│   │   ├── core/          # Config, security, LLM
│   │   ├── services/      # Business logic
│   │   └── models.py      # Database models
│   └── tests/         # Unit tests
├── workers/               # Ingestion workers
│   ├── email_ingestion/
│   ├── voice_transcription/
│   ├── slack_discord/
│   └── google_workspace/
└── infra/                 # Infrastructure
```

## 🔒 License

MIT
