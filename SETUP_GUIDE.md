# Complete Setup and Testing Guide

## 🚀 Local Development Setup

### Step 1: Clone and Start Infrastructure

```bash
git clone https://gitlab.com/student-group2400110/student-project.git
cd student-project

# Start PostgreSQL, Redis, MinIO
docker-compose up -d

# Verify services
docker-compose ps
```

### Step 2: Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Initialize database
python -m app.db_init

# Start backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Backend URLs:**
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

### Step 3: Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env

# Start development server
npm run dev
```

**Frontend URL:** http://localhost:5173

### Step 4: (Optional) Local LLM with Ollama

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama server
ollama serve

# Pull models (in another terminal)
ollama pull tinyllama        # Chat model
ollama pull nomic-embed-text # Embedding model

# Verify
curl http://localhost:11434/api/tags
```

### Step 5: Start Workers (Optional)

In separate terminals:

```bash
# Event processor
python backend/app/services/event_processor.py

# Email ingestion
python workers/email_ingestion/worker.py

# Voice transcription
python workers/voice_transcription/worker.py

# Slack webhooks
cd workers/slack
uvicorn worker:app --port 8001
```

## 🧪 Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest -v

# Run with coverage
pytest --cov=app --cov-report=html --cov-report=term

# Run specific test file
pytest tests/test_pattern_recognition.py -v

# Run specific test
pytest tests/test_pattern_recognition.py::TestPatternRecognition::test_detect_framework_patterns -v

# View coverage report
open htmlcov/index.html
```

### Frontend Tests

```bash
cd frontend

# Run tests
npm test

# Run tests in watch mode
npm run test:watch

# Run E2E tests
npm run test:e2e

# Type checking
npm run type-check
```

### Integration Tests

```bash
# Start all services
docker-compose up -d
uvicorn app.main:app --reload &
cd frontend && npm run dev &

# Run integration tests
pytest tests/integration/ -v
```

## 📝 API Testing

### 1. Create Account

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "founder@example.com",
    "password": "SecurePass123!",
    "full_name": "Test Founder"
  }'
```

### 2. Login

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "founder@example.com",
    "password": "SecurePass123!"
  }'
```

Save the `access_token` from response.

### 3. Submit Events

```bash
# Reflection
curl -X POST http://localhost:8000/api/events \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "web",
    "event_type": "reflection",
    "text": "Feeling overwhelmed with the product roadmap. Too many features, not enough focus."
  }'

# Decision with sunk cost bias
curl -X POST http://localhost:8000/api/events \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "web",
    "event_type": "decision_record",
    "text": "Decided to continue with Feature X even though it is not working. We have already invested 6 months, cannot give up now."
  }'
```

### 4. Trigger Analysis

```bash
curl -X POST http://localhost:8000/api/insights/analyze \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 5. Get Insights

```bash
# Patterns
curl http://localhost:8000/api/insights/patterns \
  -H "Authorization: Bearer YOUR_TOKEN"

# Cognitive biases
curl http://localhost:8000/api/insights/biases \
  -H "Authorization: Bearer YOUR_TOKEN"

# Time drift
curl http://localhost:8000/api/insights/drift \
  -H "Authorization: Bearer YOUR_TOKEN"

# Interventions
curl http://localhost:8000/api/interventions \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 6. Framework Recommendations

```bash
curl -X POST "http://localhost:8000/api/frameworks/recommend" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "context": "I am trying to decide whether to pivot our product strategy. We have been working on this for 6 months and have some traction, but I see a bigger opportunity in a different market.",
    "top_k": 3
  }'
```

### 7. Judgment Metrics

```bash
curl http://localhost:8000/api/judgment/metrics \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🔧 Troubleshooting

### Database Issues

```bash
# Check PostgreSQL
docker-compose ps postgres
docker-compose logs postgres

# Connect to database
docker-compose exec postgres psql -U seedlings -d seedlings

# Reset database
python -m app.db_init drop
python -m app.db_init
```

### Redis Issues

```bash
# Check Redis
docker-compose ps redis

# Test connection
redis-cli ping

# View stream
redis-cli XREAD COUNT 10 STREAMS seedlings:events 0
```

