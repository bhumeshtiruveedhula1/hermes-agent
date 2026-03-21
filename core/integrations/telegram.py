# core/integrations/telegram.py

import os
import requests
from pathlib import Path
from core.audit.audit_logger import AuditLogger
from core.audit.audit_event import AuditEvent


def _get_config() -> tuple[str, str]:
    env_file = Path(".env")
    token, chat_id = "", ""
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("TELEGRAM_TOKEN="):
                token = line.split("=", 1)[1].strip()
            elif line.startswith("TELEGRAM_CHAT_ID="):
                chat_id = line.split("=", 1)[1].strip()
    token = token or os.environ.get("TELEGRAM_TOKEN", "")
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token:
        raise ValueError("TELEGRAM_TOKEN not found in .env")
    if not chat_id:
        raise ValueError("TELEGRAM_CHAT_ID not found in .env")
    return token, chat_id


class TelegramCapability:
    def __init__(self):
        self.audit = AuditLogger()

    def execute(self, *, action: str, query: str = "", **kwargs) -> str:
        try:
            token, chat_id = _get_config()

            if action == "send":
                return self._send(token, chat_id, query)
            elif action == "get_updates":
                return self._get_updates(token)
            else:
                raise ValueError(f"Unknown action: {action}")

        except Exception as e:
            self.audit.log(AuditEvent(
                phase="plugin", action=action,
                tool_name="telegram", decision="blocked",
                metadata={"reason": str(e)}
            ))
            return f"[BLOCKED] Telegram error: {str(e)}"

    def _send(self, token: str, chat_id: str, message: str) -> str:
        if not message:
            return "[ERROR] Message cannot be empty."

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        response = requests.post(url, json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }, timeout=10)

        if response.status_code == 200:
            self.audit.log(AuditEvent(
                phase="plugin", action="send",
                tool_name="telegram", decision="allowed",
                metadata={"preview": message[:80]}
            ))
            return f"Message sent to Telegram: '{message[:60]}...'" if len(message) > 60 else f"Message sent: '{message}'"
        else:
            return f"[ERROR] Telegram API error: {response.text}"

    def _get_updates(self, token: str) -> str:
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        response = requests.get(url, timeout=10).json()

        messages = response.get("result", [])
        if not messages:
            return "No new messages."

        output = []
        for update in messages[-5:]:
            msg = update.get("message", {})
            sender = msg.get("from", {}).get("first_name", "unknown")
            text = msg.get("text", "")
            output.append(f"From {sender}: {text}")

        self.audit.log(AuditEvent(
            phase="plugin", action="get_updates",
            tool_name="telegram", decision="allowed"
        ))
        return "\n".join(output)