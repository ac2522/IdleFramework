"""Piecewise analytical engine.

Advances game state through analytical segments. Between purchases,
production is constant so accumulation is linear (rate * dt).
Each purchase creates a new segment with updated production rates.
"""
from __future__ import annotations

from idleframework.model.game import GameDefinition
from idleframework.engine.solvers import bulk_cost, time_to_afford
from idleframework.engine.events import PurchaseEvent


class PiecewiseEngine:
    """Core simulation engine using piecewise-constant analytical segments."""

    def __init__(self, game: GameDefinition):
        self._game = game
        self._time = 0.0

        # State: owned counts per generator/upgrade
        self._owned: dict[str, int] = {}
        # State: resource balances
        self._balances: dict[str, float] = {}

        # Build lookup maps
        self._nodes = {n.id: n for n in game.nodes}
        self._generators: dict[str, object] = {}
        self._resources: dict[str, object] = {}
        self._production_edges: dict[str, str] = {}  # generator_id -> resource_id

        for node in game.nodes:
            if node.type == "generator":
                self._generators[node.id] = node
                self._owned[node.id] = 0
            elif node.type == "resource":
                self._resources[node.id] = node
                self._balances[node.id] = node.initial_value

        for edge in game.edges:
            if edge.edge_type == "production_target":
                self._production_edges[edge.source] = edge.target

    @property
    def time(self) -> float:
        return self._time

    def get_balance(self, resource_id: str) -> float:
        return self._balances.get(resource_id, 0.0)

    def set_balance(self, resource_id: str, value: float) -> None:
        self._balances[resource_id] = value

    def get_owned(self, node_id: str) -> int:
        return self._owned.get(node_id, 0)

    def set_owned(self, node_id: str, count: int) -> None:
        self._owned[node_id] = count

    def get_production_rate(self, resource_id: str) -> float:
        """Total production rate for a resource from all generators."""
        total = 0.0
        for gen_id, target_id in self._production_edges.items():
            if target_id == resource_id:
                gen = self._generators.get(gen_id)
                if gen is not None:
                    count = self._owned.get(gen_id, 0)
                    total += count * gen.base_production / gen.cycle_time
        return total

    def advance_to(self, target_time: float) -> None:
        """Advance time, accumulating resources at current production rates."""
        if target_time <= self._time:
            return
        dt = target_time - self._time
        for resource_id in self._balances:
            rate = self.get_production_rate(resource_id)
            self._balances[resource_id] += rate * dt
        self._time = target_time

    def purchase(self, node_id: str, count: int = 1) -> float:
        """Purchase `count` units of a generator. Returns cost paid."""
        gen = self._generators.get(node_id)
        if gen is None:
            raise ValueError(f"Unknown generator: {node_id}")

        owned = self._owned.get(node_id, 0)
        cost = bulk_cost(gen.cost_base, gen.cost_growth_rate, owned, count)

        # Find the resource used to pay (first resource in the game)
        pay_resource = self._find_payment_resource()
        balance = self._balances.get(pay_resource, 0.0)

        if balance < cost - 1e-10:
            raise ValueError(
                f"Cannot afford {count}x {node_id}: cost={cost:.2f}, "
                f"balance={balance:.2f}"
            )

        self._balances[pay_resource] -= cost
        self._owned[node_id] = owned + count
        return cost

    def find_next_purchase_event(self, node_id: str) -> PurchaseEvent | None:
        """Find when the next unit of node_id becomes affordable."""
        gen = self._generators.get(node_id)
        if gen is None:
            return None

        owned = self._owned.get(node_id, 0)
        cost = bulk_cost(gen.cost_base, gen.cost_growth_rate, owned, 1)
        pay_resource = self._find_payment_resource()
        balance = self._balances.get(pay_resource, 0.0)
        rate = self.get_production_rate(pay_resource)

        if balance >= cost:
            return PurchaseEvent(
                time=self._time,
                node_id=node_id,
                count=1,
                cost=cost,
            )

        if rate <= 0:
            return None

        try:
            t = time_to_afford(cost, rate, balance)
        except ValueError:
            return None

        return PurchaseEvent(
            time=self._time + t,
            node_id=node_id,
            count=1,
            cost=cost,
        )

    def auto_advance(
        self,
        target_time: float,
        max_purchases_per_step: int = 100,
    ) -> list[PurchaseEvent]:
        """Advance to target_time, auto-purchasing generators as affordable.

        Returns list of purchases made.
        """
        purchases = []
        safety_counter = 0
        max_total = 10000  # Absolute safety limit

        while self._time < target_time and safety_counter < max_total:
            # Find earliest purchase event across all generators
            best_event: PurchaseEvent | None = None
            for gen_id in self._generators:
                event = self.find_next_purchase_event(gen_id)
                if event is not None and event.time <= target_time:
                    if best_event is None or event.time < best_event.time:
                        best_event = event

            if best_event is None:
                break

            # Advance to purchase time
            self.advance_to(best_event.time)

            # Buy within step limit
            step_purchases = 0
            while step_purchases < max_purchases_per_step:
                pay_resource = self._find_payment_resource()
                balance = self._balances.get(pay_resource, 0.0)
                gen = self._generators[best_event.node_id]
                owned = self._owned[best_event.node_id]
                cost = bulk_cost(gen.cost_base, gen.cost_growth_rate, owned, 1)
                if balance < cost - 1e-10:
                    break
                self.purchase(best_event.node_id, 1)
                purchases.append(PurchaseEvent(
                    time=self._time,
                    node_id=best_event.node_id,
                    count=1,
                    cost=cost,
                ))
                step_purchases += 1
                safety_counter += 1

            # Small time advance to prevent exact-time loops
            if self._time < target_time:
                self.advance_to(min(self._time + 1e-6, target_time))

        # Advance remaining time
        self.advance_to(target_time)
        return purchases

    def _find_payment_resource(self) -> str:
        """Find the primary payment resource (first resource in game)."""
        for node in self._game.nodes:
            if node.type == "resource":
                return node.id
        raise ValueError("No resource nodes in game")
