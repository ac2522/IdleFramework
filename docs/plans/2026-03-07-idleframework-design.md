# IdleFramework — Design Document

**Date:** 2026-03-07
**Status:** Approved (Revised after three design reviews)
**Revision:** 4

## Vision

An open-source Python framework for mathematically analyzing idle/incremental game balance. The open-source alternative to Machinations.io — TDD-first, math-driven, with an optional visual node editor.

### Goals

- Help game designers balance idle and incremental games to promote multiple viable strategies
- Use pure mathematics (closed-form solutions, algebraic equations, piecewise analytical methods) rather than simulation
- Identify dominant strategies, dead upgrades, progression walls, and strategy convergence/divergence
- Compare free-to-play vs paid optimal strategies via tag-based filtering
- Provide both a CLI and a visual node-based editor for defining and analyzing games
- TDD-first: every mathematical function validated against analytical results, property-based tests, and convergence-tested simulation

### Non-Goals

- Neural networks or machine learning
- A production-quality game engine
- Plugin/extension system (community contributes node types via PRs instead)
- Equipment/inventory slot-based systems (genre-blending beyond idle/incremental scope)
- Optimal active play assumed — offline/idle production out of scope
- Determinism across platforms is not guaranteed beyond 5-digit tolerance
- Toggle timing optimization (v2)
- Variance propagation through production graph (v2 — ProbabilityNode stores variance field but engine uses expected value only in v1)
- Multi-layer prestige sequence optimization (v2 — greedy heuristic per layer in v1)

---

## Delivery Phases

| Phase | Deliverable | Dependencies |
|---|---|---|
| **Phase 1** | Python library + CLI + Plotly reports + pytest suite | None — complete, shippable product |
| **Phase 2** | FastAPI API | Phase 1 |
| **Phase 3** | React Flow frontend | Phase 2 |
| **Phase 4** | Example game UI | Phase 1 |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│           React Flow Frontend (Phase 3)          │
│   Node editor + Recharts dashboards + Plotly     │
└──────────────────────┬──────────────────────────┘
                       │ REST / WebSocket
┌──────────────────────┴──────────────────────────┐
│              FastAPI Backend (Phase 2)            │
└──────────────────────┬──────────────────────────┘
                       │ imports
