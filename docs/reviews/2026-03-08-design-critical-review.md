# Critical Review: IdleFramework Design Document (Revision 2)

**Date:** 2026-03-08
**Reviewing:** `docs/plans/2026-03-07-idleframework-design.md`
**Method:** 6 parallel research agents covering academic foundations, math engine feasibility, tech stack, competitor landscape, game model coverage, and TDD strategy. Web search used throughout.

---

## Executive Summary

The design document is **architecturally sound** in its core thesis -- a piecewise analytical engine that segments the game timeline at discrete events and solves algebraically within segments. This is genuinely novel; every competitor (Machinations, cadCAD, Flowtrix, GSS) is simulation-based. The competitive positioning as "the open-source, math-first alternative to Machinations.io" is validated by research showing no other tool occupies this niche.

However, the review uncovered **4 critical issues, 8 high-severity issues, and numerous moderate concerns** across mathematical feasibility, tech stack compatibility, game model coverage, testing strategy, and academic foundations.

---

## CRITICAL Issues (Must resolve before implementation)

### C1. `decimal.Decimal` + Numba = Dead End

**Numba's `@njit` cannot compile `decimal.Decimal`.** It only supports native types (int, float, complex, NumPy arrays). The design lists Numba as the deferred performance optimization -- this path is fundamentally broken. Furthermore:

- **NumPy doesn't support Decimal** -- arrays fall back to `dtype=object`, losing all vectorization
- **SciPy's `expm()` requires float64** -- matrix exponentials can't use Decimal in production
- **Float conversion overflows at ~10^308** -- the `pow()`, `log()`, `exp()` strategy silently produces `inf` for numbers idle games routinely reach (10^500+)

The MEMORY.md records an earlier decision for a custom `BigFloat(mantissa: float, exponent: int)` class -- the break_infinity.js approach. This is **superior** for this use case: Numba-compatible (two native types), NumPy-compatible, transcendentals trivial via log-space (`log10(BigFloat) = log10(mantissa) + exponent`), and already proven by thousands of idle games.

**Resolution needed:** Pick BigFloat or Decimal. The design document and MEMORY.md currently contradict each other.

### C2. Formula DSL Cannot Express Most Real Idle Game Formulas

The DSL lacks **conditional expressions and piecewise functions**. Testing against 8 major idle games showed that all 8 require conditionals:

| Pattern | Example | Games Using It |
|---------|---------|---------------|
| Soft caps | `if value < cap: value else: cap + sqrt(value - cap)` | NGU Idle, Cookie Clicker, most games |
| Milestone breakpoints | 4x damage at hero levels 200, 500, etc. | Clicker Heroes, AdCap |
| Stage-dependent formulas | Sacrifice exponent changes with achievements | Antimatter Dimensions |
| Piecewise cost curves | Different growth rates in different ranges | Universal |

Also missing: `sum()`/`prod()` over node groups, `clamp()`, `round()`. Without `if(cond, then, else)` or `piecewise()`, the DSL is a toy that can only express the simplest idle game mechanics.

### C3. Game-Level `stacking_mode` Is Fundamentally Wrong

Real idle games use **different stacking rules for different bonus categories simultaneously**. AdVenture Capitalist (the reference game!) has at minimum 4 stacking groups:

- Angel bonus: additive per-angel, then multiplicative with other categories
- Cash upgrades: multiplicative within category
- Angel upgrades: multiplicative within category
- Milestone bonuses: multiplicative within category

Final multiplier = `(angel_bonus) * product(cash_upgrades) * product(angel_upgrades) * product(milestones)`

This pattern is universal across idle games. A single game-level `stacking_mode` cannot represent it.

**Fix:** Per-upgrade `stacking_group` field. Within a group, bonuses combine by that group's rule. Between groups, they always multiply.

### C4. No Skill Trees / Multi-Prerequisite Upgrades / Mutually Exclusive Choices

7 of 8 games analyzed have **skill trees** (multi-prerequisite AND-logic for unlocks). 5 of 8 have **mutually exclusive choices** (factions, study paths, alignments). The model has neither:

