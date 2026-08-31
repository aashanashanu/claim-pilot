import pytest
from fastapi import HTTPException

from claimpilot import api


class _OkService:
    def snapshot(self) -> dict[str, object]:
        return {"active_orders": 0}

    def trigger_scenario(self, scenario: str) -> dict[str, object]:
        return {"scenario": scenario, "action": "needs_decision"}

    def ingest_gmail_messages(self, user_id: str = "user-demo", max_results: int = 3) -> dict[str, object]:
        return {
            "source": "gmail",
            "requested": max_results,
            "ingested": max_results,
            "order_ids": [f"ORD-{user_id}-{idx}" for idx in range(max_results)],
        }

    def poll_tracking(self) -> dict[str, object]:
        return {
            "source": "carrier",
            "status_changed_count": 1,
            "order_ids": ["ORD-user-demo-0"],
            "dead_letters": [],
        }

    def gmail_readiness(self) -> dict[str, object]:
        return {
            "status": "ok",
            "code": "GMAIL_READY",
            "message": "Gmail integration is configured and token is valid.",
        }

    def storefront_snapshot(self) -> dict[str, object]:
        return {
            "recipient_email": "demo@example.com",
            "catalog": [],
            "orders": [],
            "activities": [],
            "pending_decision_items": [
                {
                    "order_id": "ORD-1",
                    "user_id": "user-demo",
                    "status": "pending_user",
                    "details": "Need photo evidence from user.",
                    "metadata": {},
                    "created_at": "2026-08-25T00:00:00+00:00",
                }
            ],
        }

    def seed_storefront_demo(self) -> dict[str, object]:
        return {"status": "seeded", "orders_created": ["SF-0001"], "storefront": self.storefront_snapshot()}

    def purchase_product(self, product_id: str, recipient_email: str | None = None) -> dict[str, object]:
        return {"order_id": f"SF-{product_id}", "product_id": product_id, "item_name": product_id, "status": "order"}

    def price_drop(self, order_id: str, new_price: float) -> dict[str, object]:
        return {"order_id": order_id, "product_id": "monitor", "item_name": "monitor", "status": "price_drop"}

    def start_return(self, order_id: str) -> dict[str, object]:
        return {"order_id": order_id, "product_id": "backpack", "item_name": "backpack", "status": "return"}

    def file_claim(self, order_id: str, claim_type: str = "damaged_item") -> dict[str, object]:
        return {"order_id": order_id, "product_id": "desk-lamp", "item_name": "desk-lamp", "status": "claim"}

    def capture_decision(self, order_id: str, decision: str, reason: str | None = None) -> dict[str, object]:
        return {"order_id": order_id, "decision": decision, "reason": reason, "status": "approved"}


class _FailService:
    def __init__(self) -> None:
        raise RuntimeError("Missing AWS credentials for Strands runtime.")


class _FailingGmailAdapter:
    def readiness_status(self) -> dict[str, object]:
        return {
            "status": "error",
            "code": "GMAIL_DEPENDENCIES_MISSING",
            "message": "Google API dependencies are missing.",
        }


def test_health_reports_strands_not_configured_when_startup_init_fails(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(api, "DemoService", _FailService)

    api._initialize_service()
    payload = api.health()

    assert payload["status"] == "error"
    assert payload["configured"] is False
    assert payload["code"] == "STRANDS_NOT_CONFIGURED"
    assert "Missing AWS credentials" in str(payload["message"])


def test_demo_endpoints_return_503_when_strands_not_configured(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(api, "DemoService", _FailService)

    api._initialize_service()

    with pytest.raises(HTTPException) as exc:
        api.get_demo()

    assert exc.value.status_code == 503
    assert exc.value.detail["code"] == "STRANDS_NOT_CONFIGURED"


def test_health_and_demo_endpoints_work_when_service_initializes(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(api, "DemoService", _OkService)

    api._initialize_service()

    payload = api.health()
    assert payload["status"] == "ok"
    assert payload["configured"] is True

    snapshot = api.get_demo()
    assert snapshot["active_orders"] == 0

    scenario = api.trigger_scenario("damaged_item")
    assert scenario["scenario"] == "damaged_item"


def test_integration_endpoints_work_when_service_is_ready(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(api, "DemoService", _OkService)
    api._initialize_service()

    ingest_result = api.ingest_gmail_messages(user_id="user-int", max_results=2)
    assert ingest_result["source"] == "gmail"
    assert ingest_result["ingested"] == 2

    tracking_result = api.poll_tracking()
    assert tracking_result["source"] == "carrier"
    assert tracking_result["status_changed_count"] == 1


def test_storefront_endpoints_work_when_service_is_ready(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(api, "DemoService", _OkService)
    api._initialize_service()

    storefront = api.storefront_snapshot()
    assert storefront["recipient_email"] == "demo@example.com"

    seeded = api.seed_storefront_demo()
    assert seeded["status"] == "seeded"

    order = api.purchase_product("monitor")
    assert order["order_id"] == "SF-monitor"

    price_drop = api.storefront_price_drop(order_id="SF-monitor", new_price=109.0)
    assert price_drop["status"] == "price_drop"

    returned = api.storefront_return(order_id="SF-monitor")
    assert returned["status"] == "return"

    claim = api.storefront_claim(order_id="SF-monitor", claim_type="damaged_item")
    assert claim["status"] == "claim"


def test_decision_capture_endpoint_work_when_service_is_ready(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(api, "DemoService", _OkService)
    api._initialize_service()

    decision = api.capture_decision(order_id="ORD-1", decision="approve_photo", reason="Looks good.")
    assert decision["order_id"] == "ORD-1"
    assert decision["status"] == "approved"


def test_gmail_health_uses_service_readiness_when_service_is_ready(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(api, "DemoService", _OkService)
    api._initialize_service()

    payload = api.gmail_health()
    assert payload["status"] == "ok"
    assert payload["code"] == "GMAIL_READY"


def test_gmail_health_available_even_when_main_service_failed_startup(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(api, "DemoService", _FailService)
    monkeypatch.setattr(api, "GmailInboxAdapter", _FailingGmailAdapter)
    api._initialize_service()

    payload = api.gmail_health()
    assert payload["status"] == "error"
    assert payload["code"] == "GMAIL_DEPENDENCIES_MISSING"
