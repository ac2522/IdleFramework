"""Benchmark suite for IdleFramework engine and optimizer performance."""
import time
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from idleframework.model.state import GameState
from idleframework.engine.segments import PiecewiseEngine
from idleframework.optimizer.greedy import GreedyOptimizer


def get_fixtures():
    """Load available fixture factories."""
    tests_dir = Path(__file__).parent.parent / "tests"
    fixtures_dir = tests_dir / "fixtures"

    def make_minicap_game():
        import json as _json
        from idleframework.model.game import GameDefinition
        with open(fixtures_dir / "minicap.json") as f:
            data = _json.load(f)
        return GameDefinition.model_validate(data)

    def make_mediumcap_game():
        import json as _json
        from idleframework.model.game import GameDefinition
        with open(fixtures_dir / "mediumcap.json") as f:
            data = _json.load(f)
        return GameDefinition.model_validate(data)

    fixtures = {
        "MiniCap": make_minicap_game,
        "MediumCap": make_mediumcap_game,
    }
    try:
        sys.path.insert(0, str(tests_dir))
        from fixtures.largecap import make_largecap
        fixtures["LargeCap"] = make_largecap
    except ImportError:
        pass
    return fixtures


HORIZONS = [3600, 36000]  # 1hr, 10hr in seconds


def benchmark_engine(name, game_factory, horizon):
    game = game_factory()
    state = GameState.from_game(game)
    for node in game.nodes:
        if hasattr(node, "base_production"):
            state.get(node.id).owned = 1
            break

    engine = PiecewiseEngine(game, state)
    start = time.perf_counter()
    engine.advance_to(float(horizon))
    elapsed = time.perf_counter() - start
    return {"fixture": name, "horizon": horizon, "engine_seconds": round(elapsed, 4),
            "segments": len(engine.segments)}


def benchmark_greedy(name, game_factory, horizon):
    game = game_factory()
    state = GameState.from_game(game)
    for node in game.nodes:
        if hasattr(node, "base_production"):
            state.get(node.id).owned = 1
            break

    opt = GreedyOptimizer(game, state)
    start = time.perf_counter()
    try:
        steps = opt.run(target_time=float(horizon), max_steps=500)
    except ValueError as exc:
        elapsed = time.perf_counter() - start
        return {"fixture": name, "horizon": horizon, "greedy_seconds": round(elapsed, 4),
                "steps": -1, "error": str(exc)}
    elapsed = time.perf_counter() - start
    return {"fixture": name, "horizon": horizon, "greedy_seconds": round(elapsed, 4),
            "steps": len(steps)}


def main():
    fixtures = get_fixtures()
    results = []
    for name, factory in fixtures.items():
        for horizon in HORIZONS:
            print(f"  Benchmarking {name} @ {horizon}s...")
            results.append(benchmark_engine(name, factory, horizon))
            results.append(benchmark_greedy(name, factory, horizon))
            print(f"    Done")

    out_path = Path("docs/benchmarks") / f"baseline-{time.strftime('%Y-%m-%d')}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\nBaseline saved to {out_path}")

    for r in results:
        print(r)


if __name__ == "__main__":
    main()
