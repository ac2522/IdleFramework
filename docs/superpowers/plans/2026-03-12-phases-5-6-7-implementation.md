# Phases 5-6-7 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add all remaining idle game mechanics (tickspeed, autobuyers, drains, buffs, synergies, multi-layer prestige, crit), integrate into the React Flow editor, and optimize performance.

**Architecture:** New mechanics are node types plugged into the existing Pydantic model → PiecewiseEngine → Optimizer stack. State edge evaluation is the composability linchpin — once the engine evaluates state_modifier edges, any property on any node can be modified by any upgrade. The UI follows the established BaseNode + PropertyPanel pattern.

**Tech Stack:** Python 3.11+, Pydantic v2, Lark LALR(1) DSL, React 19 + TypeScript 5 + React Flow v12, pytest + Hypothesis, Cython, Numba, NumPy

**Spec:** `docs/superpowers/specs/2026-03-12-phases-5-6-7-design.md`

---

## Chunk 1: Model Layer — New Node Types & Edge Enhancements

### Task 1: Add TickspeedNode

**Files:**
- Modify: `src/idleframework/model/nodes.py:186-194` (add class + union)
- Test: `tests/test_model.py`

- [ ] **Step 1: Write failing test**

```python
# In tests/test_model.py — add at end of file
def test_tickspeed_node_creation():
    node = TickspeedNode(id="ts1", base_tickspeed=1.5)
    assert node.type == "tickspeed"
    assert node.base_tickspeed == 1.5
    assert node.name == "Tickspeed"


def test_tickspeed_node_default():
    node = TickspeedNode(id="ts1")
    assert node.base_tickspeed == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_model.py::test_tickspeed_node_creation -v`
Expected: FAIL — `ImportError` or `NameError` for `TickspeedNode`

- [ ] **Step 3: Implement TickspeedNode**

In `src/idleframework/model/nodes.py`, before the `NodeUnion` definition, add:

```python
class TickspeedNode(NodeBase):
    type: Literal["tickspeed"] = "tickspeed"
    name: str = "Tickspeed"
    base_tickspeed: float = 1.0
```

Add `TickspeedNode` to the `NodeUnion` discriminated union.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_model.py::test_tickspeed_node_creation tests/test_model.py::test_tickspeed_node_default -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/idleframework/model/nodes.py tests/test_model.py
git commit -m "feat: add TickspeedNode model"
```

### Task 2: Add AutobuyerNode

**Files:**
- Modify: `src/idleframework/model/nodes.py` (add class + union)
- Test: `tests/test_model.py`

- [ ] **Step 1: Write failing test**

```python
def test_autobuyer_node_creation():
    node = AutobuyerNode(id="ab1", target="gen1", interval=2.0, priority=5)
    assert node.type == "autobuyer"
    assert node.target == "gen1"
    assert node.interval == 2.0
    assert node.priority == 5
    assert node.bulk_amount == "1"
    assert node.enabled is True
    assert node.condition is None


def test_autobuyer_node_with_condition():
    node = AutobuyerNode(
        id="ab1", target="gen1", condition="balance > cost * 2", bulk_amount="max"
    )
    assert node.condition == "balance > cost * 2"
    assert node.bulk_amount == "max"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_model.py::test_autobuyer_node_creation -v`
Expected: FAIL

- [ ] **Step 3: Implement AutobuyerNode**

```python
class AutobuyerNode(NodeBase):
    type: Literal["autobuyer"] = "autobuyer"
    name: str = ""
    target: str
    interval: float = 1.0
    priority: int = 0
    condition: str | None = None
    bulk_amount: Literal["1", "10", "max"] = "1"
    enabled: bool = True
```

Add to `NodeUnion`.

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_model.py::test_autobuyer_node_creation tests/test_model.py::test_autobuyer_node_with_condition -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/idleframework/model/nodes.py tests/test_model.py
git commit -m "feat: add AutobuyerNode model"
```

### Task 3: Add DrainNode

**Files:**
- Modify: `src/idleframework/model/nodes.py` (add class + union)
- Test: `tests/test_model.py`

- [ ] **Step 1: Write failing test**

```python
def test_drain_node_creation():
    node = DrainNode(id="drain1", rate=5.0)
    assert node.type == "drain"
    assert node.rate == 5.0
    assert node.condition is None


def test_drain_node_with_condition():
    node = DrainNode(id="drain1", rate=3.0, condition="active == 1")
    assert node.condition == "active == 1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_model.py::test_drain_node_creation -v`
Expected: FAIL

- [ ] **Step 3: Implement DrainNode**

```python
class DrainNode(NodeBase):
    type: Literal["drain"] = "drain"
    name: str = ""
    rate: float
    condition: str | None = None
```

Add to `NodeUnion`.

- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Commit**

```bash
git add src/idleframework/model/nodes.py tests/test_model.py
git commit -m "feat: add DrainNode model"
```

### Task 4: Add BuffNode

**Files:**
- Modify: `src/idleframework/model/nodes.py` (add class + union)
- Test: `tests/test_model.py`

- [ ] **Step 1: Write failing test**

```python
def test_buff_node_timed():
    node = BuffNode(id="b1", buff_type="timed", duration=10.0, multiplier=3.0, cooldown=50.0)
    assert node.type == "buff"
    assert node.buff_type == "timed"
    assert node.duration == 10.0
    assert node.cooldown == 50.0


def test_buff_node_proc():
    node = BuffNode(id="b1", buff_type="proc", proc_chance=0.05, multiplier=2.0)
    assert node.proc_chance == 0.05
    assert node.target is None  # global


def test_buff_node_zero_cooldown():
    """Zero cooldown = always active, effective multiplier equals raw multiplier."""
    node = BuffNode(id="b1", buff_type="timed", duration=10.0, multiplier=5.0, cooldown=0.0)
    assert node.cooldown == 0.0
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement BuffNode**

```python
class BuffNode(NodeBase):
    type: Literal["buff"] = "buff"
    name: str = ""
    buff_type: Literal["timed", "proc"]
    duration: float | None = None
    proc_chance: float | None = None
    multiplier: float = 2.0
    target: str | None = None
    cooldown: float = 0.0
```

Add to `NodeUnion`.

- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Commit**

```bash
git add src/idleframework/model/nodes.py tests/test_model.py
git commit -m "feat: add BuffNode model"
```

### Task 5: Add SynergyNode

**Files:**
- Modify: `src/idleframework/model/nodes.py` (add class + union)
- Test: `tests/test_model.py`

- [ ] **Step 1: Write failing test**

```python
def test_synergy_node_creation():
    node = SynergyNode(
        id="syn1",
        sources=["gen_cursor", "gen_grandma"],
        formula_expr="owned_gen_cursor * 0.001",
        target="gen_grandma",
    )
    assert node.type == "synergy"
    assert len(node.sources) == 2
    assert node.formula_expr == "owned_gen_cursor * 0.001"
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement SynergyNode**

```python
class SynergyNode(NodeBase):
    type: Literal["synergy"] = "synergy"
    name: str = ""
    sources: list[str]
    formula_expr: str
    target: str
```

Add to `NodeUnion`.

- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Commit**

```bash
git add src/idleframework/model/nodes.py tests/test_model.py
git commit -m "feat: add SynergyNode model"
```

### Task 6: Enhance Edge Model with target_property and modifier_mode

**Files:**
- Modify: `src/idleframework/model/edges.py:10-28`
- Test: `tests/test_model.py`

- [ ] **Step 1: Write failing test**

```python
def test_edge_state_modifier_with_target_property():
    edge = Edge(
        id="e1", source="upg1", target="gen1",
        edge_type="state_modifier",
        formula="owned * 0.05",
        target_property="crit_chance",
        modifier_mode="add",
    )
    assert edge.target_property == "crit_chance"
    assert edge.modifier_mode == "add"


def test_edge_backward_compat_no_target_property():
    """Existing state_modifier edges without target_property still work."""
    edge = Edge(
        id="e1", source="upg1", target="gen1",
        edge_type="state_modifier",
        formula="2.0",
    )
    assert edge.target_property is None
    assert edge.modifier_mode is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_model.py::test_edge_state_modifier_with_target_property -v`
Expected: FAIL — `target_property` not a valid field

- [ ] **Step 3: Add fields to Edge**

In `src/idleframework/model/edges.py`, add to the `Edge` class:

```python
    target_property: str | None = None
    modifier_mode: Literal["set", "add", "multiply"] | None = None
```

- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Commit**

```bash
git add src/idleframework/model/edges.py tests/test_model.py
git commit -m "feat: add target_property and modifier_mode to Edge"
```

### Task 7: Enhance PrestigeLayer with Multi-Layer Fields

**Files:**
- Modify: `src/idleframework/model/nodes.py:79-87`
- Test: `tests/test_model.py`

- [ ] **Step 1: Write failing test**

```python
def test_prestige_layer_multi_layer_fields():
    node = PrestigeLayer(
        id="p1",
        formula_expr="floor(sqrt(lifetime))",
        layer_index=1,
        reset_scope=["gen1", "res1"],
        currency_id="prestige_currency",
        parent_layer="p2",
    )
    assert node.currency_id == "prestige_currency"
    assert node.parent_layer == "p2"


def test_prestige_layer_backward_compat():
    """Existing PrestigeLayer without new fields still works."""
    node = PrestigeLayer(
        id="p1",
        formula_expr="floor(sqrt(lifetime))",
        layer_index=0,
        reset_scope=["gen1"],
    )
    assert node.currency_id is None
    assert node.parent_layer is None
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Add fields to PrestigeLayer**

In `src/idleframework/model/nodes.py`, add to `PrestigeLayer` class after `milestone_rules`:

```python
    currency_id: str | None = None
    parent_layer: str | None = None
```

- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Commit**

```bash
git add src/idleframework/model/nodes.py tests/test_model.py
git commit -m "feat: add multi-layer prestige fields to PrestigeLayer"
```

### Task 8: Enhance Resource with Capacity

**Files:**
- Modify: `src/idleframework/model/nodes.py:43-46`
- Test: `tests/test_model.py`

- [ ] **Step 1: Write failing test**

```python
def test_resource_capacity():
    node = Resource(id="r1", name="Gold", capacity=1000.0)
    assert node.capacity == 1000.0
    assert node.overflow_behavior == "clamp"


def test_resource_no_capacity():
    node = Resource(id="r1", name="Gold")
    assert node.capacity is None
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Add fields to Resource**

```python
    capacity: float | None = None
    overflow_behavior: Literal["clamp", "waste"] = "clamp"
```

- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Commit**

```bash
git add src/idleframework/model/nodes.py tests/test_model.py
git commit -m "feat: add capacity and overflow_behavior to Resource"
```

### Task 9: Enhance Converter with recipe_type and conversion_limit

**Files:**
- Modify: `src/idleframework/model/nodes.py:20-24` (ConverterIO) and `115-121` (Converter)
- Test: `tests/test_model.py`

- [ ] **Step 1: Write failing test**

