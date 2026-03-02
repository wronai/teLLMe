# Changelog

All notable changes to teLLMe will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] — 2026-03-02

### Added
- **Docker Compose** orchestration of 7 services: ollama, litellm, nlp2cmd, toonic, code2llm, stts, gateway
- **Gateway API** (FastAPI) — unified REST endpoint on port 9000
  - `/command` — natural language → command translation (via nlp2cmd)
  - `/analyze` — code analysis (via code2llm)
  - `/monitor/*` — file/media monitoring (via toonic)
  - `/chat` — LLM chat completion (via litellm → ollama)
  - `/models` — list available LLM models
  - `/files` — workspace file browser
  - `/status` — platform-wide health check
- **CLI** (`tellme`) — platform management commands: up, down, status, logs, command, analyze
- **HTTP API wrappers** for code2llm and stts (both are CLI-first tools)
- **LiteLLM config** routing to local Ollama with optional cloud fallback
- **Makefile** with prepare/build/up/down/test/clean targets
- **Shared workspace** volume mounted across all services
- Project scaffold: README with badges, CHANGELOG, TODO, VERSION, LICENSE, pyproject.toml
