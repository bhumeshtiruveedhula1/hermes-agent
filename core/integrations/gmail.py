# core/integrations/gmail.py

import os
import base64
import json
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from core.audit.audit_logger import AuditLogger
from core.audit.audit_event import AuditEvent

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

CREDENTIALS_FILE = Path("credentials.json")
TOKEN_FILE = Path("memory/gmail_token.json")


class GmailCapability:
    """
    Gmail integration — read, summarize, send emails.
    Uses OAuth 2.0. Token is cached after first login.
    """

    def __init__(self):
        self.audit = AuditLogger()
        self._service = None

    def _get_service(self):
        if self._service:
            return self._service

        creds = None

        if TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not CREDENTIALS_FILE.exists():
                    raise FileNotFoundError(
                        "credentials.json not found. "
                        "Download it from Google Cloud Console and place it in the project root."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CREDENTIALS_FILE), SCOPES
                )
                creds = flow.run_local_server(port=0)

            TOKEN_FILE.parent.mkdir(exist_ok=True)
            TOKEN_FILE.write_text(creds.to_json())

        self._service = build("gmail", "v1", credentials=creds)
        return self._service

    def execute(self, *, action: str, query: str = "", to: str = "",
                subject: str = "", body: str = "", msg_id: str = "") -> str:
        try:
            service = self._get_service()

            if action == "list":
                return self._list_emails(service, query or "is:unread", max_results=5)

            elif action == "read":
                return self._read_email(service, msg_id)

            elif action == "send":
                return self._send_email(service, to, subject, body)

            elif action == "search":
                return self._list_emails(service, query, max_results=5)

            else:
                raise ValueError(f"Unknown gmail action: {action}")

        except Exception as e:
            self.audit.log(AuditEvent(
                phase="gmail", action=action,
                tool_name="gmail", decision="blocked",
                metadata={"reason": str(e)}
            ))
            return f"[BLOCKED] Gmail error: {str(e)}"

    def _list_emails(self, service, query: str, max_results: int = 5) -> str:
        results = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()

        messages = results.get("messages", [])
        if not messages:
            return "No emails found."

        output = []
        for msg in messages:
            detail = service.users().messages().get(
                userId="me", id=msg["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"]
            ).execute()

            headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
            import re
            snippet = re.sub(r'<[^>]+>', ' ', detail.get("snippet", ""))[:100]

            output.append(
                f"ID: {msg['id']}\n"
                f"From: {headers.get('From', 'unknown')}\n"
                f"Subject: {headers.get('Subject', 'no subject')}\n"
                f"Date: {headers.get('Date', '')}\n"
                f"Preview: {snippet}...\n"
            )

            self.audit.log(AuditEvent(
                phase="gmail", action="list",
                tool_name="gmail", decision="allowed",
                metadata={"query": query}
            ))

        return "\n---\n".join(output)

    def _read_email(self, service, msg_id: str) -> str:
        if not msg_id:
            return "[ERROR] No message ID provided for read."

        detail = service.users().messages().get(
            userId="me", id=msg_id, format="full"
        ).execute()

        headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
        body = self._extract_body(detail["payload"])

        self.audit.log(AuditEvent(
            phase="gmail", action="read",
            tool_name="gmail", decision="allowed",
            metadata={"msg_id": msg_id}
        ))

        return (
            f"From: {headers.get('From', 'unknown')}\n"
            f"Subject: {headers.get('Subject', 'no subject')}\n"
            f"Date: {headers.get('Date', '')}\n\n"
            f"{body[:2000]}"
        )

    def _extract_body(self, payload) -> str:
        import re
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    data = part["body"].get("data", "")
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        body_data = payload.get("body", {}).get("data", "")
        if body_data:
            text = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")
            # Strip HTML tags
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text
        return "(no body content)"

    def _send_email(self, service, to: str, subject: str, body: str) -> str:
        if not to:
            return "[ERROR] No recipient specified."

        msg = MIMEMultipart()
        msg["To"] = to
        msg["Subject"] = subject or "(no subject)"
        msg.attach(MIMEText(body, "plain"))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

        service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()

        self.audit.log(AuditEvent(
            phase="gmail", action="send",
            tool_name="gmail", decision="allowed",
            metadata={"to": to, "subject": subject}
        ))

        return f"Email sent to {to} — Subject: {subject}"