```python
def test_converter_io_with_formula():
    cio = ConverterIO(resource="gold", amount=10.0, formula="conversion_count * 0.9")
    assert cio.formula == "conversion_count * 0.9"


def test_converter_io_no_formula():
    cio = ConverterIO(resource="gold", amount=10.0)
    assert cio.formula is None


def test_converter_scaling_recipe():
    node = Converter(
        id="c1",
        inputs=[ConverterIO(resource="wood", amount=5.0)],
        outputs=[ConverterIO(resource="plank", amount=2.0, formula="2 * conversion_count ** 0.5")],
        rate=1.0,
        recipe_type="scaling",
        conversion_limit=100,
    )
    assert node.recipe_type == "scaling"
    assert node.conversion_limit == 100
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Add fields**

In `ConverterIO`:
```python
    formula: str | None = None
```

In `Converter`:
```python
    recipe_type: Literal["fixed", "scaling"] = "fixed"
    conversion_limit: int | None = None
```

- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Commit**

```bash
git add src/idleframework/model/nodes.py tests/test_model.py
git commit -m "feat: add recipe_type and conversion_limit to Converter"
```

### Task 10: Enhance NodeState and GameState

**Files:**
- Modify: `src/idleframework/model/state.py:13-30`
- Test: `tests/test_model.py`

- [ ] **Step 1: Write failing test**

```python
def test_node_state_last_fired():
    ns = NodeState(last_fired=5.0)
    assert ns.last_fired == 5.0


def test_node_state_last_fired_default():
    ns = NodeState()
    assert ns.last_fired == 0.0


def test_game_state_layer_run_times():
    gs = GameState(node_states={}, layer_run_times={"p1": 100.0})
    assert gs.layer_run_times["p1"] == 100.0


def test_game_state_layer_run_times_default():
    gs = GameState(node_states={})
    assert gs.layer_run_times == {}
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Add fields**

In `NodeState`:
```python
    last_fired: float = 0.0
```

In `GameState`:
```python
    layer_run_times: dict[str, float] = Field(default_factory=dict)
```

- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Commit**

```bash
git add src/idleframework/model/state.py tests/test_model.py
git commit -m "feat: add last_fired to NodeState, layer_run_times to GameState"
```

### Task 11: Enhance Segment Dataclass

**Files:**
- Modify: `src/idleframework/engine/segments.py:28-36`
- Test: `tests/test_segments.py`

- [ ] **Step 1: Write failing test**

```python
def test_segment_new_fields():
    seg = Segment(
        start_time=0.0,
        end_time=10.0,
        production_rates={"gold": 5.0},
        multiplier=1.0,
        drain_rates={"gold": 1.0},
        net_rates={"gold": 4.0},
        tickspeed=2.0,
    )
    assert seg.drain_rates == {"gold": 1.0}
    assert seg.net_rates == {"gold": 4.0}
    assert seg.tickspeed == 2.0


def test_segment_new_fields_defaults():
    seg = Segment(
        start_time=0.0, end_time=10.0,
        production_rates={}, multiplier=1.0,
    )
    assert seg.drain_rates == {}
    assert seg.net_rates == {}
    assert seg.tickspeed == 1.0
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Add fields to Segment**

```python
    drain_rates: dict[str, float] = field(default_factory=dict)
    net_rates: dict[str, float] = field(default_factory=dict)
    tickspeed: float = 1.0
```

- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Commit**

```bash
git add src/idleframework/engine/segments.py tests/test_segments.py
git commit -m "feat: add drain_rates, net_rates, tickspeed to Segment"
```

### Task 12: Add Validation for New Node Types in GameDefinition

**Files:**
- Modify: `src/idleframework/model/game.py:10-16` (imports) and `33-41` (validators)
- Test: `tests/test_model.py`

- [ ] **Step 1: Write failing tests**

```python
def test_game_validates_tickspeed_singleton():
    """Only one TickspeedNode allowed per game."""
    from pydantic import ValidationError
    nodes = [
        Resource(id="r1", name="Gold"),
        TickspeedNode(id="ts1"),
        TickspeedNode(id="ts2"),
    ]
    with pytest.raises(ValidationError, match="tickspeed"):
        GameDefinition(
            schema_version="1.0", name="test",
            nodes=nodes, edges=[], stacking_groups={},
        )


def test_game_validates_state_modifier_target_property():
    """target_property must be a valid numeric field on target node."""
    from pydantic import ValidationError
    nodes = [Resource(id="r1", name="Gold"), Generator(id="g1", name="Gen", base_production=1, cost_base=1, cost_growth_rate=1.15)]
    edges = [Edge(id="e1", source="r1", target="g1", edge_type="state_modifier", formula="2", target_property="nonexistent_field", modifier_mode="multiply")]
    with pytest.raises(ValidationError, match="target_property"):
        GameDefinition(
            schema_version="1.0", name="test",
            nodes=nodes, edges=edges, stacking_groups={},
        )


def test_game_validates_synergy_formula():
    """SynergyNode formula_expr must compile."""
    from pydantic import ValidationError
    nodes = [
        Resource(id="r1", name="Gold"),
        Generator(id="g1", name="Gen", base_production=1, cost_base=1, cost_growth_rate=1.15),
        SynergyNode(id="syn1", sources=["g1"], formula_expr="invalid!!!", target="g1"),
    ]
    with pytest.raises(ValidationError, match="[Ff]ormula"):
        GameDefinition(
            schema_version="1.0", name="test",
            nodes=nodes, edges=[], stacking_groups={},
        )
```

- [ ] **Step 2: Run tests to verify they fail**
- [ ] **Step 3: Add validations to GameDefinition**

In `_validate_game`:
```python
    self._validate_tickspeed_singleton()
    self._validate_state_modifier_properties()
```

Add import for new node types. Implement:

```python
def _validate_tickspeed_singleton(self) -> None:
    from idleframework.model.nodes import TickspeedNode
    ts_count = sum(1 for n in self.nodes if isinstance(n, TickspeedNode))
    if ts_count > 1:
        raise ValueError(f"At most one TickspeedNode allowed, found {ts_count}")

def _validate_state_modifier_properties(self) -> None:
    node_map = {n.id: n for n in self.nodes}
    for edge in self.edges:
        if edge.edge_type == "state_modifier" and edge.target_property is not None:
            target_node = node_map.get(edge.target)
            if target_node is None:
                continue  # caught by _validate_edge_references
            valid_fields = {
                name for name, info in type(target_node).model_fields.items()
                if info.annotation in (float, int, "float", "int")
                or str(info.annotation).startswith("float")
                or str(info.annotation).startswith("int")
                or "float" in str(info.annotation)
            }
            if edge.target_property not in valid_fields:
                raise ValueError(
                    f"Edge {edge.id!r}: target_property {edge.target_property!r} "
                    f"is not a valid numeric field on {type(target_node).__name__}"
                )
```

Also extend `_validate_formulas` to include `SynergyNode` and `BuffNode` condition:

```python
from idleframework.model.nodes import SynergyNode, AutobuyerNode, DrainNode
# In _validate_formulas, add:
if isinstance(node, SynergyNode):
    compile_formula(node.formula_expr)
```

- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Run full test suite to check no regressions**

Run: `pytest tests/ -x -q`
Expected: All existing tests pass

- [ ] **Step 6: Commit**

```bash
git add src/idleframework/model/game.py tests/test_model.py
git commit -m "feat: add validation for new node types in GameDefinition"
```

---

## Chunk 2: Engine — State Edge Evaluation & Tickspeed

### Task 13: Variable Name Sanitization Utility

**Files:**
- Create: `src/idleframework/engine/variables.py`
- Test: `tests/test_engine_variables.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_engine_variables.py
from idleframework.engine.variables import sanitize_var_name, build_state_variables


def test_sanitize_simple():
    assert sanitize_var_name("gen1") == "gen1"


def test_sanitize_hyphens():
    assert sanitize_var_name("my-generator") == "my_generator"


def test_sanitize_special_chars():
    assert sanitize_var_name("node.with.dots") == "node_with_dots"
    assert sanitize_var_name("node@special!") == "node_special_"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_engine_variables.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# src/idleframework/engine/variables.py
"""Variable name sanitization and state variable building for formula evaluation."""

from __future__ import annotations
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from idleframework.model.game import GameDefinition
    from idleframework.model.state import GameState


def sanitize_var_name(node_id: str) -> str:
    """Sanitize a node ID into a valid Python identifier for formula variables."""
    return re.sub(r"[^a-zA-Z0-9_]", "_", node_id)


def build_state_variables(game: GameDefinition, state: GameState) -> dict[str, float]:
    """Build the variable namespace for formula evaluation from current game state.

    Variables:
    - owned_<node_id>: owned count
    - balance_<resource_id>: current value
    - level_<node_id>: level
    - lifetime_<resource_id>: lifetime earnings
    - total_production_<node_id>: total production
    - elapsed_time, run_time
    """
    from idleframework.model.nodes import Resource

    variables: dict[str, float] = {
        "elapsed_time": state.elapsed_time,
        "run_time": state.run_time,
    }

    for node in game.nodes:
        sid = sanitize_var_name(node.id)
        ns = state.get(node.id)
        variables[f"owned_{sid}"] = float(ns.owned)
        variables[f"level_{sid}"] = float(ns.level)
        variables[f"total_production_{sid}"] = ns.total_production

        if isinstance(node, Resource):
            variables[f"balance_{sid}"] = ns.current_value

    for res_id, amount in state.lifetime_earnings.items():
        sid = sanitize_var_name(res_id)
        variables[f"lifetime_{sid}"] = amount

    return variables
```

- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Write test for build_state_variables**

```python
def test_build_state_variables():
    from idleframework.model.nodes import Resource, Generator
    from idleframework.model.game import GameDefinition
    from idleframework.model.state import GameState, NodeState

    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold", initial_value=100.0),
            Generator(id="gen-1", name="Miner", base_production=1, cost_base=10, cost_growth_rate=1.15),
        ],
        edges=[], stacking_groups={},
    )
    state = GameState(
        node_states={
            "gold": NodeState(current_value=100.0),
            "gen-1": NodeState(owned=5),
        },
        elapsed_time=60.0,
        run_time=30.0,
        lifetime_earnings={"gold": 500.0},
    )
    vs = build_state_variables(game, state)
    assert vs["owned_gen_1"] == 5.0
    assert vs["balance_gold"] == 100.0
    assert vs["lifetime_gold"] == 500.0
    assert vs["elapsed_time"] == 60.0
```

- [ ] **Step 6: Run tests, verify pass**
- [ ] **Step 7: Commit**

```bash
git add src/idleframework/engine/variables.py tests/test_engine_variables.py
git commit -m "feat: add variable name sanitization and state variable builder"
```

### Task 14: State Edge Evaluation

**Files:**
- Create: `src/idleframework/engine/state_edges.py`
- Test: `tests/test_state_edges.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_state_edges.py
import pytest
from idleframework.model.nodes import Resource, Generator
from idleframework.model.edges import Edge
from idleframework.model.game import GameDefinition
from idleframework.model.state import GameState, NodeState
from idleframework.engine.state_edges import evaluate_state_edges


