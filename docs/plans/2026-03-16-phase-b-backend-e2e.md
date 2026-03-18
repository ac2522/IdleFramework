# Phase B: Backend E2E Tests — Detailed Plan

**Date:** 2026-03-16
**Status:** COMPLETE — 100 tests passing, review feedback incorporated
**Depends on:** Phase A (game fixtures)

## Overview

Backend E2E tests using pytest, organized by **test category** (not fixture). Cross-fixture parametrization is a core pattern.

## File Organization

```
tests/e2e/
    __init__.py
    conftest.py                        # Shared helpers
    test_simulation_golden.py          # Golden value checks
    test_purchase_sequences.py         # Scripted buy orders
    test_prestige_cycles.py            # Prestige mechanics
    test_optimizer_ordering.py         # Optimizer comparisons
    test_cross_mechanic.py             # Mechanic interactions
    test_edge_cases.py                 # Edge cases
    golden_values/
        cookie_clicker.json
        factory_idle.json
        prestige_tower.json
        speed_runner.json
        full_kitchen.json
```

## Shared Infrastructure (`tests/e2e/conftest.py`)

- `PHASE_B_FIXTURES` — list of 5 fixture names
- `pb_fixture_name` — parametrized fixture
- `pb_game`, `pb_engine` — load and create engine
- Per-fixture named fixtures: `cookie_engine`, `factory_engine`, etc.
- `load_golden_values(name)` — loads from golden_values/
- `snapshot_state(engine)` — captures full state dict
- `assert_balance_approx(engine, resource, expected, rel=1e-3, abs_tol=1e-6)`

## Category 1: Simulation Correctness (`test_simulation_golden.py`)

### Golden Value Strategy
- Computed analytically, stored in JSON
- Dual tolerance: rel=1e-3, abs=1e-6
- Separate goldens for no-purchase baseline vs auto-advance

### Tests (~12)
- `test_resource_balance_at_checkpoint` — parametrized over fixtures × times (60, 300, 3600)
- `test_production_rate_at_checkpoint` — rate matches golden
- `test_time_advances_exactly` — engine.time == target
- `test_auto_advance_60s_golden` — balance >= no-purchase baseline
- `test_auto_advance_300s_golden` — economy has grown
- `test_production_rate_monotonically_increases` — sample at t=10,30,60,120,300
- `test_advance_to_is_deterministic` — two engines, same result
- `test_auto_advance_is_deterministic` — two engines, same purchases

## Category 2: Purchase Sequences (`test_purchase_sequences.py`)

### Tests (~12)
- `test_purchase_with_insufficient_funds_raises` — all fixtures
- `test_purchase_with_exact_funds_succeeds` — all fixtures
- `test_upgrade_already_purchased_raises` — cookie fixture
- `test_purchase_deducts_correct_cost` — cookie fixture
- `test_cookie_clicker_opening_sequence` — scripted: buy cursor → advance → buy more
- `test_factory_idle_converter_chain` — buy miner → advance → forge converts
- `test_speed_runner_tickspeed_then_generator` — tickspeed first, verify boosted rate
- `test_bulk_10_generators` — bulk purchase cost = geometric sum
- `test_bulk_cost_matches_sequential` — bulk cost == sum of individual costs
- `test_owned_increases_by_count` — parametrized count [1,5,10,25]
- `test_upgrade_changes_production_rate` — x2 upgrade doubles rate
- `test_purchase_order_does_not_affect_final_rate` — order independence

## Category 3: Prestige Cycles (`test_prestige_cycles.py`)

### Tests (~10)
- `test_prestige_resets_resources` — gold == 0, generators == 0
- `test_prestige_grants_currency` — prestige_pts > 0
- `test_prestige_currency_persists` — not reset
- `test_replay_after_prestige_starts_clean` — can rebuy
- `test_prestige_bonus_accelerates_replay` — production after > production before
- `test_play_prestige_replay_cycle` — full cycle
- `test_prestige_formula_scales_with_lifetime` — more earnings → more points
- `test_layer2_resets_layer1_currency` — hierarchy
- `test_layer2_requires_layer1_accumulation` — dependency
- `test_three_layer_prestige_chain` — full 3-layer test
- `test_prestige_gain_increases_with_playtime` — parametrized times

## Category 4: Optimizer Ordering (`test_optimizer_ordering.py`)

### Tests (~10)
- `test_greedy_beats_no_purchases` — all fixtures
- `test_greedy_returns_valid_result` — all fixtures
- `test_greedy_purchases_are_chronological` — times non-decreasing
- `test_beam_gte_greedy` — cookie, prestige fixtures
- `test_beam_width_1_equals_greedy` — cookie fixture
- `test_mcts_beats_no_purchases` — cookie, factory fixtures
- `test_mcts_with_seed_is_deterministic` — cookie fixture
- `test_mcts_completes_within_timeout` — 30s limit
- `test_bnb_beats_no_purchases` — cookie fixture
- `test_bnb_completes_within_timeout` — 30s limit
- `test_optimize_result_has_timeline` — all fixtures
- `test_optimize_result_approximation_level` — all fixtures

## Category 5: Cross-Mechanic Interactions (`test_cross_mechanic.py`)

### Tests (~12)
- Synergy + Tickspeed: `test_synergy_boosts_target`, `test_tickspeed_multiplies_all`, `test_synergy_and_tickspeed_stack`, `test_synergy_scales_with_owned`
- Buff + Drain: `test_buff_temporarily_boosts`, `test_drain_reduces_balance`, `test_buff_can_overcome_drain`, `test_net_rate_correct_with_drain`
- Autobuyer + Converter: `test_autobuyer_purchases_over_time`, `test_converter_transforms_resources`, `test_autobuyer_and_converter_chain`
- State Modifiers: `test_set_then_multiply_then_add_order`, `test_multiple_modifiers_on_same_target`, `test_state_modifier_affects_production`

## Category 6: Edge Cases (`test_edge_cases.py`)

### Tests (~12)
- Resource capacity: `test_balance_clamped_at_capacity`, `test_overflow_behavior_clamps`, `test_production_continues_at_capacity`
- Drain: `test_drain_never_goes_negative`, `test_drain_with_zero_balance`
- Buff: `test_buff_active_then_expires`, `test_buff_cooldown_prevents_reactivation`
- Empty: `test_empty_game_no_generators`, `test_empty_game_greedy_returns_empty`
- Validation: `test_circular_dependency_detected`, `test_self_referencing_edge_detected`
- Numerical: `test_no_nan_or_inf_after_long_simulation`, `test_no_negative_balances`, `test_very_large_owned_count`

## Known Challenges

1. Multi-resource optimizer ValueError (known issue) — use pytest.raises where expected
2. MCTS/BnB timeouts — keep iterations/depth small, use @pytest.mark.timeout(30)
3. Buff timing sensitivity — check state clearly before/after expiry, not at boundary
4. Auto-advance tolerance — use rel=1e-3 near purchase thresholds

## Implementation Sequence

1. Phase A must complete first
2. Create `tests/e2e/conftest.py`
3. `test_simulation_golden.py` first (foundational)
4. Generate golden values
5. `test_purchase_sequences.py`
6. `test_prestige_cycles.py`
7. `test_optimizer_ordering.py`
8. `test_cross_mechanic.py`
9. `test_edge_cases.py` (partially independent)
