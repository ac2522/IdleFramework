# Phases 5-6-7: Complete Mechanics, UI Integration & Performance

**Date:** 2026-03-12
**Status:** Approved
**Approach:** Engine-Then-Polish (Approach B) — all mechanics in one engine phase, then UI, then performance.

## Overview

Phases 1-4 delivered the core framework: BigFloat, DSL, graph model, piecewise engine, 4-tier optimizer, FastAPI server, React Flow editor, and example game UI. This design covers the next three phases:

- **Phase 5:** All new idle game mechanics (model, engine, optimizer, tests)
- **Phase 6:** UI integration (React Flow node components, property panels, edge enhancements)
- **Phase 7:** Performance profiling and optimization (Cython, Numba, NumPy)

### Design Principle: Composability Through State Edges

Every new mechanic is either a new node type or an enhancement to an existing node. State edges connect everything — any upgrade (purchased with any currency, including prestige currencies) can modify any property of any node. This enables the full combinatorial space that idle games require (e.g., a prestige-currency upgrade that boosts crit rate on a specific generator).

### Scope

**In-scope:**
- Multi-layer prestige with per-layer currencies and cross-layer bonuses
- Tickspeed as a global production multiplier (upgradeable)
- Autobuyers with configurable intervals, priorities, and conditions
- Proc/crit chance with upgradeable probability and multiplier
- Timed and proc-based buffs (analyzed via expected value)
- Resource drains / upkeep (negative flow with break-even analysis)
- Resource caps / storage limits (optional per-resource)
- Synergy bonuses (cross-generator interactions)
- Resource conversion chain enhancements
- Milestone/threshold unlocks (via composable UnlockGate + Upgrade pairs)
- Parallel resource allocation (via Register + state edges)
- State edge evaluation in engine (the composability linchpin)
- Performance: Cython BigFloat, Numba inner loops, NumPy batch operations

**Out-of-scope (deferred):**
- Branching skill/tech trees (future phase)
- Challenge runs with restriction mechanics
- Offline/idle production (reduced-rate simulation)
- Wrinkler/parasite mechanics (too niche)
- Authentication, database, multi-user
- GPU acceleration, WASM compilation

---

## Phase 5: All New Mechanics

### 5.1 New Node Types

#### 5.1.1 TickspeedNode

Global game speed multiplier. All production rates are multiplied by the resolved tickspeed value.

```python
class TickspeedNode(NodeBase):
    type: Literal["tickspeed"] = "tickspeed"
    name: str = "Tickspeed"
    base_tickspeed: float = 1.0  # Default ticks per second
```

- Upgradeable via regular Upgrade nodes targeting the tickspeed node
- State edges can modify `base_tickspeed` dynamically
- Engine resolves final tickspeed = base_tickspeed * all applicable upgrade multipliers
- A single game should have at most one TickspeedNode (validated)

#### 5.1.2 AutobuyerNode

Automatically purchases a target node at configurable intervals.

```python
class AutobuyerNode(NodeBase):
    type: Literal["autobuyer"] = "autobuyer"
    name: str = ""
    target: str                           # Node ID to auto-purchase
    interval: float = 1.0                 # Seconds between attempts
    priority: int = 0                     # Higher = buys first when competing
    condition: str | None = None          # DSL formula condition
    bulk_amount: Literal[1, 10, "max"] = 1
    enabled: bool = True                  # Toggleable via activator edges
```

- Changes the optimization landscape: optimizer skips autobuyer-managed targets
- Unlockable via UnlockGate (e.g., unlock autobuyer after buying 100 generators)
- `interval` and `priority` modifiable via state edges
- `condition` evaluated each interval tick (e.g., `"balance > cost * 2"`)

#### 5.1.3 DrainNode

Continuous resource consumption creating break-even dynamics.

```python
class DrainNode(NodeBase):
    type: Literal["drain"] = "drain"
    name: str = ""
    target_resource: str        # Resource being consumed
    rate: float                 # Base consumption per second
    condition: str | None = None  # Only drains when condition is true
```