def _make_game_with_state_edge(formula, target_property, modifier_mode):
    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold", initial_value=100.0),
            Generator(id="gen1", name="Miner", base_production=1.0, cost_base=10, cost_growth_rate=1.15),
        ],
        edges=[
            Edge(id="e1", source="gold", target="gen1", edge_type="production_target"),
            Edge(
                id="sm1", source="gold", target="gen1",
                edge_type="state_modifier", formula=formula,
                target_property=target_property, modifier_mode=modifier_mode,
            ),
        ],
        stacking_groups={},
    )
    state = GameState(
        node_states={"gold": NodeState(current_value=100.0), "gen1": NodeState(owned=5)},
    )
    return game, state


def test_state_edge_multiply():
    game, state = _make_game_with_state_edge("2.0", "base_production", "multiply")
    modified = evaluate_state_edges(game, state)
    assert modified["gen1"]["base_production"] == pytest.approx(2.0)  # multiplier value


def test_state_edge_add():
    game, state = _make_game_with_state_edge("0.5", "base_production", "add")
    modified = evaluate_state_edges(game, state)
    assert modified["gen1"]["base_production"] == pytest.approx(0.5)  # additive delta


def test_state_edge_set():
    game, state = _make_game_with_state_edge("99.0", "base_production", "set")
    modified = evaluate_state_edges(game, state)
    assert modified["gen1"]["base_production"] == pytest.approx(99.0)  # absolute value
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement evaluate_state_edges**

```python
# src/idleframework/engine/state_edges.py
"""Evaluate state_modifier edges to compute modified node properties."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from idleframework.dsl.compiler import compile_formula, evaluate_formula
from idleframework.engine.variables import build_state_variables

if TYPE_CHECKING:
    from idleframework.model.game import GameDefinition
    from idleframework.model.state import GameState


@dataclass
class PropertyModification:
    """A resolved modification to a node property."""
    value: float
    mode: str  # "set", "add", "multiply"


def evaluate_state_edges(
    game: GameDefinition,
    state: GameState,
) -> dict[str, dict[str, list[PropertyModification]]]:
    """Evaluate all state_modifier edges and return modifications per node per property.

    Returns: {node_id: {property_name: [PropertyModification, ...]}}
    Multiple modifications to the same property are accumulated:
    - "multiply" mods are chained (product)
    - "add" mods are summed
    - "set" mods: last write wins
    """
    variables = build_state_variables(game, state)
    modified: dict[str, dict[str, list[PropertyModification]]] = {}

    # Collect and topologically sort state_modifier edges
    sm_edges = [e for e in game.edges if e.edge_type == "state_modifier" and e.formula]
    sm_edges = _topological_sort_edges(sm_edges, game)

    for edge in sm_edges:
        compiled = compile_formula(edge.formula)
        result = float(evaluate_formula(compiled, variables))

        target_id = edge.target
        prop = edge.target_property
        mode = edge.modifier_mode or "multiply"  # backward compat default

        if target_id not in modified:
            modified[target_id] = {}

        if prop is None:
            prop = "_general_multiplier"

        if prop not in modified[target_id]:
            modified[target_id][prop] = []
        modified[target_id][prop].append(PropertyModification(value=result, mode=mode))

    return modified


def apply_property_modifications(
    base_value: float,
    mods: list[PropertyModification],
) -> float:
    """Apply a list of property modifications to a base value.

    Order: set overrides first, then multiply, then add.
    """
    result = base_value
    has_set = False
    for mod in mods:
        if mod.mode == "set":
            result = mod.value
            has_set = True

    if not has_set:
        # Apply multipliers
        for mod in mods:
            if mod.mode == "multiply":
                result *= mod.value
        # Apply additives
        for mod in mods:
            if mod.mode == "add":
                result += mod.value
    else:
        # After set, still apply multiply and add on top
        for mod in mods:
            if mod.mode == "multiply":
                result *= mod.value
        for mod in mods:
            if mod.mode == "add":
                result += mod.value

    return result


def _topological_sort_edges(edges, game):
    """Topological sort of state_modifier edges by dependency.

    Edge A depends on edge B if A's formula references a variable
    derived from B's target node. Simple heuristic: sort by target
    node ID to ensure consistent ordering. Full dependency analysis
    uses the formula's referenced variables.
    """
    # Build dependency graph
    from idleframework.engine.variables import sanitize_var_name

    edge_targets = {}  # edge_id -> set of variable prefixes it produces
    for e in edges:
        sid = sanitize_var_name(e.target)
        edge_targets[e.id] = {f"owned_{sid}", f"balance_{sid}", f"level_{sid}",
                              f"total_production_{sid}", f"lifetime_{sid}"}

    # Build adjacency: edge A depends on edge B if A's formula contains
    # any variable that B's target produces
    from collections import defaultdict
    deps = defaultdict(set)  # edge_id -> set of edge_ids it depends on
    for e in edges:
        if not e.formula:
            continue
        for other in edges:
            if other.id == e.id:
                continue
            for var in edge_targets.get(other.id, set()):
                if var in e.formula:
                    deps[e.id].add(other.id)

    # Kahn's algorithm
    in_degree = {e.id: len(deps[e.id]) for e in edges}
    queue = [e for e in edges if in_degree[e.id] == 0]
    result = []
    visited = set()

    while queue:
        e = queue.pop(0)
        if e.id in visited:
            continue
        visited.add(e.id)
        result.append(e)
        for other in edges:
            if e.id in deps[other.id]:
                deps[other.id].discard(e.id)
                in_degree[other.id] -= 1
                if in_degree[other.id] == 0:
                    queue.append(other)

    # Detect cycles
    if len(result) != len(edges):
        cycle_edges = [e.id for e in edges if e.id not in visited]
        raise ValueError(f"Cycle detected in state_modifier edges: {cycle_edges}")

    return result
```

- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Commit**

```bash
git add src/idleframework/engine/state_edges.py tests/test_state_edges.py
git commit -m "feat: implement state edge evaluation engine"
```

### Task 15: Tickspeed Resolution in Engine

**Files:**
- Modify: `src/idleframework/engine/segments.py`
- Test: `tests/test_engine_tickspeed.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_engine_tickspeed.py
import pytest
from idleframework.model.nodes import Resource, Generator, TickspeedNode, Upgrade
from idleframework.model.edges import Edge
from idleframework.model.game import GameDefinition
from idleframework.model.state import GameState, NodeState
from idleframework.engine.segments import PiecewiseEngine


def _make_tickspeed_game(base_tickspeed=1.0, with_upgrade=False):
    nodes = [
        Resource(id="gold", name="Gold", initial_value=0.0),
        Generator(id="gen1", name="Miner", base_production=10.0, cost_base=100, cost_growth_rate=1.15),
        TickspeedNode(id="ts1", base_tickspeed=base_tickspeed),
    ]
    edges = [Edge(id="e1", source="gen1", target="gold", edge_type="production_target")]
    stacking = {}
    if with_upgrade:
        nodes.append(Upgrade(
            id="ts_upg", name="Tick Boost", upgrade_type="multiplicative",
            magnitude=2.0, cost=0.0, target="ts1", stacking_group="tick",
        ))
        stacking["tick"] = "multiplicative"
    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=nodes, edges=edges, stacking_groups=stacking,
    )
    state = GameState.from_game(game)
    state.get("gen1").owned = 1
    return game, state


def test_tickspeed_doubles_production():
    game, state = _make_tickspeed_game(base_tickspeed=2.0)
    engine = PiecewiseEngine(game, state)
    rates = engine.compute_production_rates()
    # 10.0 base_production * 1 owned / 1.0 cycle * 2.0 tickspeed = 20.0
    assert rates["gold"] == pytest.approx(20.0)


def test_tickspeed_default_no_change():
    game, state = _make_tickspeed_game(base_tickspeed=1.0)
    engine = PiecewiseEngine(game, state)
    rates = engine.compute_production_rates()
    assert rates["gold"] == pytest.approx(10.0)


def test_tickspeed_upgrade_multiplies():
    game, state = _make_tickspeed_game(base_tickspeed=1.0, with_upgrade=True)
    engine = PiecewiseEngine(game, state)
    # Purchase the free upgrade
    state.get("ts_upg").purchased = True
    rates = engine.compute_production_rates()
    # tickspeed = 1.0 * 2.0 (upgrade) = 2.0, production = 10 * 1 * 2.0 = 20.0
    assert rates["gold"] == pytest.approx(20.0)
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement tickspeed in PiecewiseEngine**

In `src/idleframework/engine/segments.py`, add to `__init__`:
```python
from idleframework.model.nodes import TickspeedNode
# In __init__, add after _upgrades lookup:
self._tickspeed_node: TickspeedNode | None = None
for node in self._game.nodes:
    if isinstance(node, TickspeedNode):
        self._tickspeed_node = node
        break
```

Add method:
```python
def compute_tickspeed(self) -> float:
    """Resolve the current tickspeed multiplier."""
    if self._tickspeed_node is None:
        return 1.0
    base = self._tickspeed_node.base_tickspeed

    # Collect upgrades targeting the tickspeed node
    ts_id = self._tickspeed_node.id
    ts_groups: dict[str, dict] = {}
    for node in self._game.nodes:
        if not isinstance(node, Upgrade):
            continue
        ns = self._state.get(node.id)
        if not ns.purchased:
            continue
        if node.target != ts_id:
            continue
        sg = node.stacking_group
        rule = self._game.stacking_groups.get(sg, "multiplicative")
        if sg not in ts_groups:
            ts_groups[sg] = {"rule": rule, "bonuses": []}
        ts_groups[sg]["bonuses"].append(node.magnitude)

    mult = compute_final_multiplier(ts_groups) if ts_groups else 1.0
    return base * mult
```

Modify `compute_production_rates` to multiply by tickspeed:
```python
def compute_production_rates(self) -> dict[str, float]:
    # ... existing code ...
    tickspeed = self.compute_tickspeed()
    # After computing rate for each generator, multiply:
    # rate = node.base_production * ns.owned / node.cycle_time * gen_mult * tickspeed
```

- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Run full test suite for regressions**

Run: `pytest tests/ -x -q`

- [ ] **Step 6: Commit**

```bash
git add src/idleframework/engine/segments.py tests/test_engine_tickspeed.py
git commit -m "feat: implement tickspeed resolution in PiecewiseEngine"
```

---

## Chunk 3: Engine — Drains, Buffs, Crit, Synergies

### Task 16: Drain Processing in Engine

**Files:**
- Modify: `src/idleframework/engine/segments.py`
- Test: `tests/test_engine_drains.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_engine_drains.py
import pytest
from idleframework.model.nodes import Resource, Generator, DrainNode
from idleframework.model.edges import Edge
from idleframework.model.game import GameDefinition
from idleframework.model.state import GameState, NodeState
from idleframework.engine.segments import PiecewiseEngine


