# Phase A: Realistic Game Fixtures — Detailed Plan

**Date:** 2026-03-16
**Status:** COMPLETE — implemented, validated, all tests passing
**Depends on:** Nothing (foundation for all other phases)

## Overview

Five realistic game fixtures in `tests/fixtures/e2e/`, each exercising specific mechanic combinations. All JSON files following schema version `"1.0"`.

---

## 1. CookieClicker (`cookie_clicker.json`)

**Theme:** Classic clicker — single currency, cascading generator tiers, milestone achievements, manager automation.

**Mechanics tested together:**
- Generator tier cascade (6 tiers producing "cookies")
- Multiplicative + additive stacking groups interacting
- Achievement milestones providing permanent bonuses
- Manager nodes automating collection
- Upgrade progression gating
- End condition at 1e12 cookies

**Nodes (18):**

| ID | Type | Key Properties |
|---|---|---|
| `cookies` | resource | initial_value: 0 |
| `cursor` | generator | base_production: 0.1, cost_base: 15, cost_growth_rate: 1.15 |
| `grandma` | generator | base_production: 1.0, cost_base: 100, cost_growth_rate: 1.15 |
| `farm` | generator | base_production: 8.0, cost_base: 1100, cost_growth_rate: 1.15 |
| `mine` | generator | base_production: 47.0, cost_base: 12000, cost_growth_rate: 1.15 |
| `factory` | generator | base_production: 260.0, cost_base: 130000, cost_growth_rate: 1.15 |
| `bank` | generator | base_production: 1400.0, cost_base: 1200000, cost_growth_rate: 1.15 |
| `upg_x2_cursor` | upgrade | multiplicative, 2.0, cost: 100, target: cursor, stacking_group: click_mult |
| `upg_x2_grandma` | upgrade | multiplicative, 2.0, cost: 1000, target: grandma, stacking_group: click_mult |
| `upg_x2_farm` | upgrade | multiplicative, 2.0, cost: 11000, target: farm, stacking_group: click_mult |
| `upg_x2_mine` | upgrade | multiplicative, 2.0, cost: 120000, target: mine, stacking_group: click_mult |
| `upg_x5_all` | upgrade | multiplicative, 5.0, cost: 500000, target: _all, stacking_group: click_mult |
| `upg_plus10_cursor` | upgrade | additive, 10.0, cost: 500, target: cursor, stacking_group: flat_bonus |
| `ach_10_cursors` | achievement | threshold: cursor owned >= 10, bonus: 2.0x on cursor, stacking_group: milestones |
| `ach_50_grandmas` | achievement | threshold: grandma owned >= 50, bonus: 2.0x on grandma, stacking_group: milestones |
| `ach_100_farms` | achievement | threshold: farm owned >= 100, bonus: 2.0x on farm, stacking_group: milestones |
| `mgr_cursor` | manager | target: cursor, automation_type: collect |
| `end_trillion` | end_condition | threshold: cookies >= 1e12 |

**Edges (6):** All production_target from each generator to cookies.

**Stacking groups:** `click_mult: multiplicative`, `flat_bonus: additive`, `milestones: multiplicative`

**Golden values:**
- 10 cursors, no upgrades: 0.1 × 10 = 1.0/s
- 10 cursors + x2_cursor: 0.1 × 10 × 2.0 = 2.0/s
- 10 cursors + x2_cursor + ach_10_cursors: 0.1 × 10 × 2.0 × 2.0 = 4.0/s

---

## 2. FactoryIdle (`factory_idle.json`)

**Theme:** Multi-resource converter/crafting economy with drains, buffs, autobuyers, and resource capacity.

**Mechanics tested together:**
- Multiple resources with capacity constraints
- Converter chains (ore → ingots → steel → tools)
- Drain nodes with conditions
- Buff nodes (timed and proc)
- Autobuyer nodes with priority and bulk
- Upgrades on converter-feeding generators

**Nodes (24):**

