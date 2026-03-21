# core/planner.py

import json
from langchain_core.messages import SystemMessage, HumanMessage
from core.plugin_loader import PluginLoader

class PlannerAgent:
    def __init__(self, llm):
        self.llm = llm
        plugin_tools = PluginLoader.get_planner_prompt()

        self.system_prompt = SystemMessage(content=f"""
You are the PLANNER agent for an autonomous AI system called Hermes.

Your task is to convert the user request into an EXECUTABLE PLAN.

You MUST output JSON in EXACTLY this format:

{{
  "goal": "<overall goal>",
  "steps": [
    {{
      "step_id": "<string>",
      "description": "<what to do>",
      "tool": "<tool_name or null>"
    }}
  ]
}}

AVAILABLE TOOLS — EXACT NAMES, NO VARIATIONS:
- search_web        → for web research
- check_inbox       → to check email inbox
- draft_reply       → to draft an email reply
- speak_out_loud    → to speak text aloud
- fs_list           → EXACT NAME: fs_list — list files in a sandbox directory
- fs_read           → EXACT NAME: fs_read — read a file from the sandbox
- fs_write          → EXACT NAME: fs_write — write content to a sandbox file
- fs_delete         → EXACT NAME: fs_delete — delete a file from sandbox
- browser_go        → EXACT NAME: browser_go — navigate to a URL. NEVER "browser_open"
- browser_read      → EXACT NAME: browser_read — read text from current page
- browser_click     → EXACT NAME: browser_click — click an element
- browser_fill      → EXACT NAME: browser_fill — fill a form field (selector=value)
- browser_shot      → EXACT NAME: browser_shot — take a screenshot
- browser_scroll    → EXACT NAME: browser_scroll — scroll the page
- browser_close     → EXACT NAME: browser_close — close browser. NOT "close_browser"
- gmail_list        → EXACT NAME: gmail_list — list unread emails
- gmail_read        → EXACT NAME: gmail_read — read a specific email (email ID in description)
- gmail_send        → EXACT NAME: gmail_send — send email (to=x subject=x body=x)
- gmail_search      → EXACT NAME: gmail_search — search emails
- calendar_list     → EXACT NAME: calendar_list — list upcoming calendar events
- calendar_today    → EXACT NAME: calendar_today — show today's events
- calendar_search   → EXACT NAME: calendar_search — search calendar events
- calendar_create   → EXACT NAME: calendar_create — create event (title=X start=ISO end=ISO)
- github_repos      → EXACT NAME: github_repos — list my GitHub repositories
- github_repo_info  → EXACT NAME: github_repo_info — get info about a repo (owner/repo in description)
- github_issues     → EXACT NAME: github_issues — list open issues (owner/repo in description)
- github_prs        → EXACT NAME: github_prs — list open pull requests (owner/repo in description)
- github_commits    → EXACT NAME: github_commits — list recent commits (owner/repo in description)
- github_search     → EXACT NAME: github_search — search GitHub repositories
- github_create_issue → EXACT NAME: github_create_issue — create issue (repo=x title=x body=x)

FILESYSTEM RULES:
- Use EXACTLY "fs_list" to list a directory. NOT "list_files", NOT "read_file".
- Use EXACTLY "fs_read" to read a file. NOT "read_file", NOT "file_read".
- "read", "open", "show", "display", "get contents of" a file → ALWAYS use fs_read.
- "list", "show files in", "what's in" a directory → ALWAYS use fs_list.
- NEVER return empty steps for filesystem requests.
- Virtual paths look like: /documents/ or /documents/file.txt
- NEVER use system paths like C:\\ or /etc/ or ~/.ssh/

BROWSER RULES:
- To open ANY website: ALWAYS use "browser_go". NEVER "browser_open". NEVER "browser_navigate".
- browser_go description must contain the full URL
- Use browser_read immediately after browser_go to read page content
- To close: EXACTLY "browser_close"
- NEVER navigate to localhost or 127.0.0.1
- "press enter", "hit enter", "submit" after filling → use browser_press with description "Enter"
- browser_press description should be the key name: "Enter", "Tab", "Escape"

GMAIL RULES:
- "check my emails", "show emails", "list emails", "unread emails", "inbox" → ALWAYS use "gmail_list"
- "send email", "email someone", "write email" → ALWAYS use "gmail_send"
- "read email", "open email" → ALWAYS use "gmail_read"
- "search emails", "find emails" → ALWAYS use "gmail_search"
- NEVER set tool=null for email requests.

CALENDAR RULES:
- Today's date is 2026-03-21. ALWAYS use 2026 or later for dates.
- For "tomorrow" use 2026-03-22
- calendar_create format: "title=X start=2026-MM-DDTHH:MM:00 end=2026-MM-DDTHH:MM:00"
- NEVER set calendar tools to null

GITHUB RULES:
- Use github_repos to list the user's own repositories
- For repo actions put owner/repo in description
- NEVER create issues without explicit user instruction

CRITICAL CONSTRAINTS:
- Use ONLY the tool names listed above. EXACT SPELLING. NO SUBSTITUTIONS.
- NEVER invent new tool names.
- If a request cannot be satisfied using AVAILABLE TOOLS, set tool to null.
- If the request is about system control, permissions, credentials,
  scheduler, vault, or execution settings, set tool to null.
- "browser_open", "browser_navigate", "open_browser" DO NOT EXIST. Use "browser_go".
- If user says "design a plugin", "create a plugin", "add a plugin", "make a plugin" → set tool to null and description to "PLUGIN_DESIGNER_REQUEST: <description>"


SECURITY RULES:
- NEVER suggest exploiting, bypassing, or breaking system safeguards.
- If such intent is detected, respond safely with tool=null.

Output JSON ONLY. No explanations. No markdown. No code blocks.
{plugin_tools}

/no_think
""")

    def create_plan(self, user_input: str) -> dict:
        response = self.llm.invoke([
            self.system_prompt,
            HumanMessage(content=user_input)
        ])

        raw = response.content.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        plan = json.loads(raw)

        allowed_tools = {
            "search_web", "check_inbox", "draft_reply", "speak_out_loud",
            "fs_list", "fs_read", "fs_write", "fs_delete",
            "browser_go", "browser_read", "browser_click", "browser_fill",
            "browser_shot", "browser_scroll", "browser_close",
            "gmail_list", "gmail_read", "gmail_send", "gmail_search",
            "calendar_list", "calendar_today", "calendar_search", "calendar_create",
            "github_repos", "github_repo_info", "github_issues", "github_prs",
            "github_commits", "github_search", "github_create_issue",
            "browser_press",
            None
        } | PluginLoader.get_all_tool_names()

        for step in plan.get("steps", []):
            if step.get("tool") not in allowed_tools:
                step["tool"] = None

        return plan