from datetime import datetime, timedelta, timezone

from claimpilot.agent_runtime import StrandsDecisionEngine
from claimpilot.demo_service import DemoService
from claimpilot.demo_surface import DemoDashboard
from claimpilot.models import ActionType, ExceptionType, MailMessage, Order, ResolutionDecision, TrackingStatus, TrackingUpdate


def _mock_engine() -> StrandsDecisionEngine:
    def agent_callable(payload: dict[str, object]) -> ResolutionDecision:
        order = payload["order"]
        assert isinstance(order, Order)
        exception_type = ExceptionType(str(payload["exception_type"]))
        if exception_type is ExceptionType.DELAYED:
            return ResolutionDecision(
                order_id=order.order_id,
                exception_type=exception_type,
                action=ActionType.NEEDS_DECISION,
                reason="Mock Strands escalation for delayed shipment.",
            )

        return ResolutionDecision(
            order_id=order.order_id,
            exception_type=exception_type,
            action=ActionType.AUTO_RESOLVE,
            reason="Mock Strands auto decision.",
        )

    return StrandsDecisionEngine(agent_callable=agent_callable)


class StubGmailAdapter:
    def fetch_messages(self, user_id: str, max_results: int = 5) -> list[MailMessage]:
        now = datetime.now(timezone.utc)
        messages: list[MailMessage] = []
        for idx in range(max_results):
            messages.append(
                MailMessage(
                    message_id=f"gmail-{user_id}-{idx}",
                    user_id=user_id,
                    subject=f"Order #ORD-{idx}",
                    body=(
                        "Item: Integration Item\n"
                        "Price: $19.99\n"
                        "Merchant: Integration Store\n"
                        "Carrier: USPS\n"
                        f"Tracking: TRK-{idx}\n"
                        f"Expected Delivery: {(now - timedelta(days=2)).isoformat()}"
                    ),
                    received_at=now,
                )
            )
        return messages


class StubCarrierAdapter:
    def fetch_status(self, order_id: str, tracking_number: str) -> TrackingUpdate | None:
        return TrackingUpdate(
            order_id=order_id,
            status=TrackingStatus.IN_TRANSIT,
            raw_status="IN_TRANSIT",
            event_time=datetime.now(timezone.utc),
        )


class FailingCarrierAdapter:
    def fetch_status(self, order_id: str, tracking_number: str):
        raise RuntimeError(f"carrier outage for {order_id}")


def test_mock_gmail_ingest_emits_orders_and_events():
    service = DemoService(
        dashboard=DemoDashboard(decision_engine=_mock_engine()),
        gmail_adapter=StubGmailAdapter(),
    )

    result = service.ingest_gmail_messages(user_id="user-int", max_results=2)

    assert result["source"] == "gmail"
    assert result["requested"] == 2
    assert result["ingested"] == 2
    assert len(result["order_ids"]) == 2

    snapshot = service.snapshot()
    assert snapshot["active_orders"] >= 2
    assert any(record["action"] == "order_detected" for record in snapshot["audit_records"])


def test_automatic_gmail_poll_path_ingests_messages_without_manual_endpoint():
    service = DemoService(
        dashboard=DemoDashboard(decision_engine=_mock_engine()),
        gmail_adapter=StubGmailAdapter(),
    )

    result = service.poll_gmail_inbox(user_id="user-int", max_results=1)

    assert result["watch_mode"] == "background"
    assert result["ingested"] == 1
    snapshot = service.snapshot()
    assert snapshot["active_orders"] >= 1


def test_mock_tracking_poll_emits_status_changed_and_decision_flow():
    service = DemoService(
        dashboard=DemoDashboard(decision_engine=_mock_engine()),
        gmail_adapter=StubGmailAdapter(),
        carrier_adapter=StubCarrierAdapter(),
    )
    service.ingest_gmail_messages(user_id="user-int", max_results=2)

    result = service.poll_tracking()

    assert result["source"] == "carrier"
    assert result["status_changed_count"] >= 1
    assert len(result["order_ids"]) == result["status_changed_count"]

    snapshot = service.snapshot()
    actions = [item["action"] for item in snapshot["audit_records"]]
    assert "exception_classified" in actions
    assert "needs_decision" in actions


def test_tracking_poll_records_dead_letters_for_retryable_carrier_failures():
    service = DemoService(
        dashboard=DemoDashboard(decision_engine=_mock_engine()),
        gmail_adapter=StubGmailAdapter(),
        carrier_adapter=FailingCarrierAdapter(),
    )
    service.ingest_gmail_messages(user_id="user-int", max_results=1)

    result = service.poll_tracking()

    assert result["status_changed_count"] == 0
    assert result["dead_letters"]
    assert result["dead_letters"][0]["status"] == "retry"