def _make_drain_game(production=10.0, drain_rate=3.0):
    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold", initial_value=100.0),
            Generator(id="gen1", name="Miner", base_production=production, cost_base=100, cost_growth_rate=1.15),
            DrainNode(id="drain1", rate=drain_rate),
        ],
        edges=[
            Edge(id="e1", source="gen1", target="gold", edge_type="production_target"),
            Edge(id="e2", source="drain1", target="gold", edge_type="consumption"),
        ],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("gen1").owned = 1
    return game, state


def test_drain_reduces_net_rate():
    game, state = _make_drain_game(production=10.0, drain_rate=3.0)
    engine = PiecewiseEngine(game, state)
    gross = engine.compute_gross_rates()
    drains = engine.compute_drain_rates()
    assert gross["gold"] == pytest.approx(10.0)
    assert drains["gold"] == pytest.approx(3.0)


def test_drain_accumulation():
    game, state = _make_drain_game(production=10.0, drain_rate=3.0)
    engine = PiecewiseEngine(game, state)
    engine.advance_to(10.0)
    # Net rate = 10 - 3 = 7/s, initial = 100, after 10s = 100 + 70 = 170
    assert engine.get_balance("gold") == pytest.approx(170.0, rel=0.01)
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement drain processing**

Add to `PiecewiseEngine.__init__`:
```python
from idleframework.model.nodes import DrainNode
self._drains: dict[str, DrainNode] = {}
for node in self._game.nodes:
    if isinstance(node, DrainNode):
        self._drains[node.id] = node
```

Add methods:
```python
def compute_drain_rates(self) -> dict[str, float]:
    """Compute per-resource drain rates from active DrainNodes."""
    drains: dict[str, float] = {}
    for drain in self._drains.values():
        ns = self._state.get(drain.id)
        if not ns.active:
            continue
        # Find target resource via consumption edge
        for edge in self._game.get_edges_from(drain.id):
            if edge.edge_type == "consumption":
                drains[edge.target] = drains.get(edge.target, 0.0) + drain.rate
    return drains

def compute_gross_rates(self) -> dict[str, float]:
    """Alias for compute_production_rates (gross, before drains)."""
    return self.compute_production_rates()
```

Modify `_accumulate` to subtract drains. Modify `advance_to` to use net rates and consider zero-crossing events:

```python
def _compute_net_rates(self) -> tuple[dict[str, float], dict[str, float]]:
    """Compute gross and net rates. Returns (gross_rates, net_rates)."""
    gross = self.compute_production_rates()
    drains = self.compute_drain_rates()
    net = {}
    for res_id in set(list(gross.keys()) + list(drains.keys())):
        net[res_id] = gross.get(res_id, 0.0) - drains.get(res_id, 0.0)
    return gross, net

def _find_next_zero_crossing(self, net_rates: dict[str, float]) -> tuple[str, float] | None:
    """Find earliest resource depletion from negative net rate."""
    best: tuple[str, float] | None = None
    for res_id, rate in net_rates.items():
        if rate >= 0:
            continue
        balance = self._state.get(res_id).current_value
        if balance <= 0:
            continue
        time_to_zero = balance / abs(rate)
        if best is None or time_to_zero < best[1]:
            best = (res_id, time_to_zero)
    return best
```

In `advance_to`, replace `find_next_purchase` with `find_next_event` that considers:
1. `find_next_purchase()` → earliest affordable purchase (using net rates for time-to-afford)
2. `_next_autobuyer_time()` → earliest autobuyer fire
3. `_find_next_zero_crossing(net_rates)` → earliest resource depletion

Pick the earliest event, advance to it, execute it, loop.

In `find_next_purchase`, use net rates for time-to-afford calculations:
```python
# Replace: currency_rate = rates.get(currency_id, 0.0)
# With: currency_rate = net_rates.get(currency_id, 0.0)
```

- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Commit**

```bash
git add src/idleframework/engine/segments.py tests/test_engine_drains.py
git commit -m "feat: implement drain processing with zero-crossing events"
```

### Task 17: Buff Expected Value Processing

**Files:**
- Modify: `src/idleframework/engine/segments.py`
- Test: `tests/test_engine_buffs.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_engine_buffs.py
import pytest
from idleframework.model.nodes import Resource, Generator, BuffNode
from idleframework.model.edges import Edge
from idleframework.model.game import GameDefinition
from idleframework.model.state import GameState
from idleframework.engine.segments import PiecewiseEngine


def test_timed_buff_expected_value():
    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold"),
            Generator(id="gen1", name="Miner", base_production=10.0, cost_base=100, cost_growth_rate=1.15),
            BuffNode(id="buff1", buff_type="timed", duration=10.0, multiplier=3.0, cooldown=40.0, target="gen1"),
        ],
        edges=[Edge(id="e1", source="gen1", target="gold", edge_type="production_target")],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("gen1").owned = 1
    engine = PiecewiseEngine(game, state)
    buffs = engine.evaluate_buffs()
    # EV = 1 + (3-1) * (10/(10+40)) = 1 + 2 * 0.2 = 1.4
    assert buffs.per_generator["gen1"] == pytest.approx(1.4)


def test_proc_buff_expected_value():
    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold"),
            Generator(id="gen1", name="Miner", base_production=10.0, cost_base=100, cost_growth_rate=1.15),
            BuffNode(id="buff1", buff_type="proc", proc_chance=0.1, multiplier=5.0),
        ],
        edges=[Edge(id="e1", source="gen1", target="gold", edge_type="production_target")],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("gen1").owned = 1
    engine = PiecewiseEngine(game, state)
    buffs = engine.evaluate_buffs()
    # EV = 1 + 0.1 * (5-1) = 1.4, global
    assert buffs.global_multiplier == pytest.approx(1.4)


def test_zero_cooldown_always_active():
    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold"),
            Generator(id="gen1", name="Miner", base_production=10.0, cost_base=100, cost_growth_rate=1.15),
            BuffNode(id="buff1", buff_type="timed", duration=10.0, multiplier=3.0, cooldown=0.0, target="gen1"),
        ],
        edges=[Edge(id="e1", source="gen1", target="gold", edge_type="production_target")],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("gen1").owned = 1
    engine = PiecewiseEngine(game, state)
    buffs = engine.evaluate_buffs()
    assert buffs.per_generator["gen1"] == pytest.approx(3.0)
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement buff evaluation**

Add dataclass and method to `segments.py`:

```python
from collections import defaultdict

@dataclass
class BuffMultipliers:
    global_multiplier: float = 1.0
    per_generator: dict[str, float] = field(default_factory=dict)
```

```python
def evaluate_buffs(self) -> BuffMultipliers:
    from idleframework.model.nodes import BuffNode
    result = BuffMultipliers()
    per_gen = defaultdict(lambda: 1.0)

    for node in self._game.nodes:
        if not isinstance(node, BuffNode):
            continue
        ns = self._state.get(node.id)
        if not ns.active:
            continue

        if node.buff_type == "timed":
            if node.cooldown == 0.0:
                ev = node.multiplier
            else:
                d = node.duration or 0.0
                ev = 1.0 + (node.multiplier - 1.0) * (d / (d + node.cooldown))
        elif node.buff_type == "proc":
            pc = node.proc_chance or 0.0
            ev = 1.0 + pc * (node.multiplier - 1.0)
        else:
            ev = 1.0

        if node.target is None:
            result.global_multiplier *= ev
        else:
            per_gen[node.target] *= ev

    result.per_generator = dict(per_gen)
    return result
```

Integrate into `compute_production_rates` — multiply each generator's rate by `buff_global * buff_per_gen.get(gen_id, 1.0)`.

- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Commit**

```bash
git add src/idleframework/engine/segments.py tests/test_engine_buffs.py
git commit -m "feat: implement buff expected value processing in engine"
```

### Task 18: ProbabilityNode Crit Integration

**Files:**
- Modify: `src/idleframework/engine/segments.py`
- Test: `tests/test_engine_crit.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_engine_crit.py
import pytest
from idleframework.model.nodes import Resource, Generator, ProbabilityNode
from idleframework.model.edges import Edge
from idleframework.model.game import GameDefinition
from idleframework.model.state import GameState
from idleframework.engine.segments import PiecewiseEngine


def test_crit_modifies_production():
    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold"),
            Generator(id="gen1", name="Miner", base_production=10.0, cost_base=100, cost_growth_rate=1.15),
            ProbabilityNode(id="prob1", expected_value=1.0, crit_chance=0.2, crit_multiplier=3.0),
        ],
        edges=[
            Edge(id="e1", source="gen1", target="gold", edge_type="production_target"),
            Edge(id="e2", source="prob1", target="gen1", edge_type="state_modifier",
                 formula="1 + 0.2 * (3 - 1)", target_property="base_production", modifier_mode="multiply"),
        ],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("gen1").owned = 1
    engine = PiecewiseEngine(game, state)
    rates = engine.compute_production_rates()
    # crit_ev = 1 + 0.2 * (3-1) = 1.4
    # rate = 10 * 1 * 1.4 = 14.0
    assert rates["gold"] == pytest.approx(14.0)
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Integrate state edge evaluation into compute_production_rates**

In `compute_production_rates`, call `evaluate_state_edges` and apply the modified properties:

```python
from idleframework.engine.state_edges import evaluate_state_edges, apply_property_modifications

def compute_production_rates(self) -> dict[str, float]:
    rates: dict[str, float] = {}
    gen_multipliers = self._compute_generator_multipliers()
    tickspeed = self.compute_tickspeed()
    buffs = self.evaluate_buffs()
    synergies = self.compute_synergy_multipliers()
    modified = evaluate_state_edges(self._game, self._state)

    for node in self._game.nodes:
        if not isinstance(node, Generator):
            continue
        ns = self._state.get(node.id)
        if ns.owned <= 0 or not ns.active:
            continue

        base_prod = node.base_production
        # Apply state edge modifications — handles all 3 modes (set/add/multiply)
        if node.id in modified and "base_production" in modified[node.id]:
            base_prod = apply_property_modifications(
                base_prod, modified[node.id]["base_production"]
            )

        gen_mult = gen_multipliers.get(node.id, 1.0)
        buff_mult = buffs.global_multiplier * buffs.per_generator.get(node.id, 1.0)
        syn_mult = synergies.get(node.id, 1.0)
        rate = base_prod * ns.owned / node.cycle_time * gen_mult * tickspeed * buff_mult * syn_mult

        for edge in self._game.get_edges_from(node.id):
            if edge.edge_type == "production_target":
                rates[edge.target] = rates.get(edge.target, 0.0) + rate

    return rates
```

- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Commit**

```bash
git add src/idleframework/engine/segments.py tests/test_engine_crit.py
git commit -m "feat: integrate ProbabilityNode crit into production rates"
```

### Task 19: Synergy Evaluation in Engine

