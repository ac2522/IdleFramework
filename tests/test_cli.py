"""Tests for CLI commands and export functionality.

Tests cover:
- validate: JSON loading + Pydantic validation
- analyze: full analysis with output
- report: HTML report generation
- compare: strategy comparison (free vs paid)
- export: YAML and XML serialization
- Error handling for missing/invalid files
"""
import json
import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from idleframework.cli import app
from idleframework.export import to_yaml, to_xml
from idleframework.model.game import GameDefinition

runner = CliRunner()

FIXTURE_PATH = str(Path(__file__).parent / "fixtures" / "minicap.json")


# ── validate ──────────────────────────────────────────────────────────


def test_validate_command():
    """idleframework validate <path> exits 0 for valid JSON."""
    result = runner.invoke(app, ["validate", FIXTURE_PATH])
    assert result.exit_code == 0
    assert "valid" in result.stdout.lower() or "MiniCap" in result.stdout


def test_validate_invalid_file():
    """Exits non-zero with error message for bad file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('{"not": "a valid game"}')
        bad_path = f.name
    try:
        result = runner.invoke(app, ["validate", bad_path])
        assert result.exit_code != 0
        assert "error" in result.stdout.lower() or "validation" in result.stdout.lower()
    finally:
        os.unlink(bad_path)


# ── analyze ───────────────────────────────────────────────────────────


def test_analyze_command():
    """idleframework analyze <path> produces output with game name."""
    result = runner.invoke(app, ["analyze", FIXTURE_PATH])
    assert result.exit_code == 0
    assert "MiniCap" in result.stdout


# ── report ────────────────────────────────────────────────────────────


def test_report_command():
    """idleframework report <path> --output <file> creates HTML file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "test_report.html")
        result = runner.invoke(app, ["report", FIXTURE_PATH, "--output", out_path])
        assert result.exit_code == 0
        assert os.path.exists(out_path)
        content = Path(out_path).read_text()
        assert "<html" in content.lower()
        assert "MiniCap" in content


# ── compare ───────────────────────────────────────────────────────────


def test_compare_command():
    """idleframework compare <path> --strategies free,paid runs analysis."""
    result = runner.invoke(app, ["compare", FIXTURE_PATH, "--strategies", "free,paid"])
    assert result.exit_code == 0
    # Should mention both strategies
    assert "free" in result.stdout.lower()
    assert "paid" in result.stdout.lower()


# ── export ────────────────────────────────────────────────────────────


def test_export_yaml():
    """idleframework export <path> --format yaml produces YAML output."""
    result = runner.invoke(app, ["export", FIXTURE_PATH, "--format", "yaml"])
    assert result.exit_code == 0
    # YAML should contain the game name as a key-value
    assert "name:" in result.stdout
    assert "MiniCap" in result.stdout


def test_export_xml():
    """idleframework export <path> --format xml produces XML output."""
    result = runner.invoke(app, ["export", FIXTURE_PATH, "--format", "xml"])
    assert result.exit_code == 0
    assert "<" in result.stdout
    assert "MiniCap" in result.stdout


# ── error handling ────────────────────────────────────────────────────


def test_invalid_file_error_message():
    """Clear error for nonexistent file."""
    result = runner.invoke(app, ["validate", "/nonexistent/path/game.json"])
    assert result.exit_code != 0
    assert "not found" in result.stdout.lower() or "error" in result.stdout.lower()


# ── export module unit tests ──────────────────────────────────────────


@pytest.fixture
def minicap_game() -> GameDefinition:
    data = json.loads(Path(FIXTURE_PATH).read_text())
    return GameDefinition(**data)


def test_to_yaml_produces_valid_output(minicap_game):
    """to_yaml returns string containing game fields."""
    result = to_yaml(minicap_game)
    assert isinstance(result, str)
    assert "name:" in result
    assert "MiniCap" in result
    assert "schema_version:" in result


def test_to_xml_produces_valid_output(minicap_game):
    """to_xml returns well-formed XML string."""
    result = to_xml(minicap_game)
    assert isinstance(result, str)
    assert "<?xml" in result or "<GameDefinition" in result
    assert "MiniCap" in result
