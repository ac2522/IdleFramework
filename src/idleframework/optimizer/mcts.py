"""Monte Carlo Tree Search optimizer for idle game purchase sequencing.

Uses epsilon-greedy rollout policy with UCB1 tree selection and average backup.
Designed as an anytime algorithm: more iterations yield equal or better results.
"""
from __future__ import annotations

import copy
import math
import random
from dataclasses import dataclass, field

from idleframework.engine.segments import PiecewiseEngine
from idleframework.engine.solvers import time_to_afford
from idleframework.engine.events import PurchaseEvent
from idleframework.optimizer.greedy import GreedyOptimizer, OptimizeResult


@dataclass
class _MCTSNode:
    """A node in the MCTS search tree."""

    node_id: str | None = None  # purchase that led to this node (None for root)
    parent: _MCTSNode | None = None
    children: dict[str, _MCTSNode] = field(default_factory=dict)  # node_id -> child
    visits: int = 0
    total_value: float = 0.0

    @property
    def avg_value(self) -> float:
        if self.visits == 0:
            return 0.0
        return self.total_value / self.visits


class MCTSOptimizer:
    """MCTS optimizer with epsilon-greedy rollouts and UCB1 selection.

    Parameters
    ----------
    engine : PiecewiseEngine
        The game engine (will be deepcopied for simulations).
    iterations : int
        Number of MCTS iterations per decision step.
    rollout_depth : int
        Maximum rollout depth (number of purchases per rollout).
    epsilon : float
        Probability of choosing a random candidate instead of greedy best.
    seed : int | None
        Random seed for reproducibility.
    """

    C = 1.41  # UCB1 exploration constant (sqrt(2))

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
        """Run MCTS optimization to target_time."""
        result = OptimizeResult()
        pay_resource = self._engine._find_payment_resource()

        step_count = 0
        while step_count < max_steps and self._engine.time < target_time:
            # Get candidates from current state
            greedy = GreedyOptimizer(self._engine)
            candidates = greedy.get_candidates()
            candidates = [c for c in candidates if c["efficiency"] > 0]

            if not candidates:
                break

            # Filter to candidates affordable within target_time
            balance = self._engine.get_balance(pay_resource)
            rate = self._engine.get_production_rate(pay_resource)
            remaining_time = target_time - self._engine.time
            affordable = []
            for c in candidates:
                if c["cost"] <= 0 or balance >= c["cost"] - 1e-10:
                    affordable.append(c)
                elif rate > 0:
                    wait = time_to_afford(c["cost"], rate, balance)
                    if wait <= remaining_time:
                        affordable.append(c)

            if not affordable:
                break

            candidates = affordable

            # If only one candidate, just pick it
            if len(candidates) == 1:
                best_id = candidates[0]["node_id"]
            else:
                # Run MCTS to pick the best action
                best_id = self._mcts_select(candidates, target_time, max_steps - step_count)

            # Execute the chosen purchase: advance time if needed, then buy
            candidate = next(c for c in candidates if c["node_id"] == best_id)
            cost = candidate["cost"]
            balance = self._engine.get_balance(pay_resource)
            rate = self._engine.get_production_rate(pay_resource)

            if balance < cost - 1e-10:
                if rate <= 0:
                    break
                wait = time_to_afford(cost, rate, balance)
                purchase_time = self._engine.time + wait
                if purchase_time > target_time:
                    break
                self._engine.advance_to(purchase_time)

                # Floating-point nudge
                new_balance = self._engine.get_balance(pay_resource)
                if new_balance < cost - 1e-10:
                    nudge = min(purchase_time + 1e-6, target_time)
                    if nudge > self._engine.time:
                        self._engine.advance_to(nudge)

            final_balance = self._engine.get_balance(pay_resource)
            if final_balance < cost - 1e-10:
                continue

            # Execute purchase
            if candidate["type"] == "upgrade":
                actual_cost = self._engine.purchase_upgrade(best_id)
            else:
                actual_cost = self._engine.purchase(best_id, 1)

            event = PurchaseEvent(
                time=self._engine.time,
                node_id=best_id,
                count=1,
                cost=actual_cost,
            )
            result.purchases.append(event)
            step_count += 1

        # Advance to target time
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
        """Run MCTS iterations and return the best action node_id."""
        root = _MCTSNode()

        for _ in range(self._iterations):
            # 1. Selection: walk down tree using UCB1
            node = root
            sim_engine = copy.deepcopy(self._engine)
            depth = 0

            while node.children and depth < self._rollout_depth:
                # Get candidates for this sim state
                sim_greedy = GreedyOptimizer(sim_engine)
                sim_candidates = sim_greedy.get_candidates()
                sim_candidates = [c for c in sim_candidates if c["efficiency"] > 0]
                if not sim_candidates:
                    break

                # Check if any child is unexplored
                unexplored = [
                    c for c in sim_candidates
                    if c["node_id"] not in node.children
                ]
                if unexplored:
                    # 2. Expansion: add a new child
                    chosen = self._rng.choice(unexplored)
                    child = _MCTSNode(node_id=chosen["node_id"], parent=node)
                    node.children[chosen["node_id"]] = child
                    self._sim_purchase(sim_engine, chosen, target_time)
                    node = child
                    depth += 1
                    break

                # UCB1 selection among existing children
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

                # Execute this action in simulation
                cand = next(
                    (c for c in sim_candidates if c["node_id"] == best_child.node_id),
                    None,
                )
                if cand is None:
                    break
                self._sim_purchase(sim_engine, cand, target_time)
                node = best_child
                depth += 1

            # If root has no children yet, expand all candidates
            if not root.children:
                for c in candidates:
                    child = _MCTSNode(node_id=c["node_id"], parent=root)
                    root.children[c["node_id"]] = child

                # Pick one to simulate from
                chosen = self._rng.choice(candidates)
                sim_engine = copy.deepcopy(self._engine)
                self._sim_purchase(sim_engine, chosen, target_time)
                node = root.children[chosen["node_id"]]
                depth = 1

            # 3. Rollout: epsilon-greedy simulation
            value = self._rollout(sim_engine, target_time, self._rollout_depth - depth)

            # 4. Backup: average backup
            backup_node = node
            while backup_node is not None:
                backup_node.visits += 1
                backup_node.total_value += value
                backup_node = backup_node.parent

        # Pick the child with the most visits (robust selection)
        if not root.children:
            # Fallback to greedy
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
        """Execute a purchase in simulation. Returns True if successful."""
        pay_resource = engine._find_payment_resource()
        cost = candidate["cost"]
        balance = engine.get_balance(pay_resource)
        rate = engine.get_production_rate(pay_resource)

        if balance < cost - 1e-10:
            if rate <= 0:
                return False
            wait = time_to_afford(cost, rate, balance)
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
        """Epsilon-greedy rollout from current state. Returns production rate."""
        for _ in range(remaining_depth):
            if engine.time >= target_time:
                break

            greedy = GreedyOptimizer(engine)
            candidates = greedy.get_candidates()
            candidates = [c for c in candidates if c["efficiency"] > 0]
            if not candidates:
                break

            # Epsilon-greedy: random with prob epsilon, greedy otherwise
            if self._rng.random() < self._epsilon:
                chosen = self._rng.choice(candidates)
            else:
                candidates.sort(key=lambda c: (-c["efficiency"], c["cost"]))
                chosen = candidates[0]

            if not self._sim_purchase(engine, chosen, target_time):
                break

        # Advance to target time and return production rate
        if engine.time < target_time:
            engine.advance_to(target_time)

        pay_resource = engine._find_payment_resource()
        return engine.get_production_rate(pay_resource)