- `unlock_dependency` only supports single-source dependencies, not "requires A AND B"
- No concept of "choose one of N" exclusive sets
- No concept of respeccable vs. permanent choices

**Fix:** Extend `UnlockGate` with `prerequisites: list[node_id]` + AND/OR logic. Add a `ChoiceGroup` node type with `max_selections`, `respeccable: bool`, `options: list[node_id]`.

---

## HIGH-Severity Issues

### H1. Forward Euler Test Simulator Is Unsuitable

Forward Euler is O(h) per step. For exponential growth systems (which idle games are by definition), accumulated error after T seconds is `O(h * e^{LT})`. For a generator producing at rate e^{10t}, after 1 hour the amplification factor is `e^{36000}` -- the simulator produces **numerically meaningless results** regardless of tick rate.

For stiff systems (eigenvalue ratio ~10^12 in a game with $1/sec and $1e12/sec generators), Euler requires step size h < 2e-12 for stability -- meaning 1.8e15 steps per simulated hour. Infeasible.

**Fix:** Replace with RK4 (trivial, ~20 lines, 4 orders of magnitude more accurate per step) or use SciPy's adaptive solvers (`solve_ivp` with `method='RK45'` or `method='Radau'` for stiff systems). The simulator is test-only -- runtime performance is irrelevant.

### H2. Prestige Timing Heuristic Is Not Optimal

"Prestige when `d(progress)/dt` falls below expected rate after reset" ignores that **waiting longer increases prestige currency**, which increases the next run's rate. The correct optimization is:

```
Maximize: total_progress(T_reset) + integral_of_next_run_progress(P(T_reset))
```

This requires modeling the entire next run as a function of prestige currency. The marginal analysis heuristic is a reasonable greedy approximation but should not be presented as "mathematically optimal." For multi-layer prestige (where layer-1 prestige value depends on future layer-2 resets), it fails entirely.

### H3. Branch-and-Bound "50-100 Purchases" Is 3-5x Too Optimistic

With branching factor ~30 and the state space of a typical idle game, even with dominance pruning, exact B&B is realistic for **10-20 purchases**, not 50-100. The raw tree at depth 50 has 30^50 nodes. Demaine et al.'s DP is polynomial only for fixed k items with fixed costs -- not the general increasing-cost multi-item case.

### H4. No Formula Parser Specified

The DSL accepts user-provided strings and promises "no arbitrary code execution." But the design names no parser library. This is the single most security-sensitive component. Using `eval()` in any form is unacceptable.

**Fix:** Specify Lark (LALR(1) parser, EBNF grammar, O(n) complexity) as a Phase 1 dependency. Add fuzz testing with Hypothesis. Add resource limits (max AST depth, max computation time) to prevent DoS via formulas like `2**2**2**2**2**100`.

### H5. No Graph Library Specified

The design describes cycle detection, topological sorting, dependency chain analysis, and connectivity analysis -- but names no graph library. NetworkX is the obvious choice (provides all needed algorithms, well-maintained, v3.6+).

### H6. t^n/n! Only Correct for Homogeneous Rates

The polynomial growth pattern for generator chains assumes all generators have **identical cycle times and produce continuously from creation**. AdVenture Capitalist's cycle times range from 0.6s to 36,864s. With heterogeneous rates, the formula generalizes to `t^n / product(r_i)` with per-generator rate constants, and initial conditions carry forward at segment boundaries. Still tractable but significantly more complex than the doc suggests.

### H7. No Academic Foundation for the Core Use Case

No published work extends Demaine et al.'s optimization results to handle **multiplicative production, multiple resources, or prestige mechanics**. The Immediate Purchase Principle is proven only for single-resource additive production. The framework's core use case operates beyond the boundary of proven theoretical results. The "math-first" branding should acknowledge this gap -- the closed-form solutions are building blocks, not completeness guarantees.

### H8. Property-Based Testing Missing

For a math engine, Hypothesis-based property testing is arguably more valuable than example-based tests. Essential properties: monotonicity of production, bulk cost = sum of individual costs, max-affordable inverse correctness, commutativity of independent purchases, prestige reset consistency, tag filtering subset relationships. pytest + parametrize alone is insufficient.

