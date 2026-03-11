"""Interactive engine session endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response

from idleframework.bigfloat import BigFloat
from idleframework.engine.solvers import bulk_purchase_cost
from idleframework.model.nodes import Achievement, Generator, PrestigeLayer, Resource, Upgrade
from idleframework.optimizer.greedy import GreedyOptimizer
from server.game_store import game_store
from server.schemas import (
    AchievementState,
    AdvanceRequest,
    AutoOptimizeRequest,
    AutoOptimizeResponse,
    ErrorResponse,
    GeneratorState,
    PrestigeState,
    PurchaseRequest,
    PurchaseStepResponse,
    ResourceState,
    SessionState,
    StartSessionRequest,
    TimelineEntry,
    UpgradeState,
)
from server.sessions import session_manager

router = APIRouter()


def _get_session_or_404(session_id: str):
    session = session_manager.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=ErrorResponse(
            error="session_not_found",
            detail=f"No session with ID '{session_id}' exists",
            status=404,
        ).model_dump())
    return session


def _build_state(session) -> SessionState:
    """Build SessionState response from an engine session."""
    engine = session.engine
    game = session.game
    rates = engine.compute_production_rates()
    primary = engine._get_primary_resource_id()
    balance = engine.get_balance(primary) if primary else 0.0

    resources = {}
    generators = {}
    upgrades = {}
    achievements = []

    for node in game.nodes:
        ns = engine.state.get(node.id)
        if isinstance(node, Generator):
            gen_mult = engine._compute_generator_multipliers().get(node.id, 1.0)
            prod = node.base_production * ns.owned / node.cycle_time * gen_mult if ns.owned > 0 else 0.0
            cost_bf = bulk_purchase_cost(
                BigFloat(node.cost_base), BigFloat(node.cost_growth_rate), ns.owned, 1,
            )
            generators[node.id] = GeneratorState(
                owned=ns.owned,
                cost_next=float(cost_bf),
                production_per_sec=prod,
            )
        elif isinstance(node, Upgrade):
            upgrades[node.id] = UpgradeState(
                purchased=ns.purchased,
                cost=node.cost,
                affordable=balance >= node.cost and not ns.purchased,
            )
        elif isinstance(node, Resource):
            resources[node.id] = ResourceState(
                current_value=ns.current_value,
                production_rate=rates.get(node.id, 0.0),
            )
        elif isinstance(node, Achievement):
            achievements.append(AchievementState(
                id=node.id,
                name=node.name,
                unlocked=ns.purchased,
            ))

    prestige = None
    for node in game.nodes:
        if isinstance(node, PrestigeLayer):
            prestige = PrestigeState(
                available_currency=0.0,
                formula_preview=node.formula_expr,
            )
            break

    return SessionState(
        session_id=session.session_id,
        game_id=session.game_id,
        elapsed_time=engine.current_time,
        resources=resources,
        generators=generators,
        upgrades=upgrades,
        prestige=prestige,
        achievements=achievements,
    )


@router.post("/start", response_model=SessionState)
def start_session(req: StartSessionRequest):
    game = game_store.get_game(req.game_id)
    if game is None:
        raise HTTPException(status_code=404, detail=ErrorResponse(
            error="game_not_found",
            detail=f"No game with ID '{req.game_id}' exists",
            status=404,
        ).model_dump())
    session = session_manager.create(req.game_id, game, req.initial_balance)
    return _build_state(session)


@router.get("/{session_id}/state", response_model=SessionState)
def get_state(session_id: str):
    session = _get_session_or_404(session_id)
    return _build_state(session)


@router.post("/{session_id}/advance", response_model=SessionState)
def advance(session_id: str, req: AdvanceRequest):
    session = _get_session_or_404(session_id)
    engine = session.engine
    rates = engine.compute_production_rates()
    engine._accumulate(rates, req.seconds)
    engine._time += req.seconds
    engine.state.elapsed_time = engine._time
    return _build_state(session)


@router.post("/{session_id}/purchase", response_model=SessionState)
def purchase(session_id: str, req: PurchaseRequest):
    session = _get_session_or_404(session_id)
    engine = session.engine

    # Validate node exists and is purchasable
    try:
        node = session.game.get_node(req.node_id)
    except KeyError:
        raise HTTPException(status_code=400, detail=ErrorResponse(
            error="invalid_purchase",
            detail=f"Node '{req.node_id}' not found",
            status=400,
        ).model_dump())

    if not isinstance(node, (Generator, Upgrade)):
        raise HTTPException(status_code=400, detail=ErrorResponse(
            error="invalid_purchase",
            detail=f"Node '{req.node_id}' is not purchasable",
            status=400,
        ).model_dump())

    try:
        for _ in range(req.count):
            engine.purchase(req.node_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=ErrorResponse(
            error="insufficient_funds",
            detail=str(e),
            status=400,
        ).model_dump())

    return _build_state(session)


@router.post("/{session_id}/auto-optimize", response_model=AutoOptimizeResponse)
def auto_optimize(session_id: str, req: AutoOptimizeRequest):
    session = _get_session_or_404(session_id)
    optimizer = GreedyOptimizer(session.game, session.engine.state)
    result = optimizer.optimize(target_time=req.target_time, max_steps=req.max_steps)

    purchases = [
        PurchaseStepResponse(time=p.time, node_id=p.node_id, count=p.count, cost=p.cost)
        for p in result.purchases
    ]
    timeline = [
        TimelineEntry(time=t["time"], production_rate=t["production_rate"])
        for t in result.timeline
    ]

    return AutoOptimizeResponse(
        purchases=purchases,
        timeline=timeline,
        final_production=result.final_production,
        final_balance=result.final_balance,
    )


@router.delete("/{session_id}", status_code=204)
def delete_session(session_id: str):
    if not session_manager.delete(session_id):
        raise HTTPException(status_code=404, detail=ErrorResponse(
            error="session_not_found",
            detail=f"No session with ID '{session_id}' exists",
            status=404,
        ).model_dump())
    return Response(status_code=204)
