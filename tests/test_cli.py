"""Tests for CLI commands and export functionality."""

import json
import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from idleframework.cli import app
from idleframework.export import to_xml, to_yaml
from idleframework.model.game import GameDefinition

runner = CliRunner()

FIXTURE_PATH = str(Path(__file__).parent / "fixtures" / "minicap.json")


def test_validate_command():
    result = runner.invoke(app, ["validate", FIXTURE_PATH])
    assert result.exit_code == 0
    assert "valid" in result.stdout.lower() or "MiniCap" in result.stdout


def test_validate_invalid_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('{"not": "a valid game"}')
        bad_path = f.name
    try:
        result = runner.invoke(app, ["validate", bad_path])
        assert result.exit_code != 0
        assert "error" in result.stdout.lower() or "validation" in result.stdout.lower()
    finally:
        os.unlink(bad_path)


def test_analyze_command():
    result = runner.invoke(app, ["analyze", FIXTURE_PATH])
    assert result.exit_code == 0
    assert "MiniCap" in result.stdout


def test_report_command():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "test_report.html")
        result = runner.invoke(app, ["report", FIXTURE_PATH, "--output", out_path])
        assert result.exit_code == 0
        assert os.path.exists(out_path)
        content = Path(out_path).read_text()
        assert "<html" in content.lower()
        assert "MiniCap" in content


def test_compare_command():
    result = runner.invoke(app, ["compare", FIXTURE_PATH, "--strategies", "free,paid"])
    assert result.exit_code == 0
    assert "free" in result.stdout.lower()
    assert "paid" in result.stdout.lower()


def test_export_yaml():
    result = runner.invoke(app, ["export", FIXTURE_PATH, "--format", "yaml"])
    assert result.exit_code == 0
    assert "name:" in result.stdout
    assert "MiniCap" in result.stdout


def test_export_xml():
    result = runner.invoke(app, ["export", FIXTURE_PATH, "--format", "xml"])
    assert result.exit_code == 0
    assert "<" in result.stdout
    assert "MiniCap" in result.stdout


def test_invalid_file_error_message():
    result = runner.invoke(app, ["validate", "/nonexistent/path/game.json"])
    assert result.exit_code != 0
    assert "not found" in result.stdout.lower() or "error" in result.stdout.lower()


@pytest.fixture
def minicap_game() -> GameDefinition:
    data = json.loads(Path(FIXTURE_PATH).read_text())
    return GameDefinition(**data)


def test_to_yaml_produces_valid_output(minicap_game):
    result = to_yaml(minicap_game)
    assert isinstance(result, str)
    assert "name:" in result
    assert "MiniCap" in result
    assert "schema_version:" in result


def test_to_xml_produces_valid_output(minicap_game):
    result = to_xml(minicap_game)
    assert isinstance(result, str)
    assert "<?xml" in result or "<GameDefinition" in result
    assert "MiniCap" in result
