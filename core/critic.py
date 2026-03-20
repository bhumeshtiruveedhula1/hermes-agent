# core/critic.py
import json
from langchain_core.messages import SystemMessage, HumanMessage

ALLOWED_TOOLS = {
    "search_web", "check_inbox", "draft_reply", "speak_out_loud",
    "fs_list", "fs_read", "fs_write", "fs_delete",
    "browser_go", "browser_read", "browser_click",
    "browser_fill", "browser_shot", "browser_scroll", "browser_close",
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

RULES:
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

        # Hard safety filter — critic cannot override allowed tools
        for step in reviewed.get("steps", []):
            if step.get("tool") not in ALLOWED_TOOLS:
                step["tool"] = None

        return reviewed