### Ollama Issues

```bash
# Check Ollama
curl http://localhost:11434/api/tags

# Restart Ollama
pkill ollama
ollama serve

# Re-pull models
ollama pull tinyllama
ollama pull nomic-embed-text
```

### Port Conflicts

```bash
# Find process using port
lsof -i :8000  # Backend
lsof -i :5173  # Frontend
lsof -i :5432  # PostgreSQL

# Kill process
kill -9 <PID>
```

## 🐳 Docker Deployment

### Build Images

```bash
# Backend
docker build -t seedlings-backend:latest backend/

# Frontend
docker build -t seedlings-frontend:latest frontend/
```

### Run with Docker Compose

```bash
# Production mode
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Scale workers
docker-compose up -d --scale event-processor=3
```

## 🔒 Security Testing

### Encryption Test

```python
from app.core.encryption import E2EEncryption

e2e = E2EEncryption()
data = "Sensitive founder reflection"
password = "founder-password"

# Encrypt
encrypted = e2e.encrypt_for_storage(data, password)
print(f"Encrypted: {encrypted['encrypted_data']['ciphertext'][:50]}...")

# Decrypt
decrypted = e2e.decrypt_from_storage(encrypted, password)
assert decrypted == data
print("✅ Encryption working")
```

### Privacy Zones Test

```python
from app.core.privacy import PrivacyController, UserPrivacySettings, PrivacyZone
from datetime import datetime

controller = PrivacyController()
settings = UserPrivacySettings(
    user_id="test-user",
    privacy_zones=[
        PrivacyZone(
            id="health",
            name="Personal Health",
            keywords=["therapy", "medication"],
            mode="no_storage",
            created_at=datetime.utcnow().isoformat(),
        )
    ],
    created_at=datetime.utcnow().isoformat(),
    updated_at=datetime.utcnow().isoformat(),
)

event = {"text": "Had therapy session today"}
should_store = controller.should_store_event(event, settings)
assert not should_store
print("✅ Privacy zones working")
```

## 📊 Performance Testing

### Load Test with Locust

```python
# locustfile.py
from locust import HttpUser, task, between

class FounderUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # Login
        response = self.client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "password"
        })
        self.token = response.json()["access_token"]
    
    @task(3)
    def submit_reflection(self):
        self.client.post(
            "/api/events",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "source": "web",
                "event_type": "reflection",
                "text": "Test reflection"
            }
        )
    
    @task(1)
    def get_insights(self):
        self.client.get(
            "/api/insights/patterns",
            headers={"Authorization": f"Bearer {self.token}"}
        )
```

Run: `locust -f locustfile.py --host=http://localhost:8000`

## 📚 Additional Resources

- **Architecture**: See [ARCHITECTURE.md](ARCHITECTURE.md)
- **API Docs**: http://localhost:8000/docs
- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md)
- **Deployment**: See [DEPLOYMENT.md](DEPLOYMENT.md)

## ✅ Verification Checklist

- [ ] PostgreSQL running on port 5432
- [ ] Redis running on port 6379
- [ ] Backend running on port 8000
- [ ] Frontend running on port 5173
- [ ] Ollama running on port 11434 (optional)
- [ ] Can create account via API
- [ ] Can login and get JWT token
- [ ] Can submit events
- [ ] Can trigger analysis
- [ ] Can get insights
- [ ] Tests passing (`pytest` and `npm test`)
- [ ] CI/CD pipeline passing

## 🐛 Common Issues

### "Module not found" errors
```bash
# Backend
pip install -r requirements.txt

# Frontend
npm install
```

### "Database connection failed"
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check connection string in .env
DATABASE_URL="postgresql+asyncpg://seedlings:seedlings_dev_2024@localhost:5432/seedlings"
```

### "Ollama not responding"
```bash
# Start Ollama
ollama serve

# Or use OpenAI instead
# In .env:
LLM_PROVIDER="openai"
OPENAI_API_KEY="your-key"
```

## 📧 Support

For issues, please create an issue on GitLab:
https://gitlab.com/student-group2400110/student-project/-/issues