| ID | Type | Key Properties |
|---|---|---|
| `ore` | resource | initial_value: 100, capacity: 5000 |
| `wood` | resource | initial_value: 50 |
| `ingots` | resource | initial_value: 0, capacity: 2000 |
| `steel` | resource | initial_value: 0 |
| `tools` | resource | initial_value: 0 |
| `gold` | resource | initial_value: 500 (currency) |
| `miner` | generator | base_production: 3.0, cost_base: 20, cost_growth_rate: 1.12 |
| `lumberjack` | generator | base_production: 2.0, cost_base: 25, cost_growth_rate: 1.12 |
| `smelter_worker` | generator | base_production: 1.0, cost_base: 100, cost_growth_rate: 1.15, cycle_time: 2.0 |
| `blacksmith` | generator | base_production: 5.0, cost_base: 500, cost_growth_rate: 1.18, cycle_time: 3.0 |
| `forge` | converter | inputs: [{ore, 3}], outputs: [{ingots, 1}], recipe_type: fixed |
| `foundry` | converter | inputs: [{ingots, 2}, {wood, 1}], outputs: [{steel, 1}], recipe_type: fixed |
| `workshop` | converter | inputs: [{steel, 1}, {wood, 2}], outputs: [{tools, 3}], recipe_type: scaling, conversion_limit: 10 |
| `ore_decay` | drain | rate: 1.0, condition: "balance_ore > 4000" |
| `ingot_rust` | drain | rate: 0.5 |
| `production_buff` | buff | timed, duration: 15.0, multiplier: 2.5, cooldown: 45.0, target: miner |
| `lucky_strike` | buff | proc, proc_chance: 0.15, multiplier: 3.0, target: smelter_worker |
| `auto_miner` | autobuyer | target: miner, interval: 10.0, priority: 1, bulk_amount: "1" |
| `auto_lumberjack` | autobuyer | target: lumberjack, interval: 10.0, priority: 0, bulk_amount: "1" |
| `upg_x2_miner` | upgrade | multiplicative, 2.0, cost: 500, target: miner, stacking_group: base |
| `upg_x2_smelter` | upgrade | multiplicative, 2.0, cost: 2000, target: smelter_worker, stacking_group: base |
| `upg_x3_all` | upgrade | multiplicative, 3.0, cost: 10000, target: _all, stacking_group: base |
| `ach_50_miners` | achievement | threshold: miner owned >= 50, bonus: 1.5x on miner, stacking_group: milestones |
| `end_1000_tools` | end_condition | threshold: tools >= 1000 |

**Edges (6):** production_target from generators to resources, consumption from drains to resources.

**Stacking groups:** `base: multiplicative`, `milestones: multiplicative`

**Golden values:**
- 1 miner, no upgrades: ore = 3.0/s, drain = 0 (below 4000)
- 5 miners, ore > 4000: gross 15.0/s, drain 1.0/s, net 14.0/s
- Buff EV (timed 15/45): 1 + (2.5-1)×(15/60) = 1.375

---

## 3. PrestigeTower (`prestige_tower.json`)

**Theme:** Deep prestige tree with 4 layers, sacrifice nodes, nested generators, synergies.

**Mechanics tested together:**
- 4 prestige layers with parent_layer chain
- Sacrifice node as alternative to prestige
- NestedGenerator (generates generators)
- SynergyNode bonuses across layers
- State modifier edges with all three modifier_modes (set, add, multiply)
- UnlockGate gating higher tiers

**Nodes (28):**
- 6 resources (points, p1-p4_currency, sacrifice_pts)
- 4 generators (gen_t1 through gen_t4)
- 1 nested_generator (nested_gen → gen_t1)
- 6 upgrades (x2 per tier, x3 all, p1 boost, p2 boost)
- 4 prestige_layers (layers 0-3 with parent chain)
- 1 sacrifice node
- 2 synergy nodes (t1→t2, t3→t4)
- 2 unlock_gates (gating prestige 2 and 3)
- 1 achievement (100 gen_t1, permanent)

**Edges (10):** production_target (4), state_modifier (3, one per mode: multiply/add/set), unlock_dependency (2), production_target for nested_gen.

**Stacking groups:** `base: multiplicative`, `prestige_boost: multiplicative`, `milestones: multiplicative`

**Golden values:**
- Prestige 1 at lifetime_points = 10000: floor(sqrt(10000)) = 100 p1_currency
- Prestige 2 at 500 p1_currency: floor(500/100) = 5 p2_currency
- Synergy: 20 gen_t1 → bonus = 20 × 0.02 = 0.4, gen_t2 mult = 1.4
- State modifier multiply: 100 p1_currency → 1 + 100×0.01 = 2.0× on gen_t1

---

## 4. SpeedRunner (`speed_runner.json`)

