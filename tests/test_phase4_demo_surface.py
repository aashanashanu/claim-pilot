from __future__ import annotations

from datetime import datetime, timezone

from claimpilot.agent_runtime import StrandsDecisionEngine
from claimpilot.demo_service import DemoService
from claimpilot.demo_surface import DemoDashboard
from claimpilot.models import ActionType, ExceptionType, MailMessage, Order, ResolutionDecision


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
        return []

    def readiness_status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "code": "GMAIL_READY",
            "message": "ready",
            "send_ready": True,
            "read_ready": True,
        }


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
            metadata={"decision_source": "strands"},
        )

    return StrandsDecisionEngine(agent_callable=agent_callable)


def test_phase4_demo_runbook_executes_all_three_beats_and_storefront_seed():
    gmail = StubGmailAdapter()
    service = DemoService(
        dashboard=DemoDashboard(decision_engine=_mock_engine()),
        gmail_adapter=gmail,
        gmail_target_email="demo@example.com",
    )

    result = service.run_demo_runbook()

    assert result["status"] == "ok"
    assert result["runbook"] == "phase4_demo_surface"
    assert result["storefront_seed"]["status"] == "seeded"
    assert set(result["beats"].keys()) == {"price_drop", "damaged_item", "return_window"}

    snapshot = result["snapshot"]
    assert snapshot["active_orders"] >= 3
    actions = [item["action"] for item in snapshot["audit_records"]]
    assert "auto_resolve" in actions
    assert "needs_decision" in actions

    # Storefront seed sends four order mails + three status mails.
    assert len(gmail.sent_messages) == 7
