from datetime import datetime, timezone

from claimpilot.agent_runtime import StrandsDecisionEngine
from claimpilot.demo_service import DemoService
from claimpilot.demo_surface import DemoDashboard
from claimpilot.ingestion import ingest_mailbox_messages, parse_claimpilot_event
from claimpilot.models import ActionType, ExceptionType, MailMessage, Order, ResolutionDecision
from claimpilot.pipeline import EventBus
from claimpilot.store import ProcessedEventStore


class StubGmailAdapter:
    def __init__(self) -> None:
        self.sent_messages: list[dict[str, str]] = []

    def send_message(self, recipient_email: str, subject: str, body: str) -> str:
        message_id = f"msg-{len(self.sent_messages) + 1}"
        self.sent_messages.append(
            {
                "recipient_email": recipient_email,
                "subject": subject,
                "body": body,
                "message_id": message_id,
            }
        )
        return message_id

    def fetch_messages(self, user_id: str, max_results: int = 5) -> list[MailMessage]:
        messages: list[MailMessage] = []
        for sent in self.sent_messages[:max_results]:
            messages.append(
                MailMessage(
                    message_id=sent["message_id"],
                    user_id=user_id,
                    subject=sent["subject"],
                    body=sent["body"],
                    received_at=datetime.now(timezone.utc),
                )
            )
        return messages

    def readiness_status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "code": "GMAIL_READY",
            "message": "ready",
            "send_ready": True,
            "read_ready": True,
        }


class StubCarrierAdapter:
    def fetch_status(self, order_id: str, tracking_number: str):
        return None


def _mock_engine() -> StrandsDecisionEngine:
    def agent_callable(payload: dict[str, object]) -> ResolutionDecision:
        order = payload["order"]
        assert isinstance(order, Order)
        exception_type = ExceptionType(str(payload["exception_type"]))
        action = ActionType.AUTO_RESOLVE if exception_type is ExceptionType.PRICE_DROP else ActionType.NEEDS_DECISION
        return ResolutionDecision(
            order_id=order.order_id,
            exception_type=exception_type,
            action=action,
            reason="Mock Strands decision.",
        )

    return StrandsDecisionEngine(agent_callable=agent_callable)


def test_storefront_seed_demo_sends_real_order_emails_and_tracks_state():
    gmail = StubGmailAdapter()
    service = DemoService(
        dashboard=DemoDashboard(decision_engine=_mock_engine()),
        gmail_adapter=gmail,
        carrier_adapter=StubCarrierAdapter(),
        gmail_target_email="demo@example.com",
    )

    result = service.seed_storefront_demo()

    assert result["status"] == "seeded"
    assert len(gmail.sent_messages) == 7
    storefront = service.storefront_snapshot()
    assert len(storefront["orders"]) == 4
    assert len(storefront["activities"]) >= 4
    assert storefront["recipient_email"] == "demo@example.com"


def test_storefront_emails_ingest_into_claimpilot_pipeline():
    gmail = StubGmailAdapter()
    service = DemoService(
        dashboard=DemoDashboard(decision_engine=_mock_engine()),
        gmail_adapter=gmail,
        carrier_adapter=StubCarrierAdapter(),
        gmail_target_email="demo@example.com",
    )

    order_result = service.purchase_product("monitor")
    assert order_result["status"] == "order"

    service.price_drop(order_result["order_id"], new_price=199.0)
    service.start_return(order_result["order_id"])
    service.file_claim(order_result["order_id"], claim_type="damaged_item")

    inbox_messages = service.gmail_adapter.fetch_messages(user_id="user-demo", max_results=10)
    parsed = [parse_claimpilot_event(message) for message in inbox_messages]
    assert any(item["kind"] == "order" for item in parsed)
    assert any(item["kind"] == "status" for item in parsed)

    bus = EventBus()
    processed = ProcessedEventStore()
    emitted = ingest_mailbox_messages(inbox_messages, bus, processed)
    assert emitted
    assert any(event.topic == "OrderDetected" for event in bus.published)
    assert any(event.topic == "StatusChanged" for event in bus.published)
