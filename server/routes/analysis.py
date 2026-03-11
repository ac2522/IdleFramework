"""Analysis endpoints -- run, compare, report."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from idleframework.analysis.detectors import run_full_analysis
from idleframework.model.game import GameDefinition
from idleframework.reports.html import generate_report
from server.game_store import game_store
from server.schemas import AnalysisRequest, CompareRequest, ReportRequest, ErrorResponse

router = APIRouter()


def _get_game_or_404(game_id: str) -> GameDefinition:
    game = game_store.get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail=ErrorResponse(
            error="game_not_found",
            detail=f"No game with ID '{game_id}' exists",
            status=404,
        ).model_dump())
    return game


@router.post("/run")
def run_analysis(req: AnalysisRequest):
    game = _get_game_or_404(req.game_id)
    report = run_full_analysis(game, simulation_time=req.simulation_time)
    # Serialize dataclass to dict
    result = {
        "game_name": report.game_name,
        "simulation_time": report.simulation_time,
        "dead_upgrades": report.dead_upgrades,
        "progression_walls": report.progression_walls,
        "dominant_strategy": report.dominant_strategy,
        "sensitivity": report.sensitivity,
        "optimizer_result": None,
    }
    if report.optimizer_result:
        opt = report.optimizer_result
        result["optimizer_result"] = {
            "purchases": [
                {"time": p.time, "node_id": p.node_id, "count": p.count, "cost": p.cost}
                for p in opt.purchases
            ],
            "timeline": opt.timeline,
            "final_production": opt.final_production,
            "final_balance": opt.final_balance,
            "final_time": opt.final_time,
        }
    return result


@router.post("/compare")
def compare_strategies(req: CompareRequest):
    game = _get_game_or_404(req.game_id)
    baseline = run_full_analysis(game, simulation_time=req.simulation_time)
    baseline_prod = baseline.optimizer_result.final_production if baseline.optimizer_result else 0

    variants = {}
    for tag in req.strategies:
        # Filter out upgrade nodes tagged with this tag
        filtered_nodes = []
        excluded_ids = set()
        for node in game.nodes:
            if hasattr(node, "tags") and tag in node.tags and getattr(node, "type", "") == "upgrade":
                excluded_ids.add(node.id)
            else:
                filtered_nodes.append(node)

        # Also need to remove stacking group references if they become unused
        variant_game = GameDefinition(
            schema_version=game.schema_version,
            name=f"{game.name}_no_{tag}",
            nodes=filtered_nodes,
            edges=[e for e in game.edges if e.source not in excluded_ids and e.target not in excluded_ids],
            stacking_groups=game.stacking_groups,
        )
        variant_report = run_full_analysis(variant_game, simulation_time=req.simulation_time)
        variant_prod = variant_report.optimizer_result.final_production if variant_report.optimizer_result else 0
        ratio = baseline_prod / variant_prod if variant_prod > 0 else float("inf")
        variants[tag] = {
            "final_production": variant_prod,
            "ratio_vs_baseline": ratio,
        }

    return {
        "baseline": {"final_production": baseline_prod},
        "variants": variants,
    }


@router.post("/report")
def generate_html_report(req: ReportRequest):
    game = _get_game_or_404(req.game_id)
    report = run_full_analysis(game, simulation_time=req.simulation_time)
    html = generate_report(report, use_cdn=req.use_cdn)
    return HTMLResponse(content=html)
