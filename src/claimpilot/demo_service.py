from __future__ import annotations

import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from .demo_surface import DemoDashboard
from .config import DEFAULT_CONFIG
from .ingestion import ingest_mailbox_messages
from .integrations import CarrierStatusAdapter, GmailInboxAdapter, GmailMessageAdapter
from .models import StorefrontActivity, StorefrontOrder, StorefrontProduct
from .pipeline import Event
from .store import DeadLetterStore, ProcessedEventStore, StorefrontStore, TrackingStateStore
from .telemetry import log_event
from .tracking import poll_tracking_updates


class DemoService:
    """Application service used by both desktop and web clients."""

    _DECISION_SOURCE_RE = re.compile(r"\[(?P<source>[^\]]+)\]")
    _GMAIL_POLL_RETRY_ATTEMPTS = 3

    def __init__(
        self,
        dashboard: DemoDashboard | None = None,
        gmail_adapter: GmailMessageAdapter | None = None,
        carrier_adapter: CarrierStatusAdapter | None = None,
        gmail_target_email: str | None = None,
    ) -> None:
        self.dashboard = dashboard or DemoDashboard()
        self.gmail_adapter = gmail_adapter or GmailInboxAdapter()
        self.carrier_adapter = carrier_adapter
        self.gmail_target_email = (
            gmail_target_email
            or DEFAULT_CONFIG.gmail_target_email
            or os.getenv("CLAIMPILOT_GMAIL_TARGET_ADDRESS")
            or os.getenv("GMAIL_TARGET_ADDRESS")
        )
        self.gmail_polling_enabled = DEFAULT_CONFIG.gmail_polling_enabled
        self.gmail_poll_interval_seconds = max(5, DEFAULT_CONFIG.gmail_poll_interval_seconds)
        self.gmail_poll_max_results = max(1, DEFAULT_CONFIG.gmail_poll_max_results)
        self.email_processed_store = ProcessedEventStore()
        self.tracking_state_store = TrackingStateStore()
        self.tracking_processed_store = ProcessedEventStore()
        self.dead_letter_store = DeadLetterStore()
        self.storefront = StorefrontStore()
        self._storefront_order_counter = 0
        self._gmail_poll_lock = threading.Lock()
        self._gmail_poll_stop_event = threading.Event()
        self._gmail_poll_thread: threading.Thread | None = None
        self.storefront.seed_products(self._default_storefront_products())

    def trigger_scenario(self, scenario: str) -> dict[str, Any]:
        result = self.dashboard.trigger_scenario(scenario)
        return result

    def run_demo_runbook(self) -> dict[str, Any]:
        storefront_seed = self.seed_storefront_demo()
        beats = {
            "price_drop": self.trigger_scenario("price_drop"),
            "damaged_item": self.trigger_scenario("damaged_item"),
            "return_window": self.trigger_scenario("return_window"),
        }
        return {
            "status": "ok",
            "runbook": "phase4_demo_surface",
            "storefront_seed": storefront_seed,
            "beats": beats,
            "snapshot": self.snapshot(),
            "storefront": self.storefront_snapshot(),
        }

    def ingest_gmail_messages(self, user_id: str = "user-demo", max_results: int = 3) -> dict[str, Any]:
        messages = self.gmail_adapter.fetch_messages(user_id=user_id, max_results=max_results)
        return self._ingest_messages(messages, source="gmail")

    def poll_gmail_inbox(self, user_id: str = "user-demo", max_results: int | None = None) -> dict[str, Any]:
        result = self.ingest_gmail_messages(user_id=user_id, max_results=max_results or self.gmail_poll_max_results)
        result["watch_mode"] = "background"
        return result

    def start_background_workers(self) -> None:
        if not self.gmail_polling_enabled or self._gmail_poll_thread is not None:
            return

        self._gmail_poll_stop_event.clear()
        self._gmail_poll_thread = threading.Thread(target=self._gmail_poll_loop, name="claimpilot-gmail-poller", daemon=True)
        self._gmail_poll_thread.start()

    def stop_background_workers(self) -> None:
        self._gmail_poll_stop_event.set()
        thread = self._gmail_poll_thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)
        self._gmail_poll_thread = None

    def _gmail_poll_loop(self) -> None:
        while not self._gmail_poll_stop_event.is_set():
            self._poll_gmail_with_retries(max_results=self.gmail_poll_max_results)

            self._gmail_poll_stop_event.wait(self.gmail_poll_interval_seconds)

    def _poll_gmail_with_retries(self, max_results: int) -> None:
        last_error = "unknown"
        for attempt in range(1, self._GMAIL_POLL_RETRY_ATTEMPTS + 1):
            try:
                result = self.poll_gmail_inbox(max_results=max_results)
                log_event(
                    "gmail_poll_completed",
                    attempt=attempt,
                    ingested=result.get("ingested", 0),
                    requested=result.get("requested", 0),
                )
                return
            except Exception as exc:
                last_error = str(exc)
                log_event(
                    "gmail_poll_attempt_failed",
                    attempt=attempt,
                    max_retry_attempts=self._GMAIL_POLL_RETRY_ATTEMPTS,
                    error=str(exc),
                )

        self.dead_letter_store.add(
            "gmail-inbox",
            f"poll retries exhausted: {last_error}",
            status="retry",
        )

    def _ingest_messages(self, messages: list[Any], *, source: str) -> dict[str, Any]:
        with self._gmail_poll_lock:
            emitted_order_ids = ingest_mailbox_messages(
                messages=messages,
                bus=self.dashboard.bus,
                processed_events=self.email_processed_store,
            )

        log_event(
            "ingestion_batch_completed",
            source=source,
            requested=len(messages),
            ingested=len(emitted_order_ids),
            emitted_order_ids=emitted_order_ids,
        )

        return {
            "source": source,
            "requested": len(messages),
            "ingested": len(emitted_order_ids),
            "order_ids": emitted_order_ids,
        }

    def gmail_readiness(self) -> dict[str, Any]:
        readiness_fn = getattr(self.gmail_adapter, "readiness_status", None)
        if callable(readiness_fn):
            payload = readiness_fn()
            if isinstance(payload, dict):
                payload = dict(payload)
                payload["recipient_email"] = self.gmail_target_email
                payload["recipient_email_configured"] = bool(self.gmail_target_email)
                return payload

        return {
            "status": "error",
            "code": "GMAIL_READINESS_UNAVAILABLE",
            "message": "Configured Gmail adapter does not expose readiness diagnostics.",
        }

    def storefront_snapshot(self) -> dict[str, Any]:
        return {
            "recipient_email": self.gmail_target_email,
            "recipient_email_configured": bool(self.gmail_target_email),
            "gmail_watch_enabled": self.gmail_polling_enabled,
            "gmail_watch_interval_seconds": self.gmail_poll_interval_seconds,
            "gmail_ready": self.gmail_readiness(),
            "catalog": [
                {
                    "product_id": product.product_id,
                    "name": product.name,
                    "description": product.description,
                    "price": product.price,
                    "merchant": product.merchant,
                    "return_window_days": product.return_window_days,
                }
                for product in self.storefront.products()
            ],
            "orders": [
                {
                    "order_id": order.order_id,
                    "product_id": order.product_id,
                    "item_name": order.item_name,
                    "merchant": order.merchant,
                    "purchase_price": order.purchase_price,
                    "current_price": order.current_price,
                    "status": order.status,
                    "email_kind": order.email_kind,
                    "email_subject": order.email_subject,
                    "recipient_email": order.recipient_email,
                    "created_at": order.created_at.isoformat(),
                }
                for order in self.storefront.orders()
            ],
            "activities": [
                {
                    "activity_type": activity.activity_type,
                    "order_id": activity.order_id,
                    "product_id": activity.product_id,
                    "details": activity.details,
                    "created_at": activity.created_at.isoformat(),
                }
                for activity in self.storefront.activities()
            ],
        }

    def seed_storefront_demo(self) -> dict[str, Any]:
        actions = [
            self.purchase_product("monitor"),
            self.purchase_product("headphones"),
            self.purchase_product("backpack"),
            self.purchase_product("desk-lamp"),
        ]

        # Drive the inbox with one order confirmation and three scenario emails.
        self.price_drop(actions[1]["order_id"], new_price=actions[1]["current_price"] - 20.0)
        self.start_return(actions[2]["order_id"])
        self.file_claim(actions[3]["order_id"], claim_type="damaged_item")

        return {
            "status": "seeded",
            "orders_created": [item["order_id"] for item in actions],
            "storefront": self.storefront_snapshot(),
        }

    def purchase_product(self, product_id: str, recipient_email: str | None = None) -> dict[str, Any]:
        product = self._get_product(product_id)
        order_id = self._next_storefront_order_id()
        target_email = recipient_email or self.gmail_target_email
        if not target_email:
            raise RuntimeError("CLAIMPILOT_GMAIL_TARGET_ADDRESS is required to send storefront emails.")

        order = StorefrontOrder(
            order_id=order_id,
            product_id=product.product_id,
            item_name=product.name,
            merchant=product.merchant,
            purchase_price=product.price,
            current_price=product.price,
            status="order",
            recipient_email=target_email,
            email_subject=f"ClaimPilot Order Confirmation #{order_id}",
            email_kind="order",
        )
        self.storefront.upsert_order(order)
        message_id = self._send_storefront_email(order, event_kind="order")
        self.storefront.add_activity(
            StorefrontActivity(
                activity_type="order_created",
                order_id=order.order_id,
                product_id=product.product_id,
                details=f"Order email sent to {target_email} ({message_id}).",
            )
        )
        return self._order_payload(order, message_id=message_id)

    def price_drop(self, order_id: str, new_price: float) -> dict[str, Any]:
        order = self._get_storefront_order(order_id)
        order.current_price = new_price
        order.status = "price_drop"
        order.email_kind = "status"
        order.email_subject = f"ClaimPilot Price Drop Alert #{order.order_id}"
        self.storefront.upsert_order(order)
        message_id = self._send_storefront_email(order, event_kind="status", exception_type="price_drop", current_price=new_price)
        self.storefront.add_activity(
            StorefrontActivity(
                activity_type="price_drop",
                order_id=order.order_id,
                product_id=order.product_id,
                details=f"Price drop email sent ({message_id}).",
            )
        )
        return self._order_payload(order, message_id=message_id)

    def start_return(self, order_id: str) -> dict[str, Any]:
        order = self._get_storefront_order(order_id)
        order.status = "return"
        order.email_kind = "status"
        order.email_subject = f"ClaimPilot Return Window Closing #{order.order_id}"
        self.storefront.upsert_order(order)
        message_id = self._send_storefront_email(order, event_kind="status", exception_type="return_window_closing")
        self.storefront.add_activity(
            StorefrontActivity(
                activity_type="return",
                order_id=order.order_id,
                product_id=order.product_id,
                details=f"Return email sent ({message_id}).",
            )
        )
        return self._order_payload(order, message_id=message_id)

    def file_claim(self, order_id: str, claim_type: str = "damaged_item") -> dict[str, Any]:
        order = self._get_storefront_order(order_id)
        order.status = "claim"
        order.email_kind = "status"
        order.email_subject = f"ClaimPilot Claim Filed #{order.order_id}"
        self.storefront.upsert_order(order)
        message_id = self._send_storefront_email(order, event_kind="status", exception_type=claim_type)
        self.storefront.add_activity(
            StorefrontActivity(
                activity_type="claim",
                order_id=order.order_id,
                product_id=order.product_id,
                details=f"Claim email sent ({message_id}).",
            )
        )
        return self._order_payload(order, message_id=message_id)

    def _send_storefront_email(
        self,
        order: StorefrontOrder,
        *,
        event_kind: str,
        exception_type: str | None = None,
        current_price: float | None = None,
    ) -> str:
        subject = order.email_subject
        body_lines = [
            f"ClaimPilot Event: {event_kind}",
            f"Order ID: {order.order_id}",
            f"Item: {order.item_name}",
            f"Price: ${order.purchase_price:.2f}",
            f"Merchant: {order.merchant}",
            f"Carrier: USPS",
            f"Tracking: TRK-{order.order_id}",
            f"Expected Delivery: {self._expected_delivery_iso(order)}",
        ]
        if current_price is not None:
            body_lines.append(f"Current Price: ${current_price:.2f}")
        if exception_type is not None:
            body_lines.append(f"Exception Type: {exception_type}")
            body_lines.append("Evidence Quality: strong")

        return self.gmail_adapter.send_message(order.recipient_email, subject, "\n".join(body_lines))

    def _expected_delivery_iso(self, order: StorefrontOrder) -> str:
        return (datetime.now(timezone.utc) + timedelta(days=3)).replace(microsecond=0).isoformat()

    def _order_payload(self, order: StorefrontOrder, *, message_id: str) -> dict[str, Any]:
        return {
            "order_id": order.order_id,
            "product_id": order.product_id,
            "item_name": order.item_name,
            "status": order.status,
            "purchase_price": order.purchase_price,
            "current_price": order.current_price,
            "message_id": message_id,
        }

    def _get_product(self, product_id: str) -> StorefrontProduct:
        for product in self.storefront.products():
            if product.product_id == product_id:
                return product
        raise KeyError(f"Unknown storefront product: {product_id}")

    def _get_storefront_order(self, order_id: str) -> StorefrontOrder:
        return self.storefront.get_order(order_id)

    def _next_storefront_order_id(self) -> str:
        self._storefront_order_counter += 1
        return f"SF-{self._storefront_order_counter:04d}"

    def _default_storefront_products(self) -> list[StorefrontProduct]:
        return [
            StorefrontProduct(
                product_id="monitor",
                name="4K Monitor",
                description="High-value device to demonstrate price drops and claims.",
                price=249.0,
            ),
            StorefrontProduct(
                product_id="headphones",
                name="Wireless Headphones",
                description="Popular order for inbox order detection.",
                price=129.0,
            ),
            StorefrontProduct(
                product_id="backpack",
                name="Travel Backpack",
                description="Good demo for return-window follow-up.",
                price=89.0,
            ),
            StorefrontProduct(
                product_id="desk-lamp",
                name="Desk Lamp",
                description="Simple item for damage claim demo.",
                price=59.0,
            ),
        ]

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
        log_event(
            "tracking_poll_completed",
            status_changed_count=len(emitted_order_ids),
            order_ids=emitted_order_ids,
            dead_letter_count=len(self.dead_letter_store.all()),
        )
        return {
            "source": "carrier",
            "status_changed_count": len(emitted_order_ids),
            "order_ids": emitted_order_ids,
            "dead_letters": self.dead_letter_store.all(),
        }

    def capture_decision(self, order_id: str, decision: str, reason: str | None = None) -> dict[str, Any]:
        normalized_decision = self._normalize_decision(decision)
        if self._has_captured_decision(order_id):
            raise ValueError(f"Decision already captured for order: {order_id}")

        pending_record = self._latest_pending_decision_record(order_id)
        if pending_record is None:
            raise KeyError(f"No pending decision found for order: {order_id}")

        payload = {
            "order_id": order_id,
            "user_id": pending_record["user_id"],
            "decision": normalized_decision,
            "reason": reason or pending_record["details"],
            "metadata": {
                **pending_record.get("metadata", {}),
                "correlation_id": str(
                    pending_record.get("metadata", {}).get("correlation_id", f"decision:{order_id}")
                ),
            },
        }
        self.dashboard.bus.publish(Event(topic="DecisionCaptured", payload=payload))
        log_event(
            "decision_capture_requested",
            order_id=order_id,
            decision=normalized_decision,
            correlation_id=payload["metadata"].get("correlation_id", ""),
        )
        return {
            "status": normalized_decision,
            "order_id": order_id,
            "reason": payload["reason"],
        }

    def snapshot(self) -> dict[str, Any]:
        orders = self.dashboard.order_store.all()
        records = self.dashboard.audit_store.all()
        latest = records[-1] if records else None
        decision_source = self._latest_decision_source(records)
        pending_decisions = self._pending_decision_records(records)

        return {
            "active_orders": len(orders),
            "pending_decisions": len(pending_decisions),
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
            "pending_decision_items": pending_decisions,
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

    def _pending_decision_records(self, records: list[object]) -> list[dict[str, Any]]:
        captured_order_ids = {
            str(getattr(record, "order_id", ""))
            for record in records
            if getattr(record, "action", "") == "decision_captured"
        }
        pending_by_order: dict[str, dict[str, Any]] = {}

        for record in records:
            action = getattr(record, "action", "")
            order_id = str(getattr(record, "order_id", ""))
            if action == "decision_captured":
                pending_by_order.pop(order_id, None)
                continue
            if action != "needs_decision" or order_id in captured_order_ids:
                continue

            pending_by_order[order_id] = {
                "order_id": order_id,
                "user_id": str(getattr(record, "user_id", "")),
                "status": str(getattr(record, "status", "")),
                "details": str(getattr(record, "details", "")),
                "metadata": getattr(record, "metadata", {}),
                "created_at": getattr(record, "created_at", None).isoformat() if getattr(record, "created_at", None) else None,
            }

        return list(pending_by_order.values())

    def _latest_pending_decision_record(self, order_id: str) -> dict[str, Any] | None:
        for item in reversed(self.snapshot()["pending_decision_items"]):
            if item["order_id"] == order_id:
                return item
        return None

    def _has_captured_decision(self, order_id: str) -> bool:
        for record in self.dashboard.audit_store.all():
            if record.order_id == order_id and record.action == "decision_captured":
                return True
        return False

    def _normalize_decision(self, decision: str) -> str:
        normalized = decision.strip().lower()
        if normalized in {"approve", "approved", "approve_photo"}:
            return "approved"
        if normalized in {"reject", "rejected", "deny", "denied"}:
            return "rejected"
        raise ValueError(f"Unsupported decision value: {decision}")
