from __future__ import annotations

from dataclasses import asdict

from .models import AuditRecord, Order, TrackingStatus


class OrderStore:
    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}

    def upsert(self, order: Order) -> None:
        self._orders[order.order_id] = order

    def get(self, order_id: str) -> Order:
        return self._orders[order_id]

    def all(self) -> list[Order]:
        return list(self._orders.values())


class AuditStore:
    def __init__(self) -> None:
        self._records: list[AuditRecord] = []

    def add(self, record: AuditRecord) -> None:
        self._records.append(record)

    def all(self) -> list[AuditRecord]:
        return list(self._records)

    def as_dicts(self) -> list[dict[str, str]]:
        return [asdict(item) for item in self._records]


class ProcessedEventStore:
    def __init__(self) -> None:
        self._keys: set[str] = set()

    def mark_if_new(self, key: str) -> bool:
        if key in self._keys:
            return False
        self._keys.add(key)
        return True


class TrackingStateStore:
    def __init__(self) -> None:
        self._states: dict[str, TrackingStatus] = {}

    def last_status(self, order_id: str) -> TrackingStatus:
        return self._states.get(order_id, TrackingStatus.UNKNOWN)

    def transition_if_changed(self, order_id: str, new_status: TrackingStatus) -> bool:
        old = self._states.get(order_id)
        if old == new_status:
            return False
        self._states[order_id] = new_status
        return True
