# Critical Review: IdleFramework Design Document

**Reviewed:** `docs/plans/2026-03-07-idleframework-design.md`
**Date:** 2026-03-07
**Method:** Parallel research agents with web search across 5 domains: academic literature, BigFloat/number systems, competitive landscape, stack/architecture, and game model completeness.

---

## Overall Assessment

The vision is strong and fills a genuine market gap. No open-source tool exists for algebraic analysis of idle game economies — designers currently use spreadsheets and manual playtesting. However, the design has several **architectural tensions that need resolution before implementation**, and the scope as written is too broad for a first release.

---

## 1. CRITICAL: The BigFloat/SciPy Incompatibility

**This is the single most important unresolved issue in the design.**

The document simultaneously claims:
- BigFloat handles numbers like 10^50, 10^100, 10^(10^1000)+
- SciPy ODE solvers power the math engine

These are **mutually exclusive**. SciPy's `solve_ivp` operates on `float64` numpy arrays. Maximum float64 is ~1.7e308. Any ODE solution exceeding this produces `inf` and crashes the solver. You cannot pass BigFloat objects to SciPy.

**Possible resolutions (each with trade-offs):**

| Approach | Pros | Cons |
|----------|------|------|
| **Log-space transformation** (`d(log R)/dt = rate/R`) | Standard technique in astrophysics/biology; keeps state variables small | Changes ODE structure; nonlinear terms become complex; needs auto-derivation from game graph |
| **Closed-form solutions only** (skip ODE solving) | Idle game generator chains have known polynomial solutions (`t^n/n!`); uses BigFloat natively | Cannot handle nonlinear interactions, custom formulas, or complex game graphs |
| **mpmath's `odefun`** | Arbitrary-precision ODE solver; handles any number size | 100-1000x slower than SciPy; Taylor series method |
| **Piecewise integration** | Run SciPy until near overflow, rescale, restart | Introduces error at boundaries; fragile |

**Recommendation:** Make closed-form BigFloat solutions the **primary** engine (this is the "math-first" vision), with log-space SciPy as a fallback for complex nonlinear games. Document this decision explicitly. The design doc's current framing of "SciPy ODE" as the engine is misleading given the number ranges involved.

---

## 2. Academic References: Overstated Claims and Missing Citations

### Demaine et al. Paper — Claims Need Correction

The design doc says it "proves NP-hardness, provides closed-form solutions and greedy approximation bounds." This overstates what the paper proves:

- **Closed-form solution exists only for the trivial one-item, fixed-cost case.** For k items, dynamic programming is required. "Closed-form solutions" (plural) is misleading.
- **NP-hardness is proven only for specific variants:** The R-version (achieve rate R) and the M-version with nonzero initial cookies are weakly NP-hard. The standard M-version from zero is solved in pseudo-polynomial time. The discrete-timestep variant is strongly NP-hard.
- **The greedy bound `1 + O(1/ln M)` is asymptotic** — it may not be near-optimal for small M (early game).
- **The model is extremely simplified** — single resource, additive production only. No multiplicative upgrades, no prestige, no converters.
- **Key structural result:** Claim 1.1 (Immediate Purchase Principle) — if the optimal strategy involves buying an item, buy it as soon as affordable. This means optimal play has two phases: a buying phase then a waiting phase.

### Missing Academic Work

The design doc should cite:

| Paper | Why It Matters |
|-------|---------------|
| **Dormans, "Engineering Emergence" (PhD, 2012)** | The academic foundation of Machinations.io; Petri net formalism for game economies. This is the primary competitor's theoretical basis. |
| **Alharthi et al., "Playing to Wait" (CHI 2018)** | Most comprehensive academic taxonomy of 66 idle games — would directly inform the node type system. |
| **Klint & van Rozen, "Micro-Machinations" (2014)** | Formal DSL for game economies — closest academic formalization to what IdleFramework attempts. |
| **K-Machinations (2025)** | Formal verification of Machinations semantics in the K framework — found real bugs in the commercial platform. Validates that formal methods for game economy tools work. |
| **GEEvo (IEEE CEC 2024, arXiv:2404.18574)** | Evolutionary algorithms for game economy balancing — an alternative to greedy/branch-and-bound. |
| **Kavanagh (2021)** | Probabilistic model checking for game balance — formal verification approach. |
| **Adams & Dormans, "Game Mechanics: Advanced Game Design" (2012)** | Practitioner-facing textbook that popularized Machinations for industry use. |
| **Spiel et al., "It Started as a Joke" (2019)** | Multi-institutional study on idle game design philosophy. |

