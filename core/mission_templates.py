# core/mission_templates.py — Phase 15: Mission Templates
# Built-in + user-saved reusable mission prompts.
# Builtin templates cannot be deleted.

import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

TEMPLATES_FILE = Path("memory/mission_templates.json")

# ── Built-in starter templates ────────────────────────────────────────────
DEFAULT_TEMPLATES = [
    {
        "id":          "tpl_morning",
        "name":        "Morning Briefing",
        "description": "Check emails, calendar, and weather",
        "prompt":      "Check my unread emails, show today's calendar events, and get the current weather. Summarize everything in one response.",
        "builtin":     True,
        "created_at":  "2026-01-01T00:00:00+00:00",
    },
    {
        "id":          "tpl_research",
        "name":        "Research & Save",
        "description": "Search web, summarize, save to file",
        "prompt":      "Search the web for the latest news on AI agents. Summarize the top 3 results. Save the summary to /documents/ai_research.txt",
        "builtin":     True,
        "created_at":  "2026-01-01T00:00:00+00:00",
    },
    {
        "id":          "tpl_github_report",
        "name":        "GitHub Report",
        "description": "Check repos, issues, and PRs",
        "prompt":      "List my GitHub repositories. For each repo, check open issues and pull requests. Summarize the status.",
        "builtin":     True,
        "created_at":  "2026-01-01T00:00:00+00:00",
    },
    {
        "id":          "tpl_notion_slack",
        "name":        "Notion → Slack",
        "description": "Read a Notion page and share to Slack",
        "prompt":      "List my Notion pages. Read the most recent one. Send a summary of it to the Slack general channel.",
        "builtin":     True,
        "created_at":  "2026-01-01T00:00:00+00:00",
    },
    {
        "id":          "tpl_files_report",
        "name":        "Files Report",
        "description": "List files and save an inventory",
        "prompt":      "List all files in /documents. Write a summary inventory to /documents/inventory.txt with the file names and count.",
        "builtin":     True,
        "created_at":  "2026-01-01T00:00:00+00:00",
    },
]


class MissionTemplates:
    def __init__(self):
        TEMPLATES_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not TEMPLATES_FILE.exists():
            TEMPLATES_FILE.write_text(
                json.dumps(DEFAULT_TEMPLATES, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

    def list_all(self) -> list:
        return self._load()

    def get(self, template_id: str) -> Optional[dict]:
        for t in self._load():
            if t["id"] == template_id:
                return t
        return None

    def save(self, name: str, description: str, prompt: str) -> dict:
        template = {
            "id":          f"tpl_{str(uuid.uuid4())[:6]}",
            "name":        name.strip()[:60],
            "description": description.strip()[:120],
            "prompt":      prompt.strip(),
            "builtin":     False,
            "created_at":  _now(),
        }
        templates = self._load()
        templates.append(template)
        self._save(templates)
        return template

    def delete(self, template_id: str) -> bool:
        """Delete user-saved templates only. Returns True if deleted."""
        templates = self._load()
        filtered  = [t for t in templates
                     if t["id"] != template_id or t.get("builtin", False)]
        if len(filtered) == len(templates):
            return False      # Nothing removed (builtin or not found)
        self._save(filtered)
        return True

    def _load(self) -> list:
        try:
            return json.loads(TEMPLATES_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            return list(DEFAULT_TEMPLATES)

    def _save(self, templates: list):
        TEMPLATES_FILE.write_text(
            json.dumps(templates, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
