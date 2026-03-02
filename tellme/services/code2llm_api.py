"""
code2llm HTTP API wrapper — exposes code analysis as a REST service.

Wraps the code2llm CLI tool into a lightweight FastAPI server.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logger = logging.getLogger("tellme.code2llm")

app = FastAPI(title="code2llm API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    path: str = Field(..., description="Path to analyze")
    format: str = Field(default="toon", description="Output format: toon, context, yaml, json, map, flow")


class AnalyzeResponse(BaseModel):
    success: bool
    path: str
    format: str
    output: Optional[str] = None
    error: Optional[str] = None


@app.get("/health")
async def health():
    # Check if code2llm is importable
    try:
        import code2llm  # noqa: F401
        return {"status": "healthy", "service": "code2llm", "code2llm": "available"}
    except ImportError:
        return {"status": "healthy", "service": "code2llm", "code2llm": "cli-only"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    """Run code2llm analysis on the given path."""
    target = Path(req.path)
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {req.path}")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = [
                "code2llm", str(target),
                "-f", req.format,
                "-o", tmpdir,
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(target) if target.is_dir() else str(target.parent),
            )

            # Collect output files
            output_parts = []
            out_dir = Path(tmpdir)
            for f in sorted(out_dir.rglob("*")):
                if f.is_file() and f.stat().st_size > 0:
                    try:
                        content = f.read_text(encoding="utf-8", errors="replace")
                        output_parts.append(f"# {f.name}\n{content}")
                    except Exception:
                        pass

            output = "\n\n".join(output_parts) if output_parts else result.stdout

            if result.returncode != 0 and not output:
                return AnalyzeResponse(
                    success=False,
                    path=req.path,
                    format=req.format,
                    error=result.stderr or f"code2llm exited with code {result.returncode}",
                )

            return AnalyzeResponse(
                success=True,
                path=req.path,
                format=req.format,
                output=output,
            )

    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="code2llm CLI not found. Install with: pip install code2llm",
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Analysis timed out (120s)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/formats")
async def list_formats():
    """List available output formats."""
    return {
        "formats": [
            {"name": "toon", "description": "TOON diagnostics — health, complexity, hotspots"},
            {"name": "context", "description": "LLM narrative — architecture summary, flows, API surface"},
            {"name": "map", "description": "Module structure map"},
            {"name": "flow", "description": "Data flow analysis"},
            {"name": "yaml", "description": "Full YAML export"},
            {"name": "json", "description": "Full JSON export"},
            {"name": "evolution", "description": "Refactoring queue — ranked by impact/effort"},
        ]
    }


if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    port = int(os.getenv("CODE2LLM_PORT", "8100"))
    logger.info(f"Starting code2llm API on :{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
