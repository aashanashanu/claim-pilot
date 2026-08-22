from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class ClaimActionAdapter(Protocol):
    def submit_action(self, payload: dict[str, object]) -> tuple[bool, str]:
        ...


class NotificationAdapter(Protocol):
    def send_prompt(self, payload: dict[str, object]) -> tuple[bool, str]:
        ...


class DecisionCaptureAdapter(Protocol):
    def capture(self, payload: dict[str, object]) -> tuple[bool, str]:
        ...


@dataclass(slots=True)
class AutoResolver:
    adapter: ClaimActionAdapter

    def resolve(self, payload: dict[str, object]) -> tuple[str, str]:
        ok, details = self.adapter.submit_action(payload)
        return ("success", details) if ok else ("failed", details)


@dataclass(slots=True)
class DecisionNotifier:
    adapter: NotificationAdapter

    def notify(self, payload: dict[str, object]) -> tuple[str, str]:
        ok, details = self.adapter.send_prompt(payload)
        return ("pending_user", details) if ok else ("failed", details)


@dataclass(slots=True)
class DecisionCapture:
    adapter: DecisionCaptureAdapter

    def capture(self, payload: dict[str, object]) -> tuple[str, str]:
        ok, details = self.adapter.capture(payload)
        decision = str(payload.get("decision", "pending"))
        return ("approved" if ok and decision in {"approve", "approve_photo", "approved"} else "rejected" if ok else "failed", details)


@dataclass(slots=True)
class MockClaimActionAdapter:
    def submit_action(self, payload: dict[str, object]) -> tuple[bool, str]:
        order_id = str(payload.get("order_id", ""))
        exception_type = str(payload.get("exception_type", ""))
        return True, f"Mock claim action submitted for {order_id} ({exception_type})."


@dataclass(slots=True)
class MockNotificationAdapter:
    def send_prompt(self, payload: dict[str, object]) -> tuple[bool, str]:
        order_id = str(payload.get("order_id", ""))
        reason = str(payload.get("reason", ""))
        return True, f"Decision request sent for {order_id}: {reason}"


@dataclass(slots=True)
class MockDecisionCaptureAdapter:
    def capture(self, payload: dict[str, object]) -> tuple[bool, str]:
        order_id = str(payload.get("order_id", ""))
        decision = str(payload.get("decision", "pending"))
        return True, f"Decision captured for {order_id}: {decision}"