- Net production = generator rates - drain rates
- If net < 0, resource depletes; engine handles zero-crossing time
- `rate` modifiable via state edges (upgrades can reduce drain)
- `condition` allows conditional drains (e.g., only while a toggle is active)

#### 5.1.4 BuffNode

Temporary or probabilistic multiplier effects, analyzed via expected value for closed-form engine.

```python
class BuffNode(NodeBase):
    type: Literal["buff"] = "buff"
    name: str = ""
    buff_type: Literal["timed", "proc"]
    duration: float | None = None         # Seconds active (timed buffs)
    proc_chance: float | None = None      # Probability 0-1 (proc buffs)
    multiplier: float = 2.0              # Effect magnitude
    target: str | None = None            # Specific node ID, or None for global
    cooldown: float = 0.0                # Minimum seconds between activations
```

- **Timed buffs:** `effective_multiplier = 1 + (multiplier - 1) * (duration / (duration + cooldown))`
- **Proc buffs:** `effective_multiplier = 1 + proc_chance * (multiplier - 1)`
- Folds into per-generator multiplier during production rate computation
- All fields (`proc_chance`, `multiplier`, `duration`, `cooldown`) independently modifiable via state edges
- Upgrades can target specific buff properties (e.g., "increase crit multiplier by 50%")

#### 5.1.5 SynergyNode

Cross-generator interaction bonuses that prevent lower-tier obsolescence.

```python
class SynergyNode(NodeBase):
    type: Literal["synergy"] = "synergy"
    name: str = ""
    sources: list[str]          # Node IDs contributing to synergy
    formula_expr: str           # DSL formula computing bonus
    target: str                 # Node receiving the bonus
```

- `formula_expr` evaluated each segment with source nodes' `owned` counts as variables
- Result becomes a dynamic multiplier applied to `target` via stacking system
- Example: `"owned_cursor * 0.001"` applied to grandma production (Cookie Clicker pattern)
- Formula has access to all source node states via `owned_<source_id>` variables

### 5.2 Enhanced Existing Nodes

#### 5.2.1 PrestigeLayer — Multi-Layer Support

```python
class PrestigeLayer(NodeBase):
    # Existing fields...
    type: Literal["prestige_layer"] = "prestige_layer"
    formula_expr: str
    layer_index: int
    reset_scope: list[str]
    persistence_scope: list[str]
    bonus_type: str
    # New fields:
    currency_id: str | None = None       # Resource that stores prestige currency
    parent_layer: str | None = None      # Higher layer that resets this one
```

- **Layer chaining:** Layer 0 (main) → Layer 1 (prestige) → Layer 2 (transcendence) → ...
- When layer N resets: iterate layers 0..N-1, reset their scopes
- `persistence_scope` defines what survives a reset at each layer
- Cross-layer bonuses flow via state edges from higher-layer currency resources to lower-layer multipliers
- `currency_id` points to a Resource node that accumulates prestige currency
- Prestige currency is spendable on upgrades in that layer's upgrade tree

#### 5.2.2 Resource — Capacity & Overflow

```python
class Resource(NodeBase):
    # Existing fields...
    type: Literal["resource"] = "resource"
    name: str
    initial_value: float
    # New fields:
    capacity: float | None = None                              # None = unlimited
    overflow_behavior: Literal["clamp", "waste"] = "clamp"     # What happens at cap
```

- Engine clamps `current_value` to `capacity` after each production step
- `capacity` modifiable via state edges (storage upgrades)
- `waste` means excess production is lost; `clamp` means production stops at cap

#### 5.2.3 Converter — Enhanced Conversion Chains

```python
class Converter(NodeBase):
    # Existing fields...
    type: Literal["converter"] = "converter"
    inputs: list[dict]     # [{resource_id, amount}]
    outputs: list[dict]    # [{resource_id, amount}]
    rate: float
    # New fields:
    recipe_type: Literal["fixed", "scaling"] = "fixed"
    conversion_limit: int | None = None    # Max conversions per cycle
```

