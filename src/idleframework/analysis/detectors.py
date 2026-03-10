"""Balance analysis detectors for idle game definitions."""
from __future__ import annotations

from dataclasses import dataclass, field

from idleframework.model.game import GameDefinition
from idleframework.engine.segments import PiecewiseEngine
from idleframework.engine.solvers import bulk_cost
from idleframework.optimizer.greedy import GreedyOptimizer, OptimizeResult


@dataclass
class AnalysisReport:
    game_name: str
    simulation_time: float
    dead_upgrades: list[dict] = field(default_factory=list)
    progression_walls: list[dict] = field(default_factory=list)
    dominant_strategy: dict | None = None
    sensitivity: list[dict] = field(default_factory=list)
    optimizer_result: OptimizeResult | None = None


def _run_greedy(game: GameDefinition, simulation_time: float, initial_balance: float = 50.0) -> OptimizeResult:
    engine = PiecewiseEngine(game)
    pay_resource = engine._get_primary_resource_id()
    engine.set_balance(pay_resource, initial_balance)
    for gen_id in engine._generators:
        cost = bulk_cost(
            engine._generators[gen_id].cost_base,
            engine._generators[gen_id].cost_growth_rate,
            0, 1,
        )
        if cost <= initial_balance:
            engine.purchase(gen_id, 1)
            break

    optimizer = GreedyOptimizer(game, engine.state)
    return optimizer.optimize(target_time=simulation_time, max_steps=500)


def detect_dead_upgrades(
    game: GameDefinition,
    simulation_time: float = 600.0,
) -> list[dict]:
    result = _run_greedy(game, simulation_time)
    max_earnings = result.final_balance + sum(p.cost for p in result.purchases)

    engine = PiecewiseEngine(game)

    dead = []
    for upg_id, upg in engine._upgrades.items():
        if upg.cost <= 0:
            continue
        if upg.cost > max_earnings * 10:
            dead.append({
                "upgrade_id": upg_id,
                "cost": upg.cost,
                "max_earnings": max_earnings,
                "reason": f"Cost ({upg.cost:.2e}) exceeds 10x total earnings ({max_earnings:.2e})",
            })
            continue
        if upg.magnitude is not None and upg.magnitude < 1.01 and upg.cost > max_earnings * 0.1:
            dead.append({
                "upgrade_id": upg_id,
                "cost": upg.cost,
                "magnitude": upg.magnitude,
                "reason": f"Negligible magnitude ({upg.magnitude:.4f}) for high cost ({upg.cost:.2e})",
            })

    return dead


def detect_progression_walls(
    game: GameDefinition,
    simulation_time: float = 300.0,
    sample_interval: float = 10.0,
) -> list[dict]:
    engine = PiecewiseEngine(game)
    pay_resource = engine._get_primary_resource_id()

    engine.set_balance(pay_resource, 50.0)
    for gen_id in engine._generators:
        cost = bulk_cost(
            engine._generators[gen_id].cost_base,
            engine._generators[gen_id].cost_growth_rate,
            0, 1,
        )
        if cost <= 50.0:
            engine.purchase(gen_id, 1)
            break

    optimizer = GreedyOptimizer(game, engine.state)
    result = optimizer.optimize(target_time=simulation_time, max_steps=500)

    walls = []

    for node in game.nodes:
        if node.type == "generator" and node.cost_growth_rate >= 1.30:
            severity = "severe" if node.cost_growth_rate >= 1.40 else "moderate"
            walls.append({
                "generator_id": node.id,
                "cost_growth_rate": node.cost_growth_rate,
                "severity": severity,
                "reason": f"Generator '{node.id}' has high cost growth rate ({node.cost_growth_rate:.2f})",
            })

    if len(result.timeline) >= 3:
        for i in range(2, len(result.timeline)):
            prev_rate = result.timeline[i - 1]["production_rate"]
            curr_rate = result.timeline[i]["production_rate"]
            prev_time = result.timeline[i - 1]["time"]
            curr_time = result.timeline[i]["time"]

            if prev_rate <= 0:
                continue

            time_gap = curr_time - prev_time
            growth_factor = curr_rate / prev_rate if prev_rate > 0 else 0

            if time_gap > simulation_time * 0.2 and growth_factor < 1.5:
                wall_gen = _identify_wall_generator(game)
                severity = "severe" if time_gap > simulation_time * 0.4 else "moderate"
                walls.append({
                    "time_start": prev_time,
                    "time_end": curr_time,
                    "duration": time_gap,
                    "growth_factor": growth_factor,
                    "severity": severity,
                    "generator_id": wall_gen,
                    "reason": f"Production stagnated for {time_gap:.1f}s ({severity})",
                })

    return walls


