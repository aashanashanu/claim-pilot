from datetime import datetime, timedelta, timezone

from claimpilot.decision_table import classify_exception
from claimpilot.models import ActionType, ExceptionType, Order


def make_order(**overrides):
    now = datetime.now(timezone.utc)
    base = dict(
        order_id="ord-1",
        user_id="user-1",
        item_name="Item",
        purchase_price=50.0,
        current_price=40.0,
        purchased_at=now - timedelta(days=2),
        return_window_days=30,
        expected_delivery_at=now - timedelta(days=1),
        delivered_at=None,
    )
    base.update(overrides)
    return Order(**base)


def test_price_drop_auto_resolve():
    order = make_order()
    decision = classify_exception(order, ExceptionType.PRICE_DROP)
    assert decision.action is ActionType.AUTO_RESOLVE
    assert decision.metadata["refund_amount"] == "10.00"


def test_damaged_item_needs_decision():
    order = make_order()
    decision = classify_exception(order, ExceptionType.DAMAGED_ITEM)
    assert decision.action is ActionType.NEEDS_DECISION


def test_delivered_not_received_high_value_requires_decision():
    order = make_order(purchase_price=180.0)
    decision = classify_exception(order, ExceptionType.DELIVERED_NOT_RECEIVED)
    assert decision.action is ActionType.NEEDS_DECISION


def test_delayed_short_delay_auto_resolve():
    now = datetime.now(timezone.utc)
    order = make_order(expected_delivery_at=now - timedelta(days=1))
    decision = classify_exception(order, ExceptionType.DELAYED, now=now)
    assert decision.action is ActionType.AUTO_RESOLVE


def test_return_window_closing_needs_decision():
    now = datetime.now(timezone.utc)
    order = make_order(purchased_at=now - timedelta(days=30), return_window_days=30)
    decision = classify_exception(order, ExceptionType.RETURN_WINDOW_CLOSING, now=now)
    assert decision.action is ActionType.NEEDS_DECISION
