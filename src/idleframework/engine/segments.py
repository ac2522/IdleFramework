"""Piecewise analytical engine.

Advances game state through analytical segments. Between purchases,
production is constant so accumulation is linear (rate * dt).
Each purchase creates a new segment with updated production rates.

Production rate for a generator:
  effective_rate = count * base_production / cycle_time * multiplier(gen_id)

Multiplier is computed from stacking groups:
  For each stacking group, collect bonuses from owned upgrades targeting
  this generator (or _all). Compute per-group multiplier, then multiply
  all groups together.
"""
from __future__ import annotations

import math

from idleframework.model.game import GameDefinition
from idleframework.model.stacking import compute_final_multiplier
from idleframework.graph.validation import validate_graph
from idleframework.dsl.compiler import compile_formula, evaluate_formula
from idleframework.engine.solvers import bulk_cost, time_to_afford
from idleframework.engine.events import PurchaseEvent


class PiecewiseEngine:
    """Core simulation engine using piecewise-constant analytical segments."""

    def __init__(self, game: GameDefinition, validate: bool = False):
        self._game = game
        self._time = 0.0

        if validate:
            errors = validate_graph(game)
            if errors:
                raise ValueError(f"Validation errors: {'; '.join(errors)}")

        # State: owned counts per generator
        self._owned: dict[str, int] = {}
        # State: purchased upgrades (boolean — each can only be bought once)
        self._upgrades_owned: dict[str, bool] = {}
        # State: resource balances
        self._balances: dict[str, float] = {}

        # Build lookup maps
        self._nodes = {n.id: n for n in game.nodes}
        self._generators = {}
        self._upgrades = {}
        self._resources = {}
        self._production_edges: dict[str, str] = {}  # generator_id -> resource_id

        for node in game.nodes:
            if node.type == "generator":
                self._generators[node.id] = node
                self._owned[node.id] = 0
            elif node.type == "upgrade":
                self._upgrades[node.id] = node
                self._upgrades_owned[node.id] = False
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

    def is_upgrade_owned(self, upgrade_id: str) -> bool:
        return self._upgrades_owned.get(upgrade_id, False)

    def get_generator_multiplier(self, gen_id: str) -> float:
        """Compute total multiplier for a generator from all owned upgrades.

        Collects bonuses from upgrades targeting this generator or _all,
        groups them by stacking_group, applies the stacking rule per group,
        then multiplies all group results together.
        """
        # Collect bonuses by stacking group
        groups: dict[str, dict] = {}

        for upg_id, owned in self._upgrades_owned.items():
            if not owned:
                continue
            upg = self._upgrades[upg_id]
            if upg.target != gen_id and upg.target != "_all":
                continue

            group_name = upg.stacking_group
            if group_name not in groups:
                rule = self._game.stacking_groups.get(group_name, "multiplicative")
                groups[group_name] = {"rule": rule, "bonuses": []}

            groups[group_name]["bonuses"].append(upg.magnitude)

        return compute_final_multiplier(groups)

    def get_production_rate(self, resource_id: str) -> float:
        """Total production rate for a resource from all generators."""
        total = 0.0
        for gen_id, target_id in self._production_edges.items():
            if target_id == resource_id:
                gen = self._generators.get(gen_id)
                if gen is not None:
                    count = self._owned.get(gen_id, 0)
                    multiplier = self.get_generator_multiplier(gen_id)
                    total += count * gen.base_production / gen.cycle_time * multiplier
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

    def purchase_upgrade(self, upgrade_id: str) -> float:
        """Purchase an upgrade. Returns cost paid."""
        upg = self._upgrades.get(upgrade_id)
        if upg is None:
            raise ValueError(f"Unknown upgrade: {upgrade_id}")

        if self._upgrades_owned.get(upgrade_id, False):
            raise ValueError(f"Already owned: {upgrade_id}")

        cost = upg.cost
        pay_resource = self._find_payment_resource()
        balance = self._balances.get(pay_resource, 0.0)

        if balance < cost - 1e-10:
            raise ValueError(
                f"Cannot afford upgrade {upgrade_id}: cost={cost:.2f}, "
                f"balance={balance:.2f}"
            )

        self._balances[pay_resource] -= cost
        self._upgrades_owned[upgrade_id] = True
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

    def evaluate_prestige(self, prestige_id: str, **variables: float) -> float:
        """Evaluate a prestige layer's formula with given variables."""
        node = self._nodes.get(prestige_id)
        if node is None or node.type != "prestige_layer":
            raise ValueError(f"Unknown prestige layer: {prestige_id}")
        formula = compile_formula(node.formula_expr)
        return evaluate_formula(formula, variables)

    def evaluate_register(self, register_id: str, variables: dict[str, float]) -> float:
        """Evaluate a register node's formula with given variables."""
        node = self._nodes.get(register_id)
        if node is None or node.type != "register":
            raise ValueError(f"Unknown register: {register_id}")
        formula = compile_formula(node.formula_expr)
        return evaluate_formula(formula, variables)

    def _find_payment_resource(self) -> str:
        """Find the primary payment resource (first resource in game)."""
        for node in self._game.nodes:
            if node.type == "resource":
                return node.id
        raise ValueError("No resource nodes in game")
