from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Protocol

from .decision_table import classify_exception
from .models import ActionType, ExceptionType, Order, ResolutionDecision


class DecisionEngine(Protocol):
    def decide(
        self,
        order: Order,
        exception_type: ExceptionType,
        evidence_quality: str = "strong",
        now: datetime | None = None,
    ) -> ResolutionDecision:
        ...


@dataclass(slots=True)
class RulesDecisionEngine:
    def decide(
        self,
        order: Order,
        exception_type: ExceptionType,
        evidence_quality: str = "strong",
        now: datetime | None = None,
    ) -> ResolutionDecision:
        return classify_exception(
            order=order,
            exception_type=exception_type,
            evidence_quality=evidence_quality,
            now=now,
        )


class StrandsDecisionEngine:
    """Bridge for Strands-backed decisions with safe rule fallback.

    agent_callable should return either a ResolutionDecision or a dict with keys:
    action, reason, and optional metadata.
    """

    def __init__(
        self,
        agent_callable: Callable[[dict[str, object]], ResolutionDecision | dict[str, object]] | None = None,
        fallback: DecisionEngine | None = None,
    ) -> None:
        self._agent_callable = agent_callable
        self._fallback = fallback or RulesDecisionEngine()

    def decide(
        self,
        order: Order,
        exception_type: ExceptionType,
        evidence_quality: str = "strong",
        now: datetime | None = None,
    ) -> ResolutionDecision:
        if self._agent_callable is None:
            decision = self._fallback.decide(order, exception_type, evidence_quality, now)
            decision.metadata.setdefault("decision_source", "rules_fallback")
            return decision

        payload = {
            "order": order,
            "exception_type": exception_type.value,
            "evidence_quality": evidence_quality,
            "now": now,
        }
        result = self._agent_callable(payload)
        if isinstance(result, ResolutionDecision):
            result.metadata.setdefault("decision_source", "strands")
            return result

        action_raw = str(result.get("action", ActionType.NEEDS_DECISION.value))
        action = ActionType(action_raw)
        reason = str(result.get("reason", "No reason provided by Strands agent."))
        metadata_raw = result.get("metadata", {})
        metadata: dict[str, str] = {}
        if isinstance(metadata_raw, dict):
            metadata = {str(k): str(v) for k, v in metadata_raw.items()}
        metadata.setdefault("decision_source", "strands")

        return ResolutionDecision(
            order_id=order.order_id,
            exception_type=exception_type,
            action=action,
            reason=reason,
            metadata=metadata,
        )
