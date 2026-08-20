from datetime import datetime, timedelta, timezone

from claimpilot.models import Order, TrackingStatus, TrackingUpdate
from claimpilot.pipeline import EventBus
from claimpilot.store import OrderStore, ProcessedEventStore, TrackingStateStore
from claimpilot.tracking import poll_tracking_updates


class StubTracker:
    def __init__(self, updates_by_tracking: dict[str, list[TrackingUpdate]]) -> None:
        self._updates_by_tracking = updates_by_tracking

    def fetch_status(self, order_id: str, tracking_number: str) -> TrackingUpdate | None:
        updates = self._updates_by_tracking.get(tracking_number, [])
        if not updates:
            return None
        return updates.pop(0)


def test_poll_tracking_emits_status_changed_for_overdue_in_transit():
    now = datetime(2026, 8, 20, 12, 0, 0, tzinfo=timezone.utc)
    order = Order(
        order_id="ord-track-1",
        user_id="user-1",
        item_name="Keyboard",
        purchase_price=90.0,
        current_price=90.0,
        purchased_at=now - timedelta(days=7),
        return_window_days=30,
        expected_delivery_at=now - timedelta(days=2),
        carrier="USPS",
        tracking_number="TRK-1",
    )

    update = TrackingUpdate(
        order_id=order.order_id,
        status=TrackingStatus.IN_TRANSIT,
        raw_status="IN_TRANSIT",
        event_time=now,
    )

    order_store = OrderStore()
    order_store.upsert(order)
    state_store = TrackingStateStore()
    dedupe = ProcessedEventStore()
    bus = EventBus()
    tracker = StubTracker({"TRK-1": [update]})

    emitted = poll_tracking_updates(order_store, tracker, state_store, dedupe, bus, now=now)

    assert emitted == ["ord-track-1"]
    status_events = [e for e in bus.published if e.topic == "StatusChanged"]
    assert len(status_events) == 1
    assert status_events[0].payload["exception_type"] == "delayed"


def test_poll_tracking_skips_duplicate_fingerprint_updates():
    now = datetime(2026, 8, 20, 12, 0, 0, tzinfo=timezone.utc)
    order = Order(
        order_id="ord-track-2",
        user_id="user-2",
        item_name="Mouse",
        purchase_price=30.0,
        current_price=30.0,
        purchased_at=now - timedelta(days=5),
        return_window_days=30,
        expected_delivery_at=now - timedelta(days=2),
        carrier="USPS",
        tracking_number="TRK-2",
    )

    same_update_1 = TrackingUpdate(
        order_id=order.order_id,
        status=TrackingStatus.IN_TRANSIT,
        raw_status="IN_TRANSIT",
        event_time=now,
    )
    same_update_2 = TrackingUpdate(
        order_id=order.order_id,
        status=TrackingStatus.IN_TRANSIT,
        raw_status="IN_TRANSIT",
        event_time=now,
    )

    order_store = OrderStore()
    order_store.upsert(order)
    state_store = TrackingStateStore()
    dedupe = ProcessedEventStore()
    bus = EventBus()
    tracker = StubTracker({"TRK-2": [same_update_1, same_update_2]})

    first = poll_tracking_updates(order_store, tracker, state_store, dedupe, bus, now=now)
    second = poll_tracking_updates(order_store, tracker, state_store, dedupe, bus, now=now)

    assert first == ["ord-track-2"]
    assert second == []
    status_events = [e for e in bus.published if e.topic == "StatusChanged"]
    assert len(status_events) == 1
