"""All 17 node types as Pydantic v2 models with discriminated union."""

from __future__ import annotations

from typing import Annotated, Literal, Optional, Union

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


# ---------- NodeBase ----------


class NodeBase(BaseModel):
    """Base fields shared by all node types."""

    id: str
    tags: list[str] = Field(default_factory=list)
    activation_mode: Literal["automatic", "interactive", "passive", "toggle"] = "automatic"
    pull_mode: Literal["pull_any", "pull_all"] = "pull_any"
    cooldown_time: Optional[float] = None


# ---------- 17 Node types ----------


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
    duration: Optional[float] = None
    cooldown_time: Optional[float] = None


class PrestigeLayer(NodeBase):
    type: Literal["prestige_layer"] = "prestige_layer"
    name: str = ""
    formula_expr: str
    layer_index: int
    reset_scope: list[str]
    persistence_scope: list[str] = Field(default_factory=list)
    bonus_type: str = "multiplicative"
    milestone_rules: list[dict] = Field(default_factory=list)


class SacrificeNode(NodeBase):
    type: Literal["sacrifice"] = "sacrifice"
    name: str = ""
    formula_expr: str
    reset_scope: list[str]
    bonus_type: str = "multiplicative"


class Achievement(NodeBase):
    type: Literal["achievement"] = "achievement"
    name: str = ""
    condition_type: Literal["single_threshold", "multi_threshold", "collection", "compound"]
    targets: list[ConditionTarget]
    logic: str = "and"
    bonus: Optional[dict] = None
    permanent: bool = True


class Manager(NodeBase):
    type: Literal["manager"] = "manager"
    name: str = ""
    target: str
    automation_type: str = "collect"


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
    condition_type: str = "single_threshold"
    targets: list[ConditionTarget]
    logic: str = "and"


class UnlockGate(NodeBase):
    type: Literal["unlock_gate"] = "unlock_gate"
    name: str = ""
    condition_type: str = "single_threshold"
    targets: list[ConditionTarget]
    prerequisites: list[str]
    logic: str = "and"
    permanent: bool = True


class ChoiceGroup(NodeBase):
    type: Literal["choice_group"] = "choice_group"
    name: str = ""
    options: list[str]
    max_selections: int = 1
    respeccable: bool = False
    respec_cost: Optional[float] = None


class Register(NodeBase):
    type: Literal["register"] = "register"
    name: str = ""
    formula_expr: str
    input_labels: list[dict[str, str]]


class Gate(NodeBase):
    type: Literal["gate"] = "gate"
    name: str = ""
    mode: Literal["deterministic", "probabilistic"]
    weights: Optional[list[float]] = None
    probabilities: Optional[list[float]] = None


class Queue(NodeBase):
    type: Literal["queue"] = "queue"
    name: str = ""
    delay: float
    capacity: Optional[int] = None


# ---------- Discriminated Union ----------

NodeUnion = Annotated[
    Union[
        Resource,
        Generator,
        NestedGenerator,
        Upgrade,
        PrestigeLayer,
        SacrificeNode,
        Achievement,
        Manager,
        Converter,
        ProbabilityNode,
        EndCondition,
        UnlockGate,
        ChoiceGroup,
        Register,
        Gate,
        Queue,
    ],
    Field(discriminator="type"),
]
