from claimpilot.agent_runtime import StrandsDecisionEngine
from claimpilot.demo_surface import DemoDashboard
from claimpilot.desktop_ui import DemoDesktopController
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


def test_demo_desktop_controller_integrates_with_backend():
    controller = DemoDesktopController(dashboard=DemoDashboard(decision_engine=_mock_engine()))

    result = controller.trigger_scenario("price_drop")

    assert result["action"] == "auto_resolve"
    snapshot = controller.snapshot()
    assert snapshot["active_orders"] >= 1
    assert snapshot["pending_decisions"] >= 0
    assert snapshot["last_action"] in {"auto_resolve", "needs_decision"}
    assert snapshot["latest_audit"]
