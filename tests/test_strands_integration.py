from datetime import datetime, timedelta, timezone

from claimpilot.agent_runtime import StrandsDecisionEngine
from claimpilot.handlers import register_handlers
from claimpilot.models import ActionType, ExceptionType, Order, ResolutionDecision
from claimpilot.pipeline import Event, EventBus
from claimpilot.store import AuditStore, OrderStore
from claimpilot.workers import AutoResolver, DecisionNotifier, MockClaimActionAdapter, MockNotificationAdapter


def _make_order(order_id: str, price: float = 80.0) -> Order:
    now = datetime.now(timezone.utc)
    return Order(
        order_id=order_id,
        user_id="user-1",
        item_name="Item",
        purchase_price=price,
        current_price=price,
        purchased_at=now - timedelta(days=2),
        return_window_days=30,
        expected_delivery_at=now - timedelta(days=2),
        carrier="USPS",
        tracking_number="TRK-1",
    )


def test_strands_engine_routes_to_auto_resolve_and_executes_worker():
    def agent_callable(payload: dict[str, object]) -> dict[str, object]:
        return {
            "action": ActionType.AUTO_RESOLVE.value,
            "reason": "Strands decided this is safe.",
            "metadata": {"policy": "safe_auto"},
        }

    engine = StrandsDecisionEngine(agent_callable=agent_callable)
    resolver = AutoResolver(adapter=MockClaimActionAdapter())

    bus = EventBus()
    order_store = OrderStore()
    audit_store = AuditStore()
    register_handlers(
        bus,
        order_store,
        audit_store,
        decision_engine=engine,
        resolution_worker=resolver,
    )

    order = _make_order("ord-s-1")
    bus.publish(Event(topic="OrderDetected", payload={"order": order}))
    bus.publish(
        Event(
            topic="StatusChanged",
            payload={"order_id": order.order_id, "exception_type": ExceptionType.DELAYED.value},
        )
    )

    actions = [x.action for x in audit_store.all()]
    assert "auto_resolve" in actions
    auto_record = [x for x in audit_store.all() if x.action == "auto_resolve"][0]
    assert auto_record.status == "success"
    assert "Mock claim action submitted" in auto_record.details


def test_strands_engine_routes_to_needs_decision_and_executes_notifier():
    def agent_callable(payload: dict[str, object]) -> ResolutionDecision:
        order = payload["order"]
        assert isinstance(order, Order)
        return ResolutionDecision(
            order_id=order.order_id,
            exception_type=ExceptionType.DAMAGED_ITEM,
            action=ActionType.NEEDS_DECISION,
            reason="Need photo evidence from user.",
            metadata={"confidence": "medium"},
        )

    engine = StrandsDecisionEngine(agent_callable=agent_callable)
    notifier = DecisionNotifier(adapter=MockNotificationAdapter())

    bus = EventBus()
    order_store = OrderStore()
    audit_store = AuditStore()
    register_handlers(
        bus,
        order_store,
        audit_store,
        decision_engine=engine,
        notification_worker=notifier,
    )

    order = _make_order("ord-s-2", price=220.0)
    bus.publish(Event(topic="OrderDetected", payload={"order": order}))
    bus.publish(
        Event(
            topic="StatusChanged",
            payload={"order_id": order.order_id, "exception_type": ExceptionType.DAMAGED_ITEM.value},
        )
    )

    decision_record = [x for x in audit_store.all() if x.action == "needs_decision"][0]
    assert decision_record.status == "pending_user"
    assert "Decision request sent" in decision_record.details


def test_strands_engine_falls_back_to_rules_when_not_configured():
    engine = StrandsDecisionEngine(agent_callable=None)

    order = _make_order("ord-s-3")
    order.current_price = 60.0
    decision = engine.decide(order=order, exception_type=ExceptionType.PRICE_DROP)

    assert decision.action is ActionType.AUTO_RESOLVE
    assert decision.metadata["decision_source"] == "rules_fallback"
