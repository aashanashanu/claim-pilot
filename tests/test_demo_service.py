from claimpilot.agent_runtime import StrandsDecisionEngine
from claimpilot.demo_service import DemoService
from claimpilot.demo_surface import DemoDashboard
from claimpilot.models import ActionType, ExceptionType, Order, ResolutionDecision


def _mock_engine() -> StrandsDecisionEngine:
    def agent_callable(payload: dict[str, object]) -> ResolutionDecision:
        order = payload["order"]
        assert isinstance(order, Order)
        exception_type = ExceptionType(str(payload["exception_type"]))
        if exception_type is ExceptionType.PRICE_DROP:
            return ResolutionDecision(
                order_id=order.order_id,
                exception_type=exception_type,
                action=ActionType.AUTO_RESOLVE,
                reason="Mock Strands auto decision.",
            )
        return ResolutionDecision(
            order_id=order.order_id,
            exception_type=exception_type,
            action=ActionType.NEEDS_DECISION,
            reason="Mock Strands asks for user decision.",
        )

    return StrandsDecisionEngine(agent_callable=agent_callable)


def test_demo_service_handles_scenarios_and_snapshot():
    service = DemoService(dashboard=DemoDashboard(decision_engine=_mock_engine()))

    result = service.trigger_scenario("price_drop")
    assert result["action"] == "auto_resolve"

    snapshot = service.snapshot()
    assert snapshot["active_orders"] >= 1
    assert snapshot["decision_source"] in {"strands", "unknown"}
    assert "latest_audit" in snapshot
    assert "audit_records" in snapshot

    result = service.trigger_scenario("damaged_item")
    assert result["action"] == "needs_decision"

    pending = service.snapshot()["pending_decisions"]
    assert pending >= 1
