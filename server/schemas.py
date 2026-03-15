"""API request/response Pydantic models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# -- Games --


class GameSummary(BaseModel):
    id: str
    name: str
    node_count: int
    edge_count: int
    bundled: bool


class GameListResponse(BaseModel):
    games: list[GameSummary]


class GameCreateResponse(BaseModel):
    id: str
    name: str


# -- Analysis --


class AnalysisRequest(BaseModel):
    game_id: str
    simulation_time: float = Field(default=300.0, gt=0, le=86400)
    optimizer: Literal["greedy", "beam", "mcts", "bnb"] = "greedy"
    beam_width: int = Field(default=100, ge=1)
    mcts_iterations: int = Field(default=1000, ge=1)
    mcts_seed: int | None = None
    bnb_depth: int = Field(default=20, ge=1)
    tags: list[str] | None = None


class CompareRequest(BaseModel):
    game_id: str
    strategies: list[str] = ["free", "paid"]
    simulation_time: float = Field(default=300.0, gt=0, le=86400)


class ReportRequest(BaseModel):
    game_id: str
    simulation_time: float = Field(default=300.0, gt=0, le=86400)
    use_cdn: bool = True


# -- Engine Sessions --


class StartSessionRequest(BaseModel):
    game_id: str
    initial_balance: float = Field(default=50.0, gt=0, le=1e15)


class AdvanceRequest(BaseModel):
    seconds: float = Field(default=1.0, gt=0, le=86400)


class PurchaseRequest(BaseModel):
    node_id: str
    count: int = Field(default=1, ge=1, le=1000)


class AutoOptimizeRequest(BaseModel):
    target_time: float = Field(default=300.0, gt=0, le=86400)
    optimizer: Literal["greedy", "beam", "mcts", "bnb"] = "greedy"
    max_steps: int = Field(default=500, ge=1, le=10000)
    beam_width: int = Field(default=100, ge=1)
    mcts_iterations: int = Field(default=1000, ge=1)
    bnb_depth: int = Field(default=20, ge=1)


class ResourceState(BaseModel):
    current_value: float = Field(ge=0)
    production_rate: float


class GeneratorState(BaseModel):
    owned: int = Field(ge=0)
    cost_next: float
    production_per_sec: float


class UpgradeState(BaseModel):
    purchased: bool
    cost: float
    affordable: bool


class PrestigeState(BaseModel):
    available_currency: float
    formula_preview: str


class AchievementState(BaseModel):
    id: str
    name: str
    unlocked: bool


class SessionState(BaseModel):
    session_id: str
    game_id: str
    elapsed_time: float = Field(ge=0)
    resources: dict[str, ResourceState]
    generators: dict[str, GeneratorState]
    upgrades: dict[str, UpgradeState]
    prestige: PrestigeState | None = None
    achievements: list[AchievementState] = []


class PurchaseStepResponse(BaseModel):
    time: float
    node_id: str
    cost: float
    count: int


class TimelineEntry(BaseModel):
    time: float
    production_rate: float


class AutoOptimizeResponse(BaseModel):
    purchases: list[PurchaseStepResponse]
    timeline: list[TimelineEntry]
    final_production: float
    final_balance: float


# -- Errors --


class ErrorResponse(BaseModel):
    error: str
    detail: str
    status: int
