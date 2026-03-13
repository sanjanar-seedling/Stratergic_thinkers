# Deployment Guide: Seedlings AI Co-Founder

Seedlings can be run entirely bare-metal or orchestrated via Docker Compose. Given its strict data-privacy requirements, it is designed to easily run in local or air-gapped environments.

## Prerequisites

- **Python 3.10+**
- **Node.js 18+** & npm
- **Docker & Docker Compose**
- **Ollama** (for local LLM execution)

---

## 🏗️ 1. Start Infrastructure (Docker)

The application depends on PostgreSQL (database), Redis (message broker / streams), and optionally MinIO (S3-compatible object storage).

1. Navigate to the project root:
   ```bash
   cd seedlings
   ```
2. Start the services:
   ```bash
   docker-compose up -d
   ```
   This will spin up:
   - `postgres` on `localhost:5432`
   - `redis` on `localhost:6379`
   - `minio` on `localhost:9000`

---

## 🧠 2. Setup the AI Engine (Ollama)

Seedlings defaults to local, zero-cost inference using Ollama.

1. Install [Ollama](https://ollama.com).
2. Start the Ollama server:
   ```bash
   ollama serve
   ```
3. Pull the required models (in a separate terminal):
   ```bash
   # Text Generation Model
   ollama pull aya-expanse:8b

   # Embeddings Model (Optional)
   ollama pull nomic-embed-text
   ```
> *Note: Seedlings can use `tinyllama` or `llama3` as an alternative if configured in the `.env`.*

---

## ⚙️ 3. Start the Backend (FastAPI)

The backend handles the core API, PII scrubbing (Presidio), and AI orchestration.

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   
   # Download the spaCy model required for PII Anonymization
   python -m spacy download en_core_web_lg
   ```
4. Copy the environment template:
   ```bash
   cp .env.example .env
   ```
5. Edit `.env` to match your infrastructure. Key configurations:
   ```ini
   LLM_PROVIDER=ollama
   OLLAMA_CHAT_MODEL=aya-expanse:8b
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/seedlings
   REDIS_URL=redis://localhost:6379
   ```
6. Start the API server:
   ```bash
   uvicorn app.main:app --reload
   ```
   The backend will be available at `http://localhost:8000`. You can view the automatically generated Swagger docs at `http://localhost:8000/docs`.

---

## 🎨 4. Start the Frontend (React + Vite)

The frontend is a modern React application utilizing Tailwind CSS v4 and fully responsive glassmorphism aesthetic components.

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```
   The web application will be available at `http://localhost:5173`. 
   The frontend automatically proxies `/api/*` requests to `http://localhost:8000` via its `vite.config.ts`.

---

## 🛠️ 5. Troubleshooting

- **Database Errors**: Verify `docker-compose ps` shows `postgres` as Healthy. Test the connection string.
- **Signup Failing**: Ensure the backend `requirements.txt` has `bcrypt==4.0.1` and `passlib==1.7.4`.
- **422 Errors on Journal / PII Model Downloading**: The first time you submit an event or decision, the backend takes a few moments to download the ~400MB spaCy model (`en_core_web_lg`). The process may time out. Simply wait for the backend logs to confirm the download, restart the backend, and try again.
- **LLM Timeout**: Ensure Ollama is running and the model specified in `OLLAMA_CHAT_MODEL` is pulled. Large models (like 8B parameter variants) on CPU-only machines may take several minutes to process adversarial sparring prompts. The backend HTTP client is configured with a 300-second timeout to accommodate this workload.