**Files:**
- Modify: `src/idleframework/engine/segments.py`
- Test: `tests/test_engine_synergy.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_engine_synergy.py
import pytest
from idleframework.model.nodes import Resource, Generator, SynergyNode
from idleframework.model.edges import Edge
from idleframework.model.game import GameDefinition
from idleframework.model.state import GameState
from idleframework.engine.segments import PiecewiseEngine


def test_synergy_boosts_target():
    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold"),
            Generator(id="cursor", name="Cursor", base_production=1.0, cost_base=10, cost_growth_rate=1.15),
            Generator(id="grandma", name="Grandma", base_production=5.0, cost_base=100, cost_growth_rate=1.15),
            SynergyNode(id="syn1", sources=["cursor"], formula_expr="owned_cursor * 0.01", target="grandma"),
        ],
        edges=[
            Edge(id="e1", source="cursor", target="gold", edge_type="production_target"),
            Edge(id="e2", source="grandma", target="gold", edge_type="production_target"),
        ],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("cursor").owned = 100
    state.get("grandma").owned = 1
    engine = PiecewiseEngine(game, state)
    rates = engine.compute_production_rates()
    # Cursor: 1.0 * 100 = 100.0
    # Grandma: 5.0 * 1 * synergy_mult
    # synergy = owned_cursor * 0.01 = 100 * 0.01 = 1.0 (multiplier)
    # But synergy is applied as a multiplier, so grandma rate = 5.0 * (1 + 1.0) = 10.0
    # Total = 100 + 10 = 110
    # (exact formula depends on how we apply synergy — as additive or multiplicative)
    assert rates["gold"] > 105.0  # At minimum, synergy should boost grandma
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement synergy evaluation**

Add method to PiecewiseEngine:
```python
def compute_synergy_multipliers(self) -> dict[str, float]:
    """Compute per-generator multipliers from SynergyNodes."""
    from idleframework.model.nodes import SynergyNode
    from idleframework.dsl.compiler import compile_formula, evaluate_formula
    from idleframework.engine.variables import build_state_variables

    synergies: dict[str, float] = {}
    variables = build_state_variables(self._game, self._state)

    for node in self._game.nodes:
        if not isinstance(node, SynergyNode):
            continue
        ns = self._state.get(node.id)
        if not ns.active:
            continue
        compiled = compile_formula(node.formula_expr)
        bonus = float(evaluate_formula(compiled, variables))
        # Apply as additive bonus: target_mult = 1 + bonus
        if node.target in synergies:
            synergies[node.target] += bonus
        else:
            synergies[node.target] = bonus

    # Convert to multipliers: 1 + total_bonus
    return {k: 1.0 + v for k, v in synergies.items()}
```

Integrate into `compute_production_rates` by multiplying synergy multiplier.

- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Commit**

```bash
git add src/idleframework/engine/segments.py tests/test_engine_synergy.py
git commit -m "feat: implement synergy evaluation in engine"
```

### Task 20: Resource Capacity Clamping

**Files:**
- Modify: `src/idleframework/engine/segments.py`
- Test: `tests/test_engine_capacity.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_engine_capacity.py
import pytest
from idleframework.model.nodes import Resource, Generator
from idleframework.model.edges import Edge
from idleframework.model.game import GameDefinition
from idleframework.model.state import GameState
from idleframework.engine.segments import PiecewiseEngine


def test_resource_clamped_at_capacity():
    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold", initial_value=90.0, capacity=100.0),
            Generator(id="gen1", name="Miner", base_production=10.0, cost_base=10000, cost_growth_rate=1.15),
        ],
        edges=[Edge(id="e1", source="gen1", target="gold", edge_type="production_target")],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("gen1").owned = 1
    engine = PiecewiseEngine(game, state)
    engine.advance_to(100.0)
    # Should be clamped at 100, not 90 + 10*100 = 1090
    assert engine.get_balance("gold") <= 100.0


def test_resource_no_capacity_unlimited():
    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold", initial_value=0.0),
            Generator(id="gen1", name="Miner", base_production=10.0, cost_base=10000, cost_growth_rate=1.15),
        ],
        edges=[Edge(id="e1", source="gen1", target="gold", edge_type="production_target")],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("gen1").owned = 1
    engine = PiecewiseEngine(game, state)
    engine.advance_to(100.0)
    assert engine.get_balance("gold") == pytest.approx(1000.0, rel=0.01)
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement capacity clamping**

In `_accumulate`, after adding production, clamp:
```python
def _accumulate(self, rates: dict[str, float], dt: float) -> None:
    for resource_id, rate in rates.items():
        ns = self._state.get(resource_id)
        ns.current_value += rate * dt
        ns.total_production += rate * dt

        # Clamp to capacity if set
        res_node = self._game.get_node(resource_id)
        if isinstance(res_node, Resource) and res_node.capacity is not None:
            if ns.current_value > res_node.capacity:
                ns.current_value = res_node.capacity

    # Track lifetime earnings...
```

Also adjust net rate to 0 when at capacity in `advance_to` to prevent the engine from computing time-to-afford incorrectly.

- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Commit**

```bash
git add src/idleframework/engine/segments.py tests/test_engine_capacity.py
git commit -m "feat: implement resource capacity clamping"
```

---

## Chunk 4: Engine — Autobuyers & Multi-Layer Prestige

### Task 21: Autobuyer Event Processing

**Files:**
- Modify: `src/idleframework/engine/segments.py`
- Test: `tests/test_engine_autobuyers.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_engine_autobuyers.py
import pytest
from idleframework.model.nodes import Resource, Generator, AutobuyerNode
from idleframework.model.edges import Edge
from idleframework.model.game import GameDefinition
from idleframework.model.state import GameState
from idleframework.engine.segments import PiecewiseEngine


def test_autobuyer_purchases_at_interval():
    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold", initial_value=10000.0),
            Generator(id="gen1", name="Miner", base_production=10.0, cost_base=10.0, cost_growth_rate=1.15),
            AutobuyerNode(id="ab1", target="gen1", interval=1.0),
        ],
        edges=[Edge(id="e1", source="gen1", target="gold", edge_type="production_target")],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    engine = PiecewiseEngine(game, state)
    engine.advance_to(5.0)
    # Autobuyer fires every 1s, should have bought several generators
    assert engine.get_owned("gen1") > 0


def test_autobuyer_skipped_by_optimizer():
    """find_next_purchase should skip nodes managed by autobuyers."""
    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold", initial_value=10000.0),
            Generator(id="gen1", name="Miner", base_production=10.0, cost_base=10.0, cost_growth_rate=1.15),
            Generator(id="gen2", name="Logger", base_production=5.0, cost_base=10.0, cost_growth_rate=1.15),
            AutobuyerNode(id="ab1", target="gen1", interval=1.0),
        ],
        edges=[
            Edge(id="e1", source="gen1", target="gold", edge_type="production_target"),
            Edge(id="e2", source="gen2", target="gold", edge_type="production_target"),
        ],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("gen2").owned = 1
    engine = PiecewiseEngine(game, state)
    result = engine.find_next_purchase()
    # gen1 is managed by autobuyer, so find_next_purchase should return gen2
    if result is not None:
        assert result[0] == "gen2"
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement autobuyer processing**

Add to `__init__`:
```python
from idleframework.model.nodes import AutobuyerNode
self._autobuyers: dict[str, AutobuyerNode] = {}
self._autobuyer_targets: set[str] = set()
for node in self._game.nodes:
    if isinstance(node, AutobuyerNode):
        self._autobuyers[node.id] = node
        self._autobuyer_targets.add(node.target)
```

Add method for computing next autobuyer fire time:
```python
def _next_autobuyer_time(self) -> tuple[str, float] | None:
    """Find the earliest autobuyer fire time."""
    best: tuple[str, float] | None = None
    for ab_id, ab in self._autobuyers.items():
        ns = self._state.get(ab_id)
        if not ns.active or not ab.enabled:
            continue
        next_fire = ns.last_fired + ab.interval
        if best is None or next_fire < best[1]:
            best = (ab_id, next_fire)
    return best
```

Add autobuyer execution handler with condition evaluation:
```python
def _execute_autobuyer(self, autobuyer_id: str) -> None:
    """Execute an autobuyer fire event."""
    from idleframework.dsl.compiler import compile_formula, evaluate_formula
    from idleframework.engine.variables import build_state_variables

    ab = self._autobuyers[autobuyer_id]
    ns = self._state.get(autobuyer_id)

    # Evaluate condition if set
    if ab.condition is not None:
        variables = build_state_variables(self._game, self._state)
        compiled = compile_formula(ab.condition)
        if not float(evaluate_formula(compiled, variables)):
            ns.last_fired = self._time  # Skip but update timer
            return

    # Resolve bulk amount
    amount = 1
    if ab.bulk_amount == "10":
        amount = 10
    elif ab.bulk_amount == "max":
        amount = self._compute_max_affordable(ab.target)

    if amount > 0:
        try:
            self.purchase(ab.target, amount)
        except ValueError:
            pass  # Can't afford — skip

    ns.last_fired = self._time
```

Modify `find_next_purchase` to skip autobuyer-managed targets:
```python
# In the generator/upgrade loop, add:
if node.id in self._autobuyer_targets:
    continue
```

Modify `advance_to` to consider autobuyer fire times as events alongside purchases.

- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Commit**

```bash
git add src/idleframework/engine/segments.py tests/test_engine_autobuyers.py
git commit -m "feat: implement autobuyer event processing in engine"
```

### Task 22: Multi-Layer Prestige — execute_prestige and execute_reset

**Files:**
- Modify: `src/idleframework/engine/segments.py`
- Test: `tests/test_engine_prestige.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_engine_prestige.py
import pytest
from idleframework.model.nodes import Resource, Generator, PrestigeLayer, Upgrade
from idleframework.model.edges import Edge
from idleframework.model.game import GameDefinition
from idleframework.model.state import GameState
from idleframework.engine.segments import PiecewiseEngine


def _make_two_layer_game():
    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold", initial_value=1000.0),
            Resource(id="prestige_pts", name="Prestige Points"),
            Resource(id="transcend_pts", name="Transcend Points"),
            Generator(id="gen1", name="Miner", base_production=10.0, cost_base=10, cost_growth_rate=1.15),
            PrestigeLayer(
                id="prestige", formula_expr="floor(sqrt(lifetime_gold))",
                layer_index=1, reset_scope=["gen1", "gold"],
                persistence_scope=["prestige_pts"],
                currency_id="prestige_pts",
            ),
            PrestigeLayer(
                id="transcend", formula_expr="floor(sqrt(lifetime_prestige_pts))",
                layer_index=2, reset_scope=["gen1", "gold", "prestige_pts"],
                persistence_scope=["transcend_pts"],
                currency_id="transcend_pts",
                parent_layer=None,
            ),
        ],
        edges=[Edge(id="e1", source="gen1", target="gold", edge_type="production_target")],
        stacking_groups={},
    )
    return game


def test_prestige_resets_lower_scope():
    game = _make_two_layer_game()
    state = GameState.from_game(game)
    state.get("gen1").owned = 10
    state.get("gold").current_value = 5000.0
    state.lifetime_earnings["gold"] = 10000.0
    engine = PiecewiseEngine(game, state)

    gain = engine.execute_prestige("prestige")

    # Gold and gen1 should be reset
    assert engine.get_owned("gen1") == 0
    assert engine.get_balance("gold") == 0.0
    # Prestige points gained
    assert engine.get_balance("prestige_pts") > 0
    assert gain > 0