---

## MODERATE Issues

### M1. Matrix Exponentials Need Custom Implementation

SciPy can't use Decimal; mpmath is listed as test-only. If the production engine needs `e^{At}`, it must either implement Pade approximation with Decimal (nontrivial) or promote mpmath to a production dependency. For small matrices (n=10-30, typical for idle games), this is tractable but significant implementation effort. Consider mpmath as initial implementation.

### M2. Log-Space LSE Fallback Is Oversold

The log-sum-exp trick helps with multiplicative dynamics but does NOT help with:
- Additive dynamics (most idle game production is additive)
- Resource consumption/subtraction
- Generator chains (polynomial, not exponential)
- Conditional/threshold mechanics

"Short numerical integration" is the honest fallback for nonlinear systems. The design should say so more clearly.

### M3. MCTS Max-Backup Is Non-Standard

Literature shows max-backup (instead of average) **overestimates values from noisy rollouts**, causing instability. It can be worse than average backup when rollout quality is low. Consider power mean (interpolation between average and max) with a tunable parameter, defaulting to average.

**References:**
- Khandelwal et al., "On the Analysis of Complex Backup Strategies in MCTS" (ICML 2016)
- Coulom, "Efficient Selectivity and Backup Operators in MCTS" (2007)
- Generalized Mean Estimation (IJCAI 2020)

### M4. MiniCap Fixture Is Too Simple

3 generators, 10 upgrades, 1 prestige layer won't catch bugs from: stiff systems, cross-generator interactions, multi-layer prestige, upgrade stacking interactions, or state modifier feedback loops. Need a **MediumCap** fixture (8 generators, 2 prestige layers, 30+ upgrades, managers, converters) as day-one alongside MiniCap. Begin AdCap modeling in Phase 1, not "later."

### M5. Plotly Reports Are 3-5 MB Each

Self-contained Plotly HTML embeds the full plotly.js library (~3.4 MB). For a framework generating potentially many reports, this adds up. Altair/Vega-Lite produces comparable interactive charts at ~500 KB. Worth considering as an alternative.

### M6. Missing Node Types and Mechanics

| Missing Mechanic | Games Affected | Suggested Fix |
|-----------------|----------------|---------------|
| State machines / phases | Cookie Clicker, Realm Grinder, AD | Add `PhaseNode` with state transitions |
| Non-prestige partial resets | AD (Sacrifice), Realm Grinder, NGU | Generalize PrestigeLayer or add `SacrificeNode` |
| Equipment/inventory | AD (Glyphs), Clicker Heroes, Melvor, NGU | Out of scope for Phase 1 but acknowledge |
| Toggle activation mode | NGU, many games | Add `toggle` to activation_mode enum |
| Cooldown-based abilities | Cookie Clicker, Realm Grinder | Add `cooldown_time` node property |
| Resource allocation (split pool) | NGU Idle | Consider `Allocator` node type |
| Combat/damage modeling | Melvor, Clicker Heroes, Idle Slayer | Register node could work if DSL is extended |

### M7. Missing Test Categories

- **Mutation testing** (mutmut/cosmic-ray) -- essential for math-heavy code where sign errors produce subtly wrong results
- **Golden-file tests** for Plotly report data
- **Graph validation tests** (cycle detection, edge type compatibility, tag-filtered subgraph validity)
- **Numerical edge cases**: rate=1 (div by zero in geometric series), rate<1, zero production, NaN/Inf propagation, near-MAX_EMAX values
- **Determinism tests** for MCTS (same seed = same results)
- **Performance benchmarks** (pytest-benchmark) with regression thresholds

### M8. Missing Citations

- Van Rozen, "Languages of Games and Play" (ACM Computing Surveys, 2020) -- comprehensive survey of game design DSLs
- Van Rozen, "Cascade: A Meta-Language for Change, Cause and Effect" (SLE 2023) -- directly relevant to the expression DSL
- Micro-Machinations date is 2013 (SLE), not 2014 as cited

### M9. jsonschema vs Pydantic Redundancy

