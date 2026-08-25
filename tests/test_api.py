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
