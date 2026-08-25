from __future__ import annotations

import re
from typing import Any

from .demo_surface import DemoDashboard
from .ingestion import ingest_mailbox_messages
from .integrations import CarrierStatusAdapter, GmailInboxAdapter, GmailMessageAdapter
from .store import DeadLetterStore, ProcessedEventStore, TrackingStateStore
from .tracking import poll_tracking_updates


class DemoService:
    """Application service used by both desktop and web clients."""

    _DECISION_SOURCE_RE = re.compile(r"\[(?P<source>[^\]]+)\]")

    def __init__(
        self,
        dashboard: DemoDashboard | None = None,
        gmail_adapter: GmailMessageAdapter | None = None,
        carrier_adapter: CarrierStatusAdapter | None = None,
    ) -> None:
        self.dashboard = dashboard or DemoDashboard()
        self.gmail_adapter = gmail_adapter or GmailInboxAdapter()
        self.carrier_adapter = carrier_adapter
        self.email_processed_store = ProcessedEventStore()
        self.tracking_state_store = TrackingStateStore()
        self.tracking_processed_store = ProcessedEventStore()
        self.dead_letter_store = DeadLetterStore()

    def trigger_scenario(self, scenario: str) -> dict[str, Any]:
        result = self.dashboard.trigger_scenario(scenario)
        return result

    def ingest_gmail_messages(self, user_id: str = "user-demo", max_results: int = 3) -> dict[str, Any]:
        messages = self.gmail_adapter.fetch_messages(user_id=user_id, max_results=max_results)
        emitted_order_ids = ingest_mailbox_messages(
            messages=messages,
            bus=self.dashboard.bus,
            processed_events=self.email_processed_store,
        )
        return {
            "source": "gmail",
            "requested": len(messages),
            "ingested": len(emitted_order_ids),
            "order_ids": emitted_order_ids,
        }

    def gmail_readiness(self) -> dict[str, Any]:
        readiness_fn = getattr(self.gmail_adapter, "readiness_status", None)
        if callable(readiness_fn):
            payload = readiness_fn()
            if isinstance(payload, dict):
                return payload

        return {
            "status": "error",
            "code": "GMAIL_READINESS_UNAVAILABLE",
            "message": "Configured Gmail adapter does not expose readiness diagnostics.",
        }

    def poll_tracking(self) -> dict[str, Any]:
        if self.carrier_adapter is None:
            raise RuntimeError("Carrier tracking adapter is not configured.")

        emitted_order_ids = poll_tracking_updates(
            order_store=self.dashboard.order_store,
            tracker=self.carrier_adapter,
            state_store=self.tracking_state_store,
            processed_events=self.tracking_processed_store,
            bus=self.dashboard.bus,
            dead_letter_store=self.dead_letter_store,
        )
        return {
            "source": "carrier",
            "status_changed_count": len(emitted_order_ids),
            "order_ids": emitted_order_ids,
            "dead_letters": self.dead_letter_store.all(),
        }

    def snapshot(self) -> dict[str, Any]:
        orders = self.dashboard.order_store.all()
        records = self.dashboard.audit_store.all()
        latest = records[-1] if records else None
        decision_source = self._latest_decision_source(records)

        return {
            "active_orders": len(orders),
            "pending_decisions": sum(
                1 for record in records if record.action == "needs_decision" and record.status in {"pending_user", "pending"}
            ),
            "last_action": "idle" if latest is None else latest.action,
            "decision_source": decision_source,
            "latest_audit": (
                f"{latest.action}:{latest.status}:{latest.details}" if latest is not None else "No activity yet"
            ),
            "orders": [
                {
                    "order_id": order.order_id,
                    "item_name": order.item_name,
                    "merchant": order.merchant or "Demo Merchant",
                    "current_price": order.current_price,
                    "purchase_price": order.purchase_price,
                }
                for order in orders
            ],
            "audit_records": [
                {
                    "action": record.action,
                    "status": record.status,
                    "details": record.details,
                    "order_id": record.order_id,
                    "metadata": record.metadata,
                }
                for record in records
            ],
        }

    def _latest_decision_source(self, records: list[object]) -> str:
        for record in reversed(records):
            action = getattr(record, "action", "")
            if action != "exception_classified":
                continue
            details = getattr(record, "details", "")
            match = self._DECISION_SOURCE_RE.search(details)
            if match:
                return match.group("source")
            return "unknown"
        return "unknown"
