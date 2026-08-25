from datetime import datetime, timedelta, timezone

from claimpilot.agent_runtime import StrandsDecisionEngine
from claimpilot.demo_surface import DemoDashboard
from claimpilot.models import ActionType, ExceptionType, Order, ResolutionDecision


def _mock_engine() -> StrandsDecisionEngine:
    def agent_callable(payload: dict[str, object]) -> ResolutionDecision:
        order = payload["order"]
        assert isinstance(order, Order)
        exception_raw = str(payload["exception_type"])
        exception_type = ExceptionType(exception_raw)
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


def _make_order(order_id: str, *, exception_type: ExceptionType | None = None, current_price: float | None = None) -> Order:
    now = datetime.now(timezone.utc)
    order = Order(
        order_id=order_id,
        user_id="user-1",
        item_name="Demo Item",
        purchase_price=100.0,
        current_price=100.0,
        purchased_at=now - timedelta(days=12),
        return_window_days=30,
        expected_delivery_at=now - timedelta(days=2),
        merchant="Demo Merchant",
        carrier="USPS",
        tracking_number="TRK-01",
    )
    if exception_type is ExceptionType.PRICE_DROP and current_price is not None:
        order.current_price = current_price
    if exception_type is ExceptionType.RETURN_WINDOW_CLOSING:
        order.purchased_at = now - timedelta(days=29)
        order.return_window_days = 30
    return order


def test_demo_dashboard_auto_resolve_scenario_renders_summary():
    dashboard = DemoDashboard(decision_engine=_mock_engine())
    order = _make_order("ord-demo-1", exception_type=ExceptionType.PRICE_DROP, current_price=88.0)

    result = dashboard.trigger_scenario("price_drop", order=order)

    assert result["action"] == "auto_resolve"
    assert any(record.action == "auto_resolve" for record in dashboard.audit_store.all())
    assert "Active orders" in dashboard.render()
    assert "auto_resolve" in dashboard.render().lower()


def test_demo_dashboard_needs_decision_scenario_tracks_pending_action():
    dashboard = DemoDashboard(decision_engine=_mock_engine())
    order = _make_order("ord-demo-2", exception_type=ExceptionType.DAMAGED_ITEM)

    result = dashboard.trigger_scenario("damaged_item", order=order)

    assert result["action"] == "needs_decision"
    assert any(record.action == "needs_decision" for record in dashboard.audit_store.all())
    assert "Pending decisions" in dashboard.render()


def test_demo_dashboard_return_window_scenario_prompts_user_decision():
    dashboard = DemoDashboard(decision_engine=_mock_engine())
    order = _make_order("ord-demo-3", exception_type=ExceptionType.RETURN_WINDOW_CLOSING)

    result = dashboard.trigger_scenario("return_window", order=order)

    assert result["action"] == "needs_decision"
    assert "strands" in result["reason"].lower()
    assert "needs_decision" in dashboard.render().lower()
