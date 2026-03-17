# 🌱 Infrastructure — Seedlings

> Database schema initialization and infrastructure configuration.

## 📖 Overview

The `infra/` directory contains the SQL initialization script that bootstraps the Seedlings PostgreSQL database. It creates the `seedlings` schema, enables the `pgvector` extension for embedding-based similarity search, and defines all application tables with their indexes.

## 📁 Directory Structure

```
infra/
└── init.sql          # Database schema initialization script
```

## 🗄️ Database Schema

All tables live under the `seedlings` schema.

| Table | Purpose |
|-------|---------|
| `users` | Founders/users with authentication credentials and encryption keys |
| `founder_events` | Normalized events from all ingestion sources (voice, Slack, journal, calendar, etc.) with vector embeddings |
| `decisions` | Decision tracking and Judgment Quality Scorecard with confidence/outcome scores |
| `bias_detections` | Cognitive bias detections linked to events, with severity and acknowledgment status |
| `knowledge_chunks` | RAG knowledge base chunks with vector embeddings for similarity search |
| `integrations` | OAuth tokens for third-party services (Slack, Google, Gmail) |

## 🔌 Extensions

- **pgvector** — enabled via `CREATE EXTENSION IF NOT EXISTS vector`
- Embedding columns use `vector(1536)` (OpenAI-compatible dimensions) on `founder_events` and `knowledge_chunks`
- **IVFFlat indexes** (`vector_cosine_ops`, `lists = 100`) are created on both embedding columns for fast cosine-similarity search

## 🚀 Usage

### Automatic (Docker Compose)

The `docker-compose.yml` mounts `init.sql` into the Postgres entrypoint directory:

```yaml
volumes:
  - ./infra/init.sql:/docker-entrypoint-initdb.d/init.sql
```

This means `init.sql` runs automatically the **first time** the `seedlings-postgres` container is created. To re-run it, remove the `postgres-data` volume and recreate the container.

### Manual

```bash
psql -h localhost -U seedlings -d seedlings -f infra/init.sql
```

## 📚 Related Documentation

- [`docker-compose.yml`](../docker-compose.yml) — Service definitions for Postgres (pgvector/pg16), Redis, and MinIO
- [`docs/deployment.md`](../docs/deployment.md) — Deployment guide
