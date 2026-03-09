"""Beam search optimizer for idle game purchase sequencing.

Maintains top-K engine states at each step, exploring multiple purchase
paths in parallel. At each step, every beam state is expanded by all
purchasable candidates, and the top-K resulting states (sorted by
production rate after purchase) are kept for the next step.

This allows the optimizer to find paths where a locally suboptimal
purchase (e.g., an expensive multiplier) leads to globally better
production — something the greedy optimizer misses.
"""
from __future__ import annotations

import copy

from idleframework.engine.segments import PiecewiseEngine
from idleframework.engine.solvers import time_to_afford
from idleframework.engine.events import PurchaseEvent
from idleframework.optimizer.greedy import GreedyOptimizer, OptimizeResult


class BeamSearchOptimizer:
    """Beam search purchase optimizer — maintains top-K states at each step."""

    def __init__(self, engine: PiecewiseEngine, beam_width: int = 5):
        self._engine = engine
        self._beam_width = beam_width

    def optimize(
        self,
        target_time: float,
        max_steps: int = 500,
    ) -> OptimizeResult:
        """Run beam search optimization to target_time.

        At each step:
        1. For each beam state, compute all purchasable candidates
        2. Expand each state by each candidate (wait if needed, then purchase)
        3. Keep top-K states by production rate
        4. Repeat until max_steps or target_time
        """
        pay_resource = self._engine._find_payment_resource()

        # Each beam entry: (engine_state, purchase_history, timeline)
        initial_timeline = [{
            "time": self._engine.time,
            "production_rate": self._engine.get_production_rate(pay_resource),
        }]
        beam = [(
            copy.deepcopy(self._engine),
            [],  # purchases
            list(initial_timeline),  # timeline
        )]

        for step in range(max_steps):
            # Expand all beam states
            expansions = []

            for engine_state, purchases, timeline in beam:
                if engine_state.time >= target_time:
                    # Already at target — keep as-is (no expansion)
                    expansions.append((engine_state, purchases, timeline))
                    continue

                greedy = GreedyOptimizer(engine_state)
                candidates = greedy.get_candidates()
                if not candidates:
                    # No candidates — keep state as-is
                    expansions.append((engine_state, purchases, timeline))
                    continue

                # Filter out zero/negative efficiency candidates
                candidates = [c for c in candidates if c["efficiency"] > 0]
                if not candidates:
                    expansions.append((engine_state, purchases, timeline))
                    continue

                # Sort by efficiency descending
                candidates.sort(key=lambda c: (-c["efficiency"], c["cost"]))

                # Limit candidates to beam_width to avoid combinatorial explosion
                candidates = candidates[:self._beam_width]

                expanded_any = False
                for candidate in candidates:
                    # Clone engine state for this branch
                    branch_engine = copy.deepcopy(engine_state)
                    branch_purchases = list(purchases)
                    branch_timeline = list(timeline)

                    cost = candidate["cost"]
                    node_id = candidate["node_id"]
                    branch_pay = branch_engine._find_payment_resource()
                    balance = branch_engine.get_balance(branch_pay)
                    rate = branch_engine.get_production_rate(branch_pay)

                    # If can't afford, advance time
                    if balance < cost - 1e-10:
                        if rate <= 0:
                            continue
                        wait = time_to_afford(cost, rate, balance)
                        purchase_time = branch_engine.time + wait
                        if purchase_time > target_time:
                            continue
                        branch_engine.advance_to(purchase_time)

                        # Floating-point drift nudge
                        new_balance = branch_engine.get_balance(branch_pay)
                        if new_balance < cost - 1e-10:
                            nudge = min(purchase_time + 1e-6, target_time)
                            if nudge > branch_engine.time:
                                branch_engine.advance_to(nudge)

                    # Verify affordability
                    final_balance = branch_engine.get_balance(branch_pay)
                    if final_balance < cost - 1e-10:
                        continue

                    # Execute purchase
                    if candidate["type"] == "upgrade":
                        actual_cost = branch_engine.purchase_upgrade(node_id)
                    else:
                        actual_cost = branch_engine.purchase(node_id, 1)

                    branch_purchases.append(PurchaseEvent(
                        time=branch_engine.time,
                        node_id=node_id,
                        count=1,
                        cost=actual_cost,
                    ))
                    branch_timeline.append({
                        "time": branch_engine.time,
                        "production_rate": branch_engine.get_production_rate(branch_pay),
                    })

                    expansions.append((branch_engine, branch_purchases, branch_timeline))
                    expanded_any = True

                if not expanded_any:
                    # Keep original state if no expansion succeeded
                    expansions.append((engine_state, purchases, timeline))

            if not expansions:
                break

            # Sort by production rate descending, keep top-K
            expansions.sort(
                key=lambda x: x[0].get_production_rate(x[0]._find_payment_resource()),
                reverse=True,
            )
            beam = expansions[:self._beam_width]

            # If all beam states are at or past target time, stop
            if all(e.time >= target_time for e, _, _ in beam):
                break

        # Pick the best beam state (highest production rate)
        best_engine, best_purchases, best_timeline = beam[0]

        # Advance best engine to target time
        if best_engine.time < target_time:
            best_engine.advance_to(target_time)

        # Update the original engine to match the best state
        self._engine._time = best_engine._time
        self._engine._owned = best_engine._owned
        self._engine._upgrades_owned = best_engine._upgrades_owned
        self._engine._balances = best_engine._balances

        result = OptimizeResult(
            purchases=best_purchases,
            timeline=best_timeline,
            final_production=best_engine.get_production_rate(pay_resource),
            final_balance=best_engine.get_balance(pay_resource),
            final_time=best_engine.time,
        )

        return result