### Kai Xiao MIT Thesis

The design doc describes this as providing "extended analysis." It is actually the **precursor** to the Demaine et al. journal paper (Xiao was Demaine's M.Eng. student). The journal paper supersedes it. This is a minor but misleading framing.

---

## 3. Branch-and-Bound Optimizer is Intractable

The design proposes branch-and-bound with state dominance pruning as an "exact" mode. **This will not terminate in reasonable time for real games.**

### State Space Analysis

AdVenture Capitalist alone has ~10 generators (up to 6000 levels each) and ~696 upgrades. State space: ~10^248 configurations. Branching factor: ~700 at each step.

- **State matching is too rare** — two paths almost never reach the exact same state, making dominance pruning ineffective.
- **Demaine et al. themselves use DP, not branch-and-bound**, and only for restricted cases.
- The paper proves NP-hardness even for the simplified model — real games are far harder.

### Alternative Approaches

| Method | Feasibility | Quality | Speed |
|--------|------------|---------|-------|
| **Greedy (efficiency score)** | Trivial | Near-optimal (`1 + O(1/ln M)` ratio) | Instant |
| **Branch-and-bound** | Only for tiny games | Optimal | Intractable for real games |
| **Dynamic programming** | Only for fixed-cost or small k | Optimal | Polynomial for restricted cases |
| **MCTS** | Any size game | Near-optimal, anytime | Configurable (seconds to hours) |
| **Genetic/evolutionary** | Any size game | Good, not guaranteed | Moderate |
| **Beam search** | Any size game | Good, depends on beam width | Fast |

**Recommendation:** Replace branch-and-bound with **MCTS (Monte Carlo Tree Search)** as the "better than greedy" option:
- Anytime algorithm — returns best solution found whenever you stop it
- Handles large state spaces via UCB1-guided exploration
- Naturally fits the sequential purchase decision structure
- Keep branch-and-bound only for test validation on small synthetic games

Also consider **beam search** as a middle ground: greedy-like speed but evaluates top-K candidates at each step.

---

## 4. Game Model: Critical Gaps

### High Severity — Model Cannot Represent Fundamental Mechanics

**1. No state-dependent behavior (the biggest gap).** Machinations.io separates *resource flow* (how stuff moves) from *state influence* (how current state changes the rules) using State Connections and Activators. IdleFramework conflates these into a single edge system. Without state connections, you cannot represent "production doubles when gold > 1000" or dynamic modifier activation.

**2. No temporal modifiers/buffs.** No node supports duration-based effects. Cannot represent Golden Cookie buffs (7x for 77 seconds), ad-reward boosts (2x for 4 hours), or time-limited events. The `Upgrade` type is permanent only.

**3. Multi-layered prestige is underspecified.** Antimatter Dimensions has 4+ prestige layers with cascading resets, inter-layer currency formulas, and milestones that modify reset scope. The current `PrestigeLayer` node lacks:
- `layer_index` (hierarchy position)
- `reset_scope` (list of node IDs/tags that are reset)
- `persistence_scope` (what survives this reset)
- `currency_formula` (expression referencing lower-layer values)
- `milestone_rules` (count-based modifications to reset behavior)

**4. No synergy/cross-modifier bonuses.** No edge type for "count of generator A modifies production rate of generator B." Games like Synergism are built entirely on this.

**5. Multi-resource costs not supported.** Schema assumes single-resource costs. Many games require "100 Gold AND 50 Gems AND 10 Research" for one purchase.

**6. No challenge/constraint modes.** Cannot express temporary rule modifications (e.g., "all multipliers reduced to x1 during this challenge").

### Medium Severity

- **Conditional production rates** — `UnlockGate` is binary; need continuous conditional modifiers
- **Diminishing returns / soft caps** — only implicit through cost growth; no explicit production caps or formulas like `bonus = base * (count / (count + softcap))`
- **Offline progress rules** — not modeled at all (caps, reduced rates, catch-up mechanics)
- **Monetization model too simplistic** — tags can't represent timed boosts, subscriptions, battle passes, dual-acquisition currencies (e.g., AdCap's Mega Bucks are both earnable AND purchasable), or starter bundles

