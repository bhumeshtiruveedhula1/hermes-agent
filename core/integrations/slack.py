# core/integrations/slack.py — Phase 14: Slack Integration
# Uses slack-sdk. Install: pip install slack-sdk
# Pattern: matches telegram.py structure (AuditLogger, _get_config, try/except)

import os
import re
from pathlib import Path
from core.audit.audit_logger import AuditLogger
from core.audit.audit_event import AuditEvent


def _get_token() -> str:
    """Read SLACK_BOT_TOKEN from .env or environment."""
    env_file = Path(".env")
    token = ""
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("SLACK_BOT_TOKEN="):
                token = line.split("=", 1)[1].strip()
                break
    return token or os.environ.get("SLACK_BOT_TOKEN", "")


class SlackCapability:
    def __init__(self):
        self.audit   = AuditLogger()
        self._client = None
        self._channel_cache: dict = {}    # name → id cache to avoid repeated API calls

    def _get_client(self):
        if self._client:
            return self._client
        token = _get_token()
        if not token:
            raise ValueError("SLACK_BOT_TOKEN not set in .env — get it from api.slack.com/apps")
        from slack_sdk import WebClient
        self._client = WebClient(token=token)
        return self._client

    def execute(self, *, action: str, query: str = "", **kwargs) -> str:
        try:
            client = self._get_client()

            if action == "list_channels":
                return self._list_channels(client)
            elif action == "send":
                return self._send(client, query)
            elif action == "read":
                return self._read(client, query)
            else:
                raise ValueError(f"Unknown action: {action}")

        except Exception as e:
            self.audit.log(AuditEvent(
                phase="plugin", action=action,
                tool_name="slack", decision="blocked",
                metadata={"reason": str(e)}
            ))
            return f"[BLOCKED] Slack error: {e}"

    # ── Actions ──────────────────────────────────────────────────────────

    def _list_channels(self, client) -> str:
        result   = client.conversations_list(limit=25, types="public_channel,private_channel")
        channels = result.get("channels", [])
        if not channels:
            return "No Slack channels found. Make sure the bot is in at least one channel."

        # Rebuild cache
        self._channel_cache = {c["name"]: c["id"] for c in channels}

        lines = [f"• #{c['name']} ({c.get('num_members', 0)} members)" for c in channels]
        self.audit.log(AuditEvent(phase="plugin", action="list_channels",
            tool_name="slack_channels", decision="allowed"))
        return f"Slack channels ({len(channels)}):\n" + "\n".join(lines)

    def _send(self, client, query: str) -> str:
        channel_match = re.search(r'channel=([\w\-]+)', query)
        text_match    = re.search(r'text=(.+)', query)

        channel = channel_match.group(1).strip() if channel_match else ""
        text    = text_match.group(1).strip()    if text_match    else query

        if not channel:
            return "[ERROR] channel required. Use: channel=general text=your message"
        if not text:
            return "[ERROR] text cannot be empty"

        channel_id = f"#{channel}" if not channel.startswith("#") else channel

        from slack_sdk.errors import SlackApiError
        try:
            resp = client.chat_postMessage(channel=channel_id, text=text)
        except SlackApiError as e:
            return f"[ERROR] Slack API: {e.response['error']}"

        self.audit.log(AuditEvent(
            phase="plugin", action="send",
            tool_name="slack_send", decision="allowed",
            metadata={"channel": channel, "preview": text[:80]}
        ))
        return f"Sent to #{channel}: '{text[:60]}...'" if len(text) > 60 else f"Sent to #{channel}: '{text}'"

    def _read(self, client, query: str) -> str:
        channel_match = re.search(r'channel=([\w\-]+)', query)
        channel_name  = channel_match.group(1).strip() if channel_match else "general"
        channel_name  = channel_name.lstrip("#")

        # Get channel ID — use cache or fetch fresh
        channel_id = self._channel_cache.get(channel_name)
        if not channel_id:
            result = client.conversations_list(types="public_channel,private_channel")
            for c in result.get("channels", []):
                self._channel_cache[c["name"]] = c["id"]
            channel_id = self._channel_cache.get(channel_name)

        if not channel_id:
            return f"[ERROR] Channel #{channel_name} not found. Is the bot a member of that channel?"

        from slack_sdk.errors import SlackApiError
        try:
            history  = client.conversations_history(channel=channel_id, limit=10)
        except SlackApiError as e:
            return f"[ERROR] Slack API: {e.response['error']}"

        messages = history.get("messages", [])
        if not messages:
            return f"No messages in #{channel_name}"

        lines = []
        for m in reversed(messages):
            user = m.get("user", m.get("username", "bot"))
            text = m.get("text", "")[:120]
            lines.append(f"{user}: {text}")

        self.audit.log(AuditEvent(phase="plugin", action="read",
            tool_name="slack_read", decision="allowed",
            metadata={"channel": channel_name}))
        return f"Recent messages in #{channel_name}:\n" + "\n".join(lines)