**Theme:** Speed/tickspeed focused with probability, proc buffs, end condition, queue, gate, register, choice group.

**Mechanics tested together:**
- TickspeedNode with upgrade tiers
- ProbabilityNode with crit chance
- Buff (proc and timed)
- End condition (compound: data >= 1e6 AND tokens >= 100)
- Queue node for delayed delivery
- Gate node for probabilistic splitting
- Register for computed values
- ChoiceGroup (speed vs power path)
- Drain for energy consumption

**Nodes (22):**
- 3 resources (energy, data, tokens)
- 3 generators (scanner, processor, compiler)
- 1 tickspeed
- 3 tickspeed upgrades + 2 generator upgrades
- 1 probability node (crit_scanner)
- 2 buffs (speed_burst proc, overclock timed)
- 1 queue, 1 gate, 1 register
- 1 choice_group with 2 path upgrades
- 1 drain, 1 end_condition

**Edges (9):** production_target (3), consumption (1), state_modifier (1), resource_flow (3), activator (1).

**Stacking groups:** `tick: multiplicative`, `base: multiplicative`

**Golden values:**
- 10 scanners, tickspeed 1.0: data = 5.0 × 10 = 50/s
- + tick_x1_5 + tick_x2: tickspeed = 3.0, data = 150/s
- + crit EV (1.4×): 210/s

---

## 5. FullKitchen (`full_kitchen.json`)

**Theme:** Every node type (22) and every edge type (8). Kitchen-sink game.

**Mechanics tested together:** All of them.

**Nodes (33):** All 22 node types present:
- resource (3), generator (3), nested_generator (1), converter (1)
- upgrade (6, covering mult/add/pct), prestige_layer (1), sacrifice (1)
- achievement (1), manager (1), probability (1), end_condition (1)
- unlock_gate (1), choice_group (1, with 2 path options), register (1)
- gate (1), queue (1), tickspeed (1), autobuyer (1), drain (1), buff (1), synergy (1)

**Edges (14):** All 8 edge types:
- production_target (4), consumption (1), resource_flow (3)
- state_modifier (2, multiply + add), activator (1), trigger (1)
- unlock_dependency (1), upgrade_target (1)

**Stacking groups (all 3 types):** `mult_grp: multiplicative`, `add_grp: additive`, `pct_grp: percentage`, `milestones: multiplicative`, `tick_grp: multiplicative`

---

## Infrastructure

### File structure
```
tests/fixtures/e2e/
    __init__.py
    cookie_clicker.json
    factory_idle.json
    prestige_tower.json
    speed_runner.json
    full_kitchen.json
```

### conftest.py additions
```python
E2E_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "e2e"
E2E_FIXTURE_NAMES = ["cookie_clicker", "factory_idle", "prestige_tower", "speed_runner", "full_kitchen"]

@pytest.fixture(params=E2E_FIXTURE_NAMES)
def e2e_fixture_name(request):
    return request.param

@pytest.fixture
def e2e_game(e2e_fixture_name) -> GameDefinition:
    path = E2E_FIXTURE_DIR / f"{e2e_fixture_name}.json"
    return GameDefinition.model_validate(json.loads(path.read_text()))

@pytest.fixture
def e2e_engine(e2e_game) -> PiecewiseEngine:
    return PiecewiseEngine(e2e_game, validate=True)
```

### Golden value computation
- Computed analytically (not by running the engine)
- `rate = base_production × owned / cycle_time × upgrade_mult × tickspeed × buff_ev × synergy_mult`
- Stored as `pytest.approx` assertions with `rel=1e-3`

### Implementation sequence
1. Create `tests/fixtures/e2e/` directory
2. `cookie_clicker.json` first (simplest)
3. `factory_idle.json` (adds converters, drains, buffs)
4. `prestige_tower.json` (adds prestige, nested gen, synergies)
5. `speed_runner.json` (adds tickspeed, probability, queue, gate, register, choice)
6. `full_kitchen.json` last (all types, most complex validation)
7. Update conftest.py
8. Validate each loads with `GameDefinition.model_validate()` and `PiecewiseEngine(game, validate=True)`

### Potential challenges
1. Gate/Queue nodes may lack full engine support — valuable to discover
2. NestedGenerator edge conventions need verification
3. State modifier `set` mode untested in fixtures — PrestigeTower exercises this
4. Formula variable names must use `[a-z0-9_]` only
