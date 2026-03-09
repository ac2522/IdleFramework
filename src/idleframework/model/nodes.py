"""Node type definitions — discriminated union on 'type' field."""
from __future__ import annotations

from typing import Annotated, Any, Literal
from pydantic import BaseModel, Field


class NodeBase(BaseModel):
    """Shared properties for all node types."""
    id: str
    tags: list[str] = Field(default_factory=list)
    activation_mode: Literal["automatic", "interactive", "passive", "toggle"] = "automatic"
    cooldown_time: float | None = None


class Resource(NodeBase):
    type: Literal["resource"] = "resource"
    name: str
    initial_value: float = 0.0


class Generator(NodeBase):
    type: Literal["generator"] = "generator"
    name: str
    base_production: float
    cost_base: float
    cost_growth_rate: float
    cycle_time: float = 1.0


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
    bonus_type: str = "multiplicative"
    milestone_rules: list[dict[str, Any]] = Field(default_factory=list)


class SacrificeNode(NodeBase):
    type: Literal["sacrifice"] = "sacrifice"
    name: str = ""
    formula_expr: str
    reset_scope: list[str]
    bonus_type: str = "multiplicative"


class ConditionTarget(BaseModel):
    node_id: str
    property: str
    threshold: float


class Achievement(NodeBase):
    type: Literal["achievement"] = "achievement"
    name: str = ""
    condition_type: Literal["single_threshold", "multi_threshold", "collection", "compound"]
    targets: list[ConditionTarget]
    logic: str = "and"
    bonus: dict[str, Any] | None = None
    permanent: bool = True


class Manager(NodeBase):
    type: Literal["manager"] = "manager"
    name: str = ""
    target: str
    automation_type: str = "collect"


class ConverterIO(BaseModel):
    resource: str
    amount: float


class Converter(NodeBase):
    type: Literal["converter"] = "converter"
    name: str = ""
    inputs: list[ConverterIO]
    outputs: list[ConverterIO]
    rate: float = 1.0
    pull_mode: Literal["pull_any", "pull_all"] = "pull_any"


class ProbabilityNode(NodeBase):
    type: Literal["probability"] = "probability"
    name: str = ""
    expected_value: float
    variance: float = 0.0
    crit_chance: float = 0.0
    crit_multiplier: float = 1.0


class EndCondition(NodeBase):
    type: Literal["end_condition"] = "end_condition"
    name: str = ""
    condition_type: Literal["single_threshold", "multi_threshold", "collection", "compound"] = "single_threshold"
    targets: list[ConditionTarget] = Field(default_factory=list)
    logic: str = "and"


class UnlockGate(NodeBase):
    type: Literal["unlock_gate"] = "unlock_gate"
    name: str = ""
    condition_type: Literal["single_threshold", "multi_threshold", "collection", "compound"] = "single_threshold"
    targets: list[ConditionTarget] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    logic: str = "and"
    permanent: bool = True


class ChoiceGroup(NodeBase):
    type: Literal["choice_group"] = "choice_group"
    name: str = ""
    options: list[str]
    max_selections: int = 1
    respeccable: bool = False
    respec_cost: float | None = None


class Register(NodeBase):
    type: Literal["register"] = "register"
    name: str = ""
    formula_expr: str
    input_labels: list[dict[str, str]] = Field(default_factory=list)


class Gate(NodeBase):
    type: Literal["gate"] = "gate"
    name: str = ""
    mode: Literal["deterministic", "probabilistic"] = "deterministic"
    weights: list[float] = Field(default_factory=list)
    probabilities: list[float] = Field(default_factory=list)


class Queue(NodeBase):
    type: Literal["queue"] = "queue"
    name: str = ""
    delay: float
    capacity: float | None = None


NodeUnion = Annotated[
    Resource | Generator | NestedGenerator | Upgrade | PrestigeLayer |
    SacrificeNode | Achievement | Manager | Converter | ProbabilityNode |
    EndCondition | UnlockGate | ChoiceGroup | Register | Gate | Queue,
    Field(discriminator="type"),
]
