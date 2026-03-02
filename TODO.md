# TODO — teLLMe

## v0.1.0 (current)

- [x] Docker Compose with all 7 services
- [x] Gateway API (FastAPI orchestrator)
- [x] CLI entry point (tellme)
- [x] HTTP wrappers for code2llm and stts
- [x] LiteLLM config with Ollama routing
- [x] Makefile, README, CHANGELOG, badges
- [ ] Integration tests with docker compose
- [ ] CI/CD pipeline (GitHub Actions)

## v0.2.0 (planned)

- [ ] Web UI dashboard (React/Svelte) showing all service status
- [ ] WebSocket streaming for real-time monitoring events
- [ ] Voice command mode (stts → nlp2cmd → execute pipeline)
- [ ] File upload/download through gateway
- [ ] Authentication & API keys for gateway

## v0.3.0 (future)

- [ ] Multi-workspace support
- [ ] Plugin system for custom services
- [ ] Event-driven automation (toonic triggers → nlp2cmd actions)
- [ ] RTSP camera integration via toonic
- [ ] Mobile-friendly responsive UI
- [ ] Prometheus metrics & Grafana dashboard

## Ideas / Backlog

- [ ] Voice-activated code review pipeline (stts → code2llm → TTS summary)
- [ ] Natural language file management ("move all PDFs to ~/Documents")
- [ ] Scheduled code analysis reports
- [ ] Slack/Discord bot integration
- [ ] Local RAG over workspace documents
