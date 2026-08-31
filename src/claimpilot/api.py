from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .demo_service import DemoService
from .integrations import GmailInboxAdapter


@asynccontextmanager
async def lifespan(app: FastAPI):
    _initialize_service()
    if app.state.service is not None:
        app.state.service.start_background_workers()

    try:
        yield
    finally:
        service = app.state.service
        if service is not None:
            service.stop_background_workers()


app = FastAPI(title="ClaimPilot Demo API", version="0.1.0", lifespan=lifespan)
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


@app.post("/demo/runbook")
def run_demo_runbook() -> dict[str, object]:
    service = _require_service()
    return service.run_demo_runbook()


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


@app.get("/storefront")
def storefront_snapshot() -> dict[str, object]:
    service = _require_service()
    return service.storefront_snapshot()


@app.post("/storefront/seed-demo")
def seed_storefront_demo() -> dict[str, object]:
    service = _require_service()
    return service.seed_storefront_demo()


@app.post("/storefront/orders/{product_id}")
def purchase_product(product_id: str, recipient_email: str | None = None) -> dict[str, object]:
    service = _require_service()
    return service.purchase_product(product_id=product_id, recipient_email=recipient_email)


@app.post("/storefront/orders/{order_id}/price-drop")
def storefront_price_drop(order_id: str, new_price: float) -> dict[str, object]:
    service = _require_service()
    return service.price_drop(order_id=order_id, new_price=new_price)


@app.post("/storefront/orders/{order_id}/return")
def storefront_return(order_id: str) -> dict[str, object]:
    service = _require_service()
    return service.start_return(order_id=order_id)


@app.post("/storefront/orders/{order_id}/claim")
def storefront_claim(order_id: str, claim_type: str = "damaged_item") -> dict[str, object]:
    service = _require_service()
    return service.file_claim(order_id=order_id, claim_type=claim_type)


@app.post("/decisions/{order_id}")
def capture_decision(order_id: str, decision: str, reason: str | None = None) -> dict[str, object]:
    service = _require_service()
    return service.capture_decision(order_id=order_id, decision=decision, reason=reason)
