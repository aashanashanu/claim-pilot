from __future__ import annotations

import base64
import os
from datetime import datetime, timezone
from typing import Protocol

from .models import MailMessage, TrackingUpdate


class GmailMessageAdapter(Protocol):
    def fetch_messages(self, user_id: str, max_results: int = 5) -> list[MailMessage]:
        ...


class CarrierStatusAdapter(Protocol):
    def fetch_status(self, order_id: str, tracking_number: str) -> TrackingUpdate | None:
        ...


GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


class GmailInboxAdapter:
    """Real Gmail adapter using OAuth user credentials and Gmail read-only scope."""

    def __init__(
        self,
        *,
        gmail_credentials_file: str | None = None,
        gmail_token_file: str | None = None,
        gmail_query: str | None = None,
    ) -> None:
        self.gmail_credentials_file = gmail_credentials_file or os.getenv("GMAIL_CREDENTIALS_FILE")
        self.gmail_token_file = gmail_token_file or os.getenv("GMAIL_TOKEN_FILE") or ".gmail-token.json"
        self.gmail_query = gmail_query or os.getenv("CLAIMPILOT_GMAIL_QUERY") or "newer_than:14d"

    def _build_service(self, *, allow_interactive: bool = False):
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Google API dependencies are missing. Install google-api-python-client, "
                "google-auth, and google-auth-oauthlib."
            ) from exc

        scopes = [GMAIL_READONLY_SCOPE]
        creds = None

        if os.path.exists(self.gmail_token_file):
            creds = Credentials.from_authorized_user_file(self.gmail_token_file, scopes)

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        if not creds or not creds.valid:
            if not self.gmail_credentials_file:
                raise RuntimeError(
                    "Gmail token is missing or invalid and no client credentials file is configured. "
                    "Set GMAIL_CREDENTIALS_FILE and run the OAuth flow once."
                )

            if not allow_interactive:
                raise RuntimeError(
                    "Gmail token is missing or invalid. Interactive OAuth is disabled in runtime mode; "
                    "generate a token file ahead of time and set GMAIL_TOKEN_FILE."
                )

            flow = InstalledAppFlow.from_client_secrets_file(self.gmail_credentials_file, scopes)
            creds = flow.run_local_server(port=0)
            with open(self.gmail_token_file, "w", encoding="utf-8") as token_file:
                token_file.write(creds.to_json())

        return build("gmail", "v1", credentials=creds)

    def _decode_body_data(self, data: str) -> str:
        if not data:
            return ""
        raw = base64.urlsafe_b64decode(data.encode("utf-8"))
        return raw.decode("utf-8", errors="replace")

    def _extract_text_body(self, payload: dict[str, object]) -> str:
        body = payload.get("body")
        if isinstance(body, dict):
            data = body.get("data")
            if isinstance(data, str) and data:
                return self._decode_body_data(data)

        parts = payload.get("parts")
        if isinstance(parts, list):
            for part in parts:
                if not isinstance(part, dict):
                    continue
                mime_type = str(part.get("mimeType", ""))
                if mime_type == "text/plain":
                    text = self._extract_text_body(part)
                    if text:
                        return text
            for part in parts:
                if isinstance(part, dict):
                    nested = self._extract_text_body(part)
                    if nested:
                        return nested

        return ""

    def readiness_status(self) -> dict[str, object]:
        status: dict[str, object] = {
            "status": "error",
            "code": "GMAIL_NOT_READY",
            "message": "Gmail integration is not configured.",
            "scope": GMAIL_READONLY_SCOPE,
            "credentials_file": self.gmail_credentials_file,
            "token_file": self.gmail_token_file,
            "query": self.gmail_query,
            "dependencies_installed": False,
            "credentials_file_exists": bool(self.gmail_credentials_file and os.path.exists(self.gmail_credentials_file)),
            "token_file_exists": bool(self.gmail_token_file and os.path.exists(self.gmail_token_file)),
        }

        try:
            service = self._build_service(allow_interactive=False)
            profile = service.users().getProfile(userId="me").execute()
            status.update(
                {
                    "status": "ok",
                    "code": "GMAIL_READY",
                    "message": "Gmail integration is configured and token is valid.",
                    "dependencies_installed": True,
                    "email_address": profile.get("emailAddress"),
                    "messages_total": profile.get("messagesTotal"),
                    "threads_total": profile.get("threadsTotal"),
                }
            )
            return status
        except RuntimeError as exc:
            message = str(exc)
            status["message"] = message
            if "dependencies are missing" in message:
                status["code"] = "GMAIL_DEPENDENCIES_MISSING"
            elif "token is missing or invalid" in message:
                status["code"] = "GMAIL_TOKEN_MISSING_OR_INVALID"
            elif "client credentials file" in message:
                status["code"] = "GMAIL_CREDENTIALS_MISSING"
            return status
        except Exception as exc:
            status.update(
                {
                    "code": "GMAIL_AUTH_ERROR",
                    "message": f"Gmail validation failed: {exc}",
                }
            )
            return status

    def fetch_messages(self, user_id: str, max_results: int = 5) -> list[MailMessage]:
        service = self._build_service(allow_interactive=False)
        messages: list[MailMessage] = []

        response = service.users().messages().list(
            userId="me",
            q=self.gmail_query,
            maxResults=max_results,
        ).execute()
        refs = response.get("messages", [])

        for ref in refs:
            if not isinstance(ref, dict):
                continue
            message_id = str(ref.get("id", ""))
            if not message_id:
                continue

            full_message = service.users().messages().get(
                userId="me",
                id=message_id,
                format="full",
            ).execute()
            payload = full_message.get("payload", {})
            headers = payload.get("headers", []) if isinstance(payload, dict) else []
            header_map: dict[str, str] = {}
            if isinstance(headers, list):
                for item in headers:
                    if isinstance(item, dict):
                        name = item.get("name")
                        value = item.get("value")
                        if isinstance(name, str) and isinstance(value, str):
                            header_map[name.lower()] = value

            subject = header_map.get("subject", "")
            body_text = self._extract_text_body(payload if isinstance(payload, dict) else {})
            internal_date_raw = full_message.get("internalDate")
            if isinstance(internal_date_raw, str) and internal_date_raw.isdigit():
                received_at = datetime.fromtimestamp(int(internal_date_raw) / 1000, tz=timezone.utc)
            else:
                received_at = datetime.now(timezone.utc)

            messages.append(
                MailMessage(
                    message_id=message_id,
                    user_id=user_id,
                    subject=subject,
                    body=body_text,
                    received_at=received_at,
                )
            )

        return messages
