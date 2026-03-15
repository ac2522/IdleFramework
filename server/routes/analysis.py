"""Analysis endpoints -- run, compare, report."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from idleframework.analysis.detectors import run_full_analysis
from idleframework.model.game import GameDefinition
from idleframework.reports.html import generate_report
from server.game_store import game_store
from server.schemas import (
    AnalysisRequest,
    CompareRequest,
    ErrorResponse,
    ReportRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class PurchaseEntry(BaseModel):
    time: float
    node_id: str
    count: int
    cost: float


class OptimizerResultResponse(BaseModel):
    purchases: list[PurchaseEntry]
    timeline: list[dict[str, Any]]
    final_production: float
    final_balance: float
    final_time: float


class AnalysisResponse(BaseModel):
    game_name: str
    simulation_time: float
    dead_upgrades: list[Any] = Field(default_factory=list)
    progression_walls: list[Any] = Field(default_factory=list)
    dominant_strategy: dict[str, Any] | None = None
    sensitivity: list[Any] = Field(default_factory=list)
    optimizer_result: OptimizerResultResponse | None = None


class VariantResult(BaseModel):
    final_production: float
    ratio_vs_baseline: float


class CompareResponse(BaseModel):
    baseline: dict[str, Any]
    variants: dict[str, VariantResult]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_game_or_404(game_id: str) -> GameDefinition:
    game = game_store.get_game(game_id)
    if game is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="game_not_found",
                detail=f"No game with ID '{game_id}' exists",
                status=404,
            ).model_dump(),
        )
    return game


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/run", response_model=AnalysisResponse)
def run_analysis(req: AnalysisRequest):
    """Run full analysis on a game definition."""
    game = _get_game_or_404(req.game_id)
    try:
        report = run_full_analysis(
            game,
            simulation_time=req.simulation_time,
            optimizer=req.optimizer,
            beam_width=req.beam_width,
            mcts_iterations=req.mcts_iterations,
            mcts_seed=req.mcts_seed,
            bnb_depth=req.bnb_depth,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception(
            "Unexpected error in /run for game %s",
            req.game_id,
        )
        raise HTTPException(
            status_code=500,
            detail="Internal analysis error",
        ) from exc

    result: dict[str, Any] = {
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
                {
                    "time": p.time,
                    "node_id": p.node_id,
                    "count": p.count,
                    "cost": p.cost,
                }
                for p in opt.purchases
            ],
            "timeline": opt.timeline,
            "final_production": opt.final_production,
            "final_balance": opt.final_balance,
            "final_time": opt.final_time,
        }
    return result


@router.post("/compare", response_model=CompareResponse)
def compare_strategies(req: CompareRequest):
    game = _get_game_or_404(req.game_id)
    try:
        baseline = run_full_analysis(game, simulation_time=req.simulation_time)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception(
            "Unexpected error in /compare baseline for game %s",
            req.game_id,
        )
        raise HTTPException(
            status_code=500,
            detail="Internal analysis error",
        ) from exc

    baseline_prod = baseline.optimizer_result.final_production if baseline.optimizer_result else 0

    variants: dict[str, VariantResult] = {}
    for tag in req.strategies:
        filtered_nodes = []
        excluded_ids: set[str] = set()
        for node in game.nodes:
            is_tagged = (
                hasattr(node, "tags")
                and tag in node.tags
                and getattr(node, "type", "") == "upgrade"
            )
            if is_tagged:
                excluded_ids.add(node.id)
            else:
                filtered_nodes.append(node)

        variant_game = GameDefinition(
            schema_version=game.schema_version,
            name=f"{game.name}_no_{tag}",
            nodes=filtered_nodes,
            edges=[
                e
                for e in game.edges
                if (e.source not in excluded_ids and e.target not in excluded_ids)
            ],
            stacking_groups=game.stacking_groups,
        )
        try:
            variant_report = run_full_analysis(
                variant_game,
                simulation_time=req.simulation_time,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception(
                "Unexpected error in /compare variant '%s' for game %s",
                tag,
                req.game_id,
            )
            raise HTTPException(
                status_code=500,
                detail="Internal analysis error",
            ) from exc

        variant_prod = (
            variant_report.optimizer_result.final_production
            if variant_report.optimizer_result
            else 0
        )
        ratio = variant_prod / baseline_prod if baseline_prod > 0 else float("inf")
        variants[tag] = VariantResult(
            final_production=variant_prod,
            ratio_vs_baseline=ratio,
        )

    return CompareResponse(
        baseline={"final_production": baseline_prod},
        variants=variants,
    )


@router.post("/report")
def generate_html_report(req: ReportRequest):
    game = _get_game_or_404(req.game_id)
    try:
        report = run_full_analysis(game, simulation_time=req.simulation_time)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception(
            "Unexpected error in /report for game %s",
            req.game_id,
        )
        raise HTTPException(
            status_code=500,
            detail="Internal analysis error",
        ) from exc
    html = generate_report(report, use_cdn=req.use_cdn)
    return HTMLResponse(content=html)
