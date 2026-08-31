from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Iterable

from .models import MailMessage, Order
from .pipeline import Event, EventBus
from .store import ProcessedEventStore


_ORDER_ID_RE = re.compile(r"order\s*(?:id|#)\s*[:\-]?\s*([A-Za-z0-9\-]+)", re.IGNORECASE)
_ITEM_RE = re.compile(r"item\s*[:\-]\s*(.+)", re.IGNORECASE)
_PRICE_RE = re.compile(r"price\s*[:\-]?\s*\$?([0-9]+(?:\.[0-9]{1,2})?)", re.IGNORECASE)
_TRACKING_RE = re.compile(r"tracking\s*(?:number|#)?\s*[:\-]?\s*([A-Za-z0-9\-]+)", re.IGNORECASE)
_CARRIER_RE = re.compile(r"carrier\s*[:\-]\s*([A-Za-z0-9_\- ]+)", re.IGNORECASE)
_MERCHANT_RE = re.compile(r"merchant\s*[:\-]\s*([A-Za-z0-9_\- ]+)", re.IGNORECASE)
_EXPECTED_DELIVERY_RE = re.compile(
    r"expected\s*delivery\s*[:\-]\s*([0-9]{4}-[0-9]{2}-[0-9]{2}(?:[T ][0-9:]{5,8})?)",
    re.IGNORECASE,
)
_CLAIMPILOT_EVENT_RE = re.compile(r"claimpilot\s*event\s*[:\-]\s*([A-Za-z0-9_\- ]+)", re.IGNORECASE)
_CLAIMPILOT_EXCEPTION_RE = re.compile(r"exception\s*type\s*[:\-]\s*([A-Za-z0-9_\- ]+)", re.IGNORECASE)
_CLAIMPILOT_EVIDENCE_RE = re.compile(r"evidence\s*quality\s*[:\-]\s*([A-Za-z0-9_\- ]+)", re.IGNORECASE)
_CLAIMPILOT_CURRENT_PRICE_RE = re.compile(r"current\s*price\s*[:\-]\s*\$?([0-9]+(?:\.[0-9]{1,2})?)", re.IGNORECASE)


def _extract(pattern: re.Pattern[str], text: str, default: str = "") -> str:
    match = pattern.search(text)
    if not match:
        return default
    return match.group(1).strip()


def _parse_iso_datetime(value: str, fallback: datetime) -> datetime:
    if not value:
        return fallback
    parsed = datetime.fromisoformat(value.replace(" ", "T"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def parse_order_email(message: MailMessage, default_return_window_days: int = 30) -> Order:
    text = f"{message.subject}\n{message.body}"
    order_id = _extract(_ORDER_ID_RE, text, default=f"msg-{message.message_id}")
    item_name = _extract(_ITEM_RE, text, default="Unknown item")
    price_value = _extract(_PRICE_RE, text, default="0")
    tracking_number = _extract(_TRACKING_RE, text)
    carrier = _extract(_CARRIER_RE, text)
    merchant = _extract(_MERCHANT_RE, text)
    expected_delivery_raw = _extract(_EXPECTED_DELIVERY_RE, text)

    purchase_price = float(price_value)
    expected_delivery = _parse_iso_datetime(
        expected_delivery_raw,
        fallback=message.received_at + timedelta(days=4),
    )

    return Order(
        order_id=order_id,
        user_id=message.user_id,
        item_name=item_name,
        purchase_price=purchase_price,
        current_price=purchase_price,
        purchased_at=message.received_at,
        return_window_days=default_return_window_days,
        expected_delivery_at=expected_delivery,
        merchant=merchant,
        carrier=carrier,
        tracking_number=tracking_number,
    )


def parse_claimpilot_event(message: MailMessage) -> dict[str, object]:
    text = f"{message.subject}\n{message.body}"
    event_kind = _extract(_CLAIMPILOT_EVENT_RE, text, default="order").strip().lower()
    order = parse_order_email(message)
    evidence_quality = _extract(_CLAIMPILOT_EVIDENCE_RE, text, default="strong")
    current_price_raw = _extract(_CLAIMPILOT_CURRENT_PRICE_RE, text, default="")
    current_price = float(current_price_raw) if current_price_raw else order.current_price

    if event_kind == "status":
        exception_type_raw = _extract(_CLAIMPILOT_EXCEPTION_RE, text, default="price_drop").strip().lower()
        return {
            "kind": "status",
            "order": order,
            "exception_type": exception_type_raw,
            "evidence_quality": evidence_quality,
            "current_price": current_price,
        }

    return {"kind": "order", "order": order}


def ingest_mailbox_messages(
    messages: Iterable[MailMessage],
    bus: EventBus,
    processed_events: ProcessedEventStore,
) -> list[str]:
    emitted: list[str] = []
    for message in messages:
        event_key = f"mail:{message.user_id}:{message.message_id}"
        if not processed_events.mark_if_new(event_key):
            continue

        parsed = parse_claimpilot_event(message)
        kind = str(parsed.get("kind", "order"))
        order = parsed["order"]
        if not isinstance(order, Order):
            continue

        if kind == "status":
            bus.publish(
                Event(
                    topic="StatusChanged",
                    payload={
                        "order_id": order.order_id,
                        "exception_type": str(parsed.get("exception_type", "price_drop")),
                        "evidence_quality": str(parsed.get("evidence_quality", "strong")),
                        "current_price": parsed.get("current_price", order.current_price),
                        "source_message_id": message.message_id,
                    },
                )
            )
        else:
            bus.publish(
                Event(
                    topic="OrderDetected",
                    payload={"order": order, "source_message_id": message.message_id},
                )
            )
        emitted.append(order.order_id)
    return emitted
