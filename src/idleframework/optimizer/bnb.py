"""Branch-and-Bound optimizer for idle game purchase sequencing.

Uses DFS with pruning: if the current best production exceeds a node's
upper bound, that branch is pruned. The upper bound assumes all remaining
budget goes to the highest-efficiency purchase available.
"""
from __future__ import annotations

import copy

from idleframework.engine.segments import PiecewiseEngine
from idleframework.engine.solvers import bulk_cost, time_to_afford
from idleframework.engine.events import PurchaseEvent
from idleframework.optimizer.greedy import GreedyOptimizer, OptimizeResult


class BranchAndBoundOptimizer:
    """DFS Branch-and-Bound optimizer with upper-bound pruning.

    Parameters
    ----------
    engine : PiecewiseEngine
        The game engine (will be deepcopied for branching).
    depth_limit : int
        Maximum search depth (number of purchases to consider).
    """

    def __init__(self, engine: PiecewiseEngine, depth_limit: int = 20):
        self._engine = engine
        self._depth_limit = depth_limit

    def optimize(
        self,
        target_time: float,
        max_steps: int = 500,
    ) -> OptimizeResult:
        """Run Branch-and-Bound optimization to target_time."""
        self._target_time = target_time
        self._pay_resource = self._engine._find_payment_resource()

        # Track best result found
        self._best_production = -1.0
        self._best_purchases: list[PurchaseEvent] = []
        self._best_engine: PiecewiseEngine | None = None

        # Start DFS
        self._dfs(
            engine=copy.deepcopy(self._engine),
            purchases=[],
            depth=0,
        )

        # Build result from best found
        result = OptimizeResult()
        if self._best_engine is not None:
            # Advance best engine to target time
            if self._best_engine.time < target_time:
                self._best_engine.advance_to(target_time)
            result.purchases = self._best_purchases
            result.final_production = self._best_engine.get_production_rate(self._pay_resource)
            result.final_balance = self._best_engine.get_balance(self._pay_resource)
            result.final_time = self._best_engine.time
        else:
            # No purchases possible — just advance
            engine_copy = copy.deepcopy(self._engine)
            if engine_copy.time < target_time:
                engine_copy.advance_to(target_time)
            result.final_production = engine_copy.get_production_rate(self._pay_resource)
            result.final_balance = engine_copy.get_balance(self._pay_resource)
            result.final_time = engine_copy.time

        return result

    def _dfs(
        self,
        engine: PiecewiseEngine,
        purchases: list[PurchaseEvent],
        depth: int,
    ) -> None:
        """Recursive DFS with pruning."""
        # Evaluate current node: advance to target and check production
        eval_engine = copy.deepcopy(engine)
        if eval_engine.time < self._target_time:
            eval_engine.advance_to(self._target_time)
        current_prod = eval_engine.get_production_rate(self._pay_resource)

        if current_prod > self._best_production:
            self._best_production = current_prod
            self._best_purchases = list(purchases)
            self._best_engine = eval_engine

        # Check depth limit
        if depth >= self._depth_limit:
            return

        # Get candidates
        greedy = GreedyOptimizer(engine)
        candidates = greedy.get_candidates()
        candidates = [c for c in candidates if c["efficiency"] > 0]

        if not candidates:
            return

        # Sort by efficiency descending for better pruning (best-first)
        candidates.sort(key=lambda c: (-c["efficiency"], c["cost"]))

        # Upper bound: current production + remaining depth * best possible delta
        # Use max delta across ALL candidates (not just first by efficiency)
        best_delta = max(c["delta_production"] for c in candidates)
        remaining = self._depth_limit - depth
        upper_bound = current_prod + remaining * best_delta

        if upper_bound <= self._best_production:
            # Prune: can't beat current best even in the best case
            return

        for candidate in candidates:

            # Try this purchase
            branch_engine = copy.deepcopy(engine)
            cost = candidate["cost"]
            balance = branch_engine.get_balance(self._pay_resource)
            rate = branch_engine.get_production_rate(self._pay_resource)

            # Advance time if needed
            if balance < cost - 1e-10:
                if rate <= 0:
                    continue
                wait = time_to_afford(cost, rate, balance)
                purchase_time = branch_engine.time + wait
                if purchase_time > self._target_time:
                    continue
                branch_engine.advance_to(purchase_time)

                new_balance = branch_engine.get_balance(self._pay_resource)
                if new_balance < cost - 1e-10:
                    nudge = min(purchase_time + 1e-6, self._target_time)
                    if nudge > branch_engine.time:
                        branch_engine.advance_to(nudge)

            final_balance = branch_engine.get_balance(self._pay_resource)
            if final_balance < cost - 1e-10:
                continue

            # Execute purchase
            try:
                if candidate["type"] == "upgrade":
                    actual_cost = branch_engine.purchase_upgrade(candidate["node_id"])
                else:
                    actual_cost = branch_engine.purchase(candidate["node_id"], 1)
            except ValueError:
                continue

            event = PurchaseEvent(
                time=branch_engine.time,
                node_id=candidate["node_id"],
                count=1,
                cost=actual_cost,
            )

            self._dfs(
                engine=branch_engine,
                purchases=purchases + [event],
                depth=depth + 1,
            )
