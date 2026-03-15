"""Pydantic schema validation tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from server.schemas import (
    AdvanceRequest,
    AutoOptimizeRequest,
    PurchaseRequest,
    StartSessionRequest,
)


class TestAdvanceRequestValidation:
    def test_rejects_zero_seconds(self):
        with pytest.raises(ValidationError, match="greater than 0"):
            AdvanceRequest(seconds=0)

    def test_rejects_negative_seconds(self):
        with pytest.raises(ValidationError, match="greater than 0"):
            AdvanceRequest(seconds=-1)

    def test_rejects_exceeding_max_seconds(self):
        with pytest.raises(ValidationError, match="less than or equal to 86400"):
            AdvanceRequest(seconds=86401)

    def test_accepts_valid_seconds(self):
        req = AdvanceRequest(seconds=5.0)
        assert req.seconds == 5.0

    def test_accepts_boundary_min(self):
        req = AdvanceRequest(seconds=0.001)
        assert req.seconds == pytest.approx(0.001)

    def test_accepts_boundary_max(self):
        req = AdvanceRequest(seconds=86400)
        assert req.seconds == 86400


class TestPurchaseRequestValidation:
    def test_rejects_zero_count(self):
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            PurchaseRequest(node_id="foo", count=0)

    def test_rejects_negative_count(self):
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            PurchaseRequest(node_id="foo", count=-1)

    def test_rejects_exceeding_max_count(self):
        with pytest.raises(ValidationError, match="less than or equal to 1000"):
            PurchaseRequest(node_id="foo", count=1001)

    def test_accepts_valid_count(self):
        req = PurchaseRequest(node_id="gen1", count=5)
        assert req.count == 5
        assert req.node_id == "gen1"

    def test_default_count_is_one(self):
        req = PurchaseRequest(node_id="gen1")
        assert req.count == 1


class TestStartSessionRequestValidation:
    def test_rejects_zero_initial_balance(self):
        with pytest.raises(ValidationError, match="greater than 0"):
            StartSessionRequest(game_id="minicap", initial_balance=0)

    def test_rejects_negative_initial_balance(self):
        with pytest.raises(ValidationError, match="greater than 0"):
            StartSessionRequest(game_id="minicap", initial_balance=-1)

    def test_accepts_valid_balance(self):
        req = StartSessionRequest(game_id="minicap", initial_balance=100.0)
        assert req.initial_balance == 100.0

    def test_default_balance(self):
        req = StartSessionRequest(game_id="minicap")
        assert req.initial_balance == 50.0


class TestAutoOptimizeRequestValidation:
    def test_rejects_zero_target_time(self):
        with pytest.raises(ValidationError, match="greater than 0"):
            AutoOptimizeRequest(target_time=0)

    def test_rejects_zero_max_steps(self):
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            AutoOptimizeRequest(max_steps=0)

    def test_rejects_negative_target_time(self):
        with pytest.raises(ValidationError, match="greater than 0"):
            AutoOptimizeRequest(target_time=-1)

    def test_accepts_valid_values(self):
        req = AutoOptimizeRequest(target_time=60.0, max_steps=100)
        assert req.target_time == 60.0
        assert req.max_steps == 100

    def test_defaults(self):
        req = AutoOptimizeRequest()
        assert req.target_time == 300.0
        assert req.max_steps == 500
        assert req.optimizer == "greedy"
