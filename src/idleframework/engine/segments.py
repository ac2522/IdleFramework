"""Piecewise analytical engine.

The game timeline is divided into segments between discrete events (purchases,
prestiges, unlocks). Within each segment the system is fixed and solved
analytically. The engine computes "time until next affordable purchase"
algebraically, jumps to that event, applies state changes, and starts a new
segment.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from idleframework.bigfloat import BigFloat
from idleframework.engine.events import MAX_PURCHASES_PER_EPSILON
from idleframework.engine.solvers import (
    bulk_purchase_cost,
)
from idleframework.engine.state_edges import evaluate_state_edges, apply_property_modifications
from idleframework.model.nodes import AutobuyerNode, BuffNode, DrainNode, Generator, PrestigeLayer, Register, Resource, SynergyNode, TickspeedNode, Upgrade
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
    drain_rates: dict[str, float] = field(default_factory=dict)  # resource_id -> drain/sec
    net_rates: dict[str, float] = field(default_factory=dict)  # resource_id -> net/sec
    tickspeed: float = 1.0  # current tickspeed multiplier


@dataclass
class BuffMultipliers:
    """Resolved buff multipliers for production calculation."""
    global_multiplier: float = 1.0
    per_generator: dict[str, float] = field(default_factory=dict)


class PiecewiseEngine:
    """Piecewise analytical engine for idle game simulation.

    Divides the timeline into segments at purchase events and solves each
    segment analytically using closed-form solutions.
    """

    def __init__(
        self,
        game: GameDefinition,
        state: GameState | None = None,
        validate: bool = False,
    ):
        if validate:
            from idleframework.graph.validation import validate_graph
            errors = validate_graph(game)
            if errors:
                raise ValueError(f"Graph validation errors: {errors}")

        self._game = game
        self._state = state if state is not None else GameState.from_game(game)
        self._segments: list[Segment] = []
        self._time: float = self._state.elapsed_time

        # Build lookup tables for convenience
        self._generators: dict[str, Generator] = {}
        self._upgrades: dict[str, Upgrade] = {}
        for node in self._game.nodes:
            if isinstance(node, Generator):
                self._generators[node.id] = node
            elif isinstance(node, Upgrade):
                self._upgrades[node.id] = node

        self._tickspeed_node: TickspeedNode | None = None
        for node in self._game.nodes:
            if isinstance(node, TickspeedNode):
                self._tickspeed_node = node
                break

        self._drains: dict[str, DrainNode] = {}
        for node in self._game.nodes:
            if isinstance(node, DrainNode):
                self._drains[node.id] = node

        self._autobuyers: dict[str, AutobuyerNode] = {}
        self._autobuyer_targets: set[str] = set()
        for node in self._game.nodes:
            if isinstance(node, AutobuyerNode):
                self._autobuyers[node.id] = node
                self._autobuyer_targets.add(node.target)

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

    @property
    def time(self) -> float:
        return self._time

    # -- Convenience accessors -----------------------------------------------

    def set_balance(self, resource_id: str, value: float) -> None:
        """Set the current balance of a resource."""
        self._state.get(resource_id).current_value = value

    def set_owned(self, node_id: str, count: int) -> None:
        """Set how many of a node are owned."""
        self._state.get(node_id).owned = count

    def get_balance(self, resource_id: str) -> float:
        """Get the current balance of a resource."""
        return self._state.get(resource_id).current_value

    def get_owned(self, node_id: str) -> int:
        """Get how many of a node are owned."""
        return self._state.get(node_id).owned

    def get_production_rate(self, resource_id: str) -> float:
        """Get current production rate for a single resource."""
        return self.compute_production_rates().get(resource_id, 0.0)

    def is_upgrade_owned(self, upgrade_id: str) -> bool:
        """Check if an upgrade has been purchased."""
        return self._state.get(upgrade_id).purchased

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
        tickspeed = self.compute_tickspeed()
        buffs = self.evaluate_buffs()
        synergies = self.compute_synergy_multipliers()

        # Evaluate state edges for property modifications
        modified = evaluate_state_edges(self._game, self._state)

        for node in self._game.nodes:
            if not isinstance(node, Generator):
                continue
            ns = self._state.get(node.id)
            if ns.owned <= 0 or not ns.active:
                continue

            base_prod = node.base_production
            # Apply state edge modifications to base_production
            if node.id in modified and "base_production" in modified[node.id]:
                base_prod = apply_property_modifications(
                    base_prod, modified[node.id]["base_production"]
                )

            gen_mult = gen_multipliers.get(node.id, 1.0)
            # Apply _general_multiplier from backward-compat state modifiers
            if node.id in modified and "_general_multiplier" in modified[node.id]:
                gen_mult = apply_property_modifications(
                    gen_mult, modified[node.id]["_general_multiplier"]
                )
            buff_mult = buffs.global_multiplier * buffs.per_generator.get(node.id, 1.0)
            syn_mult = synergies.get(node.id, 1.0)
            rate = base_prod * ns.owned / node.cycle_time * gen_mult * tickspeed * buff_mult * syn_mult

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

    def compute_tickspeed(self) -> float:
        """Resolve the current tickspeed multiplier."""
        if self._tickspeed_node is None:
            return 1.0
        base = self._tickspeed_node.base_tickspeed

        # Collect upgrades targeting the tickspeed node
        ts_id = self._tickspeed_node.id
        ts_groups: dict[str, dict] = {}
        for node in self._game.nodes:
            if not isinstance(node, Upgrade):
                continue
            ns = self._state.get(node.id)
            if not ns.purchased:
                continue
            if node.target != ts_id:
                continue
            sg = node.stacking_group
            rule = self._game.stacking_groups.get(sg, "multiplicative")
            if sg not in ts_groups:
                ts_groups[sg] = {"rule": rule, "bonuses": []}
            ts_groups[sg]["bonuses"].append(node.magnitude)

        mult = compute_final_multiplier(ts_groups) if ts_groups else 1.0
        return base * mult

    def evaluate_buffs(self) -> BuffMultipliers:
        """Compute expected-value buff multipliers.

        Timed: EV = 1 + (mult-1) * (duration/(duration+cooldown))
        Zero cooldown: EV = multiplier (always active)
        Proc: EV = 1 + proc_chance * (mult-1)
        """
        result = BuffMultipliers()
        per_gen: dict[str, float] = defaultdict(lambda: 1.0)

        for node in self._game.nodes:
            if not isinstance(node, BuffNode):
                continue
            ns = self._state.get(node.id)
            if not ns.active:
                continue

            if node.buff_type == "timed":
                if node.cooldown == 0.0:
                    ev = node.multiplier
                else:
                    d = node.duration or 0.0
                    ev = 1.0 + (node.multiplier - 1.0) * (d / (d + node.cooldown))
            elif node.buff_type == "proc":
                pc = node.proc_chance or 0.0
                ev = 1.0 + pc * (node.multiplier - 1.0)
            else:
                ev = 1.0

            if node.target is None:
                result.global_multiplier *= ev
            else:
                per_gen[node.target] *= ev

        result.per_generator = dict(per_gen)
        return result

    def compute_synergy_multipliers(self) -> dict[str, float]:
        """Compute per-generator multipliers from SynergyNodes."""
        from idleframework.dsl.compiler import compile_formula, evaluate_formula
        from idleframework.engine.variables import build_state_variables

        synergies: dict[str, float] = {}
        variables = build_state_variables(self._game, self._state)

        for node in self._game.nodes:
            if not isinstance(node, SynergyNode):
                continue
            ns = self._state.get(node.id)
            if not ns.active:
                continue
            compiled = compile_formula(node.formula_expr)
            bonus = float(evaluate_formula(compiled, variables))
            # Apply as additive bonus: target_mult = 1 + bonus
            if node.target in synergies:
                synergies[node.target] += bonus
            else:
                synergies[node.target] = bonus

        # Convert to multipliers: 1 + total_bonus
        return {k: 1.0 + v for k, v in synergies.items()}

    def compute_drain_rates(self) -> dict[str, float]:
        """Compute per-resource drain rates from active DrainNodes."""
        from idleframework.dsl.compiler import compile_formula, evaluate_formula
        from idleframework.engine.variables import build_state_variables

        drains: dict[str, float] = {}
        for drain in self._drains.values():
            ns = self._state.get(drain.id)
            if not ns.active:
                continue
            # Evaluate condition if present
            if drain.condition is not None:
                variables = build_state_variables(self._game, self._state)
                compiled = compile_formula(drain.condition)
                result = float(evaluate_formula(compiled, variables))
                if result <= 0:
                    continue
            # Find target resource via consumption edge
            for edge in self._game.get_edges_from(drain.id):
                if edge.edge_type == "consumption":
                    drains[edge.target] = drains.get(edge.target, 0.0) + drain.rate
        return drains

    def compute_gross_rates(self) -> dict[str, float]:
        """Alias for compute_production_rates (gross, before drains)."""
        return self.compute_production_rates()

    def _compute_net_rates(self) -> tuple[dict[str, float], dict[str, float]]:
        """Compute gross and net rates. Returns (gross_rates, net_rates)."""
        gross = self.compute_production_rates()
        drains = self.compute_drain_rates()
        net = {}
        for res_id in set(list(gross.keys()) + list(drains.keys())):
            net[res_id] = gross.get(res_id, 0.0) - drains.get(res_id, 0.0)
        return gross, net

    def _find_next_zero_crossing(self, net_rates: dict[str, float]) -> tuple[str, float] | None:
        """Find earliest resource depletion from negative net rate."""
        best: tuple[str, float] | None = None
        for res_id, rate in net_rates.items():
            if rate >= 0:
                continue
            balance = self._state.get(res_id).current_value
            if balance <= 0:
                continue
            time_to_zero = balance / abs(rate)
            if best is None or time_to_zero < best[1]:
                best = (res_id, time_to_zero)
        return best

    # -- Autobuyer support ---------------------------------------------------

    def _next_autobuyer_time(self) -> tuple[str, float] | None:
        """Find the earliest autobuyer fire time."""
        best: tuple[str, float] | None = None
        for ab_id, ab in self._autobuyers.items():
            ns = self._state.get(ab_id)
            if not ns.active or not ab.enabled:
                continue
            next_fire = ns.last_fired + ab.interval
            if next_fire <= self._time:
                next_fire = self._time  # Fire immediately
            if best is None or next_fire < best[1]:
                best = (ab_id, next_fire)
        return best

    def _execute_autobuyer(self, autobuyer_id: str) -> None:
        """Execute an autobuyer fire event."""
        ab = self._autobuyers[autobuyer_id]
        ns = self._state.get(autobuyer_id)

        # Evaluate condition if set
        if ab.condition is not None:
            from idleframework.dsl.compiler import compile_formula, evaluate_formula
            from idleframework.engine.variables import build_state_variables
            variables = build_state_variables(self._game, self._state)
            compiled = compile_formula(ab.condition)
            if not float(evaluate_formula(compiled, variables)):
                ns.last_fired = self._time
                return

        # Resolve bulk amount
        amount = 1
        if ab.bulk_amount == "10":
            amount = 10
        elif ab.bulk_amount == "max":
            amount = self._compute_max_affordable(ab.target)

        if amount > 0:
            try:
                self.purchase(ab.target, amount)
            except ValueError:
                pass  # Can't afford — skip

        ns.last_fired = self._time

    def _compute_max_affordable(self, node_id: str) -> int:
        """Compute maximum affordable count for a node using closed-form formula."""
        from idleframework.engine.solvers import max_affordable

        node = self._game.get_node(node_id)
        if not isinstance(node, Generator):
            return 1  # Upgrades are 0 or 1

        currency_id = self._get_currency_resource_id_for(node_id)
        if not currency_id:
            return 0
        balance = self._state.get(currency_id).current_value
        ns = self._state.get(node_id)

        return max_affordable(
            BigFloat(balance),
            BigFloat(node.cost_base),
            BigFloat(node.cost_growth_rate),
            ns.owned,
        )

    # -- Next purchase -------------------------------------------------------

    def find_next_purchase(self) -> tuple[str, float] | None:
        """Find the most efficient next purchase and when it's affordable.

        Evaluates all purchasable generators and upgrades. For each, computes
        cost and time-to-afford at the production rate of the specific currency
        required. Returns the most efficient (best delta_production/cost).

        Returns (node_id, time_from_now) or None if nothing is purchasable.
        """
        _, net_rates = self._compute_net_rates()
        rates = net_rates

        if not rates or all(r <= 0 for r in rates.values()):
            return None

        # Compute generator multipliers once to avoid repeated recomputation
        gen_multipliers = self._compute_generator_multipliers()

        candidates: list[tuple[str, float, float]] = []  # (node_id, time, efficiency)

        for node in self._game.nodes:
            if isinstance(node, Generator):
                if node.id in self._autobuyer_targets:
                    continue  # Skip autobuyer-managed nodes
                ns = self._state.get(node.id)
                cost_bf = bulk_purchase_cost(
                    BigFloat(node.cost_base),
                    BigFloat(node.cost_growth_rate),
                    ns.owned,
                    1,
                )
                cost = float(cost_bf)
                current_balance = self._get_currency_for(node.id)

                # Use the production rate of the specific currency this costs
                currency_id = self._get_currency_resource_id_for(node.id)
                currency_rate = rates.get(currency_id, 0.0) if currency_id else 0.0

                if current_balance >= cost:
                    time_needed = 0.0
                elif currency_rate <= 0:
                    continue  # Can never afford this
                else:
                    remaining = cost - current_balance
                    time_needed = remaining / currency_rate

                # Efficiency: what does buying 1 more generator add?
                gen_mult = gen_multipliers.get(node.id, 1.0)
                delta_prod = node.base_production / node.cycle_time * gen_mult
                eff = delta_prod / cost if cost > 0 else float("inf")

                candidates.append((node.id, time_needed, eff))

            elif isinstance(node, Upgrade):
                ns = self._state.get(node.id)
                if ns.purchased:
                    continue  # Already bought

                cost = node.cost
                current_balance = self._get_currency_for(node.id)

                # Use the production rate of the specific currency
                currency_id = self._get_currency_resource_id_for(node.id)
                currency_rate = rates.get(currency_id, 0.0) if currency_id else 0.0

                if current_balance >= cost:
                    time_needed = 0.0
                elif currency_rate <= 0:
                    continue  # Can never afford this
                else:
                    remaining = cost - current_balance
                    time_needed = remaining / currency_rate

                # Efficiency: estimate production gain from the upgrade
                delta_prod = self._estimate_upgrade_delta(node, gen_multipliers)
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
        best = max(candidates, key=lambda x: x[2])
        return (best[0], best[1])

    def _get_currency_for(self, node_id: str) -> float:
        """Get the current balance of the currency used to buy a node.

        Looks up the resource that the node's generator produces to (via
        production_target edges). For upgrades, uses the target generator's
        currency. Falls back to the first resource if no edge found.
        """
        currency_id = self._get_currency_resource_id_for(node_id)
        if currency_id:
            return self._state.get(currency_id).current_value
        return 0.0

    def _get_currency_resource_id_for(self, node_id: str) -> str | None:
        """Get the resource ID used to purchase a given node.

        For generators: follows production_target edges from the generator to
        find which resource it produces (and therefore costs).
        For upgrades: looks up the target generator's currency, or falls back
        to the first resource for _all upgrades.
        """
        node = self._game.get_node(node_id)

        if isinstance(node, Generator):
            # Generator's currency is the resource it produces to
            for edge in self._game.get_edges_from(node_id):
                if edge.edge_type == "production_target":
                    return edge.target
            return self._get_primary_resource_id()

        if isinstance(node, Upgrade):
            if node.target == "_all":
                return self._get_primary_resource_id()
            # Use the same currency as the target generator
            return self._get_currency_resource_id_for(node.target)

        return self._get_primary_resource_id()

    def _get_primary_resource_id(self) -> str | None:
        """Get the ID of the first resource node (fallback currency)."""
        for node in self._game.nodes:
            if isinstance(node, Resource):
                return node.id
        return None

    def _estimate_upgrade_delta(
        self,
        upgrade: Upgrade,
        gen_multipliers: dict[str, float] | None = None,
    ) -> float:
        """Estimate production gain from purchasing an upgrade.

        Args:
            upgrade: The upgrade to evaluate.
            gen_multipliers: Pre-computed generator multipliers (optional).
        """
        if gen_multipliers is None:
            gen_multipliers = self._compute_generator_multipliers()
        rates = self.compute_production_rates()

        upgrade_type = getattr(upgrade, "upgrade_type", "multiplicative")

        if upgrade.target == "_all":
            current_total = sum(rates.values())
            if upgrade_type == "multiplicative":
                return current_total * (upgrade.magnitude - 1)
            elif upgrade_type == "additive":
                return upgrade.magnitude
            elif upgrade_type == "percentage":
                return current_total * (upgrade.magnitude / 100)
            return current_total * (upgrade.magnitude - 1)
        else:
            node = self._game.get_node(upgrade.target)
            if isinstance(node, Generator):
                ns = self._state.get(node.id)
                if ns.owned <= 0:
                    return 0.0
                gen_mult = gen_multipliers.get(node.id, 1.0)
                gen_rate = node.base_production * ns.owned / node.cycle_time * gen_mult
                if upgrade_type == "multiplicative":
                    return gen_rate * (upgrade.magnitude - 1)
                elif upgrade_type == "additive":
                    return upgrade.magnitude * (ns.owned / node.cycle_time)
                elif upgrade_type == "percentage":
                    return gen_rate * (upgrade.magnitude / 100)
                return gen_rate * (upgrade.magnitude - 1)
        return 0.0

    # -- Purchases -----------------------------------------------------------

    def purchase(self, node_id: str, count: int = 1) -> float:
        """Execute a purchase: deduct cost, update owned/purchased.

        For generators, buys ``count`` units. For upgrades, count is ignored.
        Returns the total cost paid.
        Raises ValueError if the currency balance is insufficient.
        """
        node = self._game.get_node(node_id)
        ns = self._state.get(node_id)
        currency_id = self._get_currency_resource_id_for(node_id)
        total_cost = 0.0

        if isinstance(node, Generator):
            cost_bf = bulk_purchase_cost(
                BigFloat(node.cost_base),
                BigFloat(node.cost_growth_rate),
                ns.owned,
                count,
            )
            cost = float(cost_bf)
            if currency_id:
                balance = self._state.get(currency_id).current_value
                tol = max(1e-4, abs(cost) * 1e-9)
                if balance < cost - tol:
                    raise ValueError(
                        f"Insufficient balance to purchase {node_id!r}: "
                        f"need {cost:.2f}, have {balance:.2f}"
                    )
                # Clamp: if within tolerance, treat as exact
                if balance < cost:
                    self._state.get(currency_id).current_value = 0.0
                else:
                    self._state.get(currency_id).current_value -= cost
            ns.owned += count
            total_cost = cost

        elif isinstance(node, Upgrade):
            if ns.purchased:
                raise ValueError(f"Already purchased upgrade {node_id!r}")
            cost = node.cost
            if currency_id and cost > 0:
                balance = self._state.get(currency_id).current_value
                tol = max(1e-4, abs(cost) * 1e-9)
                if balance < cost - tol:
                    raise ValueError(
                        f"Cannot afford upgrade {node_id!r}: "
                        f"need {cost:.2f}, have {balance:.2f}"
                    )
                if balance < cost:
                    self._state.get(currency_id).current_value = 0.0
                else:
                    self._state.get(currency_id).current_value -= cost
            ns.purchased = True
            total_cost = cost

        return total_cost

    def purchase_upgrade(self, upgrade_id: str) -> float:
        """Purchase an upgrade by ID. Returns cost paid."""
        return self.purchase(upgrade_id)

    def evaluate_prestige(self, prestige_id: str, **kwargs: float) -> float:
        """Evaluate a prestige layer's formula with given variables."""
        from idleframework.dsl.compiler import compile_formula, evaluate_formula

        node = self._game.get_node(prestige_id)
        if not isinstance(node, PrestigeLayer):
            raise ValueError(f"{prestige_id!r} is not a PrestigeLayer")
        compiled = compile_formula(node.formula_expr)
        return float(evaluate_formula(compiled, kwargs))

    def execute_prestige(self, prestige_id: str) -> float:
        """Execute a prestige reset: compute gain, deposit currency, reset scopes."""
        from idleframework.dsl.compiler import compile_formula, evaluate_formula
        from idleframework.engine.variables import build_state_variables

        node = self._game.get_node(prestige_id)
        if not isinstance(node, PrestigeLayer):
            raise ValueError(f"{prestige_id!r} is not a PrestigeLayer")

        variables = build_state_variables(self._game, self._state)
        compiled = compile_formula(node.formula_expr)
        gain = float(evaluate_formula(compiled, variables))

        # Deposit into currency resource
        if node.currency_id:
            self._state.get(node.currency_id).current_value += gain

        # Collect persistence from the current (highest) layer
        all_persist = set(node.persistence_scope)

        # Reset all lower layers, but respect higher layer persistence
        for other in self._game.nodes:
            if isinstance(other, PrestigeLayer) and other.layer_index < node.layer_index:
                # Merge: lower layer persistence + higher layer persistence
                merged_persist = set(other.persistence_scope) | all_persist
                self._execute_reset(other.reset_scope, list(merged_persist))
                self._state.layer_run_times[other.id] = 0.0

        # Reset this layer's scope
        self._execute_reset(node.reset_scope, node.persistence_scope)
        self._state.layer_run_times[prestige_id] = 0.0

        return gain

    def _execute_reset(self, reset_scope: list[str], persistence_scope: list[str]) -> None:
        """Reset nodes in reset_scope except those in persistence_scope."""
        persist = set(persistence_scope)
        for node_id in reset_scope:
            if node_id in persist:
                continue
            ns = self._state.get(node_id)
            node = self._game.get_node(node_id)
            if isinstance(node, Resource):
                ns.current_value = node.initial_value
            elif isinstance(node, Generator):
                ns.owned = 0
                ns.total_production = 0.0
            elif isinstance(node, Upgrade):
                ns.purchased = False
            ns.last_fired = 0.0

    def evaluate_register(self, register_id: str, variables: dict[str, float]) -> float:
        """Evaluate a register node's formula with given variables."""
        from idleframework.dsl.compiler import compile_formula, evaluate_formula

        node = self._game.get_node(register_id)
        if not isinstance(node, Register):
            raise ValueError(f"{register_id!r} is not a Register")
        compiled = compile_formula(node.formula_expr)
        return float(evaluate_formula(compiled, variables))

    def auto_advance(self, target_time: float) -> list[str]:
        """Advance to target_time with auto-purchasing. Returns list of purchased node IDs."""
        purchased: list[str] = []
        segs = self.advance_to(target_time)
        for seg in segs:
            for event in seg.events:
                if event.startswith("purchase:"):
                    purchased.append(event.split(":", 1)[1])
        return purchased

    def apply_free_purchases(self) -> list[str]:
        """Auto-purchase items where cost/balance < free_purchase_threshold.

        Returns list of purchased node IDs.
        """
        threshold = self._game.free_purchase_threshold
        purchased: list[str] = []

        changed = True
        while changed:
            changed = False

            for node in self._game.nodes:
                currency_id = self._get_currency_resource_id_for(node.id)
                if currency_id is None:
                    continue
                balance = self._state.get(currency_id).current_value
                if balance <= 0 and not (isinstance(node, Upgrade) and node.cost == 0):
                    continue

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

            gross_rates, net_rates = self._compute_net_rates()
            rates = net_rates  # Use net rates for accumulation

            # Find next events
            next_purchase = self.find_next_purchase()
            next_ab = self._next_autobuyer_time()

            # Determine event times
            purchase_time = None
            ab_time = None
            node_id = None
            ab_id = None

            if next_purchase is not None:
                node_id, time_needed = next_purchase
                purchase_time = self._time + time_needed

            if next_ab is not None:
                ab_id, ab_time = next_ab

            # Check if autobuyer fires before purchase and before target
            ab_fires_first = False
            if ab_time is not None and ab_time < target_time - 1e-12:
                if purchase_time is None or ab_time < purchase_time:
                    ab_fires_first = True

            if ab_fires_first:
                # Advance to autobuyer fire time
                dt = ab_time - self._time
                if dt < 0:
                    dt = 0.0
                if dt > 0:
                    seg = self._create_segment(rates, dt, [f"autobuyer:{ab_id}"])
                    new_segments.append(seg)
                    self._accumulate(rates, dt)
                    self._time = ab_time
                self._execute_autobuyer(ab_id)

            elif purchase_time is not None and purchase_time < target_time - 1e-12:
                # Advance to purchase time
                dt = purchase_time - self._time
                if dt < 0:
                    dt = 0.0

                seg = self._create_segment(rates, dt, [f"purchase:{node_id}"])
                new_segments.append(seg)

                # Accumulate resources
                self._accumulate(rates, dt)
                self._time = purchase_time

                # Fix floating-point drift: ensure balance covers the purchase
                # we computed we could afford (time_to_afford said so)
                self._ensure_can_afford(node_id)

                # Handle chattering: count purchases in this epsilon window
                purchases_in_window = 0
                window_start = self._time

                while True:
                    # Apply free purchases
                    free = self.apply_free_purchases()
                    purchases_in_window += len(free)

                    # Execute the purchase (may fail if free purchases spent the balance)
                    try:
                        self.purchase(node_id)
                    except ValueError:
                        # Expected when free purchases above consumed the balance
                        break
                    purchases_in_window += 1

                    # Check chattering
                    if purchases_in_window >= MAX_PURCHASES_PER_EPSILON:
                        # Batch-evaluate: buy all affordable at once
                        self._batch_purchase_all_affordable()
                        break

                    # Check for near-simultaneous purchases
                    _, rates = self._compute_net_rates()
                    next_purchase = self.find_next_purchase()
                    if next_purchase is None:
                        break

                    node_id, time_needed = next_purchase
                    if time_needed > epsilon:
                        break
                    # Another purchase within epsilon -- continue loop
                    if self._time + time_needed > window_start + epsilon:
                        break

            else:
                # No purchase or autobuyer before target_time -- advance to target
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
            if rate > 0:
                ns.total_production += rate * dt
            # Clamp at 0
            if ns.current_value < 0:
                ns.current_value = 0.0

        # Clamp to capacity if set
        for node in self._game.nodes:
            if isinstance(node, Resource) and node.capacity is not None:
                ns = self._state.get(node.id)
                if ns.current_value > node.capacity:
                    ns.current_value = node.capacity

        # Track lifetime earnings (only positive rates)
        for resource_id, rate in rates.items():
            if rate <= 0:
                continue
            earned = rate * dt
            if resource_id in self._state.lifetime_earnings:
                self._state.lifetime_earnings[resource_id] += earned
            else:
                self._state.lifetime_earnings[resource_id] = earned

    def _ensure_can_afford(self, node_id: str) -> None:
        """Nudge balance up if floating-point drift left us barely short."""
        currency_id = self._get_currency_resource_id_for(node_id)
        if currency_id is None:
            return
        if node_id in self._generators:
            gen = self._generators[node_id]
            ns = self._state.get(node_id)
            cost = float(bulk_purchase_cost(
                BigFloat(gen.cost_base), BigFloat(gen.cost_growth_rate),
                ns.owned, 1,
            ))
        elif node_id in self._upgrades:
            cost = self._upgrades[node_id].cost
        else:
            return
        balance = self._state.get(currency_id).current_value
        if balance < cost and balance >= cost * (1 - 1e-6) - 1e-6:
            self._state.get(currency_id).current_value = cost

    def _batch_purchase_all_affordable(self) -> None:
        """Batch-purchase all currently affordable items.

        Used when chattering is detected to break out of the purchase loop.
        """
        changed = True
        while changed:
            changed = False

            # Find all affordable, sorted by efficiency
            affordable: list[tuple[str, float, float]] = []

            for node in self._game.nodes:
                currency_id = self._get_currency_resource_id_for(node.id)
                if currency_id is None:
                    continue
                balance = self._state.get(currency_id).current_value

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
