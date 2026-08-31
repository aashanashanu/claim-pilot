from datetime import datetime, timezone

from claimpilot.ingestion import ingest_mailbox_messages, parse_order_email
from claimpilot.models import MailMessage
from claimpilot.pipeline import EventBus
from claimpilot.store import ProcessedEventStore


def test_parse_order_email_extracts_normalized_fields():
    message = MailMessage(
        message_id="msg-1",
        user_id="user-1",
        subject="Order #ORD-900 confirmed",
        body=(
            "Item: Coffee Grinder\n"
            "Price: $79.99\n"
            "Merchant: BrewStore\n"
            "Carrier: USPS\n"
            "Tracking: TRACK123\n"
            "Expected Delivery: 2026-08-22T10:00:00"
        ),
        received_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=timezone.utc),
    )

    order = parse_order_email(message)
    assert order.order_id == "ORD-900"
    assert order.item_name == "Coffee Grinder"
    assert order.purchase_price == 79.99
    assert order.current_price == 79.99
    assert order.merchant == "BrewStore"
    assert order.carrier == "USPS"
    assert order.tracking_number == "TRACK123"


def test_ingest_mailbox_messages_dedupes_by_message_id():
    message = MailMessage(
        message_id="dup-1",
        user_id="user-2",
        subject="Order #ORD-1",
        body="Item: Cable\nPrice: $10.00",
        received_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=timezone.utc),
    )

    bus = EventBus()
    dedupe = ProcessedEventStore()

    emitted_first = ingest_mailbox_messages([message], bus, dedupe)
    emitted_second = ingest_mailbox_messages([message], bus, dedupe)

    assert emitted_first == ["ORD-1"]
    assert emitted_second == []
    order_detected_events = [e for e in bus.published if e.topic == "OrderDetected"]
    assert len(order_detected_events) == 1


def test_ingest_mailbox_messages_adds_correlation_id_to_emitted_events():
    message = MailMessage(
        message_id="corr-1",
        user_id="user-corr",
        subject="Order #ORD-C1",
        body="Item: Cable\nPrice: $10.00",
        received_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=timezone.utc),
    )

    bus = EventBus()
    dedupe = ProcessedEventStore()

    emitted = ingest_mailbox_messages([message], bus, dedupe)

    assert emitted == ["ORD-C1"]
    order_detected_event = [e for e in bus.published if e.topic == "OrderDetected"][0]
    assert order_detected_event.payload["correlation_id"] == "mail:user-corr:corr-1"
