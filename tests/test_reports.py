"""Tests for the HTML report generator (Plotly)."""
import json
from pathlib import Path

import pytest

from idleframework.analysis.detectors import AnalysisReport, run_full_analysis
from idleframework.engine.events import PurchaseEvent
from idleframework.model.game import GameDefinition
from idleframework.optimizer.greedy import OptimizeResult
from idleframework.reports.html import generate_report


@pytest.fixture
def minicap_game() -> GameDefinition:
    fixture_path = Path(__file__).parent / "fixtures" / "minicap.json"
    with open(fixture_path) as f:
        data = json.load(f)
    return GameDefinition.model_validate(data)


@pytest.fixture
def sample_optimizer_result() -> OptimizeResult:
    return OptimizeResult(
        purchases=[
            PurchaseEvent(time=0.0, node_id="lemonade", count=1, cost=4.0),
            PurchaseEvent(time=2.5, node_id="lemonade", count=1, cost=4.28),
            PurchaseEvent(time=5.0, node_id="newspaper", count=1, cost=60.0),
            PurchaseEvent(time=15.0, node_id="x3_lemon", count=1, cost=1000.0),
            PurchaseEvent(time=30.0, node_id="carwash", count=1, cost=720.0),
        ],
        timeline=[
            {"time": 0.0, "production_rate": 1.0},
            {"time": 2.5, "production_rate": 2.0},
            {"time": 5.0, "production_rate": 22.0},
            {"time": 15.0, "production_rate": 26.0},
            {"time": 30.0, "production_rate": 146.0},
        ],
        final_production=146.0,
        final_balance=5000.0,
        final_time=300.0,
    )


@pytest.fixture
def sample_analysis_report(sample_optimizer_result) -> AnalysisReport:
    return AnalysisReport(
        game_name="MiniCap",
        simulation_time=300.0,
        dead_upgrades=[],
        progression_walls=[],
        dominant_strategy={"dominant_gen": None, "ratio": 1.2, "productions": {}},
        optimizer_result=sample_optimizer_result,
    )


class TestGeneratesHtmlFile:
    def test_generates_html_file(self, sample_analysis_report):
        html = generate_report(sample_analysis_report)
        assert isinstance(html, str)
        assert "<html" in html.lower()
        assert "plotly" in html.lower()

    def test_html_has_closing_tags(self, sample_analysis_report):
        html = generate_report(sample_analysis_report)
        assert "</html>" in html.lower()
        assert "</body>" in html.lower()


class TestProductionCurves:
    def test_production_curves(self, sample_analysis_report):
        html = generate_report(sample_analysis_report)
        assert "Production" in html
        assert "Time" in html or "time" in html

    def test_generator_names_in_chart(self, sample_analysis_report):
        html = generate_report(sample_analysis_report)
        lower = html.lower()
        assert "lemonade" in lower or "newspaper" in lower or "carwash" in lower


class TestCdnOption:
    def test_cdn_option(self, sample_analysis_report):
        html = generate_report(sample_analysis_report, use_cdn=True)
        assert "cdn.plot.ly" in html

    def test_cdn_is_default(self, sample_analysis_report):
        html = generate_report(sample_analysis_report)
        assert "cdn.plot.ly" in html


class TestInlineOption:
    def test_inline_option(self, sample_analysis_report):
        html = generate_report(sample_analysis_report, use_cdn=False)
        assert 'src="https://cdn.plot.ly' not in html
        cdn_html = generate_report(sample_analysis_report, use_cdn=True)
        assert len(html) > len(cdn_html)


class TestApproximationLevelShown:
    def test_approximation_level_shown(self, sample_analysis_report):
        html = generate_report(sample_analysis_report)
        html_lower = html.lower()
        assert "greedy" in html_lower or "approximation" in html_lower


class TestReportFromAnalysis:
    def test_report_from_analysis(self, minicap_game):
        report = run_full_analysis(minicap_game, simulation_time=60.0)
        html = generate_report(report)
        assert isinstance(html, str)
        assert "<html" in html.lower()
        assert "MiniCap" in html

    def test_custom_title(self, sample_analysis_report):
        html = generate_report(sample_analysis_report, title="Custom Report Title")
        assert "Custom Report Title" in html

    def test_game_name_in_report(self, sample_analysis_report):
        html = generate_report(sample_analysis_report)
        assert "MiniCap" in html
