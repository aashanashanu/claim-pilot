from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from .agent_runtime import DecisionEngine, StrandsDecisionEngine, create_default_strands_agent
from .models import ActionType, AuditRecord, ExceptionType, Order
from .pipeline import Event, EventBus
from .store import AuditStore, OrderStore


class AutoResolutionWorker(Protocol):
    def resolve(self, payload: dict[str, object]) -> tuple[str, str]:
        ...


class DecisionNotificationWorker(Protocol):
    def notify(self, payload: dict[str, object]) -> tuple[str, str]:
        ...


class DecisionCaptureWorker(Protocol):
    def capture(self, payload: dict[str, object]) -> tuple[str, str]:
        ...


def register_handlers(
    bus: EventBus,
    order_store: OrderStore,
    audit_store: AuditStore,
    decision_engine: DecisionEngine | None = None,
    resolution_worker: AutoResolutionWorker | None = None,
    notification_worker: DecisionNotificationWorker | None = None,
    decision_capture_worker: DecisionCaptureWorker | None = None,
) -> None:
    decision_engine = decision_engine or StrandsDecisionEngine(agent=create_default_strands_agent())
    bus.subscribe("OrderDetected", lambda e: handle_order_detected(e, order_store, audit_store))
    bus.subscribe(
        "StatusChanged",
        lambda e: handle_status_changed(e, bus, order_store, audit_store, decision_engine),
    )
    bus.subscribe(
        "AutoResolve",
        lambda e: handle_auto_resolve(e, audit_store, resolution_worker),
    )
    bus.subscribe(
        "NeedsDecision",
        lambda e: handle_needs_decision(e, audit_store, notification_worker),
    )
    bus.subscribe(
        "DecisionCaptured",
        lambda e: handle_decision_captured(e, audit_store, decision_capture_worker),
    )


def handle_order_detected(event: Event, order_store: OrderStore, audit_store: AuditStore) -> None:
    order = event.payload["order"]
    if not isinstance(order, Order):
        raise TypeError("OrderDetected payload must include an Order instance")

    order_store.upsert(order)
    audit_store.add(
        AuditRecord(
            order_id=order.order_id,
            user_id=order.user_id,
            action="order_detected",
            status="success",
            details="Order saved to store.",
        )
    )


def handle_status_changed(
    event: Event,
    bus: EventBus,
    order_store: OrderStore,
    audit_store: AuditStore,
    decision_engine: DecisionEngine,
) -> None:
    order_id = str(event.payload["order_id"])
    exception_type_raw = str(event.payload["exception_type"])
    evidence_quality = str(event.payload.get("evidence_quality", "strong"))

    order = order_store.get(order_id)
    exception_type = ExceptionType(exception_type_raw)
    decision = decision_engine.decide(
        order=order,
        exception_type=exception_type,
        evidence_quality=evidence_quality,
        now=datetime.now(timezone.utc),
    )
    decision_source = decision.metadata.get("decision_source", "unknown")

    topic = "AutoResolve" if decision.action is ActionType.AUTO_RESOLVE else "NeedsDecision"
    bus.publish(
        Event(
            topic=topic,
            payload={
                "order_id": order_id,
                "user_id": order.user_id,
                "exception_type": decision.exception_type.value,
                "reason": decision.reason,
                "metadata": decision.metadata,
            },
        )
    )

    audit_store.add(
        AuditRecord(
            order_id=order.order_id,
            user_id=order.user_id,
            action="exception_classified",
            status="success",
            details=f"{decision.exception_type.value} -> {decision.action.value} [{decision_source}] {decision.reason}",
            metadata=decision.metadata,
        )
    )


def handle_auto_resolve(
    event: Event,
    audit_store: AuditStore,
    resolution_worker: AutoResolutionWorker | None = None,
) -> None:
    status = "success"
    details = str(event.payload["reason"])
    if resolution_worker is not None:
        status, details = resolution_worker.resolve(event.payload)

    audit_store.add(
        AuditRecord(
            order_id=str(event.payload["order_id"]),
            user_id=str(event.payload["user_id"]),
            action="auto_resolve",
            status=status,
            details=details,
            metadata={str(k): str(v) for k, v in dict(event.payload.get("metadata", {})).items()},
        )
    )


def handle_needs_decision(
    event: Event,
    audit_store: AuditStore,
    notification_worker: DecisionNotificationWorker | None = None,
) -> None:
    status = "pending_user"
    details = str(event.payload["reason"])
    if notification_worker is not None:
        status, details = notification_worker.notify(event.payload)

    audit_store.add(
        AuditRecord(
            order_id=str(event.payload["order_id"]),
            user_id=str(event.payload["user_id"]),
            action="needs_decision",
            status=status,
            details=details,
            metadata={str(k): str(v) for k, v in dict(event.payload.get("metadata", {})).items()},
        )
    )


def handle_decision_captured(
    event: Event,
    audit_store: AuditStore,
    decision_capture_worker: DecisionCaptureWorker | None = None,
) -> None:
    decision = str(event.payload.get("decision", "pending")).strip().lower()
    if decision in {"approve", "approve_photo", "approved"}:
        status = "approved"
    elif decision in {"reject", "rejected", "deny", "denied"}:
        status = "rejected"
    else:
        status = "failed"

    details = str(event.payload.get("reason", "Decision captured."))
    if decision_capture_worker is not None:
        status, details = decision_capture_worker.capture(event.payload)

    audit_store.add(
        AuditRecord(
            order_id=str(event.payload["order_id"]),
            user_id=str(event.payload["user_id"]),
            action="decision_captured",
            status=status,
            details=details,
            metadata={str(k): str(v) for k, v in dict(event.payload.get("metadata", {})).items()},
        )
    )
