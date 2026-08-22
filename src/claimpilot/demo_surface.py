from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .decision_table import classify_exception
from .handlers import register_handlers
from .models import ActionType, ExceptionType, Order
from .pipeline import Event, EventBus
from .store import AuditStore, OrderStore


class DemoDashboard:
    """Minimal operator dashboard used for deterministic hackathon demos."""

    def __init__(self) -> None:
        self.bus = EventBus()
        self.order_store = OrderStore()
        self.audit_store = AuditStore()
        register_handlers(self.bus, self.order_store, self.audit_store)

    def trigger_scenario(self, scenario: str, *, order: Order | None = None) -> dict[str, Any]:
        if scenario == "price_drop":
            target = order or self._make_price_drop_order()
            self.order_store.upsert(target)
            self.bus.publish(Event(topic="OrderDetected", payload={"order": target}))
            self.bus.publish(
                Event(
                    topic="StatusChanged",
                    payload={
                        "order_id": target.order_id,
                        "exception_type": ExceptionType.PRICE_DROP.value,
                    },
                )
            )
            decision = classify_exception(target, ExceptionType.PRICE_DROP, now=datetime.now(timezone.utc))
            return {
                "action": decision.action.value,
                "reason": decision.reason,
                "order_id": target.order_id,
            }

        if scenario == "damaged_item":
            target = order or self._make_damaged_item_order()
            self.order_store.upsert(target)
            self.bus.publish(Event(topic="OrderDetected", payload={"order": target}))
            self.bus.publish(
                Event(
                    topic="StatusChanged",
                    payload={
                        "order_id": target.order_id,
                        "exception_type": ExceptionType.DAMAGED_ITEM.value,
                    },
                )
            )
            decision = classify_exception(target, ExceptionType.DAMAGED_ITEM, now=datetime.now(timezone.utc))
            return {
                "action": decision.action.value,
                "reason": decision.reason,
                "order_id": target.order_id,
            }

        if scenario == "return_window":
            target = order or self._make_return_window_order()
            self.order_store.upsert(target)
            self.bus.publish(Event(topic="OrderDetected", payload={"order": target}))
            self.bus.publish(
                Event(
                    topic="StatusChanged",
                    payload={
                        "order_id": target.order_id,
                        "exception_type": ExceptionType.RETURN_WINDOW_CLOSING.value,
                    },
                )
            )
            decision = classify_exception(target, ExceptionType.RETURN_WINDOW_CLOSING, now=datetime.now(timezone.utc))
            return {
                "action": decision.action.value,
                "reason": decision.reason,
                "order_id": target.order_id,
            }

        raise ValueError(f"Unknown scenario: {scenario}")

    def render(self) -> str:
        orders = self.order_store.all()
        actions = [
            (record.action, record.status, record.details)
            for record in self.audit_store.all()
        ]
        lines = [
            "ClaimPilot Demo Dashboard",
            f"Active orders: {len(orders)}",
            "Pending decisions: " + str(sum(1 for action, status, _ in actions if action == "needs_decision")),
            "Recent audit events:",
        ]
        for action, status, details in actions[-5:]:
            lines.append(f"- {action}:{status}:{details}")
        if not actions:
            lines.append("- No activity yet")
        return "\n".join(lines)

    def _make_price_drop_order(self) -> Order:
        now = datetime.now(timezone.utc)
        return Order(
            order_id="ord-demo-price-drop",
            user_id="user-demo",
            item_name="Monitor",
            purchase_price=140.0,
            current_price=115.0,
            purchased_at=now - timedelta(days=7),
            return_window_days=30,
            expected_delivery_at=now - timedelta(days=1),
            merchant="Demo Merchant",
            carrier="USPS",
            tracking_number="TRK-PRICE",
        )

    def _make_damaged_item_order(self) -> Order:
        now = datetime.now(timezone.utc)
        return Order(
            order_id="ord-demo-damage",
            user_id="user-demo",
            item_name="Desk Lamp",
            purchase_price=75.0,
            current_price=75.0,
            purchased_at=now - timedelta(days=10),
            return_window_days=30,
            expected_delivery_at=now - timedelta(days=1),
            merchant="Demo Merchant",
            carrier="USPS",
            tracking_number="TRK-DAMAGE",
        )

    def _make_return_window_order(self) -> Order:
        now = datetime.now(timezone.utc)
        return Order(
            order_id="ord-demo-return-window",
            user_id="user-demo",
            item_name="Backpack",
            purchase_price=90.0,
            current_price=90.0,
            purchased_at=now - timedelta(days=29),
            return_window_days=30,
            expected_delivery_at=now - timedelta(days=1),
            merchant="Demo Merchant",
            carrier="USPS",
            tracking_number="TRK-RETURN",
        )