┌──────────────────────┴──────────────────────────┐
│         idleframework Python Library (Phase 1)    │
│                                                   │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────┐ │
│  │ Game Model   │  │ Math Engine  │  │Analysis │ │
│  │ (Graph +     │──│ (Closed-form │──│ Engine  │ │
│  │  Pydantic)   │  │  + Piecewise)│  │         │ │
│  └─────────────┘  └──────────────┘  └─────────┘ │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────┐ │
│  │ BigFloat     │  │ Report Gen   │  │ Formula │ │
│  │ (numbers)    │  │ (HTML/Plotly)│  │ DSL     │ │
│  └─────────────┘  └──────────────┘  │ (Lark)  │ │
│  ┌─────────────┐  ┌──────────────┐  └─────────┘ │
│  │ NetworkX     │  │ CLI Wrapper  │               │
│  │ (graph ops)  │  │ (typer)      │               │
│  └─────────────┘  └──────────────┘               │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│          TDD Test Infrastructure                  │
│  ┌──────────────┐  ┌───────────────────────────┐ │
│  │ RK4/Adaptive │  │ Test Fixtures             │ │
│  │ Simulator    │  │ (MiniCap + MediumCap)     │ │
│  │ SciPy/mpmath │  │ pytest + Hypothesis       │ │
│  │ (reference)  │  │                           │ │
│  └──────────────┘  └───────────────────────────┘ │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│     Example Game UI (Phase 4)                     │
│     Clean web UI generated from game JSON         │
└──────────────────────────────────────────────────┘
```

---

## Layer 1: `idleframework` Python Library (Core)

The library is the product. Everything else (CLI, API, frontend) is a wrapper around it.

### 1a. Number Representation: BigFloat

Idle games routinely produce numbers from 0 to 10^50, 10^100, 10^500, and beyond. The framework uses a custom `BigFloat` class.

**Representation:** `(mantissa: float, exponent: int)`
- Mantissa normalized to `[1, 10)`
- Exponent is a Python `int` (arbitrary precision natively — no upper limit)
- Same design as break_infinity.js, proven by thousands of idle games

**Design requirement:** 5 significant digits relative error tolerance (~1e-5). Float64 mantissa provides 15-16 digits, giving ~10 digits of headroom. Subtractive cancellation only problematic when values agree to 11+ digits — unlikely in practice.

**Why BigFloat over `decimal.Decimal`:**

Benchmarks on this machine show BigFloat is **36x faster** for the actual strategy optimizer workload (cost function evaluation: `base * rate^owned` + `log10(cost)` for 700 candidates across 100 steps):

| Operation | BigFloat | Decimal (p=20) | Winner |
|---|---|---|---|
| add/mul | 138-153 ns | 28-42 ns | Decimal (3-5x) |
| log10 | **57 ns** | 16,192 ns | **BigFloat (284x)** |
| pow | **224 ns** | 77,048 ns | **BigFloat (344x)** |
| Optimizer workload (70K evals) | **0.046s** | 1.689s | **BigFloat (36x)** |

The strategy optimizer's hot path is dominated by pow/log operations (cost curves, efficiency calculations), where BigFloat wins by orders of magnitude because:
- `log10(m * 10^e) = log10(m) + e` — one float log10 + one int addition
- `pow((m, e), p) = (m^p, e*p)` + renormalize — one float pow + one int multiply
- No overflow possible at any scale

Additional advantages:
- **NumPy-implementable** — struct-of-arrays pattern (mantissa array + exponent array) for vectorized batch operations
- **Cython-accelerable** — `cdef class` with C-level fields for 3-10x additional speedup (deferred until profiling)
- **No float overflow** — `decimal.Decimal` → `float` conversion produces `inf` above 10^308, silently corrupting results

**Implementation:** ~200-300 lines. `__slots__` for memory efficiency. First thing built, first thing tested.

**Display formatting:**
- Helper functions for idle game notation: "1.23 Trillion", "4.56e50", "1.23 Qa"
- Configurable notation styles (scientific, engineering, named)

### 1b. Game Model

Games are defined as directed graphs in JSON, validated via Pydantic models on load.

The model separates two fundamentally different semantics (following Machinations' proven approach):
- **Resource flow** (imperative): resources move, are consumed, are created
- **State influence** (reactive): values are observed and used to modify parameters continuously

Every node automatically exposes readable properties (`count`, `level`, `total_production`, `current_value`) that state modifier formulas can reference.

#### Schema Validation (Pydantic)

- Pydantic v2 models define all valid node types, edge types, and their required/optional properties
- Validated on load with clear, actionable error messages
- Schema versioned — game definitions include a `schema_version` field
- Pydantic exports JSON Schema for the React Flow frontend (Phase 3)
- Eliminates redundancy: one validation system for Python + JSON Schema export for JS
- Day-one requirement, not deferred

#### Node Types

| Node Type | Description | Key Properties |
|---|---|---|
| `Resource` | A currency or economy (pool) | `name`, `initial_value` |
| `Generator` | Produces a resource at a rate | `base_production`, `cost_base`, `cost_growth_rate`, `cycle_time` |
| `NestedGenerator` | Produces other generators | `target_generator`, `production_rate`, `cost_base`, `cost_growth_rate` |
| `Upgrade` | Modifies a generator or resource | `type` (multiplicative/additive/percentage), `magnitude`, `cost`, `target`, `stacking_group`, `duration` (optional — for temporary buffs), `cooldown_time` (optional) |
| `PrestigeLayer` | Reset mechanic with bonus | `formula_expr`, `layer_index`, `reset_scope` (list of node IDs/tags reset), `persistence_scope` (what survives), `bonus_type`, `milestone_rules` |
| `SacrificeNode` | Non-prestige partial reset | `formula_expr`, `reset_scope`, `bonus_type`. Like PrestigeLayer but no layer hierarchy — resets a subset without full layer semantics. |
| `Achievement` | Milestone that may grant bonuses | `condition_type` (`single_threshold`/`multi_threshold`/`collection`/`compound`), `targets` (list of `{node_id, property, threshold}`), `logic` (`and`/`or`/`count_N`), `bonus` (optional), `permanent` (bool, default true) |
| `Manager` | Automates purchases/collection | `target`, `automation_type` |
| `Converter` | Consumes resources, produces resources | `inputs` (list of `{resource, amount}`), `outputs` (list of `{resource, amount}`), `rate`, `pull_mode` (`pull_all` for multi-resource costs) |
| `ProbabilityNode` | Stochastic mechanic | `expected_value`, `variance` (v1: stored, engine uses expected_value only), `crit_chance`, `crit_multiplier` |
| `EndCondition` | Victory/completion target | `condition_type`, `targets`, `logic` (`and`/`or`). Enables "minimum time to reach end condition" analysis. |
| `UnlockGate` | Permanent one-time unlock | `condition_type` (`single_threshold`/`multi_threshold`/`collection`/`compound`), `targets` (list of `{node_id, property, threshold}`), `prerequisites` (list of node IDs), `logic` (`and`/`or`/`count_N`, default `and`), `permanent` (bool, default true) |
| `ChoiceGroup` | Mutually exclusive choices | `options` (list of node IDs), `max_selections`, `respeccable: bool`, `respec_cost` (optional) |
| `Register` | Computational node | `formula_expr`, `input_labels` (list of `{label, source_node}`). Computes formula over labeled inputs, outputs via state edges |
| `Gate` | Routes resources across outputs | `mode` (deterministic/probabilistic), `weights` or `probabilities` |
| `Queue` | Holds resources for N time steps | `delay`, `capacity` |

New node types are added by the community via pull requests — no plugin system needed.

#### Edge Types

**Resource edges** (solid — resources move along these):

| Edge Type | Description |
|---|---|
| `resource_flow` | Resources produced by source flow to target. Has `rate` property. |
| `consumption` | Node consumes this resource to operate |
| `production_target` | Generator's output goes to this resource |

**State edges** (reactive — no resources move, values modify parameters):

| Edge Type | Description |
|---|---|
| `state_modifier` | Current value of source node modifies a property of target node/edge. Has `formula` property (e.g., `+2`, `*1.5`, `a * 100 / (a + 100)`) |
| `activator` | Target node is active only when source node's value satisfies `condition` (e.g., `>=100`, `==0`, `3-6`). Can oscillate — re-disables if condition becomes false. |
| `trigger` | When source node changes state, fire target node once |
| `unlock_dependency` | Target is permanently locked until source condition is met (one-directional, does not re-lock) |
| `upgrade_target` | Upgrade applies to this generator/resource |

#### Node Properties (shared)

| Property | On | Description |
|---|---|---|
| `activation_mode` | All nodes | `automatic` / `interactive` / `passive` / `toggle` |
| `pull_mode` | Nodes with inputs | `pull_any` (default) / `pull_all` (all inputs required) |
| `tags` | All nodes | List of availability tags: `free`, `paid`, `ad_rewarded`, `premium_tier_N`, etc. |
| `cooldown_time` | Applicable nodes | Minimum time between activations (optional) |

#### Tags

Any node can be tagged with availability conditions. The analysis engine filters nodes by active tags:
- "Simulate free-only" vs "simulate with all paid unlocked"
- "What's the value-for-money of this specific IAP?"
- If filtering out a tagged node breaks a dependency chain, the analysis reports this explicitly

#### Game-Level Properties

| Property | Description |
|---|---|
| `schema_version` | Version of the Pydantic schema |
| `stacking_groups` | Map of group name → stacking rule. Within a group, bonuses combine by that group's rule. Between groups, always multiplicative. **Exact formula:** For additive group: `group_mult = 1 + sum(bonuses)`. For multiplicative group: `group_mult = product(bonuses)`. For percentage group: `group_mult = 1 + sum(pcts/100)`. Final: `base * product(all_group_mults)`. **Example (AdCap):** `final = base_profit * owned * (1 + angel_count * 0.02) * product(cash_mults) * product(angel_mults) * product(milestone_mults)` |
| `event_epsilon` | Tunable near-simultaneous event window (default 0.001s) |
| `free_purchase_threshold` | Auto-buy threshold: `cost/balance < threshold` (default 1e-5) |
| `time_unit` | What "1 time unit" means: `seconds` (default) |
| `tie_breaking` | Strategy optimizer tie-breaking: `lowest_cost` (default), `highest_production`, `custom` |

#### Formula Expression DSL (Lark LALR(1))

Prestige formulas, register computations, and state modifier formulas use a restricted expression DSL parsed by **Lark** with LALR(1) grammar.

**Syntax:**
- Operators: `+`, `-`, `*`, `/`, `**`, `%`
- Comparisons: `<`, `<=`, `>`, `>=`, `==`, `!=`
- Conditionals: `if(condition, then_expr, else_expr)`
- Piecewise: `piecewise(cond1, val1, cond2, val2, ..., default)`
- Functions: `sqrt`, `cbrt`, `log`, `log10`, `ln`, `abs`, `min`, `max`, `floor`, `ceil`, `clamp`, `round`, `sum`, `prod`
- Variables: predefined names (`lifetime_earnings`, `run_earnings`, `current_prestige`, `count`, `level`, etc.) and input labels (`a`, `b`, `c`, etc.)

**Security:**
- User DSL strings parsed by Lark into AST — never passed directly to `compile()`
- Our AST builder constructs controlled `ast.Expression` from the Lark parse tree
- **AST node whitelist (defense-in-depth):** Only `ast.BinOp`, `ast.UnaryOp`, `ast.Call`, `ast.Name`, `ast.Constant`, `ast.Compare`, `ast.IfExp` nodes permitted. Whitelist validated before `compile()`. This prevents sandbox escape vectors that require `ast.Attribute` or `ast.Subscript` nodes.
- Compiled to Python bytecode for fast repeated evaluation (near-native speed for millions of optimizer calls)
- Max AST depth limit (50) prevents deeply nested expressions
- Max exponent value cap (prevents `2**2**2**2**100` DoS)
- Max computation time limit per evaluation
- Restricted builtins (`{"__builtins__": {}}`)
- Fuzz tested with Hypothesis

**Validation at load time:**
- All variables resolved against known node properties — undefined variables are errors
- Type checking of operands
- Division-by-zero in constant subexpressions flagged as warnings

### 1c. Math Engine

The math engine uses pure mathematics — no simulation loops. The production engine operates entirely on BigFloat and closed-form solutions. **SciPy is a production dependency** (matrix exponentials via `scipy.linalg.expm`, root-finding via `scipy.optimize.brentq`). **mpmath and SymPy are test-only dependencies.**

#### Architecture: Piecewise Analytical

The game timeline is divided into **segments** between discrete events (purchases, prestiges, unlocks, buff expirations). Within each segment, the system of equations is fixed and can be solved analytically.

```
[Segment 1: initial state] ──purchase──> [Segment 2: +1 generator] ──purchase──> [Segment 3: +upgrade] ──prestige──> [Segment 4: reset]
```

For each segment, the engine:
1. Identifies the current system of equations (which generators are active, what multipliers apply)
2. Solves analytically using closed-form solutions
3. Computes "time until next affordable/optimal purchase" algebraically
4. Jumps to that event, applies state changes, starts new segment

**Near-simultaneous events:** When multiple purchases become affordable within a configurable epsilon (default 0.001s), all candidates are evaluated simultaneously using the greedy efficiency score to determine ordering.

**Performance bound:** At any given time, only ~20 items have purchase costs within the same exponent. Items where `cost / current_balance < 1e-5` are auto-purchased immediately ("free purchase threshold") without advancing time. This bounds per-segment candidate evaluation to O(20).

**Event engine safety:**
- **Chattering/Zeno detection:** Max 100 purchases per epsilon window. If hit, batch-evaluate all affordable candidates simultaneously.
- **Stale event invalidation:** After every state change, ALL previously computed "time to next event" values are recomputed. O(20*K) for K events total.
- **Epsilon sensitivity:** Epsilon is a tunable game-level property. Results document the epsilon used.

**Formula reference classification (load-time):**

| Tier | Input Type | Handling | Performance |
|---|---|---|---|
| **Tier 1** | Discrete values only (`count`, `level`, `owned`) | Pure piecewise analytical | Fast path |
| **Tier 2** | `current_value` with slowly-varying formulas | Evaluate once at segment start, constant within segment | Fast path (~negligible error) |
| **Tier 3** | Tight feedback loops (production → resource → production) | Short numerical integration, flagged `approximation_level: "numerical_fallback"` | Slow path |

#### Closed-Form Solvers

- **Generator chains:** Production follows polynomial patterns. For **homogeneous rates** (identical cycle times): `t^n / n!`. For **heterogeneous rates** (different cycle times, as in AdCap): `t^n / product(r_i)` with per-generator rate constants and initial conditions carrying forward at segment boundaries. Still tractable but more complex.
- **Single-item time-to-afford:** For constant production: `time = cost / production_rate`. For polynomial production (deep chains, degree ≥ 5): Brent's method root-finding via `scipy.optimize.brentq` — bracketed, guaranteed convergence in ~50 iterations. Abel-Ruffini theorem prevents closed-form for degree ≥ 5.
- **Bulk purchase cost:** `cost = base * rate^owned * (rate^n - 1) / (rate - 1)` (uses BigFloat natively — no overflow)
- **Max affordable quantity:** `max = floor(log_rate(currency * (rate - 1) / (base * rate^owned) + 1))`
- **Matrix exponentials** (`e^{At}`) for linear systems with cross-generator interactions — implemented via `scipy.linalg.expm` (Al-Mohy & Higham 2009 scaling-and-squaring algorithm, microseconds for n=10-30 matrices)

#### Fallback Methods (for complex nonlinear games)

When closed-form solutions don't exist (complex state modifiers, nonlinear register formulas):
- **Short numerical integration** using BigFloat directly — the honest fallback for nonlinear systems
- **Log-space transformation** for specific multiplicative dynamics where applicable
- Results marked with `approximation_level: "numerical_fallback"` so the user always knows

#### Prestige Timing

**Greedy heuristic:** Prestige when `d(progress)/dt` in current run falls below expected rate after reset. This is a greedy approximation — it ignores that waiting longer increases prestige currency, which changes the next run's rate. Labeled honestly as "greedy prestige timing heuristic" in all output.

**Better mode (deferred):** Model the next run as a function of prestige currency and optimize the full two-run sequence. Required for multi-layer prestige optimization.

Formulas defined via the expression DSL:
- AdVenture Capitalist: `150 * sqrt(lifetime_earnings / 1e15)`, +2% per angel
- Cookie Clicker: `cbrt(lifetime_earnings / 1e12)`
- Custom formulas via configurable expressions

#### Strategy Optimizer

Four tiers, in order of speed vs quality:

| Tier | Method | Use Case | Guarantee |
|---|---|---|---|
| **Default** | Efficiency-score greedy | Instant feedback during editing (<200ms for <100 nodes) | Near-optimal (payback period minimization) |
| **Better** | Beam search (width 100-500) | Primary improvement over greedy. Deterministic, parallelizable. | Top-K candidates at each step |
| **Best** | MCTS with greedy rollouts | Long optimization runs. Average backup (default), power mean and max-backup configurable. | Anytime — improves with more iterations. Seeded for determinism. |
| **Exact** | Branch-and-bound with state dominance pruning | Small subproblems only (user-configurable depth limit, default 20). Test validation. | Optimal (if tractable) |

**Greedy efficiency formulas:**
- **Generators:** `efficiency = delta_production / cost` (payback period inverse)
- **Additive upgrades:** `efficiency = (bonus * current_production) / cost`
- **Multiplicative upgrades:** `efficiency = current_production * (multiplier - 1) / cost`
- **Coupled purchases** (e.g., angel upgrades that spend angels): `efficiency = net_benefit / cost` where `net_benefit = production_gain - production_lost_from_side_effects`
- **Known limitation:** Greedy delays multiplicative upgrades. Beam search recommended as minimum viable tier for multiplicative-heavy games.

**MCTS rollout diversity:** Epsilon-greedy rollouts (default epsilon=0.1) with randomized tie-breaking. Without diversity, deterministic greedy rollouts produce identical results from the same state, making tree search meaningless.

**Cross-resource comparison:** Compare purchases by impact on bottleneck resource's time-to-next-milestone. Exchange rates inferred from Converter nodes when available; otherwise compare within each economy independently and report.

#### Theoretical Boundaries

The "math-first" approach builds on proven results but extends beyond them:

- **Proven territory:** Single-resource, additive production, fixed costs — closed-form solutions exist (Demaine et al.)
- **Empirically validated:** Efficiency-score greedy is near-optimal in practice for most idle games, though the `1 + O(1/ln M)` bound is proven only for the simplified model
- **Heuristic territory:** Multiplicative production, multiple resources, prestige mechanics — no published work proves optimality guarantees. The Immediate Purchase Principle may not hold when buying item A makes item B more efficient (multiplicative stacking)
- **What we guarantee:** Results are always labeled with their approximation level (`exact`, `near_optimal`, `heuristic`, `numerical_fallback`). The user always knows when a result is approximate.

### 1d. Analysis Engine

Consumes a game model + strategy, produces insights:

| Analysis | Description |
|---|---|
| **Dominant strategy detection** | Is there one obviously best route? Are alternatives within X% of optimal? |
| **Dead upgrade detection** | Upgrades/generators that a rational player will never purchase |
| **Progression wall detection** | Points where growth rate drops below a threshold — player is just waiting |
| **Multi-strategy comparison** | Do different routes converge to similar outcomes or diverge? |
| **Free vs paid comparison** | Run optimizer for both filtered and unfiltered tag sets. Report: (a) which strategies change, (b) performance gap, (c) which paid nodes cause the largest gap. Reports broken dependency chains. |
| **Time-to-completion** | Minimum time to reach target milestones under different strategies |
| **Prestige timing** | Greedy-optimal moment to reset (with caveats documented) |
| **Sensitivity analysis** | Which parameters have the most impact on outcomes? |

### 1e. Report Generator

- Self-contained interactive HTML reports using Plotly
- Production curves over time
- Strategy comparison charts (multiple lines on same axes)
- Resource flow diagrams
- Upgrade efficiency rankings
- Progression wall markers
- Approximation level indicators on all results
- Exportable, shareable — no server needed to view

### 1f. Export

- **JSON** — canonical format
- Converters to **YAML** and **XML** available as needed

---

## Layer 2: CLI

Built with `typer`. The CLI wraps the library — power users can also `import idleframework` directly in their own scripts.

```bash
# Run full analysis
idleframework analyze game.json

