"""All 22 node types as Pydantic v2 models with discriminated union."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

# ---------- Helper models ----------


class ConditionTarget(BaseModel):
    """A condition target for achievements, end conditions, unlock gates."""

    node_id: str
    property: str
    threshold: float


class ConverterIO(BaseModel):
    """Input or output spec for a Converter node."""

    resource: str
    amount: float
    formula: str | None = None


# ---------- NodeBase ----------


class NodeBase(BaseModel):
    """Base fields shared by all node types."""

    id: str
    tags: list[str] = Field(default_factory=list)
    activation_mode: Literal["automatic", "interactive", "passive", "toggle"] = "automatic"
    pull_mode: Literal["pull_any", "pull_all"] = "pull_any"
    cooldown_time: float | None = None


# ---------- 22 Node types ----------


class Resource(NodeBase):
    type: Literal["resource"] = "resource"
    name: str
    initial_value: float = 0.0
    capacity: float | None = None
    overflow_behavior: Literal["clamp", "waste"] = "clamp"


class Generator(NodeBase):
    type: Literal["generator"] = "generator"
    name: str
    base_production: float = Field(gt=0)
    cost_base: float = Field(gt=0)
    cost_growth_rate: float = Field(gt=0)
    cycle_time: float = Field(default=1.0, gt=0)


class NestedGenerator(NodeBase):
    type: Literal["nested_generator"] = "nested_generator"
    name: str
    target_generator: str
    production_rate: float
    cost_base: float
    cost_growth_rate: float


class Upgrade(NodeBase):
    type: Literal["upgrade"] = "upgrade"
    name: str
    upgrade_type: Literal["multiplicative", "additive", "percentage"]
    magnitude: float
    cost: float
    target: str
    stacking_group: str
    duration: float | None = None
    cooldown_time: float | None = None


class PrestigeLayer(NodeBase):
    type: Literal["prestige_layer"] = "prestige_layer"
    name: str = ""
    formula_expr: str
    layer_index: int
    reset_scope: list[str]
    persistence_scope: list[str] = Field(default_factory=list)
    bonus_type: Literal["multiplicative", "additive", "percentage"] = "multiplicative"
    milestone_rules: list[dict] = Field(default_factory=list)
    currency_id: str | None = None
    parent_layer: str | None = None


class SacrificeNode(NodeBase):
    type: Literal["sacrifice"] = "sacrifice"
    name: str = ""
    formula_expr: str
    reset_scope: list[str]
    bonus_type: Literal["multiplicative", "additive", "percentage"] = "multiplicative"


class Achievement(NodeBase):
    type: Literal["achievement"] = "achievement"
    name: str = ""
    condition_type: Literal["single_threshold", "multi_threshold", "collection", "compound"]
    targets: list[ConditionTarget]
    logic: str = "and"
    bonus: dict | None = None
    permanent: bool = True


class Manager(NodeBase):
    type: Literal["manager"] = "manager"
    name: str = ""
    target: str
    automation_type: Literal["collect", "buy", "activate"] = "collect"


class Converter(NodeBase):
    type: Literal["converter"] = "converter"
    name: str = ""
    inputs: list[ConverterIO]
    outputs: list[ConverterIO]
    rate: float = 1.0
    pull_mode: Literal["pull_any", "pull_all"] = "pull_any"
    recipe_type: Literal["fixed", "scaling"] = "fixed"
    conversion_limit: int | None = None


class ProbabilityNode(NodeBase):
    type: Literal["probability"] = "probability"
    name: str = ""
    expected_value: float
    variance: float = Field(default=0.0, ge=0)
    crit_chance: float = Field(default=0.0, ge=0, le=1)
    crit_multiplier: float = 1.0


class EndCondition(NodeBase):
    type: Literal["end_condition"] = "end_condition"
    name: str = ""
    condition_type: Literal[
        "single_threshold", "multi_threshold", "collection", "compound"
    ] = "single_threshold"
    targets: list[ConditionTarget]
    logic: str = "and"


class UnlockGate(NodeBase):
    type: Literal["unlock_gate"] = "unlock_gate"
    name: str = ""
    condition_type: Literal[
        "single_threshold", "multi_threshold", "collection", "compound"
    ] = "single_threshold"
    targets: list[ConditionTarget]
    prerequisites: list[str]
    logic: str = "and"
    permanent: bool = True


class ChoiceGroup(NodeBase):
    type: Literal["choice_group"] = "choice_group"
    name: str = ""
    options: list[str]
    max_selections: int = Field(default=1, ge=1)
    respeccable: bool = False
    respec_cost: float | None = None


class Register(NodeBase):
    type: Literal["register"] = "register"
    name: str = ""
    formula_expr: str
    input_labels: list[dict[str, str]]


class Gate(NodeBase):
    type: Literal["gate"] = "gate"
    name: str = ""
    mode: Literal["deterministic", "probabilistic"]
    weights: list[float] | None = None
    probabilities: list[float] | None = None


class Queue(NodeBase):
    type: Literal["queue"] = "queue"
    name: str = ""
    delay: float = Field(gt=0)
    capacity: int | None = None


class TickspeedNode(NodeBase):
    type: Literal["tickspeed"] = "tickspeed"
    name: str = "Tickspeed"
    base_tickspeed: float = 1.0


class AutobuyerNode(NodeBase):
    type: Literal["autobuyer"] = "autobuyer"
    name: str = ""
    target: str
    interval: float = 1.0
    priority: int = 0
    condition: str | None = None
    bulk_amount: Literal["1", "10", "max"] = "1"
    enabled: bool = True


class DrainNode(NodeBase):
    type: Literal["drain"] = "drain"
    name: str = ""
    rate: float
    condition: str | None = None


class BuffNode(NodeBase):
    type: Literal["buff"] = "buff"
    name: str = ""
    buff_type: Literal["timed", "proc"]
    duration: float | None = None
    proc_chance: float | None = None
    multiplier: float = 2.0
    target: str | None = None
    cooldown: float = 0.0


class SynergyNode(NodeBase):
    type: Literal["synergy"] = "synergy"
    name: str = ""
    sources: list[str]
    formula_expr: str
    target: str


# ---------- Discriminated Union ----------

NodeUnion = Annotated[
    Resource | Generator | NestedGenerator | Upgrade | PrestigeLayer
    | SacrificeNode | Achievement | Manager | Converter
    | ProbabilityNode | EndCondition | UnlockGate | ChoiceGroup
    | Register | Gate | Queue
    | TickspeedNode | AutobuyerNode | DrainNode | BuffNode | SynergyNode,
    Field(discriminator="type"),
]
