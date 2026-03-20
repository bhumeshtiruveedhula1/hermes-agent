# core/critic.py
import json
from langchain_core.messages import SystemMessage, HumanMessage

ALLOWED_TOOLS = {
    "search_web", "check_inbox", "draft_reply", "speak_out_loud",
    "fs_list", "fs_read", "fs_write", "fs_delete",
    "browser_go", "browser_read", "browser_click", "browser_fill",
    "browser_shot", "browser_scroll", "browser_close",
    "gmail_list", "gmail_read", "gmail_send", "gmail_search",
    "calendar_list", "calendar_today", "calendar_search", "calendar_create",
    None
}

class CriticAgent:
    def __init__(self, llm):
        self.llm = llm
        self.system_prompt = SystemMessage(content="""
You are the CRITIC agent.
Your job is to FIX execution plans.
Input: a JSON plan (may be imperfect)
Output: a corrected plan in EXACTLY this format:
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
browser_go, browser_read, browser_click, browser_fill, browser_shot, browser_scroll, browser_close

TOOL CORRECTION RULES:
- "browser_open", "browser_navigate", "open_browser" → ALWAYS replace with "browser_go"
- "read_page", "get_text", "page_read" → ALWAYS replace with "browser_read"
- "close_browser", "browser_exit" → ALWAYS replace with "browser_close"
- "read_file", "file_read" → ALWAYS replace with "fs_read"
- "list_files", "fs_list_dir" → ALWAYS replace with "fs_list"
- Any tool NOT in the ALLOWED TOOLS list → set to null
- "check_inbox", "list_emails", "get_emails" → ALWAYS replace with "gmail_list"
- "send_email", "email_send" → ALWAYS replace with "gmail_send"
- "read_email", "email_read" → ALWAYS replace with "gmail_read"
- "check_inbox", "list_emails", "get_emails", "show_emails" → replace with "gmail_list"
- ANY step with null tool where description mentions email/inbox → set tool to "gmail_list"
- "calendar_today", "calendar_list", "calendar_search", "calendar_create" are VALID tools — NEVER set them to null
- "what's on my calendar", "today's events", "upcoming events" → use "calendar_today" or "calendar_list"
- ANY step with tool="calendar_today" or "calendar_list" or "calendar_search" or "calendar_create" → KEEP IT, never change to null

RULES:
- NEVER set a tool to null if it is already in the ALLOWED TOOLS list
- If a tool name is valid (in the allowed list), ALWAYS keep it as-is
- Output JSON ONLY. No markdown. No code blocks.
- Remove extra fields.
- Add missing 'tool' fields (use null).
- Ensure steps are executable.

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
        print(f"[CRITIC DEBUG] output: {raw[:300]}")

        # Hard safety filter — critic cannot override allowed tools
        for step in reviewed.get("steps", []):
            if step.get("tool") not in ALLOWED_TOOLS:
                step["tool"] = None

        return reviewed