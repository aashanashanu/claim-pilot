from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Callable, Protocol

try:
    from strands import Agent
    from strands.models import BedrockModel
except ModuleNotFoundError:  # pragma: no cover - optional dependency for local/dev runs
    Agent = None  # type: ignore[assignment]
    BedrockModel = None  # type: ignore[assignment]

from .config import DEFAULT_CONFIG
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


def _parse_agent_output(raw_result: Any) -> dict[str, Any] | None:
    if isinstance(raw_result, ResolutionDecision):
        return {
            "action": raw_result.action.value,
            "reason": raw_result.reason,
            "metadata": raw_result.metadata,
        }

    if isinstance(raw_result, dict):
        return raw_result

    if hasattr(raw_result, "structured_output") and raw_result.structured_output is not None:
        structured = raw_result.structured_output
        if isinstance(structured, dict):
            return structured
        if hasattr(structured, "model_dump"):
            return structured.model_dump()

    if hasattr(raw_result, "message"):
        text = str(raw_result)
        if text:
            return _parse_agent_output(text)

    if isinstance(raw_result, str):
        cleaned = raw_result.strip()
        if not cleaned:
            return None
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            if cleaned.lower() in {ActionType.AUTO_RESOLVE.value, "auto_resolve"}:
                return {"action": ActionType.AUTO_RESOLVE.value, "reason": "Agent selected auto-resolve."}
            if cleaned.lower() in {ActionType.NEEDS_DECISION.value, "needs_decision"}:
                return {"action": ActionType.NEEDS_DECISION.value, "reason": "Agent selected needs-decision."}
            return None

    return None


CLAIMPILOT_SYSTEM_PROMPT = (
    "You are ClaimPilot, a post-purchase exception decisioning assistant. "
    "Return JSON only with keys: action, reason, metadata. "
    "Allowed actions: auto_resolve or needs_decision. "
    "Prefer auto_resolve only for clearly safe, rule-backed cases; use needs_decision for high-risk, ambiguous, or evidence-dependent cases."
)


def create_default_strands_agent(
    *,
    region_name: str | None = None,
    model_id: str | None = None,
    aws_access_key_id: str | None = None,
    aws_secret_access_key: str | None = None,
    aws_session_token: str | None = None,
    **model_kwargs: Any,
) -> Agent:
    """Create a real Strands + Bedrock agent.

    This function is strict by design and raises when required runtime pieces are missing.
    """
    config = DEFAULT_CONFIG
    aws_access_key_id = aws_access_key_id or config.aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = aws_secret_access_key or config.aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_session_token = aws_session_token or config.aws_session_token or os.getenv("AWS_SESSION_TOKEN")
    region_name = region_name or config.aws_region or config.aws_default_region or os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
    model_id = model_id or config.claimpilot_model_id or os.getenv("CLAIMPILOT_MODEL_ID") or "global.anthropic.claude-sonnet-4-6"

    if Agent is None or BedrockModel is None:
        raise RuntimeError(
            "Strands SDK is not installed. Install 'strands-agents' and required model dependencies."
        )

    if not aws_access_key_id or not aws_secret_access_key:
        raise RuntimeError(
            "Missing AWS credentials for Strands runtime. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY."
        )

    if not region_name:
        region_name = "us-west-2"

    if aws_session_token:
        boto_kwargs = {
            "aws_access_key_id": aws_access_key_id,
            "aws_secret_access_key": aws_secret_access_key,
            "aws_session_token": aws_session_token,
            "region_name": region_name,
        }
    else:
        boto_kwargs = {
            "aws_access_key_id": aws_access_key_id,
            "aws_secret_access_key": aws_secret_access_key,
            "region_name": region_name,
        }

    # Keep a clean local fallback for developer machines and CI by only constructing the
    # real Bedrock model when the necessary AWS credentials are configured.
    model = BedrockModel(model_id=model_id, **boto_kwargs, **model_kwargs)
    return Agent(model=model, system_prompt=CLAIMPILOT_SYSTEM_PROMPT)


class StrandsDecisionEngine:
    """Bridge for real Strands-backed decisions.

    Accepts either a callable returning a decision payload, or a real `strands.Agent`
    instance that can be invoked with a natural-language prompt.
    """

    def __init__(
        self,
        agent_callable: Callable[[dict[str, object]], ResolutionDecision | dict[str, object] | str | Any] | None = None,
        agent: Any | None = None,
        *,
        model: Any | None = None,
    ) -> None:
        self._agent_callable = agent_callable
        self._agent = agent
        self._model = model
        if self._agent is None and self._agent_callable is None and self._model is None:
            raise RuntimeError(
                "StrandsDecisionEngine requires a configured Strands agent, model, or callable."
            )

    def _build_agent_prompt(
        self,
        order: Order,
        exception_type: ExceptionType,
        evidence_quality: str,
        now: datetime | None,
    ) -> str:
        now_value = now.isoformat() if now is not None else datetime.now().isoformat()
        return (
            "You are ClaimPilot decisioning. Return valid JSON only with keys: "
            "action, reason, metadata. "
            f"Order: {order.order_id}, item={order.item_name}, purchase_price={order.purchase_price}, "
            f"current_price={order.current_price}, exception_type={exception_type.value}, "
            f"evidence_quality={evidence_quality}, now={now_value}, "
            f"return_window_days={order.return_window_days}, merchant={order.merchant or 'unknown'}. "
            "Use action values 'auto_resolve' or 'needs_decision'. "
            "Prefer auto_resolve only for safe, low-risk, rule-backed cases."
        )

    def decide(
        self,
        order: Order,
        exception_type: ExceptionType,
        evidence_quality: str = "strong",
        now: datetime | None = None,
    ) -> ResolutionDecision:
        payload = {
            "order": order,
            "exception_type": exception_type.value,
            "evidence_quality": evidence_quality,
            "now": now,
        }

        if self._agent is not None:
            result = self._agent(
                self._build_agent_prompt(order, exception_type, evidence_quality, now),
                structured_output_model=None,
            )
        elif self._model is not None:
            if Agent is None:
                raise RuntimeError("Strands SDK is not installed; cannot build runtime agent from model.")
            agent = Agent(model=self._model, system_prompt=CLAIMPILOT_SYSTEM_PROMPT)
            result = agent(
                self._build_agent_prompt(order, exception_type, evidence_quality, now),
                structured_output_model=None,
            )
        elif self._agent_callable is not None:
            result = self._agent_callable(payload)
        else:
            raise RuntimeError("No active Strands runtime configured.")

        parsed = _parse_agent_output(result)
        if parsed is None:
            raise ValueError("Agent result was empty or malformed.")

        action_raw = str(parsed.get("action", ActionType.NEEDS_DECISION.value))
        action = ActionType(action_raw)
        reason = str(parsed.get("reason", "No reason provided by Strands agent."))
        metadata_raw = parsed.get("metadata", {})
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
