# =============================================================================
# teLLMe — Makefile
# =============================================================================

VERSION := $(shell cat VERSION 2>/dev/null || echo "0.1.0")
COMPOSE := docker compose -f docker-compose.yml

.PHONY: help up down status logs build test clean prepare lint

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ── Docker Compose ──────────────────────────────────────────────────────────

prepare: ## Prepare build context (copy sibling repos)
	@echo "Preparing build contexts..."
	@mkdir -p workspace
	@# code2llm source for its Dockerfile
	@rm -rf code2llm-src && cp -r ../code2llm code2llm-src && rm -rf code2llm-src/.git code2llm-src/.venv code2llm-src/venv
	@# stts source for its Dockerfile
	@rm -rf stts-src && cp -r ../stts stts-src && rm -rf stts-src/.git stts-src/.venv stts-src/venv
	@# .env from example if missing
	@test -f .env || cp .env.example .env
	@echo "Done. Ready to build."

build: prepare ## Build all Docker images
	$(COMPOSE) build

up: prepare ## Start all services (foreground)
	$(COMPOSE) up --build

up-d: prepare ## Start all services (detached)
	$(COMPOSE) up --build -d

down: ## Stop all services
	$(COMPOSE) down

restart: down up-d ## Restart all services

status: ## Check platform health via gateway
	@curl -sf http://localhost:9000/status 2>/dev/null | python3 -m json.tool || \
		echo "Gateway not running. Try: make up-d"

logs: ## Tail logs from all services
	$(COMPOSE) logs -f --tail=100

logs-%: ## Tail logs from specific service (e.g. make logs-nlp2cmd)
	$(COMPOSE) logs -f --tail=100 $*

ps: ## Show running containers
	$(COMPOSE) ps

# ── Development ─────────────────────────────────────────────────────────────

install: ## Install tellme package locally (dev)
	pip install -e ".[dev]"

test: ## Run tests
	python -m pytest tests/ -v --tb=short

test-gateway: ## Run gateway tests only
	python -m pytest tests/test_gateway.py -v

lint: ## Lint code
	python -m ruff check tellme/ tests/ || true

# ── Cleanup ─────────────────────────────────────────────────────────────────

clean: ## Remove build artifacts and temp dirs
	rm -rf code2llm-src stts-src
	rm -rf __pycache__ .pytest_cache
	rm -rf tellme/__pycache__ tests/__pycache__
	rm -rf tellme/services/__pycache__
	rm -rf *.egg-info dist build

clean-docker: down ## Stop services and remove volumes
	$(COMPOSE) down -v --rmi local
	docker volume rm -f tellme-ollama-data tellme-stts-cache 2>/dev/null || true

# ── Info ────────────────────────────────────────────────────────────────────

version: ## Show version
	@echo "teLLMe v$(VERSION)"

services: ## List service URLs
	@echo "teLLMe v$(VERSION) — Service endpoints:"
	@echo "  Gateway:   http://localhost:9000"
	@echo "  Ollama:    http://localhost:11434"
	@echo "  LiteLLM:   http://localhost:4000"
	@echo "  NLP2CMD:   http://localhost:8000"
	@echo "  Toonic:    http://localhost:8900"
	@echo "  Code2LLM:  http://localhost:8100"
	@echo "  STTS:      http://localhost:8200"
