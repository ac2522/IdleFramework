# Branch Integration Plan: main ← feat/phase1-implementation

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate main-only features (beam/MCTS/B&B optimizers, analysis, reports, CLI, export) onto feat branch's superior architecture, then merge into main.

**Architecture:** Feat branch has better core (immutable BigFloat, external GameState, cleaner solvers/DSL/graph). Main has additional Phase 1 features (Tasks 10-15) that need porting. We add convenience methods to feat's engine so ported code works cleanly, then adapt each ported module.

**Tech Stack:** Python 3.12+, Pydantic v2, Lark, NetworkX, Plotly, Typer, pytest

---

## Key API Differences (feat vs main)

Feat's engine uses `GameState` externally. Main's tests/optimizers expect convenience methods:

| Main API | Feat Equivalent |
|----------|-----------------|
| `engine.set_balance(id, val)` | `engine.state.get(id).current_value = val` |
| `engine.set_owned(id, count)` | `engine.state.get(id).owned = count` |
| `engine.get_balance(id)` | `engine.state.get(id).current_value` |
| `engine.get_owned(id)` | `engine.state.get(id).owned` |
| `engine.get_production_rate(id)` | `engine.compute_production_rates().get(id, 0)` |
| `engine.purchase(id, count)` | Loop `engine.purchase(id)` count times |
| `engine.purchase_upgrade(id)` | `engine.purchase(id)` for upgrades |
| `engine.is_upgrade_owned(id)` | `engine.state.get(id).purchased` |
| `engine.time` | `engine.current_time` |
| `engine._generators` | No direct equivalent |
| `engine._find_payment_resource()` | `engine._get_primary_resource_id()` |
| `PiecewiseEngine(game, validate=True)` | Constructor + validate param |
| `engine.evaluate_prestige(id, **kw)` | Not implemented |
| `engine.evaluate_register(id, vars)` | Not implemented |
| `engine.auto_advance(target_time)` | `engine.advance_to(target_time)` (has auto-purchasing built in) |
| `GreedyOptimizer(engine)` | `GreedyOptimizer(game, state)` |
| `OptimizeResult` dataclass | `PurchaseStep` list |

---

### Task 1: Add Engine Convenience Methods

**Files:**
- Modify: `src/idleframework/engine/segments.py`
- Test: `tests/test_segments.py` (add tests for new methods)

Add these convenience methods to `PiecewiseEngine`:

```python
# Convenience methods for compatibility
def set_balance(self, resource_id: str, value: float) -> None:
    self._state.get(resource_id).current_value = value

def set_owned(self, node_id: str, count: int) -> None:
    self._state.get(node_id).owned = count

def get_balance(self, resource_id: str) -> float:
    return self._state.get(resource_id).current_value

def get_owned(self, node_id: str) -> int:
    return self._state.get(node_id).owned

def get_production_rate(self, resource_id: str) -> float:
    return self.compute_production_rates().get(resource_id, 0.0)

@property
def time(self) -> float:
    return self._time

def is_upgrade_owned(self, upgrade_id: str) -> bool:
    return self._state.get(upgrade_id).purchased

def purchase_upgrade(self, upgrade_id: str) -> float:
    """Purchase an upgrade. Returns cost paid. Raises ValueError if already owned or can't afford."""
    ns = self._state.get(upgrade_id)
    if ns.purchased:
        raise ValueError(f"Already purchased {upgrade_id!r}")
    node = self._game.get_node(upgrade_id)
    cost = node.cost
    currency_id = self._get_currency_resource_id_for(upgrade_id)
    if currency_id and cost > 0:
        balance = self._state.get(currency_id).current_value
        if balance < cost - 1e-9:
            raise ValueError(f"Cannot afford {upgrade_id!r}: need {cost}, have {balance}")
        self._state.get(currency_id).current_value -= cost
    ns.purchased = True
    return cost
```

Also add `purchase(node_id, count)` overload, `validate` constructor param, `evaluate_prestige()`, `evaluate_register()`, `_generators` property, `_upgrades` property.

**Step 1:** Write failing tests for each convenience method.
**Step 2:** Implement all convenience methods.
**Step 3:** Run tests: `pytest tests/test_segments.py -v`
**Step 4:** Commit: `feat: add engine convenience methods for optimizer compatibility`

---

### Task 2: Add OptimizeResult to Greedy Optimizer

**Files:**
- Modify: `src/idleframework/optimizer/greedy.py`

The beam/MCTS/BnB optimizers on main return `OptimizeResult`. Add this dataclass:

```python
@dataclass
class OptimizeResult:
    purchases: list = field(default_factory=list)
    timeline: list[dict] = field(default_factory=list)
    final_production: float = 0.0
    final_balance: float = 0.0
    final_time: float = 0.0
```

Also add `get_candidates()` method that returns list of dicts with `node_id`, `type`, `cost`, `efficiency`, `delta_production` — needed by beam/MCTS/BnB.

**Step 1:** Add `OptimizeResult` dataclass and `get_candidates()` method.
**Step 2:** Run tests: `pytest tests/test_greedy.py -v`
**Step 3:** Commit: `feat: add OptimizeResult and get_candidates for advanced optimizers`