### Low Severity (Reasonable to Defer)

- Minigames / subsystems (out of scope for a graph model)
- Combat/RPG mechanics (genre-blending)
- Inventory/equipment (slot-based systems are a different paradigm)
- Faction/alignment systems (mutually exclusive subgraph activation)

### The Fundamental Tension

A math-first framework needs continuous, differentiable systems. Real idle games are full of discrete state changes — unlocks, thresholds, faction choices, challenge modes. The ODE approach works for "how fast does currency grow given these generators" but breaks at every discrete decision point. The design needs an explicit **hybrid systems** strategy (continuous dynamics with discrete mode switches).

### What Machinations Does Differently

Machinations uses three mechanisms the IdleFramework model lacks:

1. **State Connections** — reactive links where the current value of a pool dynamically modifies other elements (rates, gates, activators). Separate from resource flows.
2. **Activators** — conditional connections that enable/disable nodes based on another node's state, using conditions like `>=100`, `==0`, or ranges like `3-6`.
3. **Registers** — computational nodes that perform arithmetic on inputs and feed results to modifiers. Enable complex conditional logic.

**Key insight:** Machinations separates *resource flow* from *state influence*. IdleFramework should adopt this distinction.

---

## 5. BigFloat Design — Viable but Overstated

### What's Good

- The `(mantissa: float, exponent: int)` design is a sound port of break_infinity.js with a genuine improvement: Python's arbitrary-precision `int` for the exponent removes the 9e15 ceiling that break_infinity.js hits.
- For a game analysis framework (not a game runtime), the break_eternity layer system is unnecessary.
- ~100-200 lines is a reasonable implementation size.

### What's Overstated

- **Performance claims against `decimal` are likely wrong.** The "10-13x faster" claim appears based on pre-Python 3.3 benchmarks, before `decimal` got its C-accelerated implementation via libmpdec. With the C implementation, the gap is more like 2-4x.
- `decimal.Decimal` at default 28-digit precision handles up to ~10^999999999, covers virtually all idle game scenarios, is battle-tested stdlib code, and requires zero custom implementation.

### The Strongest Case for Custom BigFloat

Not speed, but **API control** — a lightweight type the framework owns, with game-specific operations (geometric series helpers, display formatting like "1.23 Trillion") and no external dependencies. This is a valid reason, but the doc should be honest about it rather than leading with speed claims.

### break_infinity.js / break_eternity.js Context

- **break_infinity.js** uses the same design being proposed. Known issue: `pow()` normalization can require many iterations (e.g., 156 normalization steps for edge cases). Performance: pow is 100x faster than decimal.js, log is 600x faster.
- **break_eternity.js** was created because break_infinity.js was not enough for games reaching tetration territory (10^^10^^308). It introduces a `(sign, layer, mag)` system. The proposed design avoids this by using Python's unlimited `int` for the exponent — a genuine advantage.
- **Profectus** (the most active incremental game engine) uses break_eternity, validating the BigFloat approach for the incremental game space.

---

## 6. Stack and Architecture

### Overscoped — Phase the Delivery

The design proposes shipping simultaneously: library + CLI + FastAPI API + React Flow frontend + example game UI. This is 5 products. The doc correctly states "the library is the product" but then immediately adds 4 wrapper layers.

**Recommended phasing:**

| Phase | Deliverable | Dependencies |
|-------|------------|--------------|
| **Phase 1** | Library + CLI + Plotly reports | None — complete, shippable product |
| **Phase 2** | FastAPI API | Only when frontend work begins |
| **Phase 3** | React Flow frontend | Requires Phase 2 |
| **Phase 4** | Example game UI | Requires Phase 1 |

### React Flow — Right Choice

- 35.5k GitHub stars, actively maintained (v12.7.1, June 2025)
- MIT licensed, used by Stripe and LinkedIn
- Dominant in the React node editor space

| Library | Stars | Status | Notes |
|---------|-------|--------|-------|
| **React Flow** | 35.5k | Active | Best React integration, largest community |
| **Rete.js** | 11.9k | Active | Framework-agnostic, has dataflow engine |
| **Litegraph.js** | 7.9k | Stale (2yr) | Canvas-based, unmaintained |
| **Drawflow** | 6.0k | Stale (2yr) | Simple, unmaintained |