Since FastAPI (Phase 2) is built on Pydantic, using jsonschema for validation creates two parallel validation systems. Pydantic v2 validates ~3.5x faster and can export JSON Schema for the frontend. Consider Pydantic as the primary validation layer in Python, exporting JSON Schema for the React Flow frontend.

---

## Tech Stack Verification

### decimal.Decimal Performance (Benchmarked on Python 3.12)

| Operation | Claimed | Measured | Verdict |
|-----------|---------|----------|---------|
| Basic arithmetic vs float | 2-3x slower | 1.8-2.2x slower | Verified |
| `pow()` vs float | 200-800x slower | **1,191x slower** | Worse than claimed |
| `exp()` vs float | 200-800x slower | 130x slower | Within range |
| `ln()` vs float | 200-800x slower | 373x slower | Within range |

The `pow()` figure is ~50% worse than the claimed ceiling. This matters because power functions are core to idle game formulas.

### React Flow Current State

- **Current version:** React Flow 12 (renamed to `@xyflow/react`)
- **GitHub stars:** ~24,000 (not "35k+" as claimed)
- **Actively maintained:** Yes
- **Performance with large graphs:** Guidance available for 100+ nodes (memo, virtualization)
- **API stability concern:** v11-to-v12 involved significant breaking changes (package rename, API restructuring). Plan for similar churn.

### Missing from the Stack (Critical Gaps)

| Missing Dependency | Purpose | Recommendation |
|-------------------|---------|----------------|
| Formula parser | Parse expression DSL safely | Lark (LALR(1), O(n), EBNF grammar) |
| Graph library | Cycle detection, topological sort, connectivity | NetworkX (v3.6+) |
| SymPy | Symbolic verification of closed-form derivations | Add as test dependency alongside SciPy/mpmath |
| Hypothesis | Property-based testing for math engine | Add as test dependency |

---

## Competitive Landscape

| Tool | Approach | Idle-Specific | Open Source | Language |
|------|----------|---------------|-------------|----------|
| **Machinations.io** | Simulation (SaaS) | No | No | Browser |
| **cadCAD** | Simulation | No | Yes | Python |
| **Flowtrix** | Simulation | No | No (Steam) | N/A |
| **GSS** | Simulation | Yes | No (Godot) | GDScript |
| **GEEvo** | Evolutionary | No | Yes | Python |
| **Profectus** | Formula engine | Yes | Yes (game engine) | TypeScript |
| **IdleFramework** | **Analytical** | **Yes** | **Yes** | **Python** |

No other tool combines analytical math, idle-game specialization, and open-source availability. The positioning is genuinely unique and validated.

**Key competitive insights:**
- Machinations is purely simulation-based with no analytical engine -- the primary differentiation opportunity
- Machinations pricing is SaaS-tiered (Community free with public diagrams only, Starter/Pro/Enterprise paid)
- Machinations has 50k+ developers, 300+ studios, 700+ academic institutions -- brand awareness is the primary adoption challenge
- Profectus's formula system (inversion, integration, `calculateMaxAffordable()`) validates the math-first concept but solves a narrower problem
- GSS (Game Systems Simulator) is the only idle-specific tool found, and it is a solo-developer project with simulation-only approach
- cadCAD is the closest open-source alternative to Machinations but targets token engineering, not games

---

## Academic Foundations Verification

### Cited Papers -- All Verified

| Paper | Claims in Doc | Verdict |
|-------|--------------|---------|
| Demaine et al. (2020) | Closed-form for single-item fixed-cost; NP-hardness for R-goal (weak) and discrete timesteps (strong); greedy bound 1+O(1/ln M); Immediate Purchase Principle | All verified correct |
| Dormans (2012) | Petri net formalism for game economies | Verified. Still foundational but showing age |
| Klint & van Rozen | Formal DSL for game economies | Date is 2013, not 2014 as cited |
| K-Machinations | Found bugs in Machinations.io | Verified (Cotor & Craciun, 2024 proceedings) |
| Alharthi et al. (2018) | Most comprehensive idle game taxonomy | Verified. Still the most comprehensive, but 8 years old |
| Rupp & Eckert GEEvo (2024) | Evolutionary algorithms for game economy balancing | Verified. Simulation-based, complementary not competing |