- `fixed`: constant input/output ratios
- `scaling`: ratios change based on quantity converted (DSL formula per output)
- `conversion_limit`: caps throughput per engine cycle

#### 5.2.4 ProbabilityNode — Engine-Evaluated Crit

No model changes needed. Existing fields:
- `crit_chance: float`
- `crit_multiplier: float`
- `expected_value: float`
- `variance: float`

Engine now evaluates: `effective_rate = base_rate * (1 + crit_chance * (crit_multiplier - 1))`

State edges can target `crit_chance` and `crit_multiplier` independently, enabling upgrades like "Prestige Upgrade: +5% crit chance on Lemonade Stands."

### 5.3 Edge Model Enhancements

#### 5.3.1 State Modifier Edge — Property Targeting

```python
class Edge(BaseModel):
    # Existing fields...
    id: str
    source: str
    target: str
    edge_type: str
    rate: float | None = None
    formula: str | None = None
    condition: str | None = None
    # New fields:
    target_property: str | None = None       # Which property to modify
    modifier_mode: Literal["set", "add", "multiply"] | None = None
```

- `target_property`: field name on target node (e.g., `"base_production"`, `"crit_chance"`, `"rate"`, `"base_tickspeed"`)
- `modifier_mode`: how the formula result is applied
  - `set`: override property value
  - `add`: add to base value
  - `multiply`: multiply base value
- Only required when `edge_type == "state_modifier"`
- Validated: `target_property` must be a valid field on the target node type

### 5.4 Engine Changes

#### 5.4.1 State Edge Evaluation (New)

The core composability mechanism. Runs at the start of each segment.

```
evaluate_state_edges(game, state):
    1. Collect all state_modifier edges
    2. Build dependency graph (edge A depends on B if A's formula refs B's target property)
    3. Topological sort → evaluation order (cycle = validation error at game load)
    4. For each edge in order:
       a. Compile formula with current state as variables
       b. Evaluate → result value
       c. Apply to target node's property using modifier_mode
    5. Return modified property map (used by subsequent engine phases)
```

Variables available in state edge formulas:
- `owned_<node_id>`: owned count of any node
- `balance_<resource_id>`: current balance of any resource
- `level_<node_id>`: level of any node
- `lifetime_<resource_id>`: lifetime earnings of any resource
- `total_production_<node_id>`: total production of any node
- `elapsed_time`, `run_time`: time variables

#### 5.4.2 Revised Engine Loop

```
PiecewiseEngine.advance_to(target_time):
    loop:
        1. apply_free_purchases()
        2. evaluate_state_edges()              ← NEW
        3. compute_tickspeed()                 ← NEW
        4. compute_production_rates()          ← MODIFIED: ×tickspeed, +crit EV, +synergies
        5. apply_drains()                      ← NEW: subtract drain rates
        6. apply_resource_caps()               ← NEW: clamp to capacity
        7. evaluate_buffs()                    ← NEW: fold expected-value multipliers
        8. evaluate_autobuyers()               ← NEW: auto-purchases at intervals
        9. find_next_purchase()                ← MODIFIED: skip autobuyer targets
        10. advance time, record segment
        11. if past target_time: break
```

#### 5.4.3 Tickspeed Resolution

```
compute_tickspeed():
    tickspeed_node = find TickspeedNode (if any)
    if none: return 1.0
    base = tickspeed_node.base_tickspeed (possibly modified by state edges in step 2)
    upgrades = all Upgrades targeting tickspeed node
    multiplier = compute_stacking_multiplier(upgrades)
    return base * multiplier
```

All generator rates multiplied by this value in step 4.

#### 5.4.4 Drain Processing

```
apply_drains():
    for each DrainNode:
        if condition is None or evaluate(condition) is truthy:
            resource = state[drain.target_resource]
            net_rate[resource] -= drain.rate
    # Handle zero-crossing: if net_rate < 0 and resource > 0,
    # compute time_to_zero = resource.current_value / abs(net_rate)
    # Create segment boundary at zero-crossing
```

