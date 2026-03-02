"""
teLLMe Gateway — FastAPI orchestrator connecting all wronai services.

Services:
  - ollama    (LLM inference)
  - litellm   (LLM proxy)
  - nlp2cmd   (NLP → commands)
  - toonic    (file/media monitoring)
  - code2llm  (code analysis)
  - stts      (voice I/O)
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logger = logging.getLogger("tellme.gateway")

# ── Service URLs (from env) ─────────────────────────────────────────────────

SERVICES = {
    "ollama":  os.getenv("OLLAMA_URL",  "http://localhost:11434"),
    "litellm": os.getenv("LITELLM_URL", "http://localhost:4000"),
    "nlp2cmd": os.getenv("NLP2CMD_URL", "http://localhost:8000"),
    "toonic":  os.getenv("TOONIC_URL",  "http://localhost:8900"),
    "code2llm": os.getenv("CODE2LLM_URL", "http://localhost:8100"),
    "stts":    os.getenv("STTS_URL",    "http://localhost:8200"),
}

_START_TIME = time.time()


# ── Models ──────────────────────────────────────────────────────────────────

class CommandRequest(BaseModel):
    query: str = Field(..., description="Natural language query (Polish or English)")
    execute: bool = Field(default=False, description="Execute the generated command")
    explain: bool = Field(default=False, description="Include explanation")


class CommandResponse(BaseModel):
    success: bool
    command: Optional[str] = None
    explanation: Optional[str] = None
    confidence: Optional[float] = None
    domain: Optional[str] = None
    execution_result: Optional[Dict[str, Any]] = None


class AnalyzeRequest(BaseModel):
    path: str = Field(..., description="Path to analyze (inside /workspace)")
    format: str = Field(default="toon", description="Output format: toon, context, yaml, json")


class MonitorRequest(BaseModel):
    path: str = Field(..., description="Path or URL to monitor")
    goal: str = Field(default="", description="Monitoring goal description")
    interval: int = Field(default=60, description="Check interval in seconds")


class ServiceStatus(BaseModel):
    name: str
    url: str
    healthy: bool
    latency_ms: Optional[float] = None
    error: Optional[str] = None


# ── Lifespan ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("teLLMe Gateway starting — checking services...")
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, url in SERVICES.items():
            try:
                health_url = f"{url}/health" if name != "ollama" else f"{url}/api/tags"
                if name == "toonic":
                    health_url = f"{url}/api/status"
                resp = await client.get(health_url)
                status = "✓" if resp.status_code == 200 else f"⚠ {resp.status_code}"
            except Exception as e:
                status = f"✗ {e}"
            logger.info(f"  {name:10s} {url:40s} {status}")
    yield
    logger.info("teLLMe Gateway shutting down")


# ── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="teLLMe Gateway",
    description="Unified API for voice+LLM local service control",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health & Status ─────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "tellme-gateway"}


@app.get("/status")
async def status():
    """Full platform status with service health checks."""
    results: List[ServiceStatus] = []
    async with httpx.AsyncClient(timeout=3.0) as client:
        for name, url in SERVICES.items():
            t0 = time.time()
            try:
                health_url = f"{url}/health"
                if name == "ollama":
                    health_url = f"{url}/api/tags"
                elif name == "toonic":
                    health_url = f"{url}/api/status"
                resp = await client.get(health_url)
                latency = round((time.time() - t0) * 1000, 1)
                results.append(ServiceStatus(
                    name=name, url=url,
                    healthy=resp.status_code == 200,
                    latency_ms=latency,
                ))
            except Exception as e:
                results.append(ServiceStatus(
                    name=name, url=url, healthy=False,
                    error=str(e),
                ))

    healthy_count = sum(1 for r in results if r.healthy)
    return {
        "platform": "teLLMe",
        "version": "0.1.0",
        "uptime_s": round(time.time() - _START_TIME, 1),
        "services_healthy": f"{healthy_count}/{len(results)}",
        "services": [r.model_dump() for r in results],
    }


# ── Command Generation (nlp2cmd proxy) ─────────────────────────────────────

@app.post("/command", response_model=CommandResponse)
async def generate_command(req: CommandRequest):
    """Translate natural language to a shell/SQL/Docker command via nlp2cmd."""
    url = f"{SERVICES['nlp2cmd']}/query"
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(url, json={
                "query": req.query,
                "execute": req.execute,
                "explain": req.explain,
            })
            resp.raise_for_status()
            return CommandResponse(**resp.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"nlp2cmd unreachable: {e}")


# ── Code Analysis (code2llm proxy) ─────────────────────────────────────────

@app.post("/analyze")
async def analyze_code(req: AnalyzeRequest):
    """Analyze code at the given path using code2llm."""
    url = f"{SERVICES['code2llm']}/analyze"
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            resp = await client.post(url, json={
                "path": req.path,
                "format": req.format,
            })
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"code2llm unreachable: {e}")


# ── Monitoring (toonic proxy) ──────────────────────────────────────────────

@app.get("/monitor/status")
async def monitor_status():
    """Get current monitoring status from toonic."""
    url = f"{SERVICES['toonic']}/api/status"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"toonic unreachable: {e}")


@app.post("/monitor/source")
async def add_monitor_source(req: MonitorRequest):
    """Add a new source to monitor via toonic."""
    url = f"{SERVICES['toonic']}/api/sources/"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(url, json={
                "path_or_url": req.path,
                "category": "code",
            })
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"toonic unreachable: {e}")


@app.get("/monitor/events")
async def monitor_events(limit: int = 50):
    """Get recent monitoring events from toonic."""
    url = f"{SERVICES['toonic']}/api/events?limit={limit}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"toonic unreachable: {e}")


# ── LLM Chat (litellm proxy) ──────────────────────────────────────────────

@app.post("/chat")
async def chat(body: Dict[str, Any]):
    """Proxy chat completion to litellm (OpenAI-compatible)."""
    url = f"{SERVICES['litellm']}/chat/completions"
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            if "model" not in body:
                body["model"] = "default"
            resp = await client.post(url, json=body)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"litellm unreachable: {e}")


# ── LLM Models ────────────────────────────────────────────────────────────

@app.get("/models")
async def list_models():
    """List available LLM models from ollama."""
    url = f"{SERVICES['ollama']}/api/tags"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return {
                "models": [
                    {"name": m["name"], "size_gb": round(m.get("size", 0) / 1e9, 2)}
                    for m in data.get("models", [])
                ]
            }
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"ollama unreachable: {e}")


# ── Workspace File Listing ─────────────────────────────────────────────────

@app.get("/files")
async def list_workspace_files(path: str = "/workspace", depth: int = 2):
    """List files in the mounted workspace."""
    import pathlib
    base = pathlib.Path(path)
    if not base.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {path}")

    files = []
    for p in sorted(base.rglob("*")):
        rel = p.relative_to(base)
        if len(rel.parts) > depth:
            continue
        if any(part.startswith(".") for part in rel.parts):
            continue
        files.append({
            "path": str(rel),
            "type": "dir" if p.is_dir() else "file",
            "size": p.stat().st_size if p.is_file() else None,
        })

    return {"base": str(base), "count": len(files), "files": files[:500]}


# ── Run ─────────────────────────────────────────────────────────────────────

def main():
    import uvicorn
    port = int(os.getenv("GATEWAY_PORT", "9000"))
    log_level = os.getenv("GATEWAY_LOG_LEVEL", "info")
    logging.basicConfig(level=getattr(logging, log_level.upper(), logging.INFO))
    logger.info(f"Starting teLLMe Gateway on :{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level=log_level)


if __name__ == "__main__":
    main()