### Critical Gap in Academic Foundation

**No published work extends Demaine et al.'s optimization results to multiplicative production, multiple resources, or prestige mechanics.** The framework's core use case operates beyond proven theoretical results. The Immediate Purchase Principle may not hold when buying item A makes item B more efficient (multiplicative stacking). The greedy approximation bound applies only to single-resource additive production.

This is not fatal -- the framework honestly offers heuristic optimizers for the general case -- but the "math-first" branding should acknowledge the boundary between proven and heuristic territory.

### Missing Citations Worth Adding

- Van Rozen, "Languages of Games and Play: A Systematic Mapping Study" (ACM Computing Surveys, 2020)
- Van Rozen, "Cascade: A Meta-Language for Change, Cause and Effect" (SLE 2023)
- Barreto & Julia, "Formal Approach Based on Petri Nets for Modeling and Verification of Video Games" (Computing and Informatics, 2021)
- Hwang & Melcer, "Exploring Engagement in Idle Game Design" (IEEE CoG, 2024)

---

## Open Questions That Need Answering

1. **BigFloat vs Decimal -- which is it?** The MEMORY.md and design doc disagree. This cascades into every performance and compatibility decision.

2. **How does the formula parser work?** Which library? What's the grammar? How are resource limits enforced? This is Phase 1 critical.

3. **How are generator counts exposed to state modifiers?** The common pattern "each Farm gives +1% to Mines" requires a generator's count as a readable value for formulas. Is this automatic?

4. **How does the segment engine handle near-simultaneous affordability?** When 5 generators become affordable within 0.001 seconds of each other, what determines ordering?

5. **What is the cross-resource exchange rate for multi-resource payback period?** The greedy optimizer needs to compare "spend gold on A" vs "spend crystals on B" -- how?

6. **How does `reset_scope` interact with nested prestige layers?** Is it transitive? Does resetting layer 3 automatically reset layers 1-2?

7. **How are sub-graphs / worlds / event economies modeled?** AdCap has Moon, Mars events with shared angel bonuses but independent economies.

8. **What happens when the math engine encounters a system it can't solve analytically?** Is there a clear, documented fallback path? How does the user know the result is approximate?

9. **How is the DSL validated at schema load time?** Type checking? Undefined variable detection? Division by zero in constant subexpressions?

10. **What is the target for "instant feedback during editing" in the React Flow frontend?** <100ms? <500ms? This constrains the analysis engine's performance budget for Phase 3.

---

## Summary Recommendation

The core architecture -- piecewise analytical segments with closed-form solvers between discrete events -- is the right approach and genuinely innovative. The main risks are not architectural but are in **three areas that need resolution before coding begins**:

1. **Number type decision** (Decimal vs BigFloat) -- affects every module
2. **DSL expressiveness** (add conditionals, piecewise, aggregation) -- affects model coverage
3. **Stacking model** (per-category, not game-level) -- affects correctness for real games

With these resolved, the design is implementable and fills a genuine gap in the tooling landscape.

---

## Research Sources

