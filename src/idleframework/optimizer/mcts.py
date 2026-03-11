"""Monte Carlo Tree Search optimizer for idle game purchase sequencing.

Uses epsilon-greedy rollout policy with UCB1 tree selection and average backup.
"""
from __future__ import annotations

import copy
import math
import random
from dataclasses import dataclass, field

from idleframework.engine.events import PurchaseEvent
from idleframework.engine.segments import PiecewiseEngine
from idleframework.optimizer.greedy import GreedyOptimizer, OptimizeResult


@dataclass
class _MCTSNode:
    node_id: str | None = None
    parent: _MCTSNode | None = None
    children: dict[str, _MCTSNode] = field(default_factory=dict)
    visits: int = 0
    total_value: float = 0.0

    @property
    def avg_value(self) -> float:
        if self.visits == 0:
            return 0.0
        return self.total_value / self.visits


class MCTSOptimizer:
    """MCTS optimizer with epsilon-greedy rollouts and UCB1 selection."""

    C = 1.41

    def __init__(
        self,
        engine: PiecewiseEngine,
        iterations: int = 100,
        rollout_depth: int = 10,
        epsilon: float = 0.1,
        seed: int | None = None,
    ):
        self._engine = engine
        self._iterations = iterations
        self._rollout_depth = rollout_depth
        self._epsilon = epsilon
        self._rng = random.Random(seed)

    def optimize(
        self,
        target_time: float,
        max_steps: int = 500,
    ) -> OptimizeResult:
        result = OptimizeResult()
        pay_resource = self._engine._get_primary_resource_id()

        step_count = 0
        consecutive_failures = 0
        while step_count < max_steps and self._engine.time < target_time:
            greedy = GreedyOptimizer(self._engine._game, copy.deepcopy(self._engine.state))
            candidates = greedy.get_candidates()
            candidates = [c for c in candidates if c["efficiency"] > 0]

            if not candidates:
                break

            balance = self._engine.get_balance(pay_resource)
            rate = self._engine.get_production_rate(pay_resource)
            remaining_time = target_time - self._engine.time
            affordable = []
            for c in candidates:
                if c["cost"] <= 0 or balance >= c["cost"] - 1e-10:
                    affordable.append(c)
                elif rate > 0:
                    wait = (c["cost"] - balance) / rate
                    if wait <= remaining_time:
                        affordable.append(c)

            if not affordable:
                break

            candidates = affordable

            if len(candidates) == 1:
                best_id = candidates[0]["node_id"]
            else:
                best_id = self._mcts_select(candidates, target_time, max_steps - step_count)

            candidate = next(c for c in candidates if c["node_id"] == best_id)
            cost = candidate["cost"]
            balance = self._engine.get_balance(pay_resource)
            rate = self._engine.get_production_rate(pay_resource)

            if balance < cost - 1e-10:
                if rate <= 0:
                    break
                wait = (cost - balance) / rate
                purchase_time = self._engine.time + wait
                if purchase_time > target_time:
                    break
                self._engine.advance_to(purchase_time)

                new_balance = self._engine.get_balance(pay_resource)
                if new_balance < cost - 1e-10:
                    nudge = min(purchase_time + 1e-6, target_time)
                    if nudge > self._engine.time:
                        self._engine.advance_to(nudge)

            # Try purchase (advance_to may have auto-purchased, changing state)
            try:
                if candidate["type"] == "upgrade":
                    actual_cost = self._engine.purchase_upgrade(best_id)
                else:
                    actual_cost = self._engine.purchase(best_id, 1)
            except ValueError:
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    break
                continue

            consecutive_failures = 0
            event = PurchaseEvent(
                time=self._engine.time,
                node_id=best_id,
                count=1,
                cost=actual_cost,
            )
            result.purchases.append(event)
            step_count += 1

        if self._engine.time < target_time:
            self._engine.advance_to(target_time)

        result.final_production = self._engine.get_production_rate(pay_resource)
        result.final_balance = self._engine.get_balance(pay_resource)
        result.final_time = self._engine.time
        return result

    def _mcts_select(
        self,
        candidates: list[dict],
        target_time: float,
        remaining_steps: int,
    ) -> str:
        root = _MCTSNode()

        for _ in range(self._iterations):
            node = root
            sim_engine = copy.deepcopy(self._engine)
            depth = 0

            while node.children and depth < self._rollout_depth:
                sim_greedy = GreedyOptimizer(sim_engine._game, copy.deepcopy(sim_engine.state))
                sim_candidates = sim_greedy.get_candidates()
                sim_candidates = [c for c in sim_candidates if c["efficiency"] > 0]
                if not sim_candidates:
                    break

                unexplored = [
                    c for c in sim_candidates
                    if c["node_id"] not in node.children
                ]
                if unexplored:
                    chosen = self._rng.choice(unexplored)
                    child = _MCTSNode(node_id=chosen["node_id"], parent=node)
                    node.children[chosen["node_id"]] = child
                    self._sim_purchase(sim_engine, chosen, target_time)
                    node = child
                    depth += 1
                    break

                best_ucb = -float("inf")
                best_child = None
                log_parent = math.log(node.visits) if node.visits > 0 else 0

                for cand in sim_candidates:
                    cid = cand["node_id"]
                    if cid not in node.children:
                        continue
                    child = node.children[cid]
                    if child.visits == 0:
                        best_child = child
                        best_ucb = float("inf")
                        break
                    exploit = child.avg_value
                    explore = self.C * math.sqrt(log_parent / child.visits)
                    ucb = exploit + explore
                    if ucb > best_ucb:
                        best_ucb = ucb
                        best_child = child

                if best_child is None:
                    break

                cand = next(
                    (c for c in sim_candidates if c["node_id"] == best_child.node_id),
                    None,
                )
                if cand is None:
                    break
                self._sim_purchase(sim_engine, cand, target_time)
                node = best_child
                depth += 1

            if not root.children:
                for c in candidates:
                    child = _MCTSNode(node_id=c["node_id"], parent=root)
                    root.children[c["node_id"]] = child

                chosen = self._rng.choice(candidates)
                sim_engine = copy.deepcopy(self._engine)
                self._sim_purchase(sim_engine, chosen, target_time)
                node = root.children[chosen["node_id"]]
                depth = 1

            value = self._rollout(sim_engine, target_time, self._rollout_depth - depth)

            backup_node = node
            while backup_node is not None:
                backup_node.visits += 1
                backup_node.total_value += value
                backup_node = backup_node.parent

        if not root.children:
            candidates.sort(key=lambda c: (-c["efficiency"], c["cost"]))
            return candidates[0]["node_id"]

        best_child = max(root.children.values(), key=lambda c: c.visits)
        return best_child.node_id

    def _sim_purchase(
        self,
        engine: PiecewiseEngine,
        candidate: dict,
        target_time: float,
    ) -> bool:
        pay_resource = engine._get_primary_resource_id()
        cost = candidate["cost"]
        balance = engine.get_balance(pay_resource)
        rate = engine.get_production_rate(pay_resource)

        if balance < cost - 1e-10:
            if rate <= 0:
                return False
            wait = (cost - balance) / rate
            purchase_time = engine.time + wait
            if purchase_time > target_time:
                return False
            engine.advance_to(purchase_time)

            new_balance = engine.get_balance(pay_resource)
            if new_balance < cost - 1e-10:
                nudge = min(purchase_time + 1e-6, target_time)
                if nudge > engine.time:
                    engine.advance_to(nudge)

        final_balance = engine.get_balance(pay_resource)
        if final_balance < cost - 1e-10:
            return False

        try:
            if candidate["type"] == "upgrade":
                engine.purchase_upgrade(candidate["node_id"])
            else:
                engine.purchase(candidate["node_id"], 1)
        except ValueError:
            return False
        return True

    def _rollout(
        self,
        engine: PiecewiseEngine,
        target_time: float,
        remaining_depth: int,
    ) -> float:
        for _ in range(remaining_depth):
            if engine.time >= target_time:
                break

            greedy = GreedyOptimizer(engine._game, copy.deepcopy(engine.state))
            candidates = greedy.get_candidates()
            candidates = [c for c in candidates if c["efficiency"] > 0]
            if not candidates:
                break

            if self._rng.random() < self._epsilon:
                chosen = self._rng.choice(candidates)
            else:
                candidates.sort(key=lambda c: (-c["efficiency"], c["cost"]))
                chosen = candidates[0]

            if not self._sim_purchase(engine, chosen, target_time):
                break

        if engine.time < target_time:
            engine.advance_to(target_time)

        pay_resource = engine._get_primary_resource_id()
        return engine.get_production_rate(pay_resource)