def test_higher_layer_resets_lower_layers():
    game = _make_two_layer_game()
    state = GameState.from_game(game)
    state.get("gen1").owned = 10
    state.get("gold").current_value = 5000.0
    state.get("prestige_pts").current_value = 100.0
    state.lifetime_earnings["gold"] = 10000.0
    state.lifetime_earnings["prestige_pts"] = 200.0
    engine = PiecewiseEngine(game, state)

    engine.execute_prestige("transcend")

    # Everything reset except transcend_pts
    assert engine.get_owned("gen1") == 0
    assert engine.get_balance("gold") == 0.0
    assert engine.get_balance("prestige_pts") == 0.0
    assert engine.get_balance("transcend_pts") > 0
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement execute_prestige with multi-layer reset**

Rewrite `evaluate_prestige` to `execute_prestige`:

```python
def execute_prestige(self, prestige_id: str) -> float:
    """Execute a prestige reset: compute gain, deposit currency, reset scopes."""
    from idleframework.dsl.compiler import compile_formula, evaluate_formula
    from idleframework.engine.variables import build_state_variables

    node = self._game.get_node(prestige_id)
    if not isinstance(node, PrestigeLayer):
        raise ValueError(f"{prestige_id!r} is not a PrestigeLayer")

    variables = build_state_variables(self._game, self._state)
    compiled = compile_formula(node.formula_expr)
    gain = float(evaluate_formula(compiled, variables))

    # Deposit into currency resource
    if node.currency_id:
        self._state.get(node.currency_id).current_value += gain

    # Reset all lower layers
    for other in self._game.nodes:
        if isinstance(other, PrestigeLayer) and other.layer_index < node.layer_index:
            self._execute_reset(other.reset_scope, other.persistence_scope)
            self._state.layer_run_times[other.id] = 0.0

    # Reset this layer's scope
    self._execute_reset(node.reset_scope, node.persistence_scope)
    self._state.layer_run_times[prestige_id] = 0.0

    return gain

def _execute_reset(self, reset_scope: list[str], persistence_scope: list[str]) -> None:
    """Reset nodes in reset_scope except those in persistence_scope."""
    persist = set(persistence_scope)
    for node_id in reset_scope:
        if node_id in persist:
            continue
        ns = self._state.get(node_id)
        node = self._game.get_node(node_id)
        if isinstance(node, Resource):
            ns.current_value = node.initial_value
        elif isinstance(node, Generator):
            ns.owned = 0
            ns.total_production = 0.0
        elif isinstance(node, Upgrade):
            ns.purchased = False
        ns.last_fired = 0.0
```

- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Run full test suite**

Run: `pytest tests/ -x -q`

- [ ] **Step 6: Commit**

```bash
git add src/idleframework/engine/segments.py tests/test_engine_prestige.py
git commit -m "feat: implement multi-layer prestige with execute_reset"
```

---

## Chunk 5: Optimizer Updates

### Task 23: Greedy Optimizer — Tickspeed and Buff Efficiency

**Files:**
- Modify: `src/idleframework/optimizer/greedy.py`
- Test: `tests/test_greedy.py`

- [ ] **Step 1: Write failing test**

```python
# Add to tests/test_greedy.py
def test_greedy_tickspeed_upgrade_efficiency():
    """Tickspeed upgrade should be valued based on total production impact."""
    from idleframework.model.nodes import Resource, Generator, TickspeedNode, Upgrade
    from idleframework.model.edges import Edge
    from idleframework.model.game import GameDefinition
    from idleframework.model.state import GameState
    from idleframework.optimizer.greedy import GreedyOptimizer

    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold", initial_value=1000.0),
            Generator(id="gen1", name="Miner", base_production=10.0, cost_base=100, cost_growth_rate=1.15),
            TickspeedNode(id="ts1"),
            Upgrade(id="ts_upg", name="Tick Boost", upgrade_type="multiplicative",
                    magnitude=2.0, cost=500.0, target="ts1", stacking_group="tick"),
        ],
        edges=[Edge(id="e1", source="gen1", target="gold", edge_type="production_target")],
        stacking_groups={"tick": "multiplicative"},
    )
    state = GameState.from_game(game)
    state.get("gen1").owned = 5
    opt = GreedyOptimizer(game, state)
    eff = opt.compute_upgrade_efficiency("ts_upg")
    assert eff > 0  # Should have positive efficiency
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Modify greedy optimizer to handle tickspeed upgrades**

In `compute_upgrade_efficiency`, detect when the upgrade targets a TickspeedNode:
```python
from idleframework.model.nodes import TickspeedNode

# In compute_upgrade_efficiency, after checking upgrade_type:
target_node = self.game.get_node(node.target)
if isinstance(target_node, TickspeedNode):
    # Tickspeed upgrade: value = total_production * (magnitude - 1) / cost
    rates = self.engine.compute_production_rates()
    total = sum(rates.values())
    if node.upgrade_type == "multiplicative":
        return total * (node.magnitude - 1) / cost
    return 0.0
```

- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Commit**

```bash
git add src/idleframework/optimizer/greedy.py tests/test_greedy.py
git commit -m "feat: greedy optimizer handles tickspeed upgrade efficiency"
```

### Task 24: Greedy Optimizer — Autobuyer Awareness

**Files:**
- Modify: `src/idleframework/optimizer/greedy.py`
- Test: `tests/test_greedy.py`

- [ ] **Step 1: Write failing test**

```python
def test_greedy_skips_autobuyer_targets():
    """Greedy should not recommend purchasing nodes managed by autobuyers."""
    from idleframework.model.nodes import Resource, Generator, AutobuyerNode
    from idleframework.model.edges import Edge
    from idleframework.model.game import GameDefinition
    from idleframework.model.state import GameState
    from idleframework.optimizer.greedy import GreedyOptimizer

    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold", initial_value=10000.0),
            Generator(id="gen1", name="Auto-Miner", base_production=10.0, cost_base=10, cost_growth_rate=1.15),
            Generator(id="gen2", name="Manual-Logger", base_production=5.0, cost_base=10, cost_growth_rate=1.15),
            AutobuyerNode(id="ab1", target="gen1", interval=1.0),
        ],
        edges=[
            Edge(id="e1", source="gen1", target="gold", edge_type="production_target"),
            Edge(id="e2", source="gen2", target="gold", edge_type="production_target"),
        ],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("gen2").owned = 1
    opt = GreedyOptimizer(game, state)
    best = opt.find_best_purchase()
    assert best is not None
    assert best[0] == "gen2"  # Should skip gen1 (autobuyer-managed)
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement autobuyer filtering in find_best_purchase**

```python
# In __init__, build autobuyer target set:
self._autobuyer_targets: set[str] = set()
for node in self.game.nodes:
    if isinstance(node, AutobuyerNode):
        self._autobuyer_targets.add(node.target)

# In find_best_purchase, skip autobuyer targets:
if isinstance(node, Generator) and node.id in self._autobuyer_targets:
    continue
```

- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Commit**

```bash
git add src/idleframework/optimizer/greedy.py tests/test_greedy.py
git commit -m "feat: greedy optimizer skips autobuyer-managed targets"
```

### Task 25: FullMechanics Test Fixture

**Files:**
- Create: `tests/fixtures/fullmechanics.py`
- Test: `tests/test_fullmechanics.py`

- [ ] **Step 1: Create fixture that exercises all new mechanics**

```python
# tests/fixtures/fullmechanics.py
"""FullMechanics fixture — exercises all new Phase 5 mechanics together.

3 generators, 2 resources, 1 prestige layer, 1 tickspeed, 1 drain,
1 buff, 1 synergy, 1 autobuyer, 1 probability node, and various upgrades.
"""
from idleframework.model.nodes import (
    Resource, Generator, Upgrade, PrestigeLayer,
    TickspeedNode, AutobuyerNode, DrainNode, BuffNode,
    SynergyNode, ProbabilityNode,
)
from idleframework.model.edges import Edge
from idleframework.model.game import GameDefinition


def make_fullmechanics_game() -> GameDefinition:
    nodes = [
        # Resources
        Resource(id="gold", name="Gold", initial_value=100.0),
        Resource(id="prestige_pts", name="Prestige Points"),
        Resource(id="mana", name="Mana", initial_value=50.0, capacity=500.0),

        # Generators
        Generator(id="miner", name="Miner", base_production=1.0, cost_base=10, cost_growth_rate=1.15),
        Generator(id="smith", name="Smith", base_production=5.0, cost_base=100, cost_growth_rate=1.15),
        Generator(id="wizard", name="Wizard", base_production=2.0, cost_base=50, cost_growth_rate=1.2),

        # Tickspeed
        TickspeedNode(id="tickspeed"),

        # Upgrades
        Upgrade(id="upg_speed", name="Speed Boost", upgrade_type="multiplicative",
                magnitude=2.0, cost=500.0, target="miner", stacking_group="speed"),
        Upgrade(id="upg_tick", name="Tick Upgrade", upgrade_type="multiplicative",
                magnitude=1.5, cost=1000.0, target="tickspeed", stacking_group="tick"),

        # Drain
        DrainNode(id="mana_drain", name="Mana Drain", rate=1.0),

        # Buff
        BuffNode(id="frenzy", name="Frenzy", buff_type="timed",
                 duration=10.0, multiplier=3.0, cooldown=50.0, target="miner"),

        # Synergy
        SynergyNode(id="syn_miner_smith", name="Miner-Smith Synergy",
                     sources=["miner"], formula_expr="owned_miner * 0.01", target="smith"),

        # Probability
        ProbabilityNode(id="crit_miner", expected_value=1.0, crit_chance=0.1, crit_multiplier=2.0),

        # Autobuyer
        AutobuyerNode(id="auto_miner", target="miner", interval=5.0),

        # Prestige
        PrestigeLayer(
            id="prestige", name="Prestige",
            formula_expr="floor(sqrt(lifetime_gold))",
            layer_index=1, reset_scope=["miner", "smith", "gold"],
            persistence_scope=["prestige_pts"],
            currency_id="prestige_pts",
        ),
    ]
    edges = [
        Edge(id="e_miner_gold", source="miner", target="gold", edge_type="production_target"),
        Edge(id="e_smith_gold", source="smith", target="gold", edge_type="production_target"),
        Edge(id="e_wizard_mana", source="wizard", target="mana", edge_type="production_target"),
        Edge(id="e_drain_mana", source="mana_drain", target="mana", edge_type="consumption"),
        Edge(id="e_crit", source="crit_miner", target="miner", edge_type="state_modifier",
             formula="1 + 0.1 * (2.0 - 1)", target_property="base_production", modifier_mode="multiply"),
    ]
    return GameDefinition(
        schema_version="1.0", name="FullMechanics",
        nodes=nodes, edges=edges,
        stacking_groups={"speed": "multiplicative", "tick": "multiplicative"},
    )
```

- [ ] **Step 2: Write integration test**

