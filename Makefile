# ============================================================
# Seedlings Platform — Makefile
# ============================================================

.PHONY: help dev dev-frontend dev-backend stop stop-frontend stop-backend \
        infra infra-stop install install-frontend install-backend \
        build build-frontend lint test clean

# Default
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Development ──────────────────────────────────────────────

dev: infra dev-backend dev-frontend ## Start everything (infra + backend + frontend)

dev-frontend: ## Start frontend (Vite HTTPS on :5173)
	@echo "🌱 Starting frontend on https://localhost:5173 ..."
	@cd frontend && npm run dev &

dev-backend: ## Start backend (FastAPI on :8000)
	@echo "🌱 Starting backend on http://localhost:8000 ..."
	@cd backend && venv/bin/uvicorn app.main:app --reload --port 8000 &

# ── Stop ─────────────────────────────────────────────────────

stop: stop-frontend stop-backend ## Stop frontend + backend
	@echo "✅ All app processes stopped"

stop-frontend: ## Stop frontend dev server
	@echo "Stopping frontend..."
	@lsof -ti:5173 2>/dev/null | xargs kill -9 2>/dev/null || true
	@lsof -ti:5174 2>/dev/null | xargs kill -9 2>/dev/null || true

stop-backend: ## Stop backend dev server
	@echo "Stopping backend..."
	@lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null || true

stop-all: stop infra-stop ## Stop everything including Docker infra
	@echo "✅ Everything stopped"

# ── Infrastructure (Docker) ──────────────────────────────────

infra: ## Start Docker services (Postgres, Redis, MinIO)
	@echo "🐳 Starting infrastructure..."
	@docker compose up -d

infra-stop: ## Stop Docker services
	@echo "🐳 Stopping infrastructure..."
	@docker compose down

infra-logs: ## Tail Docker service logs
	@docker compose logs -f

# ── Install ──────────────────────────────────────────────────

install: install-backend install-frontend ## Install all dependencies

install-frontend: ## Install frontend dependencies
	@echo "📦 Installing frontend dependencies..."
	@cd frontend && npm install

install-backend: ## Install backend dependencies (with venv)
	@echo "📦 Installing backend dependencies..."
	@cd backend && python3 -m venv venv 2>/dev/null || true
	@cd backend && venv/bin/pip install -r requirements.txt

# ── Build ────────────────────────────────────────────────────

build: build-frontend ## Build for production

build-frontend: ## Build frontend for production
	@echo "🔨 Building frontend..."
	@cd frontend && npm run build

# ── Quality ──────────────────────────────────────────────────

lint: ## Run linters (backend + frontend)
	@echo "🔍 Linting backend..."
	@cd backend && venv/bin/python -m flake8 app/ --max-line-length=120 || true
	@echo "🔍 Linting frontend..."
	@cd frontend && npx eslint src/ || true

test: ## Run backend tests
	@echo "🧪 Running tests..."
	@cd backend && venv/bin/python -m pytest tests/ -v

# ── Utilities ────────────────────────────────────────────────

clean: ## Remove build artifacts and caches
	@echo "🧹 Cleaning..."
	@rm -rf frontend/dist frontend/node_modules/.vite
	@find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find backend -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true

logs: ## Tail backend logs
	@tail -f /tmp/seedlings-backend.log 2>/dev/null || echo "No log file. Backend logs go to stdout when running with 'make dev-backend'"

status: ## Show running services and ports
	@echo "=== Ports ==="
	@for port in 5173 8000 5432 6379 9000 9001; do \
		pid=$$(lsof -ti:$$port 2>/dev/null); \
		if [ -n "$$pid" ]; then \
			echo "  :$$port  ✅  (PID $$pid)"; \
		else \
			echo "  :$$port  ❌"; \
		fi; \
	done
	@echo ""
	@echo "=== Docker ==="
	@docker compose ps 2>/dev/null || echo "  Docker not running"
