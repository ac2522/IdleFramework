"""Piecewise analytical engine.

The game timeline is divided into segments between discrete events (purchases,
prestiges, unlocks). Within each segment the system is fixed and solved
analytically. The engine computes "time until next affordable purchase"
algebraically, jumps to that event, applies state changes, and starts a new
segment.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from idleframework.bigfloat import BigFloat
from idleframework.engine.events import MAX_PURCHASES_PER_EPSILON
from idleframework.engine.solvers import (
    bulk_purchase_cost,
    efficiency_score,
    time_to_afford,
)
from idleframework.model.nodes import Generator, Upgrade
from idleframework.model.stacking import collect_stacking_bonuses, compute_final_multiplier
from idleframework.model.state import GameState

if TYPE_CHECKING:
    from idleframework.model.game import GameDefinition


@dataclass
class Segment:
    """A time interval with fixed production rates."""

    start_time: float
    end_time: float | None  # None if open-ended
    production_rates: dict[str, float]  # resource_id -> rate/sec
    multiplier: float  # from stacking groups
    events: list[str] = field(default_factory=list)  # what caused this segment


class PiecewiseEngine:
    """Piecewise analytical engine for idle game simulation.

    Divides the timeline into segments at purchase events and solves each
    segment analytically using closed-form solutions.
    """

    def __init__(self, game: "GameDefinition", state: GameState | None = None):
        self._game = game
        self._state = state if state is not None else GameState.from_game(game)
        self._segments: list[Segment] = []
        self._time: float = self._state.elapsed_time

    # -- Properties ----------------------------------------------------------

    @property
    def state(self) -> GameState:
        return self._state

    @property
    def current_time(self) -> float:
        return self._time

    @property
    def segments(self) -> list[Segment]:
        return list(self._segments)

    # -- Production rates ----------------------------------------------------

    def compute_production_rates(self) -> dict[str, float]:
        """Compute current per-second production rates for all resources.

        For each active generator with owned > 0, compute:
            rate = base_production * owned / cycle_time * multiplier

        where multiplier accounts for purchased upgrades targeting that
        generator (or _all) via stacking groups.
        """
        rates: dict[str, float] = {}

        # Build per-generator multiplier from upgrades
        gen_multipliers = self._compute_generator_multipliers()

        for node in self._game.nodes:
            if not isinstance(node, Generator):
                continue
            ns = self._state.get(node.id)
            if ns.owned <= 0 or not ns.active:
                continue

            gen_mult = gen_multipliers.get(node.id, 1.0)
            rate = node.base_production * ns.owned / node.cycle_time * gen_mult

            # Find which resource(s) this generator produces to
            for edge in self._game.get_edges_from(node.id):
                if edge.edge_type == "production_target":
                    rates[edge.target] = rates.get(edge.target, 0.0) + rate

        return rates

    def _compute_generator_multipliers(self) -> dict[str, float]:
        """Compute per-generator multipliers from purchased upgrades.

        Groups upgrades by their target generator, computes stacking within
        each stacking_group, then multiplies across groups.

        Returns dict mapping generator_id -> total multiplier.
        """
        # Collect per-generator, per-stacking-group bonuses
        # Structure: {gen_id: {stacking_group: {"rule": ..., "bonuses": [...]}}}
        gen_groups: dict[str, dict[str, dict]] = {}
        # Also track _all upgrades
        all_groups: dict[str, dict] = {}

        for node in self._game.nodes:
            if not isinstance(node, Upgrade):
                continue
            ns = self._state.get(node.id)
            if not ns.purchased:
                continue

            sg = node.stacking_group
            rule = self._game.stacking_groups.get(sg, "multiplicative")

            if node.target == "_all":
                if sg not in all_groups:
                    all_groups[sg] = {"rule": rule, "bonuses": []}
                all_groups[sg]["bonuses"].append(node.magnitude)
            else:
                if node.target not in gen_groups:
                    gen_groups[node.target] = {}
                if sg not in gen_groups[node.target]:
                    gen_groups[node.target][sg] = {"rule": rule, "bonuses": []}
                gen_groups[node.target][sg]["bonuses"].append(node.magnitude)

        # Compute final multiplier per generator
        result: dict[str, float] = {}

        # Get all generator IDs
        gen_ids = {n.id for n in self._game.nodes if isinstance(n, Generator)}

        for gid in gen_ids:
            # Merge generator-specific groups with _all groups
            merged: dict[str, dict] = {}

            # Add generator-specific bonuses
            if gid in gen_groups:
                for sg, data in gen_groups[gid].items():
                    merged[sg] = {"rule": data["rule"], "bonuses": list(data["bonuses"])}

            # Add _all bonuses
            for sg, data in all_groups.items():
                if sg not in merged:
                    merged[sg] = {"rule": data["rule"], "bonuses": list(data["bonuses"])}
                else:
                    merged[sg]["bonuses"].extend(data["bonuses"])

            if merged:
                result[gid] = compute_final_multiplier(merged)

        return result

    # -- Next purchase -------------------------------------------------------

    def find_next_purchase(self) -> tuple[str, float] | None:
        """Find the most efficient next purchase and when it's affordable.

        Evaluates all purchasable generators and upgrades. For each, computes
        cost and time-to-afford at current production rates. Returns the most
        efficient (best delta_production/cost) candidate.

        Returns (node_id, time_from_now) or None if nothing is purchasable.
        """
        rates = self.compute_production_rates()
        total_rate = sum(rates.values())

        if total_rate <= 0:
            return None

        candidates: list[tuple[str, float, float]] = []  # (node_id, time, efficiency)

        for node in self._game.nodes:
            if isinstance(node, Generator):
                ns = self._state.get(node.id)
                cost_bf = bulk_purchase_cost(
                    BigFloat(node.cost_base),
                    BigFloat(node.cost_growth_rate),
                    ns.owned,
                    1,
                )
                cost = float(cost_bf)
                current_balance = self._get_currency_for(node.id)

                if current_balance >= cost:
                    time_needed = 0.0
                else:
                    remaining = cost - current_balance
                    time_needed = remaining / total_rate

                # Efficiency: what does buying 1 more generator add?
                gen_mult = self._compute_generator_multipliers().get(node.id, 1.0)
                delta_prod = node.base_production / node.cycle_time * gen_mult
                eff = delta_prod / cost if cost > 0 else float("inf")

                candidates.append((node.id, time_needed, eff))

            elif isinstance(node, Upgrade):
                ns = self._state.get(node.id)
                if ns.purchased:
                    continue  # Already bought

                cost = node.cost
                current_balance = self._get_currency_for(node.id)

                if current_balance >= cost:
                    time_needed = 0.0
                else:
                    remaining = cost - current_balance
                    time_needed = remaining / total_rate

                # Efficiency: estimate production gain from the upgrade
                delta_prod = self._estimate_upgrade_delta(node)
                eff = delta_prod / cost if cost > 0 else float("inf")

                candidates.append((node.id, time_needed, eff))

        if not candidates:
            return None

        # Among candidates affordable now (time_needed <= 0), pick best efficiency
        affordable_now = [(nid, t, e) for nid, t, e in candidates if t <= 0]
        if affordable_now:
            best = max(affordable_now, key=lambda x: x[2])
            return (best[0], 0.0)

        # Otherwise pick the one with best efficiency among all
        # Use efficiency as primary sort, but also consider time
        best = max(candidates, key=lambda x: x[2])
        return (best[0], best[1])

    def _get_currency_for(self, node_id: str) -> float:
        """Get the current balance of the currency used to buy a node.

        For now, assumes all purchases use the first resource (typically 'cash').
        """
        # Find the first resource node
        from idleframework.model.nodes import Resource

        for node in self._game.nodes:
            if isinstance(node, Resource):
                return self._state.get(node.id).current_value
        return 0.0

    def _get_currency_resource_id(self) -> str | None:
        """Get the ID of the primary currency resource."""
        from idleframework.model.nodes import Resource

        for node in self._game.nodes:
            if isinstance(node, Resource):
                return node.id
        return None

    def _estimate_upgrade_delta(self, upgrade: Upgrade) -> float:
        """Estimate production gain from purchasing an upgrade."""
        rates = self.compute_production_rates()

        if upgrade.target == "_all":
            # Multiplies all production
            current_total = sum(rates.values())
            return current_total * (upgrade.magnitude - 1)
        else:
            # Multiplies specific generator's contribution
            # Find that generator's contribution to total rate
            node = self._game.get_node(upgrade.target)
            if isinstance(node, Generator):
                ns = self._state.get(node.id)
                if ns.owned <= 0:
                    return 0.0
                gen_mult = self._compute_generator_multipliers().get(node.id, 1.0)
                gen_rate = node.base_production * ns.owned / node.cycle_time * gen_mult
                return gen_rate * (upgrade.magnitude - 1)
        return 0.0

    # -- Purchases -----------------------------------------------------------

    def purchase(self, node_id: str) -> None:
        """Execute a purchase: deduct cost, update owned/purchased."""
        node = self._game.get_node(node_id)
        ns = self._state.get(node_id)
        currency_id = self._get_currency_resource_id()

        if isinstance(node, Generator):
            cost_bf = bulk_purchase_cost(
                BigFloat(node.cost_base),
                BigFloat(node.cost_growth_rate),
                ns.owned,
                1,
            )
            cost = float(cost_bf)
            if currency_id:
                self._state.get(currency_id).current_value -= cost
            ns.owned += 1

        elif isinstance(node, Upgrade):
            cost = node.cost
            if currency_id:
                self._state.get(currency_id).current_value -= cost
            ns.purchased = True

    def apply_free_purchases(self) -> list[str]:
        """Auto-purchase items where cost/balance < free_purchase_threshold.

        Returns list of purchased node IDs.
        """
        threshold = self._game.free_purchase_threshold
        purchased: list[str] = []
        currency_id = self._get_currency_resource_id()
        if currency_id is None:
            return purchased

        changed = True
        while changed:
            changed = False
            balance = self._state.get(currency_id).current_value
            if balance <= 0:
                break

            for node in self._game.nodes:
                if isinstance(node, Generator):
                    ns = self._state.get(node.id)
                    cost_bf = bulk_purchase_cost(
                        BigFloat(node.cost_base),
                        BigFloat(node.cost_growth_rate),
                        ns.owned,
                        1,
                    )
                    cost = float(cost_bf)
                    if cost > 0 and balance >= cost and cost / balance < threshold:
                        self._state.get(currency_id).current_value -= cost
                        ns.owned += 1
                        purchased.append(node.id)
                        changed = True
                        balance = self._state.get(currency_id).current_value

                elif isinstance(node, Upgrade):
                    ns = self._state.get(node.id)
                    if ns.purchased:
                        continue
                    cost = node.cost
                    if cost > 0 and balance >= cost and cost / balance < threshold:
                        self._state.get(currency_id).current_value -= cost
                        ns.purchased = True
                        purchased.append(node.id)
                        changed = True
                        balance = self._state.get(currency_id).current_value
                    elif cost == 0:
                        # Free upgrades
                        ns.purchased = True
                        purchased.append(node.id)
                        changed = True

        return purchased

    # -- Main entry point ----------------------------------------------------

    def advance_to(self, target_time: float) -> list[Segment]:
        """Advance simulation to target_time, creating segments at events.

        For each segment:
        1. Compute production rates
        2. Find next affordable purchase (time_to_afford)
        3. If purchase time < target_time, advance to it, execute purchase
        4. Repeat until target_time reached

        Returns list of segments created during this call.
        """
        new_segments: list[Segment] = []
        epsilon = self._game.event_epsilon

        while self._time < target_time - 1e-12:
            # Apply free purchases at current time
            self.apply_free_purchases()

            rates = self.compute_production_rates()
            total_rate = sum(rates.values())

            # Find next purchase
            next_purchase = self.find_next_purchase()

            if next_purchase is not None:
                node_id, time_needed = next_purchase
                purchase_time = self._time + time_needed
            else:
                purchase_time = None

            if purchase_time is not None and purchase_time < target_time - 1e-12:
                # Advance to purchase time
                dt = purchase_time - self._time
                if dt < 0:
                    dt = 0.0

                seg = self._create_segment(rates, dt, [f"purchase:{node_id}"])
                new_segments.append(seg)

                # Accumulate resources
                self._accumulate(rates, dt)
                self._time = purchase_time

                # Handle chattering: count purchases in this epsilon window
                purchases_in_window = 0
                window_start = self._time

                while True:
                    # Apply free purchases
                    free = self.apply_free_purchases()
                    purchases_in_window += len(free)

                    # Execute the purchase
                    self.purchase(node_id)
                    purchases_in_window += 1

                    # Check chattering
                    if purchases_in_window >= MAX_PURCHASES_PER_EPSILON:
                        # Batch-evaluate: buy all affordable at once
                        self._batch_purchase_all_affordable()
                        break

                    # Check for near-simultaneous purchases
                    rates = self.compute_production_rates()
                    next_purchase = self.find_next_purchase()
                    if next_purchase is None:
                        break

                    node_id, time_needed = next_purchase
                    if time_needed > epsilon:
                        break
                    # Another purchase within epsilon — continue loop
                    if self._time + time_needed > window_start + epsilon:
                        break

            else:
                # No purchase before target_time — advance to target
                dt = target_time - self._time
                seg = self._create_segment(rates, dt, [])
                new_segments.append(seg)
                self._accumulate(rates, dt)
                self._time = target_time

        self._segments.extend(new_segments)
        self._state.elapsed_time = self._time
        return new_segments

    def _create_segment(
        self, rates: dict[str, float], duration: float, events: list[str]
    ) -> Segment:
        """Create a Segment record."""
        # Compute overall multiplier from stacking groups
        bonuses = collect_stacking_bonuses(self._game, self._state)
        mult = compute_final_multiplier(bonuses)

        return Segment(
            start_time=self._time,
            end_time=self._time + duration if duration is not None else None,
            production_rates=dict(rates),
            multiplier=mult,
            events=events,
        )

    def _accumulate(self, rates: dict[str, float], dt: float) -> None:
        """Add production to resource balances for a time interval."""
        for resource_id, rate in rates.items():
            ns = self._state.get(resource_id)
            ns.current_value += rate * dt
            ns.total_production += rate * dt

        # Track lifetime earnings
        for resource_id, rate in rates.items():
            earned = rate * dt
            if resource_id in self._state.lifetime_earnings:
                self._state.lifetime_earnings[resource_id] += earned
            else:
                self._state.lifetime_earnings[resource_id] = earned

    def _batch_purchase_all_affordable(self) -> None:
        """Batch-purchase all currently affordable items.

        Used when chattering is detected to break out of the purchase loop.
        """
        currency_id = self._get_currency_resource_id()
        if currency_id is None:
            return

        changed = True
        while changed:
            changed = False
            balance = self._state.get(currency_id).current_value
            if balance <= 0:
                break

            # Find all affordable, sorted by efficiency
            affordable: list[tuple[str, float, float]] = []

            for node in self._game.nodes:
                if isinstance(node, Generator):
                    ns = self._state.get(node.id)
                    cost_bf = bulk_purchase_cost(
                        BigFloat(node.cost_base),
                        BigFloat(node.cost_growth_rate),
                        ns.owned,
                        1,
                    )
                    cost = float(cost_bf)
                    if cost <= balance:
                        gen_mult = self._compute_generator_multipliers().get(node.id, 1.0)
                        delta = node.base_production / node.cycle_time * gen_mult
                        eff = delta / cost if cost > 0 else float("inf")
                        affordable.append((node.id, cost, eff))

                elif isinstance(node, Upgrade):
                    ns = self._state.get(node.id)
                    if ns.purchased:
                        continue
                    if node.cost <= balance:
                        delta = self._estimate_upgrade_delta(node)
                        eff = delta / node.cost if node.cost > 0 else float("inf")
                        affordable.append((node.id, node.cost, eff))

            if not affordable:
                break

            # Buy best efficiency first
            affordable.sort(key=lambda x: x[2], reverse=True)
            best_id, _, _ = affordable[0]
            self.purchase(best_id)
            changed = True
