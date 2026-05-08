# core/integrations/whatsapp.py — Phase 14: WhatsApp via Twilio
# Pattern: matches telegram.py structure exactly (AuditLogger, _get_config, try/except)

import os
import requests
from pathlib import Path
from core.audit.audit_logger import AuditLogger
from core.audit.audit_event import AuditEvent


def _get_config() -> dict:
    """Read Twilio credentials from .env or environment."""
    env_file = Path(".env")
    cfg = {"account_sid": "", "auth_token": "", "from_number": "", "to_number": ""}
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("TWILIO_ACCOUNT_SID="):
                cfg["account_sid"] = line.split("=", 1)[1].strip()
            elif line.startswith("TWILIO_AUTH_TOKEN="):
                cfg["auth_token"] = line.split("=", 1)[1].strip()
            elif line.startswith("TWILIO_WHATSAPP_FROM="):
                cfg["from_number"] = line.split("=", 1)[1].strip()
            elif line.startswith("TWILIO_WHATSAPP_TO="):
                cfg["to_number"] = line.split("=", 1)[1].strip()

    cfg["account_sid"] = cfg["account_sid"] or os.environ.get("TWILIO_ACCOUNT_SID", "")
    cfg["auth_token"]  = cfg["auth_token"]  or os.environ.get("TWILIO_AUTH_TOKEN", "")
    cfg["from_number"] = cfg["from_number"] or os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
    cfg["to_number"]   = cfg["to_number"]   or os.environ.get("TWILIO_WHATSAPP_TO", "")

    if not cfg["account_sid"] or not cfg["auth_token"]:
        raise ValueError("TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN not set in .env")
    return cfg


class WhatsAppCapability:
    def __init__(self):
        self.audit = AuditLogger()

    def execute(self, *, action: str, query: str = "", **kwargs) -> str:
        try:
            cfg = _get_config()

            if action == "send":
                return self._send(cfg, query, kwargs)

            elif action == "list":
                return self._list(cfg)

            else:
                raise ValueError(f"Unknown action: {action}")

        except Exception as e:
            self.audit.log(AuditEvent(
                phase="plugin", action=action,
                tool_name="whatsapp", decision="blocked",
                metadata={"reason": str(e)}
            ))
            return f"[BLOCKED] WhatsApp error: {e}"

    def _send(self, cfg: dict, query: str, kwargs: dict) -> str:
        """Send a WhatsApp message via Twilio REST API (no SDK needed)."""
        import re

        # Parse: to=+91XXXXXXXXXX body=hello world
        # Require at least 7 digits so we reject "+91XXXXXXXXXX" planner placeholders
        to_match   = re.search(r'to=(\+\d{7,15})', query)
        body_match = re.search(r'body=(.+)', query)

        to   = to_match.group(1).strip()   if to_match   else ""
        body = body_match.group(1).strip() if body_match else query

        # Fallback: if no valid to= found (or only a format placeholder),
        # use the pre-configured TWILIO_WHATSAPP_TO from .env
        if not to or re.search(r'X{3,}', to):
            to = cfg["to_number"]

        if not to:
            return "[ERROR] No recipient number. Set TWILIO_WHATSAPP_TO in .env or use: to=+919876543210 body=message"
        if not body:
            return "[ERROR] Message body is empty"

        if not to.startswith("whatsapp:"):
            to = f"whatsapp:{to}"

        url = f"https://api.twilio.com/2010-04-01/Accounts/{cfg['account_sid']}/Messages.json"
        resp = requests.post(url,
            auth=(cfg["account_sid"], cfg["auth_token"]),
            data={"From": cfg["from_number"], "To": to, "Body": body},
            timeout=15
        )

        if resp.status_code in (200, 201):
            sid = resp.json().get("sid", "unknown")
            self.audit.log(AuditEvent(
                phase="plugin", action="send",
                tool_name="whatsapp_send", decision="allowed",
                metadata={"to": to, "preview": body[:80]}
            ))
            return f"WhatsApp sent to {to} ✓ (SID: {sid})"
        else:
            return f"[ERROR] Twilio API error {resp.status_code}: {resp.text[:200]}"

    def _list(self, cfg: dict) -> str:
        """List recent incoming WhatsApp messages."""
        url = f"https://api.twilio.com/2010-04-01/Accounts/{cfg['account_sid']}/Messages.json"
        resp = requests.get(url,
            auth=(cfg["account_sid"], cfg["auth_token"]),
            params={"To": cfg["from_number"], "PageSize": 10},
            timeout=15
        )
        if resp.status_code != 200:
            return f"[ERROR] Twilio error: {resp.text[:200]}"

        messages = resp.json().get("messages", [])
        if not messages:
            return "No recent WhatsApp messages"

        lines = []
        for m in messages:
            sender = m.get("from", "unknown")
            body   = m.get("body", "")[:100]
            lines.append(f"From {sender}: {body}")

        self.audit.log(AuditEvent(
            phase="plugin", action="list",
            tool_name="whatsapp_list", decision="allowed"
        ))
        return "Recent WhatsApp messages:\n" + "\n".join(lines)