# Analyze free-to-play only
idleframework analyze game.json --tags free

# Run beam search optimizer
idleframework analyze game.json --optimizer beam --beam-width 200

# Run MCTS optimizer
idleframework analyze game.json --optimizer mcts --iterations 10000

# Compare strategies
idleframework compare game.json --strategies "free,paid"

# Generate interactive HTML report
idleframework report game.json --output report.html

# Export to different format
idleframework export game.json --format yaml

# Validate a game definition
idleframework validate game.json
```

---

## Layer 3: FastAPI Backend (Phase 2)

- REST endpoints mirroring CLI commands
- WebSocket connection for live analysis feedback during node editing
- Serves the React Flow frontend as static files
- API auto-documented via FastAPI's built-in OpenAPI support
- Pydantic models shared with the library — zero duplication

---

## Layer 4: React Flow Frontend (Phase 3)

The visual node editor. Not required — everything works via CLI and library.

**Node editor:**
- Custom React components per mechanic type (Generator, Upgrade, Prestige Layer, Register, ChoiceGroup, etc.)
- Drag-and-drop node creation from a palette
- Two visually distinct edge types: solid for resource flow, dotted for state connections
- Tag management panel for free/paid filtering

**In-UI analysis:**
- Recharts dashboards alongside the node editor
- Live feedback — edit a node, see analysis update (<200ms target for greedy analysis on <100 nodes)
- Strategy comparison views
- Approximation level indicators

**Import/export:**
- Load and save game definitions as JSON
- React Flow's native `toObject()` produces JSON-serializable graphs
- JSON Schema (exported from Pydantic) validates on the frontend

---

## Layer 5: Example Game UI (Phase 4)

- Simple, clean web UI auto-generated from a game JSON definition
- AdVenture Capitalist as the reference implementation
- Functional: buy generators, see production, prestige, apply upgrades
- Not a production game — proves the export pipeline works end-to-end
- Doubles as an integration test fixture

---

## TDD Strategy

**The simulator is never the product — it's the test harness.**

### Test Infrastructure

**RK4/Adaptive simulator:**
- Runge-Kutta 4th order (RK4) method — O(h^4) accuracy per step, ~20 lines of code
- Fixed-step with manual event checking (check affordability at each step, bisect to find exact purchase time). Simpler and more correct than SciPy's event system for our test-harness use case.
- For stiff systems: attempt RK4 first, monitor step rejection rate, fall back to SciPy `solve_ivp(method='Radau')` if step size drops below floor (runtime heuristic, not fixed threshold)
- Configurable step size
- Exists exclusively in the test suite
- Used for convergence testing, NOT as sole ground truth

**Reference solvers (test-only dependencies):**
- SciPy `solve_ivp` for ODE-based reference solutions
- mpmath `odefun` for arbitrary-precision reference solutions
- SymPy for symbolic verification of closed-form derivations

### Testing Methodology

1. **Closed-form formulas** → test against exact pen-and-paper analytical results. NOT the simulator.
2. **Piecewise analytical engine** → convergence testing: run RK4 simulator at multiple step sizes and verify results converge toward the math engine's answer. If they converge to a *different* value, one has the wrong equations.
3. **Dual tolerances** → relative (0.1%) for large values, absolute for small values. Mirrors SciPy's `rtol`/`atol` approach.
4. **Stiff system detection** → generators with vastly different time scales require adaptive step sizing. Detected automatically, falls back to SciPy Radau.
5. **Event boundary precision** → purchases, prestige resets, and unlocks create discontinuities. Simulator uses event detection to handle these cleanly.

### Test Layers

1. **BigFloat tests** — arithmetic accuracy validated against Python's `decimal` module for known values across the full range. Properties tested with Hypothesis: commutativity (exact), approximate associativity (within tolerance), identity (`a+0==a`, `a*1==a`), zero (`a*0==0`), monotonicity (`a>0, b>0 => a+b>a`), log-product (`log10(a*b) ~= log10(a)+log10(b)`). Edge cases: rate=1 (geometric series singularity), rate<1, zero values, negative values, near-overflow exponents. Numerical stability: long chains (1000+ operations) with error accumulation tracking, subtractive cancellation scenarios, comparison against mpmath arbitrary-precision.

2. **Formula DSL tests** — parser correctness, compilation, evaluation. Fuzz tested with Hypothesis. Security: max depth, max exponent, timeout enforcement. Edge cases: NaN propagation, division by zero, undefined variables.

3. **Math engine tests** — every closed-form formula tested against:
   - Exact analytical results (pen-and-paper) where available
   - Convergence of RK4 simulator at decreasing step sizes
   - SciPy/mpmath reference solutions for complex cases
   - SymPy symbolic verification for derivations

4. **Game fixture tests** — test games modeled as JSON:
   - **MiniCap** (unit testing): 3 generators, 10 upgrades, 1 prestige layer, 2 resources. Simple enough for manual verification.
   - **MediumCap** (integration testing): 8 generators, 30 upgrades, 2 prestige layers, managers, converters, state modifiers. Catches cross-interaction bugs.
   - **LargeCap** (stress testing): ~100 upgrades, procedurally generated with known analytical properties. Stress-tests piecewise segmentation with many purchase events.
   - **AdCap** (real-world validation): Begin modeling in Phase 1 as a long-running goal.

5. **Analysis tests** — intentionally designed game graphs with known properties:
   - A graph with one clearly dead upgrade — verify detection
   - A graph with a progression wall at a known point — verify flagging
   - A graph with two equally viable strategies — verify convergence detection
   - A graph where filtering `paid` tags breaks a dependency — verify reporting
   - A graph with stacking groups — verify correct multiplicative combination

6. **Property-based tests (Hypothesis)** — essential for math-heavy code:
   - BigFloat arithmetic properties (commutativity, inverse correctness)
   - Monotonicity of production (more generators = more production)
   - Bulk cost = sum of individual costs
   - Max-affordable inverse: `can_afford(max_affordable(currency)) == True`
   - Commutativity of independent purchases
   - Tag filtering: filtered results are subsets of unfiltered results

7. **Schema validation tests** — malformed JSON produces clear errors, not silent wrong results.

8. **Graph validation tests** — cycle detection, edge type compatibility, tag-filtered subgraph validity.

9. **Numerical edge cases** — rate=1 (div-by-zero in geometric series), rate<1, zero production, NaN/Inf propagation, near-max exponent values.

10. **Determinism tests** — MCTS with same seed produces same results.

11. **Integration tests** — CLI commands produce expected output. API endpoints return correct results.

12. **Regression tests** — Every bug fix includes a test case in `tests/regressions/` with the game JSON, expected result, and explanatory comment. Permanent fixtures.

13. **JSON parser fuzz tests** — Hypothesis generates adversarial JSON: missing fields, wrong types, circular edges, huge arrays, Unicode in names, duplicate IDs. Pydantic catches many, but error paths and messages are tested.

14. **Performance benchmarks** — pytest-benchmark for BigFloat operations, optimizer hot path, piecewise engine segment processing. Tracked across commits to catch regressions.

**Tests are the specification.** We write the test first, then implement the math to pass it.

---

## Tech Stack

| Component | Technology | Rationale |
|---|---|---|
| Core language | Python 3.12+ | Scientific computing ecosystem, longer support window, `type` statement, `typing.override` |
| Number type | Custom BigFloat `(mantissa, exponent)` | 36x faster than Decimal for optimizer workload, NumPy-implementable, Cython-accelerable, no overflow at any scale |
| Formula DSL | Lark (LALR(1), standalone mode) | O(n) parsing, compiles to Python bytecode for fast repeated evaluation, safe (no eval) |
| Graph operations | NetworkX | Cycle detection, topological sort, subgraph analysis, connectivity |
| Schema validation | Pydantic v2 | Fast validation, JSON Schema export for frontend, shared with FastAPI |
| Math (production) | Closed-form solutions, piecewise analytical, SciPy (matrix exponentials + root-finding) | Pure math, no simulation |
| Math (test-only) | SciPy, mpmath, SymPy | Reference solutions, symbolic verification |
| Testing | pytest + Hypothesis + parametrize | TDD standard + property-based testing for math code |
| CLI | typer | Modern, type-hint-based CLI framework |
| API (Phase 2) | FastAPI | Async, auto-docs, shares Pydantic models |
| Frontend (Phase 3) | React Flow (@xyflow/react v12) | ~24k stars, custom nodes as React components, JSON export |
| Charting (in-UI) | Recharts | Native React, declarative, lightweight |
| Charting (reports) | Plotly | Interactive HTML, scientific visualization |
| Game definitions | JSON (canonical) | Universal, React Flow compatible, schema-validated |
| Performance (deferred) | Cython BigFloat `cdef class`, NumPy struct-of-arrays | Apply after profiling identifies bottlenecks |

---

## Key Design Decisions

1. **Math-first, not simulation-first.** The core product computes answers via closed-form solutions and piecewise analytical methods. Simulation exists only for test validation. SciPy is a production dependency for matrix exponentials and root-finding. mpmath and SymPy are test-only.

2. **Piecewise analytical architecture.** The game timeline is segmented at discrete events (purchases, prestiges, unlocks). Within each segment, the math engine solves analytically.

3. **BigFloat over `decimal.Decimal`.** 36x faster for the actual optimizer workload (pow/log-dominated). NumPy-implementable, Cython-accelerable, no overflow at any scale. Cython-accelerable if needed.

4. **Resource flow vs state influence.** Following Machinations' proven approach, the graph model separates resource edges (resources move) from state edges (values modify parameters). This distinction reflects fundamentally different computational semantics.

5. **Library-first, phased delivery.** The Python library is the product. CLI, API, and frontend are wrappers delivered in phases.

6. **Pydantic for validation.** One validation system: Pydantic models in Python, JSON Schema export for the React Flow frontend. Eliminates redundancy with FastAPI in Phase 2.

7. **Lark for formula DSL.** Parse once, compile to bytecode, evaluate millions of times at near-native speed. Safe by construction (AST control), with resource limits for DoS prevention.

8. **Per-group stacking, not game-level.** Each upgrade belongs to a `stacking_group`. Within a group, bonuses combine by that group's rule. Between groups, always multiplicative. Matches how real games work (AdCap has 4+ stacking categories).

9. **Tag-based filtering for monetization.** Any node tagged with availability conditions. Analysis filters by active tags and reports broken dependency chains.

10. **Four-tier strategy optimizer.** Greedy (instant) → beam search (better) → MCTS (best, average backup default) → B&B (exact, small subproblems only, user-configurable depth limit).

11. **Honest about theoretical boundaries.** Results always labeled with approximation level. The "math-first" claim acknowledges where we're in proven territory vs heuristic territory.

12. **No plugin system.** New node types are contributed via PRs to the main repository.

---

## Open Questions (Resolved)

| # | Question | Resolution |
|---|---|---|
| 1 | How does the math engine handle discrete/continuous boundary? | Piecewise analytical segments between events. Compute "time to next purchase" algebraically, jump forward, apply state change, restart. |
| 2 | What is the input format for prestige formulas? | Lark-parsed expression DSL with predefined variables. Compiled to bytecode. Validated at load. |
| 3 | How are game graphs validated? | Pydantic for structure. NetworkX for graph analysis: resource cycles are valid feedback loops, dependency cycles are errors. |
| 4 | Can designers model just a subsystem? | Yes. Unconnected nodes are valid. The framework analyzes whatever subgraph it's given. |
| 5 | How does tag filtering interact with connectivity? | If filtering breaks dependencies, analysis reports this explicitly. Does not silently produce wrong results. |
| 6 | What is "time"? | Game-seconds by default. Each prestige layer tracks per-run time. |
| 7 | How do upgrade interactions stack? | Per-group stacking: `stacking_groups` map defines rule per group. Between groups: multiplicative. |
| 8 | Tied efficiency scores? | Tie-breaking configurable: `lowest_cost` (default), `highest_production`, `custom`. |
| 9 | Bulk-purchase formulas at huge ranges? | BigFloat handles the geometric series formula natively at any scale. |
| 10 | MVP fixture? | MiniCap (unit) + MediumCap (integration). AdCap modeling begins in Phase 1. |
| 11 | How are generator counts exposed to formulas? | Automatically. Every node exposes `count`, `level`, `total_production`, `current_value` as readable properties. |
| 12 | Near-simultaneous affordability? | All candidates within epsilon (0.001s) evaluated simultaneously using efficiency score. |
| 13 | Cross-resource optimization? | Exchange rates inferred from Converter nodes. Otherwise compare by relative production improvement per economy. |
| 14 | Nested prestige reset_scope? | Not automatically transitive. Each layer explicitly lists its reset_scope. Framework validates supersets (warning if inconsistent). |
| 15 | Sub-worlds (Moon/Mars in AdCap)? | Model as separate subgraphs with `world` tags and shared nodes (angel bonuses). World-scoped analysis. |
| 16 | Unsolvable analytical systems? | Results marked `approximation_level: "numerical_fallback"`. User always knows. |
| 17 | DSL validation depth? | Lark parses AST. Type checking, undefined variable detection, constant-folding checks. Max depth 50. |
| 18 | Frontend latency target? | <200ms for greedy analysis on <100 nodes. Cache intermediate results, incremental re-analysis. |
| 19 | Formula parser library? | Lark (LALR(1), standalone mode). Compiled to bytecode for repeated evaluation. |
| 20 | Graph library? | NetworkX v3.6+. |

---

## Research References

### Academic

- Demaine et al., "Cookie Clicker," *Graphs and Combinatorics* 36, 269-302 (2020). [arXiv:1808.07540](https://arxiv.org/abs/1808.07540). [Springer](https://link.springer.com/article/10.1007/s00373-019-02093-4)
- Xiao, "Cookie Clicker," M.Eng. Thesis, MIT (2018). [MIT DSpace](https://dspace.mit.edu/handle/1721.1/119555)
- Dormans, "Engineering Emergence: Applied Theory for Game Design," PhD, University of Amsterdam (2012). [PDF](https://www.illc.uva.nl/Research/Publications/Dissertations/DS-2012-12.text.pdf)
- Adams & Dormans, "Game Mechanics: Advanced Game Design" (2012)
- Alharthi et al., "Playing to Wait: A Taxonomy of Idle Games," CHI (2018). [ACM DL](https://dl.acm.org/doi/10.1145/3173574.3174195)
- Klint & van Rozen, "Micro-Machinations: A DSL for Game Economies," SLE (2013). [CWI PDF](https://ir.cwi.nl/pub/21923/21923B.pdf)
- Van Rozen, "Languages of Games and Play: A Systematic Mapping Study," ACM Computing Surveys (2020)
- Van Rozen, "Cascade: A Meta-Language for Change, Cause and Effect," SLE (2023)
- K-Machinations, "Testing and Repairing Machinations Diagrams" (2024). [Springer](https://link.springer.com/chapter/10.1007/978-3-031-76440-0_18)
- Rupp & Eckert, "GEEvo: Game Economy Generation and Balancing," IEEE CEC (2024). [arXiv:2404.18574](https://arxiv.org/abs/2404.18574)
- Kavanagh, "Using Probabilistic Model Checking to Balance Games," PhD (2021). [PDF](https://ludii.games/citations/Thesis2021-5.pdf)
- Barreto & Julia, "Formal Approach Based on Petri Nets for Modeling and Verification of Video Games," Computing and Informatics (2021)
- Hwang & Melcer, "Exploring Engagement in Idle Game Design," IEEE CoG (2024). [IEEE](https://ieeexplore.ieee.org/document/10645671/)
- Khandelwal et al., "On the Analysis of Complex Backup Strategies in MCTS," ICML (2016)

### Mathematical Foundations

- [The Math of Idle Games Part I](https://blog.kongregate.com/the-math-of-idle-games-part-i/) — cost/production functions, bulk purchase formulas
- [The Math of Idle Games Part II](https://blog.kongregate.com/the-math-of-idle-games-part-ii/) — generator chains, derivative-based growth (`t^n/n!`), Taylor series
- [The Math of Idle Games Part III](https://blog.kongregate.com/the-math-of-idle-games-part-iii/) — prestige mechanics, reset currency formulas
- [Dealing with Huge Numbers in Idle Games](https://blog.innogames.com/dealing-with-huge-numbers-in-idle-games/) — InnoGames' mantissa+exponent approach
- Moler & Van Loan, "19 Dubious Ways to Compute the Exponential of a Matrix" — matrix exponential methods

### Existing Projects Studied

- [Machinations.io](https://machinations.io/) — commercial, closed-source. Key learnings: state connections vs resource flow, activators, registers
- [Profectus](https://github.com/profectus-engine/Profectus) — Formula system closest prior art to math-first approach
- [Incremental Game Template](https://github.com/123ishaTest/incremental-game-template) — testing reference
- [Kalivra](https://github.com/DevBawky/Kalivra) — game balance analysis tool
- [break_infinity.js](https://github.com/Patashu/break_infinity.js) / [break_eternity.js](https://github.com/Patashu/break_eternity.js) — BigFloat design reference
- [Antimatter Dimensions](https://github.com/IvarK/AntimatterDimensionsSourceCode) — multi-layer prestige reference
- [Micro-Machinations Lib](https://github.com/vrozen/MM-Lib) — architecture reference
- [cadCAD](https://cadcad.org/) — open-source simulation (token engineering, not games)
- [GEEvo](https://github.com/FlorianRupp/GEEvo-game-economies) — evolutionary game economy balancing

### Tools and Libraries

- [Lark Parser](https://github.com/lark-parser/lark) — LALR(1) parser for formula DSL
- [NetworkX](https://networkx.org/) — graph algorithms
- [React Flow (@xyflow/react)](https://reactflow.dev/) — v12, ~24k stars
- [Pydantic v2](https://docs.pydantic.dev/) — validation + JSON Schema export

### Communities

- [r/incremental_games](https://reddit.com/r/incremental_games) — 154K members
- [Incremental Social](https://code.incremental.social/) — dedicated Gitea instance