---

### Task 3: Port Beam Search Optimizer

**Files:**
- Create: `src/idleframework/optimizer/beam.py`
- Create: `tests/test_beam.py`

Adapt from main. Key changes:
- `engine._find_payment_resource()` → `engine._get_primary_resource_id()`
- `engine.purchase(id, 1)` stays (Task 1 adds count param)
- `GreedyOptimizer(engine)` → `GreedyOptimizer(engine._game, copy.deepcopy(engine.state))`
- `engine.time` → works after Task 1

**Step 1:** Port beam.py with API adaptations.
**Step 2:** Port test_beam.py with API adaptations.
**Step 3:** Run tests: `pytest tests/test_beam.py -v`
**Step 4:** Commit: `feat: beam search optimizer`

---

### Task 4: Port MCTS Optimizer

**Files:**
- Create: `src/idleframework/optimizer/mcts.py`
- Create: `tests/test_mcts_bnb.py`

Same API adaptations as beam. Key differences: uses random seed, epsilon-greedy rollouts.

**Step 1:** Port mcts.py.
**Step 2:** Port MCTS tests from test_mcts_bnb.py.
**Step 3:** Run tests: `pytest tests/test_mcts_bnb.py::TestMCTS -v`
**Step 4:** Commit: `feat: MCTS optimizer`

---

### Task 5: Port Branch-and-Bound Optimizer

**Files:**
- Create: `src/idleframework/optimizer/bnb.py`

**Step 1:** Port bnb.py with API adaptations.
**Step 2:** Port BnB tests into test_mcts_bnb.py.
**Step 3:** Run tests: `pytest tests/test_mcts_bnb.py::TestBranchAndBound -v`
**Step 4:** Commit: `feat: branch-and-bound optimizer`

---

### Task 6: Port Analysis Detectors

**Files:**
- Create: `src/idleframework/analysis/__init__.py`
- Create: `src/idleframework/analysis/detectors.py`
- Create: `tests/test_analysis.py`

Key adaptations:
- `PiecewiseEngine(game)` → same
- `engine._find_payment_resource()` → `engine._get_primary_resource_id()`
- `engine.set_balance()`, `engine.purchase()` → work after Task 1
- `engine._generators` → work after Task 1
- `bulk_cost()` → `bulk_purchase_cost()` (feat name)
- `GreedyOptimizer(engine)` → `GreedyOptimizer(game)` (feat API)
- `GreedyOptimizer.optimize()` → `GreedyOptimizer.run()`

**Step 1:** Port detectors.py.
**Step 2:** Port test_analysis.py.
**Step 3:** Port fixtures: `tests/fixtures/mediumcap.json`, `tests/fixtures/largecap.py`
**Step 4:** Run tests: `pytest tests/test_analysis.py -v`
**Step 5:** Commit: `feat: analysis detectors + fixtures`

---

### Task 7: Port Reports Module

**Files:**
- Create: `src/idleframework/reports/__init__.py`
- Create: `src/idleframework/reports/html.py`
- Create: `tests/test_reports.py`

**Step 1:** Port html.py (minimal changes — depends on AnalysisReport).
**Step 2:** Port test_reports.py.
**Step 3:** Run tests: `pytest tests/test_reports.py -v`
**Step 4:** Commit: `feat: HTML report generator with Plotly`

---

### Task 8: Port CLI + Export

**Files:**
- Create: `src/idleframework/cli.py`
- Create: `src/idleframework/export.py`
- Create: `tests/test_cli.py`

**Step 1:** Port export.py (no changes needed).
**Step 2:** Port cli.py (adjust imports).
**Step 3:** Port test_cli.py.
**Step 4:** Run tests: `pytest tests/test_cli.py -v`
**Step 5:** Commit: `feat: Typer CLI + YAML/XML export`

---

### Task 9: Port E2E and Engine Integration Tests

**Files:**
- Create: `tests/test_e2e_minicap.py`
- Create: `tests/test_engine_formulas.py`
- Create: `tests/test_engine_upgrades.py`

These tests exercise the full pipeline and rely on convenience methods from Task 1.

**Step 1:** Port all three test files, adapting to feat's API.
**Step 2:** Run tests: `pytest tests/test_e2e_minicap.py tests/test_engine_formulas.py tests/test_engine_upgrades.py -v`
**Step 3:** Commit: `test: E2E, engine formula, and engine upgrade integration tests`

---

### Task 10: Port CI + Final Integration

**Files:**
- Create: `.github/workflows/ci.yml`
- Modify: `src/idleframework/optimizer/__init__.py` (update exports)

**Step 1:** Copy CI workflow from main.
**Step 2:** Update `__init__.py` files with new exports.
**Step 3:** Run full test suite: `pytest -v --tb=short`
**Step 4:** Ensure ruff passes: `ruff check src/ tests/`
**Step 5:** Commit: `chore: CI workflow + updated exports`

---

### Task 11: Merge into Main

**Step 1:** Verify all tests pass on feat branch.
**Step 2:** Merge feat/phase1-implementation into main (overwriting main's content).
**Step 3:** Delete feat branch.