### Academic
- [Demaine et al., Cookie Clicker (arXiv:1808.07540)](https://arxiv.org/abs/1808.07540)
- [Demaine et al., Cookie Clicker (Graphs and Combinatorics)](https://link.springer.com/article/10.1007/s00373-019-02093-4)
- [Dormans, Engineering Emergence (PhD, 2012)](https://eprints.illc.uva.nl/id/eprint/2118/1/DS-2012-12.text.pdf)
- [Klint & van Rozen, Micro-Machinations (SLE 2013)](https://www.semanticscholar.org/paper/Micro-Machinations-A-DSL-for-Game-Economies-Klint-Rozen/4b5b729747f3db5d87008d76a7ecceb0566af555)
- [K-Machinations (Springer, 2024)](https://link.springer.com/chapter/10.1007/978-3-031-76440-0_18)
- [Alharthi et al., Playing to Wait (CHI 2018)](https://dl.acm.org/doi/10.1145/3173574.3174195)
- [GEEvo (arXiv:2404.18574)](https://arxiv.org/abs/2404.18574)
- [GEEvo (IEEE Xplore)](https://ieeexplore.ieee.org/document/10612054/)
- [Khandelwal et al., MCTS Backup Strategies (ICML 2016)](http://proceedings.mlr.press/v48/khandelwal16.pdf)
- [Coulom, MCTS Selectivity and Backup (2007)](https://inria.hal.science/inria-00116992/document)
- [Generalized Mean Estimation in MCTS (IJCAI 2020)](https://www.ijcai.org/proceedings/2020/0332.pdf)
- [Moler & Van Loan, 19 Dubious Ways to Compute Matrix Exponential](https://www.cs.jhu.edu/~misha/ReadingSeminar/Papers/Moler03.pdf)
- [Hwang & Melcer, Exploring Engagement in Idle Game Design (IEEE CoG 2024)](https://ieeexplore.ieee.org/document/10645671/)
- [Van Rozen Publications](https://vrozen.github.io/Publications/)
- [Kavanagh PhD Thesis (2021)](https://theses.gla.ac.uk/82618/)
- [Barreto & Julia, Petri Nets for Game Verification (2021)](https://www.cai.sk/ojs/index.php/cai/article/view/2021_1_216)

### Technical
- [Python decimal module](https://docs.python.org/3/library/decimal.html)
- [mpdecimal benchmarks](https://www.bytereef.org/mpdecimal/benchmarks.html)
- [Numba supported Python features](https://numba.pydata.org/numba-doc/dev/reference/pysupported.html)
- [React Flow performance docs](https://reactflow.dev/learn/advanced-use/performance)
- [React Flow v12 migration](https://reactflow.dev/learn/troubleshooting/migrate-to-v12)
- [xyflow GitHub](https://github.com/xyflow/xyflow)
- [Plotly HTML file size discussion](https://community.plotly.com/t/plotly-huge-html-file-size/64342)
- [Lark parser](https://github.com/lark-parser/lark)
- [NetworkX](https://networkx.org/)
- [break_infinity.js](https://github.com/Patashu/break_infinity.js)
- [break_eternity.js](https://github.com/Patashu/break_eternity.js)

### Competitors and Prior Art
- [Machinations.io](https://machinations.io/)
- [Machinations Pricing](https://machinations.io/pricing)
- [cadCAD](https://cadcad.org/)
- [Flowtrix (Steam)](https://store.steampowered.com/app/3687390/Flowtrix_System_and_Economy_Designer/)
- [GSS - Game Systems Simulator](https://neopryus.itch.io/idle-economy-simulator)
- [GEEvo (GitHub)](https://github.com/FlorianRupp/GEEvo-game-economies)
- [Profectus (GitHub)](https://github.com/profectus-engine/Profectus)
- [Profectus Formulas](https://moddingtree.com/guide/important-concepts/formulas)
- [Kalivra (GitHub)](https://github.com/DevBawky/Kalivra)

### Game Mechanics Research
- [Kongregate Math of Idle Games Part I](https://blog.kongregate.com/the-math-of-idle-games-part-i/)
- [Kongregate Math of Idle Games Part II](https://blog.kongregate.com/the-math-of-idle-games-part-ii/)
- [Kongregate Math of Idle Games Part III](https://blog.kongregate.com/the-math-of-idle-games-part-iii/)
- [AdVenture Capitalist Wiki](https://adventure-capitalist.fandom.com/)
- [Antimatter Dimensions Wiki](https://antimatter-dimensions.fandom.com/)
- [Cookie Clicker Wiki](https://cookieclicker.wiki.gg/)
- [Realm Grinder Wiki](https://realm-grinder.fandom.com/)
- [Clicker Heroes Wiki](https://clickerheroes.fandom.com/)
- [Melvor Idle Wiki](https://wiki.melvoridle.com/)
- [NGU Idle Wiki](https://ngu-idle.fandom.com/)
- [Idle Slayer Wiki](https://idleslayer.fandom.com/)
