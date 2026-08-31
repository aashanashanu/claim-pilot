from __future__ import annotations

import pytest

from claimpilot.agent_runtime import StrandsDecisionEngine
from claimpilot.demo_service import DemoService
from claimpilot.demo_surface import DemoDashboard
from claimpilot.models import ActionType, ExceptionType, Order, ResolutionDecision


def _mock_engine() -> StrandsDecisionEngine:
    def agent_callable(payload: dict[str, object]) -> ResolutionDecision:
        order = payload["order"]
        assert isinstance(order, Order)
        return ResolutionDecision(
            order_id=order.order_id,
            exception_type=ExceptionType.DAMAGED_ITEM,
            action=ActionType.NEEDS_DECISION,
            reason="Need customer confirmation.",
            metadata={"confidence": "medium"},
        )

    return StrandsDecisionEngine(agent_callable=agent_callable)


def _service_with_pending_decision() -> DemoService:
    service = DemoService(dashboard=DemoDashboard(decision_engine=_mock_engine()))
    service.trigger_scenario("damaged_item")
    return service


def test_capture_decision_approves_pending_order_and_clears_dashboard_state():
    service = _service_with_pending_decision()
    pending_before = service.snapshot()["pending_decision_items"]
    assert pending_before

    result = service.capture_decision(pending_before[0]["order_id"], "approve_photo", reason="Photo is clear.")

    assert result["status"] == "approved"
    snapshot = service.snapshot()
    assert snapshot["pending_decisions"] == 0
    assert any(record["action"] == "decision_captured" for record in snapshot["audit_records"])


def test_capture_decision_rejects_pending_order():
    service = _service_with_pending_decision()
    order_id = service.snapshot()["pending_decision_items"][0]["order_id"]

    result = service.capture_decision(order_id, "reject", reason="Need more evidence.")

    assert result["status"] == "rejected"


def test_capture_decision_rejects_invalid_or_duplicate_submissions():
    service = _service_with_pending_decision()
    order_id = service.snapshot()["pending_decision_items"][0]["order_id"]

    with pytest.raises(ValueError, match="Unsupported decision value"):
        service.capture_decision(order_id, "maybe")

    service.capture_decision(order_id, "approve_photo", reason="Valid.")

    with pytest.raises(ValueError, match="Decision already captured"):
        service.capture_decision(order_id, "approve_photo", reason="Duplicate.")