Known limitation: DOM-based rendering degrades with 1000+ nodes, but game graphs rarely reach that size.

### Performance: Add Numba from Day One

Python is the right language for the ecosystem, but the strategy optimizer (which calls the math engine thousands of times) will be the bottleneck. **`@numba.njit` on ODE right-hand-side functions yields 8-60x speedup** with a trivial annotation. CuPy/GPU is premature — GPUs help for batched parallel solves, not individual small ODE systems.

Consider [CyRK](https://github.com/jrenaud90/CyRK) as a drop-in `solve_ivp` replacement if SciPy performance becomes critical — Cython/Numba backends yield 40-300x speedup over pure SciPy.

### JSON Schema Validation is Day-One

JSON is the right format (React Flow native, human-readable, git-diffable). But a game definition with a typo silently produces wrong results. **Define a strict JSON Schema, validate on load, provide clear errors.** This is a day-one requirement, not a nice-to-have.

### Consider Altair/Vega-Lite Over Plotly for Reports

Self-contained Plotly HTML files include the full plotly.js bundle (~3.4 MB) regardless of chart complexity. Altair/Vega-Lite produces equivalent interactive HTML at ~400 KB (1/8th the size). For line charts and strategy comparisons, Altair is sufficient.

| Library | Self-contained HTML size | Interactivity | Fit |
|---------|------------------------|---------------|-----|
| **Plotly** | ~3.4 MB | Excellent | Heavy |
| **Altair/Vega-Lite** | ~400 KB | Good | Lighter, declarative |
| **Bokeh** | ~1.5 MB | Excellent | Middle ground |

### Pyodide/WASM Alternative

Consider whether the FastAPI layer could be replaced by **Pyodide/WASM** — running the Python library directly in the browser. This eliminates the API layer entirely and is increasingly viable for computational libraries of this size.

---

## 7. Tick Simulator as Test Harness — Sound but Needs Rigor

The strategy is correct but the implementation details matter:

### The Accuracy Paradox

The "ground truth" (tick simulator using forward Euler with O(h) error) is actually **less accurate** than what it's testing (SciPy's RK45 with O(h^4) error). You're validating that the *model* is correctly specified, not that SciPy works.

### Recommendations

1. **For closed-form formulas:** Test against exact analytical results (pen-and-paper calculations), not the simulator. The Demaine et al. paper provides specific formulas with known outputs.

2. **Use convergence testing for ODEs:** Run the simulator at multiple rates (100, 1000, 10000, 100000 ticks/sec) and verify results converge toward the ODE solver's answer. If they converge to a *different* value, one has the wrong equations.

3. **Specify dual tolerances:** Relative (0.1%) for large values, absolute for small values. Mirror SciPy's `rtol`/`atol` approach.

4. **Handle stiff systems:** Generators with vastly different time scales (1/sec vs 1e12/sec) make forward Euler unstable. Detect stiff systems and adjust simulator tick rate accordingly.

5. **Event detection at discontinuities:** Purchases, prestige resets, and unlock gates create discontinuities where Euler error spikes. The simulator needs very small steps near purchase events.

---

## 8. Competitive Landscape — The Gap is Real

### Machinations.io