#### 5.4.5 Buff Processing

```
evaluate_buffs():
    for each BuffNode:
        if buff_type == "timed":
            ev = 1 + (multiplier - 1) * (duration / (duration + cooldown))
        elif buff_type == "proc":
            ev = 1 + proc_chance * (multiplier - 1)

        if target is None:  # global
            global_multiplier *= ev
        else:
            per_generator_multiplier[target] *= ev
```

#### 5.4.6 Autobuyer Processing

```
evaluate_autobuyers():
    active_autobuyers = [a for a in autobuyers if a.enabled and unlocked(a)]
    sort by priority (descending)
    for each autobuyer:
        time_since_last = elapsed - autobuyer_last_fired[a.id]
        if time_since_last >= a.interval:
            if condition is None or evaluate(condition):
                if can_afford(a.target, a.bulk_amount):
                    purchase(a.target, a.bulk_amount)
                    autobuyer_last_fired[a.id] = elapsed
```

#### 5.4.7 Multi-Layer Prestige

```
execute_prestige(layer_id):
    layer = game.get_node(layer_id)

    # Compute prestige currency gain
    gain = evaluate_formula(layer.formula_expr, state_variables)

    # Deposit into currency resource
    if layer.currency_id:
        state[layer.currency_id].current_value += gain

    # Reset all lower layers
    for lower_layer in layers where layer_index < layer.layer_index:
        execute_reset(lower_layer.reset_scope, lower_layer.persistence_scope)

    # Reset this layer's scope
    execute_reset(layer.reset_scope, layer.persistence_scope)

    # Reset run_time (for this layer's run tracking)
    state.run_time = 0.0
```

#### 5.4.8 Milestone Thresholds (Composable Approach)

No engine changes needed. Milestones are modeled as:
- `UnlockGate` with `condition_type: "ownership"` and `targets: ["generator_id"]`
- `Upgrade` with `unlock_dependency` edge from the gate
- Engine evaluates UnlockGate conditions during `apply_free_purchases()` phase

Example: "At 25 lemonade stands, production x2" = UnlockGate(condition: owned >= 25) → Upgrade(magnitude: 2.0, target: lemonade_stand)

### 5.5 Optimizer Changes

#### 5.5.1 Greedy Optimizer — New Efficiency Calculations

| Purchasable | Efficiency Formula |
|---|---|
| Generator | `delta_production / cost` (existing) |
| Upgrade (multiplicative) | `production * (magnitude - 1) / cost` (existing) |
| Tickspeed upgrade | `total_production * (tick_delta - 1) / cost` |
| Crit chance upgrade | `target_production * delta_crit_ev / cost` |
| Crit multiplier upgrade | `target_production * delta_crit_ev / cost` |
| Buff upgrade (any field) | `affected_production * delta_effective_multiplier / cost` |
| Drain reduction | `drain_rate_saved / cost` |
| Autobuyer unlock | Heuristic: `time_saved_over_horizon / cost` |

Where:
- `crit_ev = 1 + crit_chance * (crit_multiplier - 1)`
- `delta_crit_ev = new_crit_ev - old_crit_ev`
- `tick_delta = new_tickspeed / old_tickspeed`

#### 5.5.2 Autobuyer-Aware Purchasing

- `find_next_purchase()` filters out nodes managed by active autobuyers
- Optimizer focuses on: unlocks, upgrades, prestige timing, autobuyer unlocks

#### 5.5.3 Multi-Layer Prestige Timing

Per-layer greedy heuristic:
- For each layer, compute `prestige_gain_rate = d(currency_gain) / d(time)`
- When `prestige_gain_rate` starts diminishing (rate of change is negative), consider resetting
- Higher layers use longer evaluation windows
- Label results with `approximation_level: "greedy_heuristic"`

#### 5.5.4 Beam / MCTS / B&B

