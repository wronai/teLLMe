# teLLMe

[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](VERSION)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-yellow.svg)](pyproject.toml)
[![Docker](https://img.shields.io/badge/docker-compose-2496ED.svg)](docker-compose.yml)
[![Services](https://img.shields.io/badge/services-7-purple.svg)](#architecture)

**Unified voice+LLM platform for local code, media, and service control** — powered by the [wronai](https://github.com/wronai) ecosystem.

> Talk to your local environment. Monitor files. Analyze code. Execute commands. All through natural language.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    teLLMe Gateway :9000                  │
│              (FastAPI orchestrator / REST API)           │
├──────────┬──────────┬──────────┬──────────┬──────────────┤
│  stts    │ nlp2cmd  │  toonic  │ code2llm │   litellm    │
│  :8200   │  :8000   │  :8900   │  :8100   │    :4000     │
│ Voice IO │ NL→Cmd   │ Monitor  │ Analysis │  LLM Proxy   │
└──────────┴──────────┴──────────┴──────────┴──────┬───────┘
                                                   │
                                            ┌──────┴───────┐
                                            │    ollama    │
                                            │    :11434    │
                                            │  Local LLM   │
                                            └──────────────┘
```

| Service | Port | Description | Repo |
|---------|------|-------------|------|
| **gateway** | 9000 | Orchestrator API — unified endpoint for all services | this repo |
| **ollama** | 11434 | Local LLM inference (qwen2.5-coder, etc.) | [ollama/ollama](https://github.com/ollama/ollama) |
| **litellm** | 4000 | LLM proxy/router — local + cloud fallback | [BerriAI/litellm](https://github.com/BerriAI/litellm) |
| **nlp2cmd** | 8000 | Natural language → shell/SQL/Docker commands | [wronai/nlp2cmd](https://github.com/wronai/nlp2cmd) |
| **toonic** | 8900 | File/media/stream monitoring with LLM analysis | [wronai/toonic](https://github.com/wronai/toonic) |
| **code2llm** | 8100 | Static code analysis (complexity, flows, refactoring) | [wronai/code2llm](https://github.com/wronai/code2llm) |
| **stts** | 8200 | Speech-to-Text / Text-to-Speech (Vosk, Whisper, Piper) | [wronai/stts](https://github.com/wronai/stts) |

## Quick Start

```bash
# 1. Clone
git clone https://github.com/wronai/teLLMe.git
cd teLLMe

# 2. Ensure sibling repos exist
ls ../nlp2cmd ../code2llm ../toonic ../stts

# 3. Configure
cp .env.example .env
# Edit .env — add API keys if using cloud LLMs

# 4. Start everything
make up-d

# 5. Check health
make status
# or: curl http://localhost:9000/status
```

## Usage

### CLI

```bash
# Platform management
tellme up -d --build       # Start all services
tellme status              # Check health
tellme logs -f             # Tail logs
tellme down                # Stop everything

# Natural language commands
tellme command "list all Python files larger than 1MB"
tellme command -x "find cameras on local network"
tellme command -e "show disk usage"

# Code analysis
tellme analyze /workspace/myproject -f toon
tellme analyze /workspace/myproject -f context
```

### REST API (Gateway :9000)

```bash
# Health & status
curl http://localhost:9000/health
curl http://localhost:9000/status

# Generate command from natural language
curl -X POST http://localhost:9000/command \
  -H 'Content-Type: application/json' \
  -d '{"query": "find large log files", "explain": true}'

# Analyze code
curl -X POST http://localhost:9000/analyze \
  -H 'Content-Type: application/json' \
  -d '{"path": "/workspace/myproject", "format": "toon"}'

# Monitor files
curl http://localhost:9000/monitor/status
curl http://localhost:9000/monitor/events?limit=20

# Chat with LLM
curl -X POST http://localhost:9000/chat \
  -H 'Content-Type: application/json' \
  -d '{"model": "default", "messages": [{"role": "user", "content": "hello"}]}'

# List LLM models
curl http://localhost:9000/models

# Browse workspace
curl http://localhost:9000/files?path=/workspace
```

## Development

```bash
# Install locally
pip install -e ".[dev]"

# Run tests
make test

# Run gateway standalone (without Docker)
python -m tellme.gateway
```

## Configuration

All config is via environment variables (`.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MODEL` | `qwen2.5-coder:7b` | Default model to pull |
| `LITELLM_MODEL` | `ollama/qwen2.5-coder:7b` | Default model for LLM calls |
| `GATEWAY_PORT` | `9000` | Gateway listen port |
| `NLP2CMD_PORT` | `8000` | NLP2CMD service port |
| `TOONIC_PORT` | `8900` | Toonic monitoring port |
| `WORKSPACE_DIR` | `./workspace` | Shared workspace mount |
| `OPENROUTER_API_KEY` | *(empty)* | For cloud LLM fallback |

## Project Structure

```
teLLMe/
├── docker-compose.yml       # All 7 services
├── litellm-config.yaml      # LLM proxy routing
├── docker/
│   ├── Dockerfile.gateway   # Gateway image
│   ├── Dockerfile.code2llm  # code2llm API wrapper
│   └── Dockerfile.stts      # stts API wrapper
├── tellme/
│   ├── gateway.py           # FastAPI orchestrator
│   ├── cli.py               # CLI entry point
│   └── services/
│       ├── code2llm_api.py  # code2llm HTTP wrapper
│       └── stts_api.py      # stts HTTP wrapper
├── tests/
│   ├── test_gateway.py
│   └── test_cli.py
├── Makefile                 # Build/run/test commands
├── README.md
├── CHANGELOG.md
├── TODO.md
└── pyproject.toml
```

## License

[Apache License 2.0](LICENSE)

## Related Projects

- **[nlp2cmd](https://github.com/wronai/nlp2cmd)** — NLP to domain-specific commands
- **[code2llm](https://github.com/wronai/code2llm)** — Code flow analysis for LLMs
- **[toonic](https://github.com/wronai/toonic)** — Universal TOON format platform
- **[stts](https://github.com/wronai/stts)** — Universal Voice Shell