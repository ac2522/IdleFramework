"""Greedy optimizer — always buys the highest efficiency item next.

Wraps PiecewiseEngine to advance time to each purchase, then pick the
most efficient next candidate. Efficiency formulas:

- Generator: delta_production / cost
- Multiplicative upgrade: production * (magnitude - 1) / cost
- Additive upgrade: bonus * (base_production / cycle_time) / cost
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from idleframework.bigfloat import BigFloat
from idleframework.engine.segments import PiecewiseEngine
from idleframework.engine.solvers import bulk_purchase_cost
from idleframework.model.nodes import AutobuyerNode, Generator, TickspeedNode, Upgrade
from idleframework.model.state import GameState

if TYPE_CHECKING:
    from idleframework.model.game import GameDefinition


@dataclass
class PurchaseStep:
    """A single purchase decision."""

    time: float
    node_id: str
    cost: float
    efficiency: float
    cash_before: float
    cash_after: float


@dataclass
class OptimizeResult:
    """Result from any optimizer run."""

    purchases: list = field(default_factory=list)
    timeline: list[dict] = field(default_factory=list)
    final_production: float = 0.0
    final_balance: float = 0.0
    final_time: float = 0.0


class GreedyOptimizer:
    """Greedy optimizer: always buy the highest-efficiency item next."""

    def __init__(self, game: GameDefinition, state: GameState | None = None):
        self.game = game
        self.engine = PiecewiseEngine(game, state)
        self.steps: list[PurchaseStep] = []
        self._autobuyer_targets: set[str] = set()
        for node in self.game.nodes:
            if isinstance(node, AutobuyerNode):
                self._autobuyer_targets.add(node.target)

    def compute_generator_efficiency(self, gen_id: str) -> float:
        """Efficiency of buying 1 more of a generator.

        Formula: (base_production / cycle_time * multiplier) / cost
        """
        node = self.game.get_node(gen_id)
        if not isinstance(node, Generator):
            return 0.0

        ns = self.engine.state.get(gen_id)
        cost_bf = bulk_purchase_cost(
            BigFloat(node.cost_base),
            BigFloat(node.cost_growth_rate),
            ns.owned,
            1,
        )
        cost = float(cost_bf)
        if cost <= 0:
            return float("inf")

        gen_mult = self.engine._compute_generator_multipliers().get(gen_id, 1.0)
        delta_prod = node.base_production / node.cycle_time * gen_mult
        return delta_prod / cost

    def compute_upgrade_efficiency(self, upgrade_id: str) -> float:
        """Efficiency of buying an upgrade.

        Multiplicative: production * (magnitude - 1) / cost
        Additive: bonus * (base_production / cycle_time) / cost
        """
        node = self.game.get_node(upgrade_id)
        if not isinstance(node, Upgrade):
            return 0.0

        ns = self.engine.state.get(upgrade_id)
        if ns.purchased:
            return 0.0

        cost = node.cost
        if cost <= 0:
            return float("inf")

        # Check if target is a TickspeedNode — affects ALL production
        if node.target != "_all":
            try:
                target_node = self.game.get_node(node.target)
                if isinstance(target_node, TickspeedNode):
                    rates = self.engine.compute_production_rates()
                    total = sum(rates.values())
                    if node.upgrade_type == "multiplicative":
                        return total * (node.magnitude - 1) / cost
                    return 0.0
            except KeyError:
                pass

        if node.upgrade_type == "multiplicative":
            # production * (magnitude - 1) / cost
            if node.target == "_all":
                rates = self.engine.compute_production_rates()
                current_prod = sum(rates.values())
            else:
                target_node = self.game.get_node(node.target)
                if isinstance(target_node, Generator):
                    tns = self.engine.state.get(node.target)
                    if tns.owned <= 0:
                        return 0.0
                    gen_mult = self.engine._compute_generator_multipliers().get(
                        node.target, 1.0
                    )
                    current_prod = (
                        target_node.base_production
                        * tns.owned
                        / target_node.cycle_time
                        * gen_mult
                    )
                else:
                    return 0.0
            return current_prod * (node.magnitude - 1) / cost

        if node.upgrade_type == "additive":
            # bonus * (base_production / cycle_time) / cost
            if node.target == "_all":
                # For _all additive, sum base_production / cycle_time across all generators
                total_base = 0.0
                for n in self.game.nodes:
                    if isinstance(n, Generator) and self.engine.state.get(n.id).owned > 0:
                        total_base += n.base_production / n.cycle_time
                return node.magnitude * total_base / cost
            else:
                target_node = self.game.get_node(node.target)
                if isinstance(target_node, Generator):
                    base_rate = target_node.base_production / target_node.cycle_time
                    return node.magnitude * base_rate / cost
                return 0.0

        if node.upgrade_type == "percentage":
            # Similar to multiplicative but magnitude is a percentage
            rates = self.engine.compute_production_rates()
            current_prod = sum(rates.values())
            return current_prod * (node.magnitude / 100.0) / cost

        return 0.0

    def find_best_purchase(self) -> tuple[str, float] | None:
        """Find the highest-efficiency purchase.

        Returns (node_id, efficiency) or None.
        """
        best_id: str | None = None
        best_eff = -1.0

        for node in self.game.nodes:
            if isinstance(node, Generator):
                if node.id in self._autobuyer_targets:
                    continue
                eff = self.compute_generator_efficiency(node.id)
                if eff > best_eff:
                    best_eff = eff
                    best_id = node.id

            elif isinstance(node, Upgrade):
                ns = self.engine.state.get(node.id)
                if ns.purchased:
                    continue
                eff = self.compute_upgrade_efficiency(node.id)
                if eff > best_eff:
                    best_eff = eff
                    best_id = node.id

        if best_id is None or best_eff <= 0:
            return None
        return (best_id, best_eff)

    def total_production_rate(self) -> float:
        """Current total production rate across all resources."""
        rates = self.engine.compute_production_rates()
        return sum(rates.values())

    def run(
        self,
        target_time: float | None = None,
        max_steps: int = 1000,
    ) -> list[PurchaseStep]:
        """Run greedy optimization until target_time or max_steps.

        Returns the purchase sequence.
        """
        steps: list[PurchaseStep] = []

        for _ in range(max_steps):
            # Find best purchase
            best = self.find_best_purchase()
            if best is None:
                break

            node_id, efficiency = best

            # Compute cost of this purchase
            node = self.game.get_node(node_id)
            ns = self.engine.state.get(node_id)
            if isinstance(node, Generator):
                cost_bf = bulk_purchase_cost(
                    BigFloat(node.cost_base),
                    BigFloat(node.cost_growth_rate),
                    ns.owned,
                    1,
                )
                cost = float(cost_bf)
            elif isinstance(node, Upgrade):
                cost = node.cost
            else:
                break

            # Get current balance
            currency_id = self.engine._get_primary_resource_id()
            if currency_id is None:
                break
            balance = self.engine.state.get(currency_id).current_value

            # If we can't afford it, accumulate resources until we can
            if balance < cost:
                rates = self.engine.compute_production_rates()
                currency_rate = rates.get(currency_id, 0.0)
                if currency_rate <= 0:
                    break  # Can never afford it
                time_needed = (cost - balance) / currency_rate
                advance_target = self.engine.current_time + time_needed

                if target_time is not None and advance_target > target_time:
                    # Can't afford before target_time — just accumulate to end
                    dt = target_time - self.engine.current_time
                    self.engine._accumulate(rates, dt)
                    self.engine._time = target_time
                    self.engine.state.elapsed_time = target_time
                    break

                # Accumulate without triggering auto-purchases
                dt = advance_target - self.engine.current_time
                self.engine._accumulate(rates, dt)
                self.engine._time = advance_target
                self.engine.state.elapsed_time = advance_target

            # Record cash before purchase
            cash_before = self.engine.state.get(currency_id).current_value

            # Execute purchase
            self.engine.purchase(node_id)

            cash_after = self.engine.state.get(currency_id).current_value

            step = PurchaseStep(
                time=self.engine.current_time,
                node_id=node_id,
                cost=cost,
                efficiency=efficiency,
                cash_before=cash_before,
                cash_after=cash_after,
            )
            steps.append(step)

            # Check if we've passed target_time
            if target_time is not None and self.engine.current_time >= target_time:
                break

        self.steps.extend(steps)
        return steps

    def get_candidates(self) -> list[dict]:
        """Get all purchasable candidates with their efficiency metrics.

        Returns list of dicts with keys: node_id, type, cost, efficiency,
        delta_production. Used by beam/MCTS/BnB optimizers.
        """
        candidates: list[dict] = []
        gen_multipliers = self.engine._compute_generator_multipliers()

        for node in self.game.nodes:
            if isinstance(node, Generator):
                if node.id in self._autobuyer_targets:
                    continue
                ns = self.engine.state.get(node.id)
                cost_bf = bulk_purchase_cost(
                    BigFloat(node.cost_base),
                    BigFloat(node.cost_growth_rate),
                    ns.owned,
                    1,
                )
                cost = float(cost_bf)
                if cost <= 0:
                    continue
                gen_mult = gen_multipliers.get(node.id, 1.0)
                delta_prod = node.base_production / node.cycle_time * gen_mult
                eff = delta_prod / cost
                candidates.append({
                    "node_id": node.id,
                    "type": "generator",
                    "cost": cost,
                    "efficiency": eff,
                    "delta_production": delta_prod,
                })

            elif isinstance(node, Upgrade):
                ns = self.engine.state.get(node.id)
                if ns.purchased:
                    continue
                cost = node.cost
                if cost <= 0:
                    cost = 0.0
                eff = self.compute_upgrade_efficiency(node.id)
                delta_prod = self.engine._estimate_upgrade_delta(node, gen_multipliers)
                candidates.append({
                    "node_id": node.id,
                    "type": "upgrade",
                    "cost": cost,
                    "efficiency": eff,
                    "delta_production": delta_prod,
                })

        return candidates

    def optimize(
        self,
        target_time: float,
        max_steps: int = 500,
    ) -> OptimizeResult:
        """Run greedy optimization and return an OptimizeResult.

        This wraps ``run()`` to produce the result format expected by
        beam/MCTS/BnB optimizers and the analysis module.
        """
        from idleframework.engine.events import PurchaseEvent

        steps = self.run(target_time=target_time, max_steps=max_steps)

        purchases = []
        timeline = []
        pay_resource = self.engine._get_primary_resource_id()

        for step in steps:
            purchases.append(PurchaseEvent(
                time=step.time,
                node_id=step.node_id,
                count=1,
                cost=step.cost,
            ))
            prod_rate = (
                self.engine.get_production_rate(pay_resource)
                if pay_resource
                else 0.0
            )
            timeline.append({
                "time": step.time,
                "production_rate": prod_rate,
            })

        final_prod = (
            self.engine.get_production_rate(pay_resource)
            if pay_resource
            else 0.0
        )
        final_bal = (
            self.engine.get_balance(pay_resource)
            if pay_resource
            else 0.0
        )
        return OptimizeResult(
            purchases=purchases,
            timeline=timeline,
            final_production=final_prod,
            final_balance=final_bal,
            final_time=self.engine.current_time,
        )
