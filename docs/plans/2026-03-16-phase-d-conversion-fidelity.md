# Phase D: Conversion Fidelity Tests — Detailed Plan

**Date:** 2026-03-16
**Status:** COMPLETE — 29 Vitest tests passing (82 total frontend unit tests), review feedback incorporated
**Depends on:** Phase A (game fixtures)

## Overview

Verify that `gameToGraph()` → `graphToGame()` round-trip preserves all node properties, edge properties, and metadata for all 22 node types and all 8 edge types.

## Test Locations

### Primary: Vitest (`frontend/src/editor/__tests__/conversion-fidelity.test.ts`)
Pure TypeScript unit tests — no browser needed. Fast, direct imports.

### Secondary: Python pytest (`tests/test_conversion_validation.py`)
Backend validation — verify Pydantic accepts round-tripped JSON.

## Known Asymmetries

The round-trip is NOT perfectly lossless:

1. **Injected defaults** — `gameToGraph` adds `tags: []`, `activation_mode: 'automatic'`, `pull_mode: 'pull_any'`, `cooldown_time: null` if absent
2. **Missing `name`** — nodes without `name` get `name: id` from `defaultNodeData`
3. **Position** — dagre generates positions not in source JSON
4. **Label/nodeType** — added by `gameToGraph`, stripped by `graphToGame`
5. **Extra fields survive** — `currency_id`, `parent_layer` etc. pass through via `[key: string]: unknown`

## Normalization Strategy

```typescript
function normalizeGameJson(game: GameDefinitionJSON): GameDefinitionJSON {
  // Deep clone
  // Sort nodes by id, sort edges by id
  // Add base defaults (tags, activation_mode, pull_mode, cooldown_time) to nodes
  // Remove undefined/null optional edge fields
  // Ignore positions
}
```

Compare: `expect(normalizeGameJson(roundTripped)).toEqual(normalizeGameJson(original))`

## Test Structure (~63 tests total)

### Section A: Helper utilities
- `loadFixture(filename)` — reads from `tests/fixtures/`
- `normalizeGameJson(game)` — normalization for comparison
- `roundTrip(game)` — gameToGraph → graphToGame

### Section B: Metadata round-trip (3 tests)
- Preserves name, description, stacking_groups, time_unit
- Preserves schema_version
- Handles absent optional fields

### Section C: Per-fixture round-trip (11 tests)
For each of the 11 existing fixture JSON files:
- Load → roundTrip → normalize → compare
- Verify node count, edge count, all properties

### Section D: Per-node-type coverage (22 tests)
For each of the 22 node types, create a minimal game with one node using non-default values:

1. `resource` — initial_value, capacity, overflow_behavior
2. `generator` — base_production, cost_base, cost_growth_rate, cycle_time
3. `nested_generator` — target_generator, production_rate, cost_base, cost_growth_rate
4. `upgrade` — upgrade_type, magnitude, cost, target, stacking_group, duration
5. `prestige_layer` — formula_expr, layer_index, reset_scope, persistence_scope, bonus_type, currency_id, parent_layer
6. `sacrifice` — formula_expr, reset_scope, bonus_type
7. `achievement` — condition_type, targets (array), logic, bonus (nested object), permanent
8. `manager` — target, automation_type
9. `converter` — inputs (array), outputs, rate, recipe_type, conversion_limit
10. `probability` — expected_value, variance, crit_chance, crit_multiplier
11. `end_condition` — condition_type, targets, logic
12. `unlock_gate` — condition_type, targets, prerequisites, logic, permanent
13. `choice_group` — options, max_selections, respeccable, respec_cost
14. `register` — formula_expr, input_labels
15. `gate` — mode, weights, probabilities
16. `queue` — delay, capacity
17. `tickspeed` — base_tickspeed
18. `autobuyer` — target, interval, priority, condition, bulk_amount, enabled
19. `drain` — rate, condition
20. `buff` — buff_type, duration, proc_chance, multiplier, target, cooldown
21. `synergy` — sources, formula_expr, target
22. All types with optional fields absent

### Section E: Per-edge-type coverage (12 tests)
For each of 8 edge types:
- Basic round-trip (edge_type, source, target, id)
- With optional properties (rate, formula, condition)
- `state_modifier` with all 3 modifier_modes (set, add, multiply) + target_property

### Section F: Edge cases (4 tests)
- Empty game (0 nodes, 0 edges)
- Node with base field overrides (activation_mode: 'interactive', tags: ['paid'])
- Node with explicit null optional fields
- Edge with rate: 0 (falsy but valid)

### Backend validation (11 tests)
Python pytest — for each fixture:
- Load JSON, add injected defaults, validate with `GameDefinition.model_validate()`
- Verify no validation errors

## Implementation Sequence

1. Create normalization utility first
2. Start with `minicap.json` round-trip
3. Add per-node-type tests (independent, parallelizable)
4. Add per-edge-type tests
5. Add complex fixture tests (highest bug risk: synergy_tickspeed, multi_prestige, gate_unlock)
6. Add backend validation (parallel with frontend tests)

## Potential Challenges

- Floating-point: `1000.0` vs `1000` — JS doesn't distinguish, should be fine
- Property ordering: `toEqual` handles key order differences
- Missing node types in fixtures: register, queue, probability, etc. — synthetic tests fill gap
- `stacking_group` on achievement bonus — nested object passes through unchanged, verify
