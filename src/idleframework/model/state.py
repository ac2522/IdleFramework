"""GameState — runtime state of an idle game."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from idleframework.model.game import GameDefinition


class NodeState(BaseModel):
    """Runtime state for a single node."""

    owned: int = 0
    current_value: float = 0.0
    level: int = 0
    purchased: bool = False
    active: bool = True
    total_production: float = 0.0
    last_fired: float = 0.0


class GameState(BaseModel):
    """Runtime state for the entire game."""

    node_states: dict[str, NodeState]
    elapsed_time: float = 0.0
    run_time: float = 0.0
    lifetime_earnings: dict[str, float] = Field(default_factory=dict)
    layer_run_times: dict[str, float] = Field(default_factory=dict)

    @classmethod
    def from_game(cls, game: GameDefinition) -> GameState:
        """Initialize state from a game definition."""
        from idleframework.model.nodes import Resource

        node_states: dict[str, NodeState] = {}
        for node in game.nodes:
            ns = NodeState()
            if isinstance(node, Resource):
                ns.current_value = node.initial_value
            node_states[node.id] = ns
        return cls(node_states=node_states)

    def get(self, node_id: str) -> NodeState:
        """Get state for a node. Raises KeyError if not found."""
        return self.node_states[node_id]

    def get_resource_value(self, resource_id: str) -> float:
        """Get the current value of a resource."""
        return self.node_states[resource_id].current_value