```python
# tests/test_fullmechanics.py
import pytest
from tests.fixtures.fullmechanics import make_fullmechanics_game
from idleframework.model.state import GameState
from idleframework.engine.segments import PiecewiseEngine
from idleframework.optimizer.greedy import GreedyOptimizer


def test_fullmechanics_game_loads():
    game = make_fullmechanics_game()
    assert len(game.nodes) == 15
    state = GameState.from_game(game)
    assert "gold" in state.node_states


def test_fullmechanics_engine_runs():
    game = make_fullmechanics_game()
    state = GameState.from_game(game)
    state.get("miner").owned = 1
    state.get("smith").owned = 1
    state.get("wizard").owned = 1
    engine = PiecewiseEngine(game, state)
    engine.advance_to(60.0)
    assert engine.get_balance("gold") > 100.0


def test_fullmechanics_greedy_optimizer():
    game = make_fullmechanics_game()
    state = GameState.from_game(game)
    state.get("miner").owned = 1
    opt = GreedyOptimizer(game, state)
    steps = opt.run(target_time=300.0, max_steps=50)
    assert len(steps) > 0
```

- [ ] **Step 3: Run tests, verify pass**

Run: `pytest tests/test_fullmechanics.py -v`

- [ ] **Step 4: Run full test suite**

Run: `pytest tests/ -x -q`

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/fullmechanics.py tests/test_fullmechanics.py
git commit -m "test: add FullMechanics fixture exercising all Phase 5 mechanics"
```

### Task 26: Hypothesis Property Tests for New Mechanics

**Files:**
- Create: `tests/test_mechanics_props.py`

- [ ] **Step 1: Write property tests**

```python
# tests/test_mechanics_props.py
"""Property-based tests for new Phase 5 mechanics."""
import pytest
from hypothesis import given, strategies as st, assume

from idleframework.model.nodes import (
    Resource, Generator, TickspeedNode, DrainNode, BuffNode,
)
from idleframework.model.edges import Edge
from idleframework.model.game import GameDefinition
from idleframework.model.state import GameState
from idleframework.engine.segments import PiecewiseEngine


@given(tickspeed=st.floats(min_value=0.1, max_value=100.0))
def test_tickspeed_always_scales_production(tickspeed):
    """Higher tickspeed always means higher production."""
    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold"),
            Generator(id="g1", name="G", base_production=1.0, cost_base=100, cost_growth_rate=1.15),
            TickspeedNode(id="ts1", base_tickspeed=tickspeed),
        ],
        edges=[Edge(id="e1", source="g1", target="gold", edge_type="production_target")],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("g1").owned = 1
    engine = PiecewiseEngine(game, state)
    rates = engine.compute_production_rates()
    assert rates["gold"] == pytest.approx(tickspeed * 1.0, rel=1e-6)


@given(
    multiplier=st.floats(min_value=1.01, max_value=100.0),
    duration=st.floats(min_value=0.1, max_value=1000.0),
    cooldown=st.floats(min_value=0.01, max_value=1000.0),
)
def test_buff_ev_between_1_and_multiplier(multiplier, duration, cooldown):
    """Timed buff EV is always between 1.0 and the raw multiplier."""
    ev = 1.0 + (multiplier - 1.0) * (duration / (duration + cooldown))
    assert 1.0 <= ev <= multiplier


@given(drain_rate=st.floats(min_value=0.01, max_value=100.0))
def test_drain_exceeding_production_depletes(drain_rate):
    """When drain > production, resource decreases."""
    assume(drain_rate > 1.0)  # production is 1.0
    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold", initial_value=100.0),
            Generator(id="g1", name="G", base_production=1.0, cost_base=10000, cost_growth_rate=1.15),
            DrainNode(id="d1", rate=drain_rate),
        ],
        edges=[
            Edge(id="e1", source="g1", target="gold", edge_type="production_target"),
            Edge(id="e2", source="d1", target="gold", edge_type="consumption"),
        ],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("g1").owned = 1
    engine = PiecewiseEngine(game, state)
    initial = engine.get_balance("gold")
    engine.advance_to(10.0)
    assert engine.get_balance("gold") < initial
```

- [ ] **Step 2: Run tests, verify pass**

Run: `pytest tests/test_mechanics_props.py -v`

- [ ] **Step 3: Commit**

```bash
git add tests/test_mechanics_props.py
git commit -m "test: add Hypothesis property tests for new mechanics"
```

### Task 26b: Multi-Layer Prestige Timing in Optimizer

**Files:**
- Modify: `src/idleframework/optimizer/greedy.py`
- Test: `tests/test_greedy.py`

- [ ] **Step 1: Write failing test**

```python
def test_greedy_prestige_action():
    """Optimizer should consider prestige as a candidate action."""
    from idleframework.model.nodes import Resource, Generator, PrestigeLayer
    from idleframework.model.edges import Edge
    from idleframework.model.game import GameDefinition
    from idleframework.model.state import GameState
    from idleframework.optimizer.greedy import GreedyOptimizer

    game = GameDefinition(
        schema_version="1.0", name="test",
        nodes=[
            Resource(id="gold", name="Gold", initial_value=0.0),
            Resource(id="prestige_pts", name="PP"),
            Generator(id="gen1", name="G", base_production=1.0, cost_base=10, cost_growth_rate=1.15),
            PrestigeLayer(id="p1", formula_expr="floor(sqrt(lifetime_gold))",
                         layer_index=1, reset_scope=["gen1", "gold"],
                         currency_id="prestige_pts"),
        ],
        edges=[Edge(id="e1", source="gen1", target="gold", edge_type="production_target")],
        stacking_groups={},
    )
    state = GameState.from_game(game)
    state.get("gen1").owned = 1
    state.lifetime_earnings["gold"] = 10000.0
    opt = GreedyOptimizer(game, state)
    # Should be able to evaluate prestige as an action
    candidates = opt.get_candidates()
    prestige_candidates = [c for c in candidates if c.get("type") == "prestige"]
    # At minimum, prestige should appear as a candidate when gain > 0
```

- [ ] **Step 2: Run test, verify fails**
- [ ] **Step 3: Implement prestige as candidate action in greedy**

Add prestige layers to `get_candidates()` and `find_best_purchase()`. Use per-layer greedy heuristic: compute `prestige_gain / run_time` as efficiency. Label results with `approximation_level: "greedy_heuristic"`.

- [ ] **Step 4: Run tests, verify pass**
- [ ] **Step 5: Commit**

```bash
git add src/idleframework/optimizer/greedy.py tests/test_greedy.py
git commit -m "feat: greedy optimizer considers prestige as candidate action"
```

### Task 26c: Approximation Level Labels

**Files:**
- Modify: `src/idleframework/optimizer/greedy.py`
- Modify: `src/idleframework/engine/segments.py`

- [ ] **Step 1: Add approximation_level to OptimizeResult**

```python
@dataclass
class OptimizeResult:
    purchases: list = field(default_factory=list)
    timeline: list[dict] = field(default_factory=list)
    final_production: float = 0.0
    final_balance: float = 0.0
    final_time: float = 0.0
    approximation_level: str = "exact"  # NEW: "exact", "expected_value", "greedy_heuristic"
```

- [ ] **Step 2: Set labels based on mechanics in play**

In `GreedyOptimizer.optimize()`, detect which mechanics are active:
```python
has_buffs = any(isinstance(n, BuffNode) for n in self.game.nodes)
has_crit = any(isinstance(n, ProbabilityNode) for n in self.game.nodes)
has_prestige = any(isinstance(n, PrestigeLayer) for n in self.game.nodes)

if has_prestige:
    level = "greedy_heuristic"
elif has_buffs or has_crit:
    level = "expected_value"
else:
    level = "exact"
```

- [ ] **Step 3: Commit**

```bash
git add src/idleframework/optimizer/greedy.py src/idleframework/engine/segments.py
git commit -m "feat: add approximation_level labels to OptimizeResult"
```

### Task 26d: Beam/MCTS/B&B Expanded Action Space

**Files:**
- Modify: `src/idleframework/optimizer/beam.py`
- Modify: `src/idleframework/optimizer/mcts.py`
- Modify: `src/idleframework/optimizer/bnb.py`

- [ ] **Step 1: Review current action space generation in each optimizer**

Read beam.py, mcts.py, bnb.py to find where candidate actions are generated.

- [ ] **Step 2: Extend action space to include prestige-per-layer and new upgrade types**

Since these optimizers use `PiecewiseEngine` internally, the engine already handles all new mechanics. The key changes:
- Add "prestige layer N" as a candidate action alongside purchases
- Include tickspeed upgrades, buff upgrades, autobuyer unlocks in candidate lists
- Update B&B upper bound estimates to account for tickspeed (global multiplier) and prestige (exponential jumps)

- [ ] **Step 3: Run existing optimizer tests**

Run: `pytest tests/test_beam.py tests/test_mcts_bnb.py -v`

- [ ] **Step 4: Commit**

```bash
git add src/idleframework/optimizer/beam.py src/idleframework/optimizer/mcts.py src/idleframework/optimizer/bnb.py
git commit -m "feat: expand Beam/MCTS/B&B action space for new mechanics"
```

---

## Chunk 6: UI Integration (Phase 6)

### Task 27: TypeScript Interfaces for New Node Types

**Files:**
- Modify: `frontend/src/editor/types.ts`
- Test: Manual — TypeScript compilation check

- [ ] **Step 1: Add interfaces**

Add to `frontend/src/editor/types.ts`:

```typescript
export interface TickspeedNodeData extends NodeDataBase {
  nodeType: 'tickspeed'
  name: string
  base_tickspeed: number
}

export interface AutobuyerNodeData extends NodeDataBase {
  nodeType: 'autobuyer'
  name: string
  target: string
  interval: number
  priority: number
  condition: string
  bulk_amount: '1' | '10' | 'max'
  enabled: boolean
}

export interface DrainNodeData extends NodeDataBase {
  nodeType: 'drain'
  name: string
  rate: number
  condition: string
}

export interface BuffNodeData extends NodeDataBase {
  nodeType: 'buff'
  name: string
  buff_type: 'timed' | 'proc'
  duration: number
  proc_chance: number
  multiplier: number
  target: string
  cooldown: number
}

export interface SynergyNodeData extends NodeDataBase {
  nodeType: 'synergy'
  name: string
  sources: string[]
  formula_expr: string
  target: string
}
```

Add to `EditorNodeData` union. Add colors to `NODE_COLORS`:
```typescript
tickspeed: '#06b6d4',   // cyan
autobuyer: '#f97316',   // orange
drain: '#dc2626',       // red
buff: '#eab308',        // gold/yellow
synergy: '#a855f7',     // purple
```

Add factories to `defaultNodeData()`.

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/editor/types.ts
git commit -m "feat: add TypeScript interfaces for new node types"
```

### Task 28: React Flow Node Components (5 new)

**Files:**
- Create: `frontend/src/editor/nodes/TickspeedNode.tsx`
- Create: `frontend/src/editor/nodes/AutobuyerNode.tsx`
- Create: `frontend/src/editor/nodes/DrainNode.tsx`
- Create: `frontend/src/editor/nodes/BuffNode.tsx`
- Create: `frontend/src/editor/nodes/SynergyNode.tsx`

- [ ] **Step 1: Read existing node component for pattern**

