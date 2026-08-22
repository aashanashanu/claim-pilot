from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Protocol

from .models import ExceptionType, TrackingStatus, TrackingUpdate
from .pipeline import Event, EventBus
from .store import DeadLetterStore, OrderStore, ProcessedEventStore, TrackingStateStore


class CarrierTrackingAdapter(Protocol):
    def fetch_status(self, order_id: str, tracking_number: str) -> TrackingUpdate | None:
        ...


def _event_fingerprint(update: TrackingUpdate) -> str:
    delivered = update.delivered_at.isoformat() if update.delivered_at else ""
    expected = update.expected_delivery_at.isoformat() if update.expected_delivery_at else ""
    return (
        f"track:{update.order_id}:{update.status.value}:"
        f"{delivered}:{expected}:{update.raw_status}"
    )


def _infer_exception_type(
    status: TrackingStatus,
    expected_delivery_at: datetime,
    now: datetime,
) -> ExceptionType | None:
    if status is TrackingStatus.EXCEPTION:
        return ExceptionType.DELAYED

    if status is TrackingStatus.IN_TRANSIT:
        if now > expected_delivery_at + timedelta(days=1):
            return ExceptionType.DELAYED

    return None


def poll_tracking_updates(
    order_store: OrderStore,
    tracker: CarrierTrackingAdapter,
    state_store: TrackingStateStore,
    processed_events: ProcessedEventStore,
    bus: EventBus,
    now: datetime | None = None,
    dead_letter_store: DeadLetterStore | None = None,
) -> list[str]:
    now = now or datetime.now(timezone.utc)
    emitted_order_ids: list[str] = []

    for order in order_store.all():
        if not order.tracking_number:
            continue

        try:
            update = tracker.fetch_status(order.order_id, order.tracking_number)
        except Exception as exc:  # retryable carrier issues should never break the event loop
            if dead_letter_store is not None:
                dead_letter_store.add(order.order_id, str(exc), status="retry")
            continue

        if update is None:
            continue

        fingerprint = _event_fingerprint(update)
        if not processed_events.mark_if_new(fingerprint):
            continue

        if not state_store.transition_if_changed(order.order_id, update.status):
            continue

        if update.delivered_at is not None:
            order.delivered_at = update.delivered_at

        if update.expected_delivery_at is not None:
            order.expected_delivery_at = update.expected_delivery_at

        exception_type = _infer_exception_type(update.status, order.expected_delivery_at, now)
        if exception_type is None:
            continue

        bus.publish(
            Event(
                topic="StatusChanged",
                payload={
                    "order_id": order.order_id,
                    "exception_type": exception_type.value,
                    "carrier_status": update.status.value,
                    "raw_status": update.raw_status,
                },
            )
        )
        emitted_order_ids.append(order.order_id)

    return emitted_order_ids
