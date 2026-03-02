"""
teLLMe CLI — manage the platform from the command line.

Usage:
  tellme up         — start all services (docker compose up)
  tellme down       — stop all services
  tellme status     — check service health
  tellme logs       — tail logs from all services
  tellme command    — send a natural language command
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent


def _compose(*args, **kwargs):
    """Run docker compose with project context."""
    cmd = ["docker", "compose", "-f", str(PROJECT_DIR / "docker-compose.yml")]
    cmd.extend(args)
    return subprocess.run(cmd, cwd=str(PROJECT_DIR), **kwargs)


def cmd_up(args):
    """Start all services."""
    extra = []
    if args.build:
        extra.append("--build")
    if args.detach:
        extra.append("-d")
    _compose("up", *extra)


def cmd_down(args):
    """Stop all services."""
    _compose("down")


def cmd_status(args):
    """Check health of all services."""
    import urllib.request
    gateway_url = os.getenv("GATEWAY_URL", "http://localhost:9000")
    try:
        req = urllib.request.Request(f"{gateway_url}/status")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            print(f"teLLMe v{data.get('version', '?')}  |  uptime: {data.get('uptime_s', 0)}s")
            print(f"Services: {data.get('services_healthy', '?')}")
            print()
            for svc in data.get("services", []):
                icon = "✓" if svc["healthy"] else "✗"
                lat = f"{svc['latency_ms']}ms" if svc.get("latency_ms") else svc.get("error", "")
                print(f"  {icon} {svc['name']:12s} {svc['url']:40s} {lat}")
    except Exception as e:
        print(f"Gateway unreachable ({gateway_url}): {e}")
        print("Try: tellme up -d --build")
        return 1
    return 0


def cmd_logs(args):
    """Tail logs from services."""
    extra = []
    if args.follow:
        extra.append("-f")
    if args.service:
        extra.append(args.service)
    _compose("logs", "--tail", str(args.tail), *extra)


def cmd_command(args):
    """Send a natural language command to nlp2cmd via gateway."""
    import urllib.request
    gateway_url = os.getenv("GATEWAY_URL", "http://localhost:9000")
    payload = json.dumps({
        "query": " ".join(args.query),
        "execute": args.execute,
        "explain": args.explain,
    }).encode()

    try:
        req = urllib.request.Request(
            f"{gateway_url}/command",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            if data.get("success"):
                print(f"Command:    {data.get('command', '')}")
                if data.get("explanation"):
                    print(f"Explain:    {data['explanation']}")
                if data.get("confidence"):
                    print(f"Confidence: {data['confidence']:.0%}")
                if data.get("execution_result"):
                    er = data["execution_result"]
                    print(f"\nExecution:  {'OK' if er.get('success') else 'FAIL'}")
                    if er.get("stdout"):
                        print(er["stdout"])
            else:
                print(f"Error: {data}")
    except Exception as e:
        print(f"Failed: {e}")
        return 1
    return 0


def cmd_analyze(args):
    """Analyze code via code2llm service."""
    import urllib.request
    gateway_url = os.getenv("GATEWAY_URL", "http://localhost:9000")
    payload = json.dumps({
        "path": args.path,
        "format": args.format,
    }).encode()

    try:
        req = urllib.request.Request(
            f"{gateway_url}/analyze",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
            if data.get("success"):
                print(data.get("output", ""))
            else:
                print(f"Error: {data.get('error', data)}")
    except Exception as e:
        print(f"Failed: {e}")
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="tellme",
        description="teLLMe — Unified voice+LLM platform for local service control",
    )
    sub = parser.add_subparsers(dest="cmd")

    # up
    p_up = sub.add_parser("up", help="Start all services")
    p_up.add_argument("--build", action="store_true", help="Rebuild images")
    p_up.add_argument("-d", "--detach", action="store_true", help="Run in background")
    p_up.set_defaults(func=cmd_up)

    # down
    p_down = sub.add_parser("down", help="Stop all services")
    p_down.set_defaults(func=cmd_down)

    # status
    p_status = sub.add_parser("status", help="Check service health")
    p_status.set_defaults(func=cmd_status)

    # logs
    p_logs = sub.add_parser("logs", help="Tail service logs")
    p_logs.add_argument("-f", "--follow", action="store_true")
    p_logs.add_argument("--tail", type=int, default=100)
    p_logs.add_argument("service", nargs="?", help="Specific service name")
    p_logs.set_defaults(func=cmd_logs)

    # command
    p_cmd = sub.add_parser("command", aliases=["cmd"], help="Send NL command")
    p_cmd.add_argument("query", nargs="+", help="Natural language query")
    p_cmd.add_argument("--execute", "-x", action="store_true", help="Execute the command")
    p_cmd.add_argument("--explain", "-e", action="store_true", help="Include explanation")
    p_cmd.set_defaults(func=cmd_command)

    # analyze
    p_analyze = sub.add_parser("analyze", help="Analyze code")
    p_analyze.add_argument("path", help="Path to analyze")
    p_analyze.add_argument("-f", "--format", default="toon", help="Output format")
    p_analyze.set_defaults(func=cmd_analyze)

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        return 0

    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