These use PiecewiseEngine internally, so new mechanics work automatically. Changes:
- **Expanded action space:** prestige-per-layer, tickspeed upgrades, buff upgrades, autobuyer unlocks
- **B&B pruning:** account for tickspeed (multiplicative global effect) and multi-layer prestige (exponential jumps) in upper bound estimates

### 5.6 Approximation Levels

| Mechanic | Approximation | Label |
|---|---|---|
| Timed/proc buffs | Expected value (continuous) | `"expected_value"` |
| Crit chance/multiplier | Expected value | `"expected_value"` |
| Multi-layer prestige timing | Greedy heuristic | `"greedy_heuristic"` |
| Autobuyer timing | Discrete interval approximation | `"discrete_approximation"` |
| Synergy bonuses | Exact (formula evaluated) | `"exact"` |
| Drain zero-crossing | Exact (analytical) | `"exact"` |

### 5.7 Testing Strategy

- **Unit tests:** Each new node type serialization/deserialization, validation
- **Engine tests:** Each mechanic in isolation (tickspeed multiplies rates, drain subtracts, buffs fold in EV, autobuyers fire at intervals, multi-layer prestige cascades)
- **Integration tests:** MiniCap extended with new mechanics, verify optimizer handles them
- **Property tests (Hypothesis):**
  - Tickspeed > 0 always increases production
  - Drain rate > production rate always depletes resource
  - Buff EV is always between 1.0 and multiplier
  - Multi-layer reset preserves higher-layer state
- **New fixture:** Create a "FullMechanics" fixture that exercises all new mechanics together

---

## Phase 6: UI Integration

### 6.1 New React Flow Node Components (5 new)

Each follows the established pattern: BaseNode wrapper + type-specific display + PropertyPanel fields.

| Component | Color | Display Summary |
|---|---|---|
| `TickspeedNode.tsx` | Cyan/teal | `"{base_tickspeed}x speed"` |
| `AutobuyerNode.tsx` | Orange | Target name + `"every {interval}s"` |
| `DrainNode.tsx` | Dark red | Resource name + `"-{rate}/s"` |
| `BuffNode.tsx` | Gold/yellow | Type badge + `"{multiplier}x for {duration}s"` or `"{proc_chance*100}% chance"` |
| `SynergyNode.tsx` | Purple | Source names → target + formula preview |

### 6.2 TypeScript Interfaces

Add to `frontend/src/editor/types.ts`:
- `TickspeedNodeData`, `AutobuyerNodeData`, `DrainNodeData`, `BuffNodeData`, `SynergyNodeData`
- Add to `EditorNodeData` union
- Add colors to `NODE_COLORS`
- Add factories to `defaultNodeData()`

### 6.3 PropertyPanel Enhancements

**New node type fields:**
- TickspeedNode: `base_tickspeed` (number)
- AutobuyerNode: `target` (node select), `interval` (number), `priority` (number), `condition` (formula), `bulk_amount` (select: 1/10/max), `enabled` (checkbox)
- DrainNode: `target_resource` (resource node select), `rate` (number), `condition` (formula)
- BuffNode: `buff_type` (select: timed/proc), `duration` (number, shown if timed), `proc_chance` (number, shown if proc), `multiplier` (number), `cooldown` (number), `target` (node select, optional)
- SynergyNode: `sources` (multi-node select), `formula_expr` (FormulaField with validation), `target` (node select)

**Enhanced existing node fields:**
- PrestigeLayer: `currency_id` (resource select), `parent_layer` (prestige node select)
- Resource: `capacity` (optional number), `overflow_behavior` (select: clamp/waste)
- Converter: `recipe_type` (select: fixed/scaling), `conversion_limit` (optional number)

### 6.4 Edge Property Enhancements

State modifier edges get two new fields in edge property panel:
- `target_property`: select dropdown populated dynamically from target node's field names
- `modifier_mode`: select (set/add/multiply)

### 6.5 Node Palette Reorganization

Group nodes by function for better discoverability:

