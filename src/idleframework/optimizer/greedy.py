"""Greedy optimizer for idle game purchase sequencing.

At each step, evaluates all purchasable candidates (generators + upgrades)
and picks the one with highest efficiency = delta_production / cost.

Efficiency formulas:
- Generator: base_production / cycle_time / next_unit_cost
- Multiplicative upgrade: current_production * (magnitude - 1) / cost
- Additive upgrade: current_production * magnitude / cost
  (magnitude is the raw bonus, e.g., 0.05 for +5%)
"""
from __future__ import annotations

from dataclasses import dataclass, field

from idleframework.engine.segments import PiecewiseEngine
from idleframework.engine.solvers import bulk_cost, time_to_afford
from idleframework.engine.events import PurchaseEvent


@dataclass
class OptimizeResult:
    """Result of an optimization run."""

    purchases: list[PurchaseEvent] = field(default_factory=list)
    timeline: list[dict] = field(default_factory=list)
    final_production: float = 0.0
    final_balance: float = 0.0
    final_time: float = 0.0


class GreedyOptimizer:
    """Greedy purchase optimizer — picks highest efficiency at each step."""

    def __init__(self, engine: PiecewiseEngine):
        self._engine = engine

    def get_candidates(self) -> list[dict]:
        """Compute efficiency for all purchasable items.

        Returns list of dicts with keys: node_id, type, cost, efficiency, delta_production.
        """
        candidates = []
        pay_resource = self._engine._find_payment_resource()
        current_total_rate = self._engine.get_production_rate(pay_resource)

        # Generator candidates
        for gen_id, gen in self._engine._generators.items():
            owned = self._engine.get_owned(gen_id)
            cost = bulk_cost(gen.cost_base, gen.cost_growth_rate, owned, 1)
            if cost <= 0:
                continue

            # Delta production from one more unit
            target_resource = self._engine._production_edges.get(gen_id)
            if target_resource is None:
                continue

            multiplier = self._engine.get_generator_multiplier(gen_id)
            delta = gen.base_production / gen.cycle_time * multiplier
            efficiency = delta / cost

            candidates.append({
                "node_id": gen_id,
                "type": "generator",
                "cost": cost,
                "efficiency": efficiency,
                "delta_production": delta,
            })

        # Upgrade candidates
        for upg_id, upg in self._engine._upgrades.items():
            if self._engine.is_upgrade_owned(upg_id):
                continue
            cost = upg.cost
            if cost <= 0:
                # Free upgrade — infinite efficiency, always buy immediately
                candidates.append({
                    "node_id": upg_id,
                    "type": "upgrade",
                    "cost": 0.0,
                    "efficiency": float("inf"),
                    "delta_production": 0.0,
                })
                continue

            delta = self._compute_upgrade_delta(upg, pay_resource)
            efficiency = delta / cost if cost > 0 else float("inf")

            candidates.append({
                "node_id": upg_id,
                "type": "upgrade",
                "cost": cost,
                "efficiency": efficiency,
                "delta_production": delta,
            })

        return candidates

    def _compute_upgrade_delta(self, upg, pay_resource: str) -> float:
        """Compute production delta from purchasing an upgrade."""
        # Find which generators this upgrade affects
        affected_gen_ids = []
        if upg.target == "_all":
            affected_gen_ids = list(self._engine._generators.keys())
        else:
            if upg.target in self._engine._generators:
                affected_gen_ids = [upg.target]

        total_delta = 0.0
        for gen_id in affected_gen_ids:
            target_resource = self._engine._production_edges.get(gen_id)
            if target_resource != pay_resource:
                continue

            gen = self._engine._generators[gen_id]
            count = self._engine.get_owned(gen_id)
            if count == 0:
                continue

            current_mult = self._engine.get_generator_multiplier(gen_id)
            base_rate = count * gen.base_production / gen.cycle_time

            # Compute what the new multiplier would be after purchasing this upgrade
            # We need to simulate adding this upgrade's bonus to its stacking group
            group_name = upg.stacking_group
            rule = self._engine._game.stacking_groups.get(group_name, "multiplicative")

            if rule == "multiplicative":
                # New mult = current_mult * magnitude
                new_mult = current_mult * upg.magnitude
            elif rule == "additive":
                # Additive: group goes from (1 + existing_sum) to (1 + existing_sum + magnitude)
                # Delta in multiplier = magnitude * (product of other groups)
                # Simpler: delta_production = base_rate * magnitude * (other_groups_product)
                # Since current_mult = all_groups_product, and this group contributes (1 + sum),
                # adding magnitude increases this group by magnitude, so:
                # new_total = current_mult + base_rate_without_this_group * magnitude
                # Actually: new_mult = current_mult / current_group * (current_group + magnitude)
                # For simplicity, delta = base_rate * magnitude (approx for small bonuses)
                new_mult = current_mult + self._get_other_groups_product(gen_id, group_name) * upg.magnitude
            elif rule == "percentage":
                new_mult = current_mult + self._get_other_groups_product(gen_id, group_name) * upg.magnitude / 100.0
            else:
                new_mult = current_mult * upg.magnitude

            delta = base_rate * (new_mult - current_mult)
            total_delta += delta

        return total_delta

    def _get_other_groups_product(self, gen_id: str, exclude_group: str) -> float:
        """Product of all stacking group multipliers except the excluded one."""
        groups: dict[str, dict] = {}

        for upg_id, owned in self._engine._upgrades_owned.items():
            if not owned:
                continue
            upg = self._engine._upgrades[upg_id]
            if upg.target != gen_id and upg.target != "_all":
                continue
            if upg.stacking_group == exclude_group:
                continue

            group_name = upg.stacking_group
            if group_name not in groups:
                rule = self._engine._game.stacking_groups.get(group_name, "multiplicative")
                groups[group_name] = {"rule": rule, "bonuses": []}
            groups[group_name]["bonuses"].append(upg.magnitude)

        from idleframework.model.stacking import compute_final_multiplier
        return compute_final_multiplier(groups)

    def step(self) -> PurchaseEvent | None:
        """Execute one greedy step: pick best candidate and purchase it.

        If the best candidate isn't affordable yet, advance time until it is.
        Returns the purchase event, or None if nothing can ever be purchased.
        """
        candidates = self.get_candidates()
        if not candidates:
            return None

        # Sort by efficiency descending, then by cost ascending (prefer cheaper on ties)
        candidates.sort(key=lambda c: (-c["efficiency"], c["cost"]))

        pay_resource = self._engine._find_payment_resource()
        balance = self._engine.get_balance(pay_resource)
        rate = self._engine.get_production_rate(pay_resource)

        for candidate in candidates:
            cost = candidate["cost"]
            node_id = candidate["node_id"]

            if balance >= cost - 1e-10:
                # Can afford now — buy it
                return self._execute_purchase(candidate)

            # Need to wait — check if we can ever afford it
            if rate <= 0:
                continue

            return candidate  # Return best candidate (will be waited for in optimize())

        return None

    def _execute_purchase(self, candidate: dict) -> PurchaseEvent:
        """Execute a purchase and return the event."""
        node_id = candidate["node_id"]
        cost = candidate["cost"]

        if candidate["type"] == "upgrade":
            actual_cost = self._engine.purchase_upgrade(node_id)
        else:
            actual_cost = self._engine.purchase(node_id, 1)

        return PurchaseEvent(
            time=self._engine.time,
            node_id=node_id,
            count=1,
            cost=actual_cost,
        )

    def optimize(
        self,
        target_time: float,
        max_steps: int = 500,
    ) -> OptimizeResult:
        """Run greedy optimization to target_time.

        At each step:
        1. Compute efficiency for all candidates
        2. Pick the best one
        3. If not affordable, advance time until it is
        4. Purchase it
        5. Record timeline entry
        """
        result = OptimizeResult()
        pay_resource = self._engine._find_payment_resource()

        # Record initial state
        result.timeline.append({
            "time": self._engine.time,
            "production_rate": self._engine.get_production_rate(pay_resource),
        })

        step_count = 0
        while step_count < max_steps and self._engine.time < target_time:
            candidates = self.get_candidates()
            if not candidates:
                break

            # Sort by efficiency descending, cost ascending for ties
            candidates.sort(key=lambda c: (-c["efficiency"], c["cost"]))
            best = candidates[0]

            if best["efficiency"] <= 0:
                break

            cost = best["cost"]
            balance = self._engine.get_balance(pay_resource)
            rate = self._engine.get_production_rate(pay_resource)

            # If can't afford, advance time until we can
            if balance < cost - 1e-10:
                if rate <= 0:
                    break
                wait = time_to_afford(cost, rate, balance)
                purchase_time = self._engine.time + wait
                if purchase_time > target_time:
                    break
                self._engine.advance_to(purchase_time)

                # Floating-point drift: if still just short, nudge forward
                new_balance = self._engine.get_balance(pay_resource)
                if new_balance < cost - 1e-10:
                    nudge = min(purchase_time + 1e-6, target_time)
                    if nudge > self._engine.time:
                        self._engine.advance_to(nudge)

            # Verify affordability before purchase
            final_balance = self._engine.get_balance(pay_resource)
            if final_balance < cost - 1e-10:
                continue  # Skip this candidate, try next step

            # Execute purchase
            event = self._execute_purchase(best)
            result.purchases.append(event)
            step_count += 1

            # Record timeline
            result.timeline.append({
                "time": self._engine.time,
                "production_rate": self._engine.get_production_rate(pay_resource),
            })

        # Advance to target time
        if self._engine.time < target_time:
            self._engine.advance_to(target_time)

        result.final_production = self._engine.get_production_rate(pay_resource)
        result.final_balance = self._engine.get_balance(pay_resource)
        result.final_time = self._engine.time

        return result
