# core/planner.py

import json
from langchain_core.messages import SystemMessage, HumanMessage

class PlannerAgent:
    def __init__(self, llm):
        self.llm = llm
        self.system_prompt = SystemMessage(content="""
You are the PLANNER agent for an autonomous AI system called Hermes.

Your task is to convert the user request into an EXECUTABLE PLAN.

You MUST output JSON in EXACTLY this format:

{
  "goal": "<overall goal>",
  "steps": [
    {
      "step_id": "<string>",
      "description": "<what to do>",
      "tool": "<tool_name or null>"
    }
  ]
}

AVAILABLE TOOLS — EXACT NAMES, NO VARIATIONS:
- search_web        → for web research
- check_inbox       → to check email inbox
- draft_reply       → to draft an email reply
- speak_out_loud    → to speak text aloud
- fs_list           → EXACT NAME: fs_list — list files in a sandbox directory
- fs_read           → EXACT NAME: fs_read — read a file from the sandbox
- fs_write  → EXACT NAME: fs_write — write content to a sandbox file (path in description, content in step)
- fs_delete → EXACT NAME: fs_delete — delete a file from sandbox (path in description)

FILESYSTEM RULES:
- Use EXACTLY "fs_list" to list a directory. NOT "list_files", NOT "read_file", NOT "fs_list_dir".
- Use EXACTLY "fs_read" to read a file. NOT "read_file", NOT "file_read", NOT "fs_read_file".
- "read", "open", "show", "display", "get contents of" a file → ALWAYS use fs_read.
- "list", "show files in", "what's in" a directory → ALWAYS use fs_list.
- NEVER return empty steps for filesystem requests. Always map to fs_list or fs_read. 
- For fs_list and fs_read, put the virtual path in "description".
- Virtual paths look like: /documents/ or /documents/file.txt
- NEVER use system paths like C:\\ or /etc/ or ~/.ssh/
- NEVER use relative paths like ../ or ./

CRITICAL CONSTRAINTS:
- Use ONLY the tool names listed above. EXACT SPELLING. NO SUBSTITUTIONS.
- NEVER invent new tool names.
- If a request cannot be satisfied using AVAILABLE TOOLS, set tool to null.
- If the request is about system control, permissions, credentials,
  scheduler, vault, or execution settings, set tool to null.
- NEVER describe how a human would do it.
- NEVER mention browsers, apps, or system settings.

SECURITY RULES:
- NEVER suggest exploiting, bypassing, or breaking system safeguards.
- If such intent is detected, respond safely with tool=null.

Output JSON ONLY. No explanations. No markdown. No code blocks.

/no_think
""")

    def create_plan(self, user_input: str) -> dict:
        response = self.llm.invoke([
            self.system_prompt,
            HumanMessage(content=user_input)
        ])

        raw = response.content.strip()

        # Strip markdown code blocks if model wraps output
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        plan = json.loads(raw)

        allowed_tools = {
        "search_web", "check_inbox", "draft_reply", "speak_out_loud",
        "fs_list", "fs_read", "fs_write", "fs_delete", None
        }

        for step in plan.get("steps", []):
            if step.get("tool") not in allowed_tools:
                step["tool"] = None  # force safe fallback

        return plan
