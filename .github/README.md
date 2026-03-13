# 🌱 GitHub Actions — Seedlings

> CI/CD pipeline configuration using GitHub Actions.

## 📖 Overview

This directory contains three GitHub Actions workflows that handle continuous integration (linting, type checking, testing, security scanning) and continuous deployment (Docker image builds and deployment) for the Seedlings monorepo.

## 🔄 Workflows

| Workflow | File | Trigger | Jobs |
|----------|------|---------|------|
| **CI — Lint, Type Check, Build** | `ci.yml` | Push to `main`, `develop`; PRs to `main` | `backend` (Python lint via Ruff, Mypy type check), `frontend` (TypeScript type check, build), `docker` (Docker Compose validation) |
| **CD — Build & Deploy** | `cd.yml` | Push to `main`; tags matching `v*` | `build-backend` (build & push backend image), `build-frontend` (build & push frontend image), `deploy` (placeholder deployment step, runs on `main` only) |
| **CI/CD Pipeline** | `ci-cd.yml` | Push to `main`, `master`, `develop`; PRs to `main`, `master` | `backend-test` (pytest with coverage), `frontend-test` (tests, type check), `code-quality` (Black, isort, Mypy, Flake8), `security-scan` (Safety, Bandit), `build` (Docker image builds, runs after tests pass on `main`/`master`) |

## 🐳 Service Containers

The `ci-cd.yml` pipeline spins up service containers for integration testing:

- **PostgreSQL 15** (`postgres:15-alpine`) — test database on port `5432`
- **Redis 7** (`redis:7-alpine`) — caching layer on port `6379`

Both containers include health checks to ensure readiness before tests run.

## 📦 Container Registry

Docker images for `backend` and `frontend` are built and pushed to **GitHub Container Registry** (`ghcr.io`). Each image is tagged with both `latest` and the commit SHA for traceability.

## 📚 Related Documentation

- [Project README](../README.md)
- [Deployment Guide](../docs/deployment.md)
