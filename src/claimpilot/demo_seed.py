from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .handlers import register_handlers
from .models import ExceptionType, Order
from .pipeline import Event, EventBus
from .store import AuditStore, OrderStore


def _sample_order() -> Order:
    now = datetime.now(timezone.utc)
    return Order(
        order_id="ord-1001",
        user_id="user-001",
        item_name="Wireless Headphones",
        purchase_price=50.0,
        current_price=40.0,
        purchased_at=now - timedelta(days=2),
        return_window_days=30,
        expected_delivery_at=now - timedelta(days=1),
    )


def run_demo() -> list[str]:
    bus = EventBus()
    orders = OrderStore()
    audit = AuditStore()
    register_handlers(bus, orders, audit)

    order = _sample_order()
    bus.publish(Event(topic="OrderDetected", payload={"order": order}))

    bus.publish(
        Event(
            topic="StatusChanged",
            payload={
                "order_id": order.order_id,
                "exception_type": ExceptionType.PRICE_DROP.value,
            },
        )
    )

    return [f"{r.action}:{r.status}:{r.details}" for r in audit.all()]


if __name__ == "__main__":
    for row in run_demo():
        print(row)
