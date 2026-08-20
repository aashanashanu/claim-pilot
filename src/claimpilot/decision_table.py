from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .models import ActionType, ExceptionType, Order, ResolutionDecision

HIGH_VALUE_THRESHOLD = 100.0
DELAY_ESCALATION_DAYS = 3
RETURN_WINDOW_URGENT_DAYS = 1


def _days_since(date_value: datetime, now: datetime) -> int:
    return max((now - date_value).days, 0)


def _days_until(date_value: datetime, now: datetime) -> int:
    return (date_value - now).days


def classify_exception(
    order: Order,
    exception_type: ExceptionType,
    now: datetime | None = None,
    evidence_quality: str = "strong",
) -> ResolutionDecision:
    now = now or datetime.now(timezone.utc)

    if exception_type is ExceptionType.PRICE_DROP:
        within_window = _days_since(order.purchased_at, now) <= order.return_window_days
        if within_window and order.current_price < order.purchase_price:
            delta = order.purchase_price - order.current_price
            return ResolutionDecision(
                order_id=order.order_id,
                exception_type=exception_type,
                action=ActionType.AUTO_RESOLVE,
                reason="Price dropped within adjustment window.",
                metadata={"refund_amount": f"{delta:.2f}"},
            )
        return ResolutionDecision(
            order_id=order.order_id,
            exception_type=exception_type,
            action=ActionType.NEEDS_DECISION,
            reason="Price drop is outside adjustment window or invalid.",
        )

    if exception_type is ExceptionType.DELAYED:
        delay_days = _days_since(order.expected_delivery_at, now)
        if delay_days <= DELAY_ESCALATION_DAYS:
            return ResolutionDecision(
                order_id=order.order_id,
                exception_type=exception_type,
                action=ActionType.AUTO_RESOLVE,
                reason="Delay under escalation threshold; filing trace automatically.",
            )
        return ResolutionDecision(
            order_id=order.order_id,
            exception_type=exception_type,
            action=ActionType.NEEDS_DECISION,
            reason="Delay exceeds threshold and may need user choice.",
        )

    if exception_type is ExceptionType.DELIVERED_NOT_RECEIVED:
        high_value = order.purchase_price >= HIGH_VALUE_THRESHOLD
        weak_evidence = evidence_quality != "strong"
        if high_value or weak_evidence:
            return ResolutionDecision(
                order_id=order.order_id,
                exception_type=exception_type,
                action=ActionType.NEEDS_DECISION,
                reason="High value or weak evidence requires user confirmation.",
            )
        return ResolutionDecision(
            order_id=order.order_id,
            exception_type=exception_type,
            action=ActionType.AUTO_RESOLVE,
            reason="Low-value claim with strong evidence can be auto-filed.",
        )

    if exception_type is ExceptionType.DAMAGED_ITEM:
        return ResolutionDecision(
            order_id=order.order_id,
            exception_type=exception_type,
            action=ActionType.NEEDS_DECISION,
            reason="Photo evidence required from user.",
        )

    if exception_type is ExceptionType.RETURN_WINDOW_CLOSING:
        return_deadline = (
            order.purchased_at + timedelta(days=order.return_window_days)
        ).replace(hour=23, minute=59, second=59, microsecond=0)
        days_left = _days_until(return_deadline, now)
        if days_left <= RETURN_WINDOW_URGENT_DAYS:
            return ResolutionDecision(
                order_id=order.order_id,
                exception_type=exception_type,
                action=ActionType.NEEDS_DECISION,
                reason="Return window is closing and needs user judgment.",
            )
        return ResolutionDecision(
            order_id=order.order_id,
            exception_type=exception_type,
            action=ActionType.AUTO_RESOLVE,
            reason="Return window not urgent yet; queueing reminder.",
        )

    return ResolutionDecision(
        order_id=order.order_id,
        exception_type=exception_type,
        action=ActionType.NEEDS_DECISION,
        reason="Unknown exception type.",
    )