- **Flow:** Resource, Generator, NestedGenerator, Converter
- **Modifiers:** Upgrade, BuffNode, SynergyNode, DrainNode
- **Automation:** Manager, AutobuyerNode, TickspeedNode
- **Progression:** PrestigeLayer, UnlockGate, Achievement, SacrificeNode
- **Logic:** Register, Gate, Queue, ChoiceGroup, ProbabilityNode, EndCondition

### 6.6 graphToGame / gameToGraph

Extend conversion functions to handle 5 new node types. Same pattern as existing — map EditorNodeData fields to Pydantic model fields and back.

### 6.7 Testing

- Component render tests for each new node type
- PropertyPanel field interaction tests
- graphToGame/gameToGraph round-trip tests for new node types
- Edge property panel tests for target_property and modifier_mode

---

## Phase 7: Performance Optimization

### 7.1 Profile First — Establish Baselines

**Benchmark suite:**
- Run MiniCap, MediumCap, LargeCap through all 4 optimizers
- Time horizons: 1hr, 10hr, 100hr, 1000hr simulated time
- Tools: `cProfile` for function-level, `line_profiler` for line-level
- Metrics: wall time, function call count, time per call, peak memory
- Record baselines in `docs/benchmarks/baseline-YYYY-MM-DD.md`

### 7.2 Cython BigFloat

Convert BigFloat dataclass to Cython `cdef class`:

```cython
cdef class BigFloat:
    cdef double mantissa
    cdef long exponent
    # All arithmetic at C level
```

- Estimated 3-10x speedup for pow/log dominated workloads
- Keep pure-Python fallback via conditional import:
  ```python
  try:
      from idleframework._bigfloat_cython import BigFloat
  except ImportError:
      from idleframework.bigfloat import BigFloat
  ```
- Must remain immutable (all operations return new instances)
- All existing BigFloat tests + Hypothesis property tests must pass identically

### 7.3 Numba @njit Inner Loops

Extract hot loops into standalone functions:

```python
@njit(cache=True)
def bulk_purchase_cost(base: float, growth: float, owned: int, count: int) -> float:
    ...

@njit(cache=True)
def time_to_afford(cost: float, balance: float, rate: float) -> float:
    ...

@njit(cache=True)
def efficiency_scores(productions: np.ndarray, costs: np.ndarray) -> np.ndarray:
    ...
```

- Functions operate on primitives (float, int, numpy arrays), not BigFloat
- Convert at boundary between engine and Numba functions
- Graceful fallback if Numba not installed (use plain Python versions)

### 7.4 NumPy Struct-of-Arrays

For batch evaluation in `find_next_purchase()` and `compute_production_rates()`:

```python
# Instead of looping over generator objects:
rates = np.array([g.base_production for g in generators])
owned = np.array([state[g.id].owned for g in generators])
cycles = np.array([g.cycle_time for g in generators])
multipliers = np.array([get_multiplier(g) for g in generators])

# Vectorized computation:
production = rates * owned / cycles * multipliers * tickspeed
```

- Only applied to engine/optimizer hot paths
- Model layer remains object-oriented (Pydantic models unchanged)

### 7.5 Benchmark Again

- Re-run identical benchmark suite
- Compare against baselines
- Document per-optimization speedups
- Determine if further optimization needed (target: 10x overall for large games)

### 7.6 What We're NOT Doing

- No GPU acceleration
- No async/parallel optimizer
- No custom memory allocator
- No WASM compilation for frontend
- No premature optimization of non-hot paths

---

## Summary

| Phase | Scope | Key Deliverables |
|---|---|---|
| 5 | All new mechanics | 5 new node types, 4 enhanced nodes, state edge evaluation, revised engine loop, optimizer awareness, tests |
| 6 | UI integration | 5 new React Flow components, enhanced property panels, edge enhancements, palette reorganization |
| 7 | Performance | Profiling baselines, Cython BigFloat, Numba inner loops, NumPy batch ops, benchmark comparison |
