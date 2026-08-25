from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class ExceptionType(str, Enum):
    PRICE_DROP = "price_drop"
    DELAYED = "delayed"
    DELIVERED_NOT_RECEIVED = "delivered_not_received"
    DAMAGED_ITEM = "damaged_item"
    RETURN_WINDOW_CLOSING = "return_window_closing"


class ActionType(str, Enum):
    AUTO_RESOLVE = "auto_resolve"
    NEEDS_DECISION = "needs_decision"


class TrackingStatus(str, Enum):
    UNKNOWN = "unknown"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    EXCEPTION = "exception"


@dataclass(slots=True)
class Order:
    order_id: str
    user_id: str
    item_name: str
    purchase_price: float
    current_price: float
    purchased_at: datetime
    return_window_days: int
    expected_delivery_at: datetime
    merchant: str = ""
    carrier: str = ""
    tracking_number: str = ""
    delivered_at: datetime | None = None


@dataclass(slots=True)
class MailMessage:
    message_id: str
    user_id: str
    subject: str
    body: str
    received_at: datetime


@dataclass(slots=True)
class TrackingUpdate:
    order_id: str
    status: TrackingStatus
    expected_delivery_at: datetime | None = None
    delivered_at: datetime | None = None
    event_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    raw_status: str = ""


@dataclass(slots=True)
class ResolutionDecision:
    order_id: str
    exception_type: ExceptionType
    action: ActionType
    reason: str
    metadata: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class AuditRecord:
    order_id: str
    user_id: str
    action: str
    status: str
    details: str
    metadata: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