def _identify_wall_generator(game: GameDefinition) -> str | None:
    worst_gen = None
    worst_growth = 0.0
    for node in game.nodes:
        if node.type == "generator":
            if node.cost_growth_rate > worst_growth:
                worst_growth = node.cost_growth_rate
                worst_gen = node.id
    return worst_gen


def detect_dominant_strategy(
    game: GameDefinition,
    simulation_time: float = 300.0,
) -> dict:
    pay_resource = None
    gen_ids = []

    for node in game.nodes:
        if node.type == "resource" and pay_resource is None:
            pay_resource = node.id
        elif node.type == "generator":
            gen_ids.append(node.id)

    if len(gen_ids) < 2:
        return {"dominant_gen": None, "ratio": 1.0, "productions": {}}

    productions = {}

    for gen_id in gen_ids:
        single_game = _make_single_gen_game(game, gen_id)
        engine = PiecewiseEngine(single_game)
        gen = engine._generators[gen_id]
        first_cost = bulk_cost(gen.cost_base, gen.cost_growth_rate, 0, 1)
        engine.set_balance(pay_resource, first_cost + 50.0)
        engine.purchase(gen_id, 1)

        _auto_buy_single(engine, gen_id, simulation_time)
        productions[gen_id] = engine.get_production_rate(pay_resource)

    sorted_gens = sorted(productions.items(), key=lambda x: x[1], reverse=True)
    best_gen, best_prod = sorted_gens[0]
    second_prod = sorted_gens[1][1] if len(sorted_gens) > 1 else 0

    ratio = best_prod / second_prod if second_prod > 0 else float("inf")

    return {
        "dominant_gen": best_gen if ratio > 2.0 else None,
        "ratio": ratio,
        "productions": productions,
    }


def _make_single_gen_game(game: GameDefinition, gen_id: str) -> GameDefinition:
    """Create a stripped game with only one generator for isolated analysis."""
    resource_nodes = [n for n in game.nodes if n.type == "resource"]
    gen_nodes = [n for n in game.nodes if n.type == "generator" and n.id == gen_id]
    edges = [e for e in game.edges if e.source == gen_id]
    return GameDefinition(
        schema_version=game.schema_version,
        name=f"{game.name}_single_{gen_id}",
        nodes=resource_nodes + gen_nodes,
        edges=edges,
        stacking_groups={},
    )


def _auto_buy_single(engine: PiecewiseEngine, gen_id: str, target_time: float) -> None:
    """Advance engine to target_time; engine auto-purchases as it goes."""
    engine.advance_to(target_time)


def run_sensitivity_analysis(
    game: GameDefinition,
    parameter: str,
    perturbation_pcts: list[float],
    simulation_time: float = 300.0,
) -> list[dict]:
    results = []

    for pct in perturbation_pcts:
        perturbed = _perturb_game(game, parameter, pct)
        opt_result = _run_greedy(perturbed, simulation_time)

        results.append({
            "perturbation_pct": pct,
            "final_production": opt_result.final_production,
            "final_balance": opt_result.final_balance,
        })

    return results


def _perturb_game(game: GameDefinition, parameter: str, multiplier: float) -> GameDefinition:
    game_copy = game.model_copy(deep=True)

    for node in game_copy.nodes:
        if node.type == "generator" and hasattr(node, parameter):
            current = getattr(node, parameter)
            if isinstance(current, (int, float)):
                setattr(node, parameter, current * multiplier)

    return game_copy


def run_full_analysis(
    game: GameDefinition,
    simulation_time: float = 300.0,
) -> AnalysisReport:
    report = AnalysisReport(
        game_name=game.name,
        simulation_time=simulation_time,
    )

    report.dead_upgrades = detect_dead_upgrades(game, simulation_time)
    report.progression_walls = detect_progression_walls(game, simulation_time)
    report.dominant_strategy = detect_dominant_strategy(game, simulation_time)
    report.optimizer_result = _run_greedy(game, simulation_time)

    return report
