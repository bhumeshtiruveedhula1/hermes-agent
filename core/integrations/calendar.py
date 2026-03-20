# core/integrations/calendar.py

from pathlib import Path
from datetime import datetime, timedelta
import re

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
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]

CREDENTIALS_FILE = Path("credentials.json")
TOKEN_FILE = Path("memory/gmail_token.json")


class CalendarCapability:
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
                flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
                creds = flow.run_local_server(port=0)
            TOKEN_FILE.parent.mkdir(exist_ok=True)
            TOKEN_FILE.write_text(creds.to_json())

        self._service = build("calendar", "v3", credentials=creds)
        return self._service

    def execute(self, *, action: str, query: str = "", title: str = "",
                start: str = "", end: str = "", description: str = "") -> str:
        try:
            service = self._get_service()

            if action == "list":
                return self._list_events(service)
            elif action == "search":
                return self._search_events(service, query)
            elif action == "create":
                return self._create_event(service, title, start, end, description)
            elif action == "today":
                return self._today_events(service)
            else:
                raise ValueError(f"Unknown calendar action: {action}")

        except Exception as e:
            self.audit.log(AuditEvent(
                phase="calendar", action=action, tool_name="calendar",
                decision="blocked", metadata={"reason": str(e)}
            ))
            return f"[BLOCKED] Calendar error: {str(e)}"

    def _list_events(self, service, max_results: int = 10) -> str:
        now = datetime.utcnow().isoformat() + "Z"
        events_result = service.events().list(
            calendarId="primary", timeMin=now,
            maxResults=max_results, singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = events_result.get("items", [])
        if not events:
            return "No upcoming events found."

        output = []
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date", ""))
            output.append(
                f"Title: {event.get('summary', 'No title')}\n"
                f"When: {start}\n"
                f"ID: {event['id']}"
            )

        self.audit.log(AuditEvent(
            phase="calendar", action="list", tool_name="calendar", decision="allowed"
        ))
        return "\n---\n".join(output)

    def _today_events(self, service) -> str:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0).isoformat() + "Z"
        today_end = datetime.utcnow().replace(hour=23, minute=59, second=59).isoformat() + "Z"

        events_result = service.events().list(
            calendarId="primary", timeMin=today_start, timeMax=today_end,
            singleEvents=True, orderBy="startTime"
        ).execute()

        events = events_result.get("items", [])
        if not events:
            return "No events today."

        output = []
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date", ""))
            output.append(f"• {event.get('summary', 'No title')} — {start}")

        self.audit.log(AuditEvent(
            phase="calendar", action="today", tool_name="calendar", decision="allowed"
        ))
        return "Today's events:\n" + "\n".join(output)

    def _search_events(self, service, query: str) -> str:
        now = datetime.utcnow().isoformat() + "Z"
        events_result = service.events().list(
            calendarId="primary", timeMin=now, q=query,
            maxResults=5, singleEvents=True, orderBy="startTime"
        ).execute()

        events = events_result.get("items", [])
        if not events:
            return f"No events found matching '{query}'."

        output = []
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date", ""))
            output.append(
                f"Title: {event.get('summary', 'No title')}\n"
                f"When: {start}"
            )
        return "\n---\n".join(output)

    def _create_event(self, service, title: str, start: str, end: str, description: str) -> str:
        if not title:
            return "[ERROR] Event title required."
        if not start:
            return "[ERROR] Start time required."

        # Default end = 1 hour after start
        if not end:
            try:
                start_dt = datetime.fromisoformat(start.replace("Z", ""))
                end_dt = start_dt + timedelta(hours=1)
                end = end_dt.isoformat()
            except:
                end = start

        event = {
            "summary": title,
            "description": description,
            "start": {"dateTime": start, "timeZone": "Asia/Kolkata"},
            "end": {"dateTime": end, "timeZone": "Asia/Kolkata"},
        }

        created = service.events().insert(calendarId="primary", body=event).execute()

        self.audit.log(AuditEvent(
            phase="calendar", action="create", tool_name="calendar",
            decision="allowed", metadata={"title": title, "start": start}
        ))
        return f"Event created: {created.get('summary')} — {created.get('start', {}).get('dateTime', '')}"