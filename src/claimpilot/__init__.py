"""ClaimPilot MVP core package."""

from .agent_runtime import StrandsDecisionEngine
from .config import AppConfig, DEFAULT_CONFIG
from .decision_table import classify_exception
from .demo_surface import DemoDashboard
from .desktop_ui import DemoDesktopApp, DemoDesktopController
from .models import (
    ActionType,
    ExceptionType,
    MailMessage,
    Order,
    ResolutionDecision,
    TrackingStatus,
    TrackingUpdate,
)
from .workers import AutoResolver, DecisionNotifier

__all__ = [
    "ActionType",
    "AppConfig",
    "AutoResolver",
    "DEFAULT_CONFIG",
    "DecisionNotifier",
    "DemoDashboard",
    "DemoDesktopApp",
    "DemoDesktopController",
    "ExceptionType",
    "MailMessage",
    "Order",
    "ResolutionDecision",
    "StrandsDecisionEngine",
    "TrackingStatus",
    "TrackingUpdate",
    "classify_exception",
]
