from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .demo_service import DemoService
from .integrations import GmailInboxAdapter

app = FastAPI(title="ClaimPilot Demo API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.service = None
app.state.startup_error = "Service not initialized."


def _initialize_service() -> None:
    try:
        app.state.service = DemoService()
        app.state.startup_error = None
    except Exception as exc:
        app.state.service = None
        app.state.startup_error = f"Strands not configured: {exc}"


@app.on_event("startup")
def startup_event() -> None:
    _initialize_service()


def _require_service() -> DemoService:
    service = app.state.service
    if service is None:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "code": "STRANDS_NOT_CONFIGURED",
                "message": app.state.startup_error,
            },
        )
    return service


@app.get("/health")
def health() -> dict[str, str | bool | None]:
    if app.state.service is None:
        return {
            "status": "error",
            "configured": False,
            "code": "STRANDS_NOT_CONFIGURED",
            "message": str(app.state.startup_error),
        }

    return {
        "status": "ok",
        "configured": True,
        "code": "READY",
        "message": "Strands runtime configured.",
    }


@app.get("/demo")
def get_demo() -> dict[str, object]:
    service = _require_service()
    return service.snapshot()


@app.post("/demo/scenario/{scenario}")
def trigger_scenario(scenario: str) -> dict[str, object]:
    service = _require_service()
    return service.trigger_scenario(scenario)


@app.post("/integrations/email/gmail/ingest")
def ingest_gmail_messages(user_id: str = "user-demo", max_results: int = 3) -> dict[str, object]:
    service = _require_service()
    return service.ingest_gmail_messages(user_id=user_id, max_results=max_results)


@app.get("/health/gmail")
def gmail_health() -> dict[str, object]:
    # Keep this endpoint available even when the main service failed startup,
    # so deployment diagnostics can inspect Gmail configuration independently.
    if app.state.service is not None:
        return app.state.service.gmail_readiness()

    return GmailInboxAdapter().readiness_status()


@app.post("/integrations/tracking/poll")
def poll_tracking() -> dict[str, object]:
    service = _require_service()
    return service.poll_tracking()