Read: `frontend/src/editor/nodes/GeneratorNode.tsx`

- [ ] **Step 2: Create all 5 node components following BaseNode pattern**

Each follows:
```tsx
export default function TickspeedNode({ data, selected }: NodeProps<EditorNode>) {
  if (data.nodeType !== 'tickspeed') return null
  return (
    <BaseNode nodeType="tickspeed" name={data.name} selected={selected}>
      <div className="text-sm">{data.base_tickspeed}x speed</div>
    </BaseNode>
  )
}
```

- [ ] **Step 3: Register in node type map**

Add all 5 to wherever custom node types are registered (likely in editor setup).

- [ ] **Step 4: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/editor/nodes/
git commit -m "feat: add 5 new React Flow node components"
```

### Task 29: PropertyPanel Fields for New Node Types

**Files:**
- Modify: `frontend/src/editor/PropertyPanel.tsx`

- [ ] **Step 1: Read current PropertyPanel**

Read: `frontend/src/editor/PropertyPanel.tsx`

- [ ] **Step 2: Add TypeFields cases for all 5 new types**

Follow existing pattern with Field, NumberField, SelectField, CheckboxField.

- [ ] **Step 3: Add enhanced fields for existing nodes**

- PrestigeLayer: `currency_id` (resource select), `parent_layer` (prestige node select)
- Resource: `capacity` (optional number), `overflow_behavior` (select: clamp/waste)
- Converter: `recipe_type` (select: fixed/scaling), `conversion_limit` (optional number)

- [ ] **Step 4: Verify TypeScript compiles**
- [ ] **Step 5: Commit**

```bash
git add frontend/src/editor/PropertyPanel.tsx
git commit -m "feat: add property panel fields for new and enhanced node types"
```

### Task 30: Edge Property Enhancements

**Files:**
- Modify: `frontend/src/editor/PropertyPanel.tsx` (edge section)

- [ ] **Step 1: Add target_property and modifier_mode fields**

For state_modifier edges, add:
- `target_property`: select dropdown populated from target node's numeric fields
- `modifier_mode`: select (set/add/multiply)

- [ ] **Step 2: Verify TypeScript compiles**
- [ ] **Step 3: Commit**

```bash
git add frontend/src/editor/PropertyPanel.tsx
git commit -m "feat: add edge property fields for state modifier targeting"
```

### Task 31: Node Palette Reorganization

**Files:**
- Modify: `frontend/src/editor/NodePalette.tsx`

- [ ] **Step 1: Read current palette**
- [ ] **Step 2: Reorganize into groups**

- Flow: Resource, Generator, NestedGenerator, Converter
- Modifiers: Upgrade, BuffNode, SynergyNode, DrainNode, ProbabilityNode
- Automation: Manager, AutobuyerNode, TickspeedNode
- Progression: PrestigeLayer, UnlockGate, Achievement, SacrificeNode
- Logic: Register, Gate, Queue, ChoiceGroup, EndCondition

- [ ] **Step 3: Verify TypeScript compiles**
- [ ] **Step 4: Commit**

```bash
git add frontend/src/editor/NodePalette.tsx
git commit -m "feat: reorganize node palette into functional groups"
```

### Task 32: graphToGame / gameToGraph Extensions

**Files:**
- Modify: `frontend/src/editor/conversion.ts` (or wherever these functions live)
- Test: `tests/test_api/test_editor_workflow.py`

- [ ] **Step 1: Read current conversion functions**
- [ ] **Step 2: Add conversion for 5 new node types + enhanced fields**
- [ ] **Step 3: Write round-trip test**
- [ ] **Step 4: Verify TypeScript compiles and tests pass**
- [ ] **Step 5: Commit**

```bash
git add frontend/src/editor/
git commit -m "feat: extend graphToGame/gameToGraph for new node types"
```

---

## Chunk 7: Performance Optimization (Phase 7)

### Task 33: Benchmark Suite Setup

**Files:**
- Create: `benchmarks/run_benchmarks.py`
- Create: `benchmarks/__init__.py`

- [ ] **Step 1: Create benchmark runner**

```python
# benchmarks/run_benchmarks.py
"""Benchmark suite for IdleFramework engine and optimizer performance."""
import time
import cProfile
import json
from pathlib import Path

from idleframework.model.state import GameState
from idleframework.engine.segments import PiecewiseEngine
from idleframework.optimizer.greedy import GreedyOptimizer
from tests.conftest import make_minicap_game, make_mediumcap_game
from tests.fixtures.largecap import make_largecap_game


FIXTURES = {
    "MiniCap": make_minicap_game,
    "MediumCap": make_mediumcap_game,
    "LargeCap": make_largecap_game,
}
HORIZONS = [3600, 36000]  # 1hr, 10hr in seconds


def benchmark_engine(name, game_factory, horizon):
    game = game_factory()
    state = GameState.from_game(game)
    # Give initial owned to avoid empty state
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
    steps = opt.run(target_time=float(horizon), max_steps=500)
    elapsed = time.perf_counter() - start
    return {"fixture": name, "horizon": horizon, "greedy_seconds": round(elapsed, 4),
            "steps": len(steps)}


def main():
    results = []
    for name, factory in FIXTURES.items():
        for horizon in HORIZONS:
            results.append(benchmark_engine(name, factory, horizon))
            results.append(benchmark_greedy(name, factory, horizon))
            print(f"  {name} @ {horizon}s done")

    out_path = Path("docs/benchmarks") / f"baseline-{time.strftime('%Y-%m-%d')}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\nBaseline saved to {out_path}")

    for r in results:
        print(r)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run benchmarks to establish baseline**

Run: `python benchmarks/run_benchmarks.py`

- [ ] **Step 3: Commit**

```bash
git add benchmarks/ docs/benchmarks/
git commit -m "perf: add benchmark suite and establish baselines"
```

### Task 34: Cython BigFloat

**Files:**
- Create: `src/idleframework/_bigfloat_cython.pyx`
- Modify: `src/idleframework/bigfloat.py` (conditional import)
- Create: `setup_cython.py`
- Test: existing `tests/test_bigfloat.py` and `tests/test_bigfloat_props.py`

- [ ] **Step 1: Create Cython implementation**

```cython
# src/idleframework/_bigfloat_cython.pyx
# Cython BigFloat with C-level arithmetic
cdef class BigFloat:
    cdef public double mantissa
    cdef public long exponent

    def __init__(self, value=0.0, long exponent=0):
        if isinstance(value, (int, float)):
            self.mantissa = float(value)
            self.exponent = exponent
            self._normalize()
        # ... same API as pure Python BigFloat
```

- [ ] **Step 2: Add conditional import to bigfloat.py**

```python
try:
    from idleframework._bigfloat_cython import BigFloat as _CyBigFloat
    BigFloat = _CyBigFloat
except ImportError:
    pass  # Use pure Python BigFloat defined above
```

- [ ] **Step 3: Run existing BigFloat tests**

Run: `pytest tests/test_bigfloat.py tests/test_bigfloat_props.py -v`
Expected: All pass (with or without Cython)

- [ ] **Step 4: Commit**

```bash
git add src/idleframework/_bigfloat_cython.pyx src/idleframework/bigfloat.py setup_cython.py
git commit -m "perf: add Cython BigFloat with pure-Python fallback"
```

### Task 35: Numba Inner Loops

**Files:**
- Create: `src/idleframework/engine/_numba_accel.py`
- Modify: `src/idleframework/engine/solvers.py` (use accelerated if available)

- [ ] **Step 1: Create Numba-accelerated functions**

```python
# src/idleframework/engine/_numba_accel.py
"""Numba-accelerated inner loops for engine hot paths."""
try:
    from numba import njit
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False
    def njit(*args, **kwargs):
        def decorator(f):
            return f
        return decorator if not args else args[0]

import numpy as np


@njit(cache=True)
def bulk_purchase_cost_fast(base: float, growth: float, owned: int, count: int) -> float:
    """Compute cost of buying `count` units starting from `owned`."""
    if abs(growth - 1.0) < 1e-12:
        return base * count
    total = 0.0
    for i in range(count):
        total += base * growth ** (owned + i)
    return total


@njit(cache=True)
def efficiency_scores_batch(
    productions: np.ndarray,
    costs: np.ndarray,
) -> np.ndarray:
    """Vectorized efficiency = production / cost."""
    result = np.empty_like(productions)
    for i in range(len(productions)):
        if costs[i] > 0:
            result[i] = productions[i] / costs[i]
        else:
            result[i] = np.inf
    return result
```

- [ ] **Step 2: Add float64 range detection and fallback**

```python
MAX_FLOAT64 = 1e308

def can_use_numba(value: float) -> bool:
    return HAS_NUMBA and abs(value) < MAX_FLOAT64
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_solvers.py -v`

- [ ] **Step 4: Commit**

```bash
git add src/idleframework/engine/_numba_accel.py
git commit -m "perf: add Numba-accelerated inner loop functions"
```

### Task 36: NumPy Batch Operations in Engine

**Files:**
- Modify: `src/idleframework/engine/segments.py`

- [ ] **Step 1: Add vectorized compute_production_rates path**

When many generators exist, batch-compute rates using NumPy:

```python
def _compute_production_rates_vectorized(self) -> dict[str, float]:
    """Vectorized production rate computation for large games."""
    import numpy as np
    # ... extract arrays, compute vectorized, map back to dict
```

- [ ] **Step 2: Run benchmarks to compare**

Run: `python benchmarks/run_benchmarks.py`

- [ ] **Step 3: Commit**

```bash
git add src/idleframework/engine/segments.py
git commit -m "perf: add NumPy vectorized production rate computation"
```

### Task 37: Final Benchmark Comparison

- [ ] **Step 1: Run full benchmark suite**

Run: `python benchmarks/run_benchmarks.py`

- [ ] **Step 2: Compare with baselines**

- [ ] **Step 3: Document results**

Create `docs/benchmarks/comparison-YYYY-MM-DD.md`

- [ ] **Step 4: Run full test suite**

Run: `pytest tests/ -x -q`
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add docs/benchmarks/
git commit -m "perf: document benchmark comparison results"
```

---

## Chunk 8: Final Integration & Regression

### Task 38: Full Regression Test

- [ ] **Step 1: Run entire test suite**

Run: `pytest tests/ -v --tb=short`
Expected: All tests pass

- [ ] **Step 2: Run MiniCap and MediumCap e2e tests**

Run: `pytest tests/test_e2e_minicap.py -v`

- [ ] **Step 3: Run FullMechanics integration test**

Run: `pytest tests/test_fullmechanics.py -v`

- [ ] **Step 4: Verify frontend builds**

Run: `cd frontend && npm run build`

- [ ] **Step 5: Fix any failures and commit**

### Task 39: Update Existing Fixtures with New Mechanics (Optional)

- [ ] **Step 1: Extend MiniCap with a TickspeedNode and one BuffNode**
- [ ] **Step 2: Run MiniCap tests to verify no regressions**
- [ ] **Step 3: Commit**

```bash
git commit -m "feat: extend MiniCap fixture with tickspeed and buff"
```
