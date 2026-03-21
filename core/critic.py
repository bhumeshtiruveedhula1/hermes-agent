# core/critic.py

import json
from langchain_core.messages import SystemMessage, HumanMessage
from core.plugin_loader import PluginLoader


def _get_allowed_tools() -> set:
    static = {
        "search_web", "check_inbox", "draft_reply", "speak_out_loud",
        "fs_list", "fs_read", "fs_write", "fs_delete",
        "browser_go", "browser_read", "browser_click", "browser_fill",
        "browser_shot", "browser_scroll", "browser_close",
        "gmail_list", "gmail_read", "gmail_send", "gmail_search",
        "calendar_list", "calendar_today", "calendar_search", "calendar_create",
        "github_repos", "github_repo_info", "github_issues", "github_prs",
        "github_commits", "github_search", "github_create_issue",
        None
    }
    return static | PluginLoader.get_all_tool_names()


ALLOWED_TOOLS = _get_allowed_tools()


class CriticAgent:
    def __init__(self, llm):
        self.llm = llm
        self.system_prompt = SystemMessage(content="""
You are the CRITIC agent.
Your job is to VALIDATE execution plans — fix broken tool names, never remove valid ones.

Input: a JSON plan
Output: corrected plan in EXACTLY this format:
{
  "goal": "<goal>",
  "steps": [
    {
      "step_id": "<string>",
      "description": "<string>",
      "tool": "<tool_name or null>"
    }
  ]
}

ALLOWED TOOLS (ONLY these exact names, nothing else):
search_web, check_inbox, draft_reply, speak_out_loud,
fs_list, fs_read, fs_write, fs_delete,
browser_go, browser_read, browser_click, browser_fill, browser_shot, browser_scroll, browser_close,
gmail_list, gmail_read, gmail_send, gmail_search,
calendar_list, calendar_today, calendar_search, calendar_create,
github_repos, github_repo_info, github_issues, github_prs, github_commits, github_search, github_create_issue,
weather_current, weather_forecast

GOLDEN RULE: If a tool is in the ALLOWED list above — KEEP IT. NEVER change it to null.

TOOL CORRECTION RULES:
- "browser_open", "browser_navigate", "open_browser" → replace with "browser_go"
- "read_page", "get_text", "page_read" → replace with "browser_read"
- "close_browser", "browser_exit" → replace with "browser_close"
- "read_file", "file_read" → replace with "fs_read"
- "list_files", "fs_list_dir" → replace with "fs_list"
- "check_inbox", "list_emails", "get_emails", "show_emails" → replace with "gmail_list"
- "send_email", "email_send" → replace with "gmail_send"
- "read_email", "email_read" → replace with "gmail_read"
- "calendar_today", "calendar_list", "calendar_search", "calendar_create" → KEEP, never null
- "github_repos", "github_issues", "github_prs", "github_commits", "github_repo_info", "github_search", "github_create_issue" → KEEP, never null
- "weather_current", "weather_forecast" → KEEP, never null
- ANY tool in the ALLOWED list → ALWAYS keep as-is
- Any tool NOT in the ALLOWED list and cannot be corrected → set to null

RULES:
- Output JSON ONLY. No markdown. No code blocks.
- Remove extra fields.
- Add missing 'tool' fields (use null).
- NEVER set a valid allowed tool to null.

/no_think
""")

    def review_plan(self, plan: dict) -> dict:
        messages = [
            self.system_prompt,
            HumanMessage(content=json.dumps(plan))
        ]
        response = self.llm.invoke(messages)

        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        reviewed = json.loads(raw)

        # Dynamic hard filter — reloads plugin tools each time
        allowed = _get_allowed_tools()
        for step in reviewed.get("steps", []):
            if step.get("tool") not in allowed:
                step["tool"] = None

        return reviewed
