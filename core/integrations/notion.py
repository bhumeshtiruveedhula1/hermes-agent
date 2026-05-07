# core/integrations/notion.py — Phase 14: Notion Integration
# Uses notion-client SDK. Install: pip install notion-client
# Pattern: matches telegram.py structure (AuditLogger, _get_config, try/except)

import os
import re
from pathlib import Path
from core.audit.audit_logger import AuditLogger
from core.audit.audit_event import AuditEvent


def _get_token() -> str:
    """Read NOTION_TOKEN from .env or environment."""
    env_file = Path(".env")
    token = ""
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("NOTION_TOKEN="):
                token = line.split("=", 1)[1].strip()
                break
    return token or os.environ.get("NOTION_TOKEN", "")


class NotionCapability:
    def __init__(self):
        self.audit = AuditLogger()
        self._client = None

    def _get_client(self):
        if self._client:
            return self._client
        token = _get_token()
        if not token:
            raise ValueError("NOTION_TOKEN not set in .env — get it from notion.so/my-integrations")
        from notion_client import Client
        self._client = Client(auth=token)
        return self._client

    def execute(self, *, action: str, query: str = "", **kwargs) -> str:
        try:
            client = self._get_client()

            if action == "list_pages":
                return self._list_pages(client)

            elif action == "read_page":
                page_id = self._parse_id(query, "page_id")
                return self._read_page(client, page_id)

            elif action == "create_page":
                return self._create_page(client, query)

            elif action == "append_to_page":
                return self._append_to_page(client, query)

            else:
                raise ValueError(f"Unknown action: {action}")

        except Exception as e:
            self.audit.log(AuditEvent(
                phase="plugin", action=action,
                tool_name="notion", decision="blocked",
                metadata={"reason": str(e)}
            ))
            return f"[BLOCKED] Notion error: {e}"

    # ── Actions ──────────────────────────────────────────────────────────

    def _list_pages(self, client) -> str:
        results = client.search(
            filter={"property": "object", "value": "page"}
        ).get("results", [])

        if not results:
            return "No Notion pages found. Make sure your integration is shared with pages."

        lines = []
        for p in results[:15]:
            title = self._extract_title(p)
            lines.append(f"• {title or 'Untitled'} — ID: {p['id']}")

        self.audit.log(AuditEvent(
            phase="plugin", action="list_pages",
            tool_name="notion_list", decision="allowed"
        ))
        return f"Notion Pages ({len(results)} found):\n" + "\n".join(lines)

    def _read_page(self, client, page_id: str) -> str:
        if not page_id:
            return "[ERROR] page_id required. Use: page_id=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

        blocks = client.blocks.children.list(page_id).get("results", [])
        content = []
        for b in blocks:
            btype = b.get("type", "")
            block = b.get(btype, {})
            rich  = block.get("rich_text", [])
            text  = " ".join([r.get("plain_text", "") for r in rich])
            if text.strip():
                content.append(text)

        self.audit.log(AuditEvent(
            phase="plugin", action="read_page",
            tool_name="notion_read", decision="allowed",
            metadata={"page_id": page_id}
        ))
        return "\n".join(content) if content else "Page is empty or has no readable text blocks"

    def _create_page(self, client, query: str) -> str:
        parent_match  = re.search(r'parent_id=([\w\-]+)', query)
        title_match   = re.search(r'title=(.+?)(?:\s+content=|$)', query)
        content_match = re.search(r'content=(.+)', query)

        parent_id = parent_match.group(1).strip()  if parent_match  else ""
        title     = title_match.group(1).strip()   if title_match   else "New Page from Hermes"
        content   = content_match.group(1).strip() if content_match else ""

        if not parent_id:
            return "[ERROR] parent_id required. Use: parent_id=XXXX title=My Page content=Hello"

        children = []
        if content:
            children.append({
                "object": "block", "type": "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": content}}]}
            })

        new_page = client.pages.create(
            parent={"page_id": parent_id},
            properties={"title": {"title": [{"text": {"content": title}}]}},
            children=children
        )

        self.audit.log(AuditEvent(
            phase="plugin", action="create_page",
            tool_name="notion_create", decision="allowed",
            metadata={"title": title}
        ))
        return f"Created Notion page '{title}' — ID: {new_page['id']}"

    def _append_to_page(self, client, query: str) -> str:
        page_match    = re.search(r'page_id=([\w\-]+)', query)
        content_match = re.search(r'content=(.+)', query)

        page_id = page_match.group(1).strip()    if page_match    else ""
        content = content_match.group(1).strip() if content_match else query

        if not page_id:
            return "[ERROR] page_id required. Use: page_id=XXXX content=your text"
        if not content:
            return "[ERROR] content cannot be empty"

        client.blocks.children.append(
            block_id=page_id,
            children=[{
                "object": "block", "type": "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": content}}]}
            }]
        )

        self.audit.log(AuditEvent(
            phase="plugin", action="append_to_page",
            tool_name="notion_append", decision="allowed",
            metadata={"page_id": page_id, "preview": content[:80]}
        ))
        return f"Appended to Notion page {page_id}: '{content[:60]}...'" if len(content) > 60 else f"Appended: '{content}'"

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _extract_title(page: dict) -> str:
        """Extract title text from any Notion page object."""
        props = page.get("properties", {})
        for key in ["Name", "Title", "title", "name"]:
            if key in props:
                rich = props[key].get("title", [])
                if rich:
                    return rich[0].get("plain_text", "")
        return ""

    @staticmethod
    def _parse_id(query: str, key: str) -> str:
        """Extract key=VALUE from a description string."""
        m = re.search(rf'{key}=([\w\-]+)', query)
        return m.group(1).strip() if m else ""
