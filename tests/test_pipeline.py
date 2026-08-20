from datetime import datetime, timedelta, timezone

from claimpilot.handlers import register_handlers
from claimpilot.models import ExceptionType, Order
from claimpilot.pipeline import Event, EventBus
from claimpilot.store import AuditStore, OrderStore


def test_pipeline_routes_to_auto_resolve_for_price_drop():
    now = datetime.now(timezone.utc)
    order = Order(
        order_id="ord-100",
        user_id="user-100",
        item_name="Shoes",
        purchase_price=80.0,
        current_price=60.0,
        purchased_at=now - timedelta(days=1),
        return_window_days=30,
        expected_delivery_at=now - timedelta(days=1),
    )

    bus = EventBus()
    order_store = OrderStore()
    audit_store = AuditStore()
    register_handlers(bus, order_store, audit_store)

    bus.publish(Event(topic="OrderDetected", payload={"order": order}))
    bus.publish(
        Event(
            topic="StatusChanged",
            payload={"order_id": order.order_id, "exception_type": ExceptionType.PRICE_DROP.value},
        )
    )

    actions = [x.action for x in audit_store.all()]
    assert "order_detected" in actions
    assert "exception_classified" in actions
    assert "auto_resolve" in actions


def test_pipeline_routes_to_needs_decision_for_damaged_item():
    now = datetime.now(timezone.utc)
    order = Order(
        order_id="ord-200",
        user_id="user-200",
        item_name="Monitor",
        purchase_price=240.0,
        current_price=240.0,
        purchased_at=now - timedelta(days=2),
        return_window_days=30,
        expected_delivery_at=now - timedelta(days=1),
    )

    bus = EventBus()
    order_store = OrderStore()
    audit_store = AuditStore()
    register_handlers(bus, order_store, audit_store)

    bus.publish(Event(topic="OrderDetected", payload={"order": order}))
    bus.publish(
        Event(
            topic="StatusChanged",
            payload={"order_id": order.order_id, "exception_type": ExceptionType.DAMAGED_ITEM.value},
        )
    )

    actions = [x.action for x in audit_store.all()]
    assert "needs_decision" in actions