- **Simulation-only** — cannot answer "what is optimal?" algebraically
- **Closed-source, expensive** — 100 component limit even on paid plans (their own Hades showcase uses 450+)
- **Steep learning curve** — users report significant onboarding friction
- **No code export** — translating models to game code is entirely manual
- **Deep academic foundation** (Dormans' PhD, Petri nets) that IdleFramework should engage with, not dismiss
- 50k+ developers, 300+ studios, 700+ academic institutions

### Flowtrix

Recent entrant (Early Access). Node-based desktop app, essentially a Machinations clone. Solo developer, very early stage. Plans for game engine integration.

### Kalivra

Open-source (GitHub, 151 stars), alpha-stage. Focuses on RPG stat balancing, not idle game economies. Uses Monte Carlo simulation. Different focus from IdleFramework.

### Spreadsheets — The Real Competitor

The vast majority of idle game designers use Google Sheets or Excel with Desmos for visualization. Pain points IdleFramework can solve:

- **Iteration speed** — each playtest takes days; no fast-forward to endgame
- **Late-game balance** — small parameter changes create huge divergences at high levels
- **Interaction effects** — hard to reason about how prestige, generators, and multipliers interact
- **Big numbers** — spreadsheets break at 10^308
- **No "what-if" analysis** — can't ask "if I change this cost curve, how does endgame change?" without replaying

### What Designers Want (But May Not Know to Ask For)

- Fast answers to "how long until milestone X?"
- Optimal upgrade ordering analysis
- Sensitivity analysis (which parameters matter most?)
- Growth curve visualization
- Export to game engine code
- Handling arbitrarily large numbers

### Profectus

The most active incremental game engine (Vue.js, TypeScript, break_eternity). Its **Formula system** (integration, inversion, cost calculations, affordability analysis) is the closest prior art to IdleFramework's math-first approach — but embedded in a game engine, not exposed as an analysis tool. Complementary, not competing.

---

## 9. ODE Solver Appropriateness — Where It Works and Breaks

### Where ODE Approximation Works Well

- **Generator chains with continuous production** — exact for the continuous-time version
- **Long time horizons** — continuous approximation error becomes negligible
- **Exponential/polynomial growth curves** — smooth, well-suited to ODE methods

### Where ODE Approximation Breaks Down

1. **Discrete purchase thresholds** — you can't buy 0.7 of a generator; the ODE smears this out. Error compounds across rapid early-game purchases.
2. **Early game / low numbers** — with 3 generators at 1/sec, discrete-to-continuous error is proportionally enormous. Worst precision where players spend the most attention.
3. **Prestige resets** — discontinuous state jumps. Requires event-driven ODE solving (SciPy supports events, but adds complexity).
4. **Conditional unlocks** — `UnlockGate`, Achievements, Managers create discontinuities where the system of equations changes entirely. Requires hybrid systems modeling.
5. **Stochastic mechanics** — `ProbabilityNode` expected values ignore variance, which matters for optimization (high-variance strategies have different worst-case performance).
6. **Integer floor/ceiling effects** — `floor(affordable)` rounding; for rapidly increasing costs, the difference matters.
7. **Offline accumulation with caps** — piecewise functions that break the smoothness assumption.

**The design should explicitly acknowledge that the ODE solver produces a continuous relaxation of the true discrete game.**

---

## 10. Open Questions That Need Answering

1. **How does the math engine handle the discrete/continuous boundary?** When a player buys a generator, the ODE system changes. How are purchase events detected and handled during integration?

2. **What is the input format for prestige formulas?** "Custom formulas via configurable expressions" — is this a string expression parser? A Python lambda? A restricted DSL? This has security implications if user-supplied.

3. **How are game graphs validated for well-formedness?** Can a game have cycles that create infinite resource loops? How are these detected vs. intentional feedback loops?

4. **What is the story for incremental adoption?** Can a designer model just one subsystem (e.g., the generator chain) without defining the entire game?

5. **How does tag filtering interact with graph connectivity?** If a `paid` upgrade is filtered out, but a `free` generator depends on it via an `unlock_dependency` edge, what happens?

6. **What is "time" in the framework?** Real-world seconds? Game ticks? Prestige-run-local time? Multi-layer prestige creates multiple time frames.

7. **How are upgrade interactions modeled?** If Upgrade A gives +100% and Upgrade B gives +100%, is the result +200% (additive stacking) or +300% (multiplicative stacking)? This is game-specific and must be configurable.

8. **What happens when the greedy optimizer encounters tied efficiency scores?** Tie-breaking strategy can significantly affect results.

9. **How are the Kongregate bulk-purchase formulas extended to BigFloat ranges?** The geometric series formula `base * rate^owned * (rate^n - 1) / (rate - 1)` overflows float64 for large `owned` or `n`.

10. **What is the MVP game fixture?** AdCap is mentioned but is surprisingly complex (10 generators, 696 upgrades, angel investors, events, mega bucks). A simpler reference game (3-5 generators, 10 upgrades, one prestige layer) would be better for initial validation.

---

## Summary: Prioritized Recommendations

### Must Fix Before Implementation

1. **Resolve the BigFloat/SciPy incompatibility** — decide on closed-form primary + log-space fallback
2. **Add state connections / reactive modifiers** to the game model — without these, you can model structure but not dynamics
3. **Replace branch-and-bound with MCTS** — B&B is intractable for real games
4. **Correct Demaine et al. claims** in the doc

### Should Fix Before v1.0

5. **Add temporal modifiers** (duration-based buffs/effects)
6. **Support multi-resource costs**
7. **Flesh out multi-layer prestige** (hierarchy, cascading resets, inter-layer formulas)
8. **Add JSON Schema validation** (day-one requirement)
9. **Phase the delivery** — library+CLI first, API+frontend later

### Nice to Have

10. Numba JIT on hot paths
11. Altair/Vega-Lite as lighter alternative to Plotly
12. Engage with Dormans' Petri net formalism in the academic references
13. Design a simpler MVP reference game than AdCap
14. Investigate Pyodide/WASM as alternative to FastAPI for browser integration

---

## Sources

### Academic Papers
- Demaine et al., "Cookie Clicker," *Graphs and Combinatorics* 36, 269-302 (2020). [arXiv:1808.07540](https://arxiv.org/abs/1808.07540)
- Xiao, "Cookie Clicker," M.Eng. Thesis, MIT (2018). [MIT DSpace](https://dspace.mit.edu/handle/1721.1/119555)
- Dormans, "Engineering Emergence: Applied Theory for Game Design," PhD Dissertation, University of Amsterdam (2012). [ILLC](https://www.illc.uva.nl/Research/Publications/Dissertations/DS-2012-12.text.pdf)
- Dormans, "Simulating Mechanics to Study Emergence in Games," AIIDE (2011). [AAAI](https://cdn.aaai.org/ojs/12477/12477-52-16005-1-2-20201228.pdf)
- Alharthi et al., "Playing to Wait: A Taxonomy of Idle Games," CHI (2018). [ACM DL](https://dl.acm.org/doi/10.1145/3173574.3174195)
- Klint & van Rozen, "Micro-Machinations: A DSL for Game Economies" (2014)
- K-Machinations, "Testing and Repairing Machinations Diagrams" (2025). [ResearchGate](https://www.researchgate.net/publication/390940739)
- Rupp & Eckert, "GEEvo: Game Economy Generation and Balancing," IEEE CEC (2024). [arXiv:2404.18574](https://arxiv.org/abs/2404.18574)
- Kavanagh, "Using Probabilistic Model Checking to Balance Games," PhD (2021). [PDF](https://ludii.games/citations/Thesis2021-5.pdf)
- Spiel et al., "It Started as a Joke: On the Design of Idle Games" (2019). [NSF PAR](https://par.nsf.gov/servlets/purl/10174274)

### Tools and Libraries
- [Machinations.io](https://machinations.io/) — Framework basics, State Connections, Activators, Registers, Pricing, Reviews
- [React Flow / xyflow](https://github.com/xyflow/xyflow) — v12.7.1, 35.5k stars
- [break_infinity.js](https://github.com/Patashu/break_infinity.js)
- [break_eternity.js](https://github.com/Patashu/break_eternity.js)
- [Profectus](https://github.com/profectus-engine/Profectus) — Formula system, Board system
- [Kalivra](https://github.com/DevBawky/Kalivra)
- [CyRK](https://github.com/jrenaud90/CyRK) — Cython/Numba ODE integrator
- [Flowtrix](https://store.steampowered.com/app/3687390/Flowtrix_System_and_Economy_Designer/)

### Game Design Resources
- [The Math of Idle Games Parts I-III](https://blog.kongregate.com/the-math-of-idle-games-part-i/) (Kongregate)
- [Balancing Tips: Idle Idol Postmortem](https://www.gamedeveloper.com/design/balancing-tips-how-we-managed-math-on-idle-idol)
- [Idle Games: The Mechanics and Monetization (GDC)](https://www.gdcvault.com/play/1022065/Idle-Games-The-Mechanics-and)
- [Idle Game Models Worksheets](https://archive.org/details/idlegameworksheets) (Internet Archive)

### Game Wikis (Mechanics Reference)
- [AdVenture Capitalist Wiki](https://adventure-capitalist.fandom.com/) — Angel Investors, Mega Bucks, Upgrades
- [Cookie Clicker Wiki](https://cookieclicker.wiki.gg/) — Golden Cookie, Garden, Wrinklers
- [Antimatter Dimensions Wiki](https://antimatter-dimensions.fandom.com/) — Eternity, Challenges, Time Dilation
- [Realm Grinder Wiki](https://realm-grinder.fandom.com/) — Research, Excavations
- [NGU Idle Wiki](https://ngu-idle.fandom.com/) — Adventure Mode, Questing
