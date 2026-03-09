# IdleFramework Design Document — Critical Review

**Reviewed:** 2026-03-08
**Document:** `docs/plans/2026-03-07-idleframework-design.md` (Revision 3)
**Method:** Parallel research agents with web search across academic foundations, math engine, tech stack, game model, competitive landscape, and TDD strategy.

---

## Table of Contents

1. [Critical Issues (Must Resolve Before Implementation)](#1-critical-issues)
2. [High-Priority Issues (Fix Before v1.0)](#2-high-priority-issues)
3. [Medium-Priority Issues](#3-medium-priority-issues)
4. [Low-Priority / Documentation Issues](#4-low-priority--documentation-issues)
5. [Competitive Context](#5-competitive-context)
6. [Resolved Questions](#6-resolved-questions)
7. [Required Design Doc Changes](#7-required-design-doc-changes)

---

## 1. Critical Issues

These must be resolved before implementation begins. Each represents either a contradiction in the design, a false claim, or a fundamental gap that affects correctness.

### 1.1 SciPy/mpmath Dependency Contradiction

**The problem:** Line 243 states "SciPy and mpmath are test-only dependencies." Line 267 states "Matrix exponentials (e^{At}) for linear systems with cross-generator interactions — implemented via mpmath for production use." These are mutually exclusive.

**Resolution required:** Accept scipy as a production dependency. `scipy.linalg.expm` uses the Al-Mohy and Higham (2009) scaling-and-squaring algorithm with Pade approximation. For the stated matrix sizes (n=10-30), this runs in microseconds and is well-tested. mpmath's matrix exponential is significantly slower and provides unnecessary arbitrary-precision for this use case.

**Recommendation:** Change line 243 to "SciPy is a production dependency for matrix exponentials. mpmath and SymPy are test-only dependencies." Alternatively, implement a custom matrix exponential using only NumPy (feasible but not recommended — reimplementing a numerically sensitive algorithm for no reason).

**Sources:**
- [SciPy expm documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.expm.html)
- Moler & Van Loan, "19 Dubious Ways to Compute the Exponential of a Matrix"

---

### 1.2 Numba Compatibility Claims Are False

**The problem:** The doc claims BigFloat is "Numba-compatible" (line 118) and uses `__slots__` (line 123). These are contradictory:

- Numba's `@jitclass` **does not support `__slots__`** ([numba/numba#6033](https://github.com/numba/numba/issues/6033)).
- `@jitclass` requires its own type specification system (`numba.types`), not Python class attributes.
- `@jitclass` does not support `staticmethod`, `classmethod`, or inheritance from anything other than `object`.
- The doc touts "Python int exponent for unlimited range" as a feature, but Numba requires `int64`, capping at ~9.2e18. You cannot have both unlimited range and Numba compatibility.

**Resolution required:** Either:
1. **Drop the Numba claim.** The doc's other performance claims (Cython, NumPy struct-of-arrays) are valid. Numba is not needed if Cython acceleration is the deferred performance path.
2. **Spec a dual-implementation strategy:** Pure Python BigFloat (with `__slots__` and Python `int` exponent) for correctness and flexibility, plus a separate Numba kernel using raw `float64` + `int64` arrays for the optimizer hot path. This is the struct-of-arrays pattern the doc already mentions.

**Recommendation:** Option 1. Drop the Numba claim. The 36x advantage over Decimal is already sufficient for Phase 1. Cython `cdef class` is a cleaner acceleration path that works with the existing class design.

**Sources:**
- [Numba jitclass documentation](https://numba.readthedocs.io/en/stable/user/jitclass.html)
- [Numba __slots__ issue](https://github.com/numba/numba/issues/6033)

---

### 1.3 `ast.Expression` + `compile()` Security Is Overconfident

**The problem:** The doc states the formula DSL is "safe (no eval)" because Lark parses into an AST, which is compiled via `ast.Expression` + `compile()`. This is misleading — `compile()` + `eval()` of the resulting code object IS eval with an extra step. The safety depends entirely on what AST nodes are constructed.

**Known bypass vectors even with `{"__builtins__": {}}`:**
- `().__class__.__bases__[0].__subclasses__()` can reach `os._wrap_close` or similar classes providing `__import__`, enabling arbitrary code execution.
- The asteval library (same approach) had a sandbox escape: [GHSA-vp47-9734-prjw](https://github.com/lmfit/asteval/security/advisories/GHSA-vp47-9734-prjw).
- New AST node types in future Python versions could provide unexpected capabilities.

**The doc's mitigations (max depth 50, max exponent, timeout) address DoS but not sandbox escape.**

**Resolution required:** Since IdleFramework controls the Lark grammar and builds AST nodes itself (users never write raw Python), the actual risk is lower than generic eval. But the doc must:
1. Explicitly state that the generated `ast.Expression` only contains whitelisted node types: `ast.BinOp`, `ast.UnaryOp`, `ast.Call`, `ast.Name`, `ast.Constant`, `ast.Compare`, `ast.IfExp`.
2. Add an AST node whitelist validator as a defense-in-depth check before `compile()`.
3. Never pass user-controlled strings directly to `compile()` — always go through Lark parse -> controlled AST construction.
4. Consider [simpleeval](https://pypi.org/project/simpleeval/) or [evalidate](https://pypi.org/project/evalidate/) as battle-tested alternatives that already handle node whitelisting.

**Sources:**
- [HackTricks: Bypass Python Sandboxes](https://book.hacktricks.xyz/generic-methodologies-and-resources/python/bypass-python-sandboxes)
- [asteval CVE](https://security.snyk.io/vuln/SNYK-PYTHON-ASTEVAL-1073629)
- [simpleeval on PyPI](https://pypi.org/project/simpleeval/)

---

### 1.4 ProbabilityNode Needs Variance, Not Just Expected Value

**The problem:** The ProbabilityNode only has `expected_value`, `crit_chance`, `crit_multiplier`. Using expected value alone is insufficient for balance analysis.

**Why variance matters:**
- A 5% drop rate mechanic has expected time of 20 attempts, but 95th-percentile players need ~60 attempts. Analysis using only expected value says "this takes 20 attempts" and misses that 5% of players will be stuck 3x longer — exactly the kind of progression wall the Analysis Engine should detect.
- Crit-dependent builds may look competitive on expected value but are unreliable due to variance.
- Multiple stochastic nodes in a production chain compound variance super-linearly.

**Resolution required:** Propagate variance alongside expected value through the production graph. For independent stochastic nodes: `Var(XY) = E[X]^2*Var(Y) + E[Y]^2*Var(X) + Var(X)*Var(Y)`. Report confidence intervals (e.g., 5th/95th percentile) for time-to-milestone. For progression wall detection, check whether the *tail* of the distribution creates walls, not just the mean.

This is analytically tractable — no simulation needed. The framework remains "math-first."

---

### 1.5 Time-to-Purchase Has No Closed Form for Deep Generator Chains

**The problem:** With n-tier generator chains, resource accumulation is a degree-(n+1) polynomial in time. "Time until affordable" requires solving `integral_0^t P(s) ds = C - B` where P(s) is a polynomial of degree n. This yields a polynomial equation of degree n+1 in t. For n >= 4, **there is no general closed-form solution** (Abel-Ruffini theorem).

**The doc implies algebraic solutions are always available for "time to next purchase" (line 256). They aren't.**

**Resolution required:** Acknowledge numerical root-finding as a production requirement, not just a fallback. Brent's method (bracketed, guaranteed convergence) is the right choice. This is fast (converges in ~50 iterations for machine epsilon) and does not change the "math-first" philosophy — root-finding is mathematics, not simulation.

**Additional context from design owner:** At any given time, only ~20 items are within purchasing range (items in the same cost exponent). Items whose cost is within relative error of the current balance should be auto-purchased for free. This bounds the per-segment candidate evaluation to O(20), making the root-finding overhead negligible.

---

## 2. High-Priority Issues

These should be fixed before v1.0. They represent gaps that will cause incorrect results or prevent modeling real games.

### 2.1 Register Chains with Dynamic Inputs Silently Force Numerical Fallback

**The problem:** A Register computing `sqrt(gold.current_value)` that modifies a Generator's rate via a state_modifier edge creates a nonlinear ODE (`d(gold)/dt = f(sqrt(gold))`) with no polynomial solution. The doc doesn't acknowledge that register chains with dynamic inputs commonly trigger numerical fallback.

**Resolution required:** Classify formula references at load time into three tiers:

| Tier | Input Type | Handling | Performance |
|---|---|---|---|
| **Tier 1** | Discrete values only (`count`, `level`, `owned`) | Pure piecewise analytical | Fast path |
| **Tier 2** | `current_value` with monotonic, slowly-varying formulas | Evaluate once at segment start, treat as constant within segment | Fast path (negligible error within 5-digit tolerance) |
| **Tier 3** | Tight feedback loops (production -> resource -> production) | Short numerical integration, flagged as `approximation_level: "numerical_fallback"` | Slow path |

Tier 2 covers 90%+ of real cases. A Register computing `sqrt(lifetime_earnings)` changes by <0.1% per segment in mid-to-late game. Only tight feedback loops need Tier 3.

---

### 2.2 ChoiceGroup Combinatorics Are Unaddressed by Optimizer

**The problem:** The four-tier optimizer handles sequential purchase decisions. ChoiceGroups are *configuration* decisions — k binary choices create 2^k configurations. The optimizer has no mechanism for this. Respeccable choices with `respec_cost` add another dimension the greedy tier can't handle.

**Resolution required:** For ChoiceGroups, enumerate configurations (up to ~10,000) and run the sequential optimizer for each configuration. Report the best configuration alongside its optimal sequence. For games with too many configurations, use the MCTS tier to sample the configuration space.

The greedy tier should evaluate each choice option independently and pick the best. The beam/MCTS tiers should include "respec choice X" as a candidate action when `respeccable: true`.

---

### 2.3 Toggle Activation Creates a Control Problem

**The problem:** Nodes with `activation_mode: "toggle"` require deciding *when to toggle*, not *what to buy*. Toggle timing is continuous and reversible — fundamentally different from discrete, irreversible purchases. The optimizer design ignores this entirely.

**Real games with toggles:** NGU Idle (energy/magic allocation), Cookie Clicker (wrinkler management), many games with "boost X at cost of Y" toggleable abilities.

**Resolution required:**
- **Greedy/beam tiers:** Evaluate "always on" vs. "always off" for each toggle node. Pick the better option per segment.
- **MCTS tier:** Include toggle actions as possible moves.
- **Analytical treatment:** Identify toggle states that create distinct production regimes and solve each regime separately.
- **Document honestly:** Toggle timing optimization is not solved exactly by any tier.

---

### 2.4 Pydantic v2 Discriminated Union JSON Schema Bugs

**The problem:** Pydantic v2 has documented bugs with JSON Schema generation for nested discriminated unions:
- [Issue #7491](https://github.com/pydantic/pydantic/issues/7491): OpenAPI schema broken for nested discriminated unions.
- [Issue #9136](https://github.com/pydantic/pydantic/issues/9136): `List[DiscriminatedUnion]` fails with `TypeAliasType`.
- [Issue #8628](https://github.com/pydantic/pydantic/issues/8628): Incorrect schema for discriminated unions in nested dataclasses.

Since the node type system IS a discriminated union (16 types distinguished by a `type` field), this is directly relevant.

**Resolution required:** Not a Phase 1 blocker, but test JSON Schema export early for the node type union. Fallback plan: use `Annotated[Union[...], Field(discriminator='type')]` with explicit `json_schema_extra` overrides, or generate the JSON Schema manually for the Phase 3 frontend.

---

### 2.5 Queue/Delay Nodes Create Delay Differential Equations

**The problem:** A Queue with delay T creates a DDE: `d(output)/dt = f(input(t-T))`. DDEs generally lack closed-form solutions. Capacity limits add backpressure discontinuities.

**Resolution required:**
- For constant-input segments, the solution is piecewise-linear and tractable.
- For anything more complex, mark as `approximation_level: "numerical_fallback"`.
- Document that Queues are the node type most likely to force numerical methods.
- Multiple queues in series create multi-delay systems that are genuinely difficult — document this limitation.

---

### 2.6 Greedy Efficiency Formula Is Unspecified and Wrong for Multiplicative Upgrades

**The problem:** The doc says "payback period minimization" but never gives the formula. The standard idle game efficiency metric is `payback = cost / delta_production`. But:

- For multiplicative upgrades, payback period is `cost / (current_production * (multiplier - 1))`, which *decreases as production grows*. The greedy optimizer will perpetually delay multiplicative upgrades in favor of "cheaper" generators, even when buying the upgrade first would be globally better.
- The Demaine et al. paper proves the greedy approach is near-optimal ONLY for additive production with exponential costs. For multiplicative stacking, the Immediate Purchase Principle is unproven and likely fails.
- In practice, greedy is within 5-15% of optimal for typical idle games, but up to 30%+ worse for games with build-defining multiplicative choices.

**Resolution required:**
1. Specify the efficiency formula explicitly in the doc.
2. For multiplicative upgrades, consider a modified metric that accounts for compounding benefit over a look-ahead window (e.g., "production gained over the next N seconds, discounted by time to afford").
3. Recommend beam search as the minimum viable tier for games with heavy multiplicative stacking.

**Additional context from design owner:** Purchases with side effects on other bonuses (e.g., angel upgrades that spend angels, reducing the angel bonus) must have their efficiency score computed as net effect: `net_benefit = multiplier_gained - (angels_spent * 0.02 * current_production)`. This is a general pattern that applies to any purchase with coupled side effects.

---

### 2.7 Synergy/Threshold Bonuses Need Dedicated Modeling

**The problem (from design owner feedback):** The current node types don't cleanly capture:
- "Own 10 of everything -> x3 bonus"
- "Reach 1000 knowledge -> unlock recipe"
- "Craft 3 different items -> unlock new crafting recipe"
- Secondary economy thresholds (knowledge, prestige currency milestones)

**Resolution required:** Extend the `Achievement` and/or `UnlockGate` node with a richer condition system:

```
condition_type: single_threshold | multi_threshold | collection | compound
targets: list of {node_id, property, threshold}
logic: and | or | count_N
```

This covers:
- "Own 100 of Generator A" -> `single_threshold`
- "Own 25 of all generators" -> `multi_threshold` with `logic: and`
- "Craft 3 different recipes" -> `collection` with `logic: count_3`
- "Reach 1000 knowledge" -> `single_threshold` on a Resource node

**Critical design question:** Are these bonuses permanent one-time unlocks or conditional (deactivate if count drops below threshold)? The distinction matters for prestige — if a reset drops counts below the threshold, does the bonus deactivate? Both patterns exist in real games. The current `Achievement` implies permanent; `activator` edges imply conditional. Both semantics should be supported, with a `permanent: bool` field.

---

## 3. Medium-Priority Issues

### 3.1 Missing Node Types from Machinations Taxonomy

Machinations has two node types IdleFramework lacks:

- **Trader node:** Bidirectional resource exchange where net resources are preserved. IdleFramework's Converter only handles one-directional transformation (destroy input, create output). Two-way marketplaces, auction houses, and exchange mechanics have no representation.
- **End Condition node:** First-class "the game is won when X" element. Useful for analysis: "minimum time to reach end condition under different strategies."

**Recommendation:** Add both. Trader is straightforward (a Converter with bidirectional flow). End Condition enables the Analysis Engine to define victory conditions as part of the game graph rather than external parameters.

---

### 3.2 Event-Driven Engine Has Multiple Unaddressed Failure Modes

**a) Chattering / Zeno behavior:** State modifier feedback loops can create infinite event cascades in finite time. Example: buying Generator A increases production, which immediately affords Upgrade B, which increases production, which immediately affords Generator C... No detection or prevention is mentioned.

**Fix:** Add a maximum-events-per-epsilon-time safety bound (e.g., max 100 purchases within 0.001s). If hit, batch-evaluate all affordable candidates simultaneously.

**b) Simultaneous event epsilon is arbitrary:** The 0.001s epsilon affects results deterministically. Two purchases at t=10.0001 and t=10.0009 are simultaneous with epsilon=0.001 but sequential with epsilon=0.0001.

**Fix:** Document that epsilon is a tunable parameter and analyze sensitivity. Consider making it relative to segment length rather than absolute.

**c) Stale event invalidation:** After processing a purchase, ALL previously computed "time to next event" values are invalidated. The engine must recompute all candidate event times after every state change.

**Fix:** Document this as O(N) per event, O(N*K) total for K events. With the ~20 candidates bound from Section 1.5, this is O(20*K) — fast.

**d) Root-finding reliability:** Need bracketed methods (Brent's method) for finding when resource curves cross cost thresholds. Unbounded Newton's method can oscillate or diverge for polynomials with multiple nearby roots.

---

### 3.3 Tag Filtering Should Compare Strategies, Not Just Report Broken Chains

**The problem:** The doc says filtering by tags reports broken dependency chains. But filtering changes the *optimal strategy*, not just node reachability.

**Example:** With a paid x10 multiplier on Generator A, the optimal free strategy may focus on Generator B (always second-best with paid content available). The framework should report: "Filtering paid nodes changes the optimal strategy from A-focused to B-focused, with a Y% reduction in time-to-completion."

**Fix:** When tag filtering is applied, run the optimizer for both filtered and unfiltered graphs. Report: (a) which strategies change, (b) the performance gap, (c) which specific paid nodes cause the largest gap. This directly answers "what's the value-for-money of this IAP?"

---

### 3.4 MCTS Rollout Diversity Problem

**The problem:** For a deterministic domain with greedy rollouts, every rollout from the same state produces the same result. "Monte Carlo" exploration is meaningless without diversity.

**Fix:** Use epsilon-greedy rollouts with varied epsilon values, or randomized tie-breaking rules. Present MCTS as "tree search with greedy rollouts and UCB1 exploration" rather than implying connection to game-playing MCTS. Document that rollout diversity is needed for meaningful exploration.

Also: the doc specifies "average backup (default)" — but with deterministic greedy rollouts, average backup of identical values adds nothing. Max-backup or power-mean backup is more useful for exploring alternatives.

---

### 3.5 Multi-Layer Prestige Breaks the Greedy Heuristic

**The problem:** Antimatter Dimensions has 6 prestige-like mechanics with interacting timing. The greedy heuristic ("prestige when marginal rate drops below expected post-reset rate") cannot optimize nested prestige layers.

**Antimatter Dimensions' prestige mechanics:**
1. Dimension Boost (intra-run, repeatable)
2. Antimatter Galaxy (intra-run, repeatable)
3. Infinity (first major prestige)
4. Eternity (resets Infinity progress)
5. Time Dilation (modified eternity rules)
6. Reality (resets everything)

Galaxy timing affects Infinity timing which affects Eternity timing. The greedy heuristic for each layer individually will not find the global optimum.

**Fix:** The "better mode" (model next run as function of prestige currency) cannot be deferred — it is needed for any game with 2+ interacting prestige layers. For the greedy tier, at minimum provide "prestige when you can double your prestige currency" as the simpler community-standard heuristic alongside the marginal rate version.

---

### 3.6 Stacking Group Order-of-Operations Needs Specification

**The problem:** "Between groups, always multiplicative" is ambiguous. What does `additive_group_result * multiplicative_group_result` mean? Is the additive group's result `(1 + sum_of_bonuses)` that then multiplies with other groups?

**AdCap's actual model:**
```
final_profit = base_profit * owned_count
    * (1 + angel_count * 0.02)             // Angels: additive per angel
    * product(cash_upgrade_multipliers)     // Cash: multiplicative within
    * product(angel_upgrade_multipliers)    // Angel upgrades: multiplicative within
    * product(milestone_multipliers)        // Milestones: multiplicative within
```

Gold multipliers in AdCap are **additive with each other** (x12 + x12 = x24, not x144) — then the group total is multiplicative with other groups.

**Fix:** Specify the exact formula: for an additive group, the group multiplier is `(1 + sum_of_bonuses)`. For a multiplicative group, the group multiplier is `product(bonuses)`. Between groups: `final = base * product(group_multipliers)`. Document an explicit worked example in the design doc.

---

### 3.7 Cross-Resource Comparison Is Vague

**The problem:** "Exchange rates inferred from Converter nodes" fails when no converters exist. "Compare by relative production improvement per economy" is undefined.

**Fix:** Compare purchases by their effect on the *bottleneck resource's* time-to-next-milestone. If buying Gem upgrade A saves 10 minutes off the next Gold milestone (via indirect effects), and buying Gold generator B saves 8 minutes, buy A. This is computable from the piecewise analytical engine without needing explicit exchange rates.

---

### 3.8 Numerical Stability Testing Is Absent

**The problem:** For a "math-first" framework operating on BigFloat with float64 mantissa, numerical stability must be validated.

**Design owner decision:** 5 significant digits relative error is the acceptable tolerance. This means float64 (15-16 digits) has ~10 digits of headroom. Subtractive cancellation only becomes a problem when two values agree to 11+ digits.

**Still needed:**
- Tests for long chains of operations (1000+ sequential add/multiply) with error accumulation tracking.
- Subtractive cancellation scenarios (specifically: "time until affordable" when production rate nearly matches cost rate).
- Comparison against mpmath arbitrary-precision results for multi-segment analytical solutions.
- Document the 5-digit tolerance as a design requirement.

---

### 3.9 Test Fixtures Are 1-2 Orders of Magnitude Too Small

| Game | Generators | Upgrades | Prestige Layers |
|---|---|---|---|
| **MiniCap** (fixture) | 3 | 10 | 1 |
| **MediumCap** (fixture) | 8 | 30 | 2 |
| **AdVenture Capitalist** (Earth) | 10 | 700+ | 1 |
| **Cookie Clicker** | 20 | 700+ | 1 |
| **Antimatter Dimensions** | 8 | 100+ | 3-6 |

**Fix:** Add a "LargeCap" fixture at ~50-100 upgrades as an intermediate step. Can be procedurally generated with known analytical properties. Stress-tests the piecewise segmentation with many purchase events.

---

## 4. Low-Priority / Documentation Issues

### 4.1 Hypothesis Property Tests Are Wrong for Floats

Floating-point arithmetic is NOT associative or distributive. The doc lists "commutativity, associativity, distributivity" as BigFloat test properties.

**Fix:** Test *approximate* associativity (within tolerance) and *exact* properties:
- `a + 0 == a`, `a * 1 == a` (identity)
- `a * 0 == 0` (zero)
- `a + b == b + a` (commutativity, excluding NaN)
- If `a > 0` and `b > 0`, then `a + b > a` (monotonicity)
- `log10(a * b) ~= log10(a) + log10(b)` (within float epsilon)

Use `hypothesis.strategies.floats(allow_nan=False, allow_infinity=False, min_value=1.0, max_value=9.999)` for mantissa, `hypothesis.strategies.integers(min_value=-10**9, max_value=10**9)` for exponents.

---

### 4.2 "NumPy-compatible" Overstates the Integration

Struct-of-arrays requires writing all arithmetic functions manually. There is no automatic operator dispatch for compound dtypes.

**Fix:** Change "NumPy-compatible" to "NumPy-implementable via struct-of-arrays pattern." Describe the actual API: separate mantissa/exponent arrays with explicit vectorized functions.

---

### 4.3 No Packaging Strategy Specified

**Fix:** Add `pyproject.toml` with hatchling or setuptools as build backend. Define optional dependency groups:
- `[project.optional-dependencies]`
  - `test`: pytest, hypothesis, scipy, mpmath, sympy
  - `api`: fastapi, uvicorn
  - `cli`: typer
  - `dev`: all of the above

---

### 4.4 Python 3.11+ Should Be Reconsidered as 3.12+

Python 3.11 EOL is October 2027 (~18 months from project maturity). Python 3.12+ provides:
- `type` statement for cleaner type aliases (useful for discriminated union definitions)
- Improved error messages
- 5% additional performance
- `typing.override` decorator
- Longer support window

**Recommendation:** Target 3.12+.

---

### 4.5 Plotly HTML Reports Are 5-15MB Each

Each self-contained report includes ~3MB inlined plotly.js. Acceptable for the use case (shareable analysis reports), but should be documented. Offer `include_plotlyjs='cdn'` for smaller files when internet access is available.

---

### 4.6 Minor Citation: "1 + O(1/ln M)" Should Be "1 + O(1/log M)"

To match Demaine et al.'s notation. Asymptotically equivalent but should cite correctly.

---

### 4.7 SciPy solve_ivp Cannot Modify State Via Events (Test Harness Impact)

SciPy's `solve_ivp` events cannot modify state when fired ([scipy/scipy#19645](https://github.com/scipy/scipy/issues/19645)). The simulator needs a custom event-handling loop: detect terminal event, stop integration, modify state externally, restart with new initial conditions.

**Recommendation:** Consider whether a simpler fixed-step RK4 with manual event checking (check affordability at each step, bisect to find exact purchase time) is more reliable for the test-harness use case. The simulator doesn't need to be fast — it needs to be correct.

---

### 4.8 Stiffness Detection Threshold (10^6 Eigenvalue Ratio) Is Not Well-Founded

No universally accepted threshold exists (Trefethen & Bau, BIT 33, 1993).

**Recommendation:** Use a practical runtime heuristic instead: attempt explicit RK4 first, monitor step rejection rate, switch to Radau if step size drops below a floor. This is what production solvers (LSODA) actually do.

---

### 4.9 Missing: Regression Test Convention

No mention of preserving bug-revealing configurations as permanent regression tests.

**Fix:** Establish convention: every bug fix includes a test case in `tests/regressions/` with the game JSON, expected result, and explanatory comment.

---

### 4.10 Missing: Fuzz Testing of JSON Parser

The doc mentions fuzz testing the Formula DSL with Hypothesis but not the game model JSON parser.

**Fix:** Use Hypothesis to generate adversarial JSON: missing fields, wrong types, circular edge references, huge node arrays, Unicode in node names, duplicate IDs. Pydantic catches many, but error paths and messages should be tested.

---

## 5. Competitive Context

### 5.1 Market Position

IdleFramework occupies an **empty niche**: open-source, idle-game-specific, math-first analysis with automated strategy optimization. No existing tool combines these properties.

| Tool | Open Source | Idle-Specific | Math-First | Strategy Optimizer |
|---|---|---|---|---|
| **Machinations.io** | No | No | No (simulation) | No |
| **Profectus** | Yes | Yes | Partial (Formula system) | No |
| **cadCAD** | Yes | No | No (simulation) | No |
| **GEEvo** | Yes | No | No (evolutionary) | Yes (evolutionary) |
| **Spreadsheets** | N/A | Manual | Manual | Manual |
| **IdleFramework** | Yes | Yes | Yes | Yes (4-tier) |

### 5.2 Machinations.io Weaknesses (Competitive Opportunities)

- Simulation-based, not math-based (cannot give instant exact answers)
- Closed-source, no self-hosting, no programmatic access
- No idle-game-specific features (no BigFloat, no prestige node, no generator chain math)
- No strategy optimizer (users manually design "artificial players")
- Simulation run limits on lower tiers (1,000/month on free plan)
- UI complexity cited in user reviews ("very abstract and very dense")
- K-Machinations (2024) found **6 types of defects** in the commercial Machinations platform — validates need for open-source alternative with well-defined semantics

### 5.3 Developer Workflow Today

Developers currently balance idle games using:
1. Google Sheets / Excel spreadsheets (dominant tool)
2. Manual iteration in-engine with playtesting
3. Console prototyping
4. One-off Python/JS scripts
5. Desmos calculators for curve visualization

**No developer documented appears to use closed-form mathematical analysis.** This is the gap IdleFramework fills.

### 5.4 Market Size

The idle games market reached $2.5B in 2024 (CAGR 10.8%). The r/incremental_games community has 154K members. The target audience is primarily solo indie devs and small studios who are technical enough to use CLI/Python.

### 5.5 Academic Landscape

The academic literature on idle game optimization is **extremely thin**:
- Demaine et al. (2020) is essentially the only rigorous optimization-theoretic treatment.
- The 1 + O(1/log M) greedy bound applies only to single-resource, additive production, exponential costs.
- For multiplicative production, multiple resources, and prestige mechanics: no published optimality guarantees exist.
- The framework's ambition to extend beyond proven territory is novel and should be explicitly framed as such.

**Missing references worth adding:**
- Rupp, "Game Balancing via PCG and Simulations" (AIIDE 2025) — extends GEEvo
- "It might be balanced, but is it actually good?" (arXiv:2407.11396, 2024) — questions whether formal balance metrics correlate with player experience

---

## 6. Resolved Questions

These were open questions from the initial review. Design owner has provided answers.

### 6.1 Acceptable Relative Error for BigFloat: 5 Significant Digits

5 significant digits (~1e-5 relative error). This is very comfortable for float64 mantissa (15-16 digits), leaving ~10 digits of headroom. Subtractive cancellation only becomes problematic when values agree to 11+ digits — unlikely in practice. **Document this as a design requirement.**

### 6.2 Angel Upgrade / Angel Bonus Coupling: Must Be Modeled

The optimizer's efficiency score for angel upgrades must account for the net effect: multiplier gained minus angel bonus lost. This is a specific case of "purchases with side effects on other bonuses." The greedy efficiency score must evaluate net effect, not just direct benefit. **Add to Strategy Optimizer section.**

### 6.3 Offline/Idle Production: Out of Scope

Optimal strategy assumes active play. For most games, optimal strategy involves no idle time. **Add to Non-Goals or Strategy Optimizer assumptions.**

### 6.4 Purchasable Candidates Are Bounded to ~20

At any given time, only ~20 items have purchase costs within the same exponent. Items whose cost is within relative error of zero should be auto-purchased immediately ("free purchase threshold"). **This is a critical performance insight:**
- Per-segment candidate evaluation is O(20), not O(700)
- Free purchase threshold: if `cost / current_balance < 1e-5`, buy immediately without advancing time
- 700+ total purchases with O(20) candidates each and fast closed-form solves should be well under 200ms

**Document as a performance analysis in Math Engine section.**

### 6.5 Determinism Guarantee: Not a Concern

With 5 significant digits as the target tolerance, float non-determinism across platforms (x87 vs SSE, compiler flags) is irrelevant. **Drop as a concern.**

---

## 7. Required Design Doc Changes

Summary of all changes needed, organized by section:

### BigFloat Section
- [ ] Add: "5 significant digits relative error tolerance" as design requirement
- [ ] Remove or heavily qualify Numba compatibility claim
- [ ] Change "NumPy-compatible" to "NumPy-implementable via struct-of-arrays pattern"

### Game Model Section
- [ ] Add: Formula reference classification (Tier 1/2/3) for `current_value` dependencies
- [ ] Extend `Achievement` / `UnlockGate` with rich condition system for synergy/threshold bonuses
- [ ] Add `permanent: bool` field to distinguish permanent unlocks from conditional bonuses
- [ ] Add: Trader node (bidirectional exchange)
- [ ] Add: End Condition node
- [ ] Specify stacking group order-of-operations with explicit formula and worked example
- [ ] Clarify ProbabilityNode: add variance propagation, confidence intervals

### Math Engine Section
- [ ] Resolve scipy dependency: accept as production dep for matrix exponentials
- [ ] Add: Free purchase threshold (`cost / balance < 1e-5` -> auto-buy)
- [ ] Add: Purchasable candidate bound (~20) as performance assumption
- [ ] Add: Numerical root-finding (Brent's method) for time-to-purchase with deep chains
- [ ] Add: Chattering/Zeno detection and prevention
- [ ] Document Queue nodes as most likely to force numerical fallback

### Formula DSL Section
- [ ] Add: AST node type whitelist as defense-in-depth
- [ ] Remove claim of "no eval" — replace with accurate security description

### Strategy Optimizer Section
- [ ] Specify greedy efficiency formula explicitly
- [ ] Add: Net-effect evaluation for purchases with coupled side effects
- [ ] Add: ChoiceGroup configuration enumeration strategy
- [ ] Add: Toggle activation handling per optimizer tier
- [ ] Add: MCTS rollout diversity requirement
- [ ] Document that beam search is minimum viable tier for multiplicative-heavy games
- [ ] "Better mode" prestige timing should not be deferred for 2+ layer games

### Analysis Engine Section
- [ ] Tag filtering: run optimizer for both filtered/unfiltered, report strategy changes and performance gap
- [ ] Cross-resource comparison: define formally (bottleneck resource time-to-milestone)

### TDD Section
- [ ] Add: LargeCap fixture (~50-100 upgrades)
- [ ] Fix: Hypothesis property tests (approximate associativity, not exact)
- [ ] Add: Numerical stability test suite
- [ ] Add: Regression test convention (`tests/regressions/`)
- [ ] Add: JSON parser fuzz testing
- [ ] Add: Performance benchmark enforcement (pytest-benchmark)
- [ ] Replace fixed stiffness threshold with runtime heuristic
- [ ] Document SciPy event handling limitations and custom loop requirement

### Non-Goals / Assumptions Section
- [ ] Add: "Optimal active play assumed — offline production out of scope"
- [ ] Add: "Determinism across platforms is not guaranteed beyond 5-digit tolerance"

### Tech Stack Section
- [ ] Target Python 3.12+ instead of 3.11+
- [ ] Add: Packaging strategy (pyproject.toml, dependency groups)
- [ ] Fix citation: "1 + O(1/log M)" to match Demaine et al.

### New References
- [ ] Rupp, AIIDE 2025
- [ ] arXiv:2407.11396 (2024) — balance metrics vs player experience
