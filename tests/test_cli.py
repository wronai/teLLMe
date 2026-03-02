"""Tests for teLLMe CLI."""

import subprocess
import sys
from pathlib import Path


def test_cli_help():
    """CLI --help should exit 0."""
    result = subprocess.run(
        [sys.executable, "-m", "tellme.cli", "--help"],
        capture_output=True, text=True,
        cwd=str(Path(__file__).parent.parent),
    )
    assert result.returncode == 0
    assert "teLLMe" in result.stdout


def test_cli_no_args():
    """CLI with no args should print help and exit 0."""
    result = subprocess.run(
        [sys.executable, "-m", "tellme.cli"],
        capture_output=True, text=True,
        cwd=str(Path(__file__).parent.parent),
    )
    assert result.returncode == 0
