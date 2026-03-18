# ============================================================
# Seedlings Platform — Makefile
# ============================================================

.PHONY: help dev dev-frontend dev-backend stop stop-frontend stop-backend \
        infra infra-stop install install-frontend install-backend \
        build build-frontend lint test clean setup prod prod-build \
        prod-up prod-down db-init db-migrate status logs

# Default
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Quick Start (New Systems) ────────────────────────────────

setup: ## Setup project from scratch (install deps + infra)
	@echo "🚀 Setting up Seedlings platform..."
	@$(MAKE) install-frontend
	@$(MAKE) certs
	@$(MAKE) infra
	@$(MAKE) db-init
	@echo "✅ Setup complete! Run 'make dev' to start development"

init-prod: ## Initialize production environment (build + migrate)
	@echo "🚀 Initializing production..."
	@$(MAKE) prod-build
	@$(MAKE) db-init
	@echo "✅ Production ready! Run 'make prod-up' to start"

# ── Development ──────────────────────────────────────────────

dev: certs infra ## Start everything (infra + backend + frontend) with Docker
	@echo ""
	@echo "✅ All services started!"
	@echo ""
	@echo "🌐 Access the app:"
	@echo "   Frontend:  https://localhost:5173"
	@echo "   Backend:   http://localhost:8000"
	@echo "   API Docs:  http://localhost:8000/docs"
	@echo ""
	@echo "📦 Backend Logs:   make logs-backend"
	@echo "📦 Frontend Logs:  make logs-frontend"
	@echo "🛑 Stop services:  make stop-all"
	@echo ""

dev-frontend: ## Start frontend (Vite HTTPS on :5173)
	@echo "🌱 Starting frontend on https://localhost:5173 ..."
	@cd frontend && npm run dev &

dev-backend: ## Start backend (FastAPI on :8000)
	@echo "🌱 Starting backend on http://localhost:8000 ..."
	@cd backend && venv/bin/uvicorn app.main:app --reload --port 8000 &

# ── Production (Docker) ──────────────────────────────────────

prod: prod-up ## Alias for prod-up

prod-build: ## Build Docker images for production
	@echo "🔨 Building production Docker images..."
	@docker compose build --no-cache

prod-up: ## Start production stack with Docker Compose
	@echo "🚀 Starting production stack..."
	@docker compose up -d
	@echo "✅ Services running:"
	@echo "   Backend: http://localhost:8000"
	@echo "   Frontend: https://localhost:5173 (or your domain)"
	@echo "   MinIO Console: http://localhost:9001"

prod-down: ## Stop production stack
	@echo "🛑 Stopping production stack..."
	@docker compose down

prod-logs: ## Tail production logs
	@docker compose logs -f

prod-status: ## Show production container status
	@docker compose ps

# ── Logs ─────────────────────────────────────────────────────

logs: ## Tail all Docker logs
	@docker compose logs -f

logs-backend: ## Tail backend logs
	@docker compose logs -f backend

logs-frontend: ## Tail frontend logs
	@docker compose logs -f frontend

logs-postgres: ## Tail database logs
	@docker compose logs -f postgres

logs-redis: ## Tail Redis logs
	@docker compose logs -f redis

# ── Stop ─────────────────────────────────────────────────────

stop: infra-stop ## Stop all services (Docker)
	@echo "✅ All services stopped"

stop-frontend: ## Stop frontend dev server
	@echo "Stopping frontend..."
	@lsof -ti:5173 2>/dev/null | xargs kill -9 2>/dev/null || true
	@lsof -ti:5174 2>/dev/null | xargs kill -9 2>/dev/null || true

stop-backend: ## Stop backend dev server
	@echo "Stopping backend..."
	@lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null || true

stop-all: infra-stop ## Stop everything including Docker infra
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

# ── SSL Certificates ────────────────────────────────────────

certs: ## Generate local SSL certificates (mkcert)
	@if [ ! -f frontend/localhost+1.pem ] || [ ! -f frontend/localhost+1-key.pem ]; then \
		echo "🔐 Generating local SSL certificates..."; \
		cd frontend && mkcert localhost 127.0.0.1; \
		echo "✅ SSL certificates created"; \
	else \
		echo "✅ SSL certificates already exist"; \
	fi

certs-install: ## Install mkcert CA in system trust store
	@echo "🔐 Installing mkcert CA..."
	@sudo mkcert -install
	@echo "✅ CA installed (browser will trust localhost SSL)"

certs-clean: ## Remove local SSL certificates
	@echo "🧹 Removing SSL certificates..."
	@rm -f frontend/localhost+1.pem frontend/localhost+1-key.pem
	@echo "✅ SSL certificates removed"

db-init: ## Initialize database (runs with Docker)
	@echo "🗄️  Initializing database..."
	@docker compose exec -T postgres psql -U seedlings -d seedlings -f /docker-entrypoint-initdb.d/init.sql >/dev/null 2>&1 && \
		echo "✅ Database initialized" || \
		echo "✅ Database already initialized"

db-migrate: ## Run pending database migrations
	@echo "📦 Running migrations..."
	@echo "TODO: Add Alembic migrations when ready"

db-reset: ## Reset database (WARNING: deletes all data)
	@echo "⚠️  WARNING: This will DELETE all data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose down -v; \
		docker compose up -d; \
		$(MAKE) db-init; \
	fi

# ── Install ──────────────────────────────────────────────────

install: install-frontend ## Install frontend dependencies (backend runs in Docker)

install-frontend: ## Install frontend dependencies
	@echo "📦 Installing frontend dependencies..."
	@cd frontend && npm install

install-backend: ## Install backend dependencies locally (optional, for local dev)
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

status: ## Show running services and ports
	@echo "🔍 Development Services:"
	@lsof -i :5173 2>/dev/null | grep -q LISTEN && echo "  ✅ Frontend (https://localhost:5173)" || echo "  ❌ Frontend"
	@lsof -i :8000 2>/dev/null | grep -q LISTEN && echo "  ✅ Backend (http://localhost:8000)" || echo "  ❌ Backend"
	@docker ps --format "table {{.Names}}\t{{.Status}}" 2>/dev/null | grep -q seedlings && \
		echo "🐳 Docker Services:" && docker ps --format "  {{.Names}}: {{.Status}}" | grep seedlings || \
		echo "  ❌ Docker services not running"

version: ## Show system versions
	@echo "Platform Versions:"
	@echo "  Node: $$(node --version)"
	@echo "  Python: $$(python3 --version)"
	@echo "  Docker: $$(docker --version)"
	@echo "  Docker Compose: $$(docker compose version)"
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
