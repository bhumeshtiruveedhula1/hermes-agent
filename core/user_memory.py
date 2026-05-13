# core/user_memory.py — Phase 17: User Profile Memory & Personality
# Manages two distinct memory layers:
#   1. memory_entries — specific facts (preferences, corrections, personal facts)
#      stored in SQLite; injected into every planner call.
#   2. user_profile / soul_md — freeform Markdown profiles stored in SQLite;
#      soul_md is a personality overlay that prepends the planner system prompt.
#
# Security: all user-provided content is scanned for prompt injection patterns
# before storage. This is NON-NEGOTIABLE — memory poisoning would compromise
# every future interaction.
#
# Inspired by NousResearch/hermes-agent tools/memory_tool.py's MEMORY.md
# pattern. Key adaptation: we use SQLite (not markdown files) for dedup,
# per-user isolation, and structured category grouping.

import json
import re
from core.hermes_db import get_db

# ---------------------------------------------------------------------------
# Injection threat patterns — rejects any content that looks like a prompt
# injection attempt. Pattern source: OWASP LLM Top 10 + community research.
# ---------------------------------------------------------------------------
_THREAT_PATTERNS = [
    r"ignore\s+(?:all\s+)?previous\s+instructions",
    r"new\s+instructions\s*:",
    r"you\s+are\s+now\s+(?:a\s+)?(?:different|new|another)",
    r"disregard\s+(?:all|your|the)",
    r"system\s+prompt\s*:",
    r"forget\s+(?:everything|all|your)",
    # Invisible unicode (zero-width spaces, directional overrides, etc.)
    r"[\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff]",
    # Credential exfiltration via shell expansion
    r"(?:curl|wget)\s.*\$\{.*(?:KEY|TOKEN|SECRET|PASSWORD)",
    # SSH / AWS key paths
    r"~/\.(?:ssh|aws|gnupg)",
    r"/etc/(?:passwd|shadow|hosts)",
    # Classic DAN-style jailbreaks
    r"DAN\s+mode",
    r"developer\s+mode\s+enabled",
    r"jailbreak",
]
_THREAT_RE = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in _THREAT_PATTERNS]

MAX_MEMORY_ENTRY_LENGTH = 500   # characters


def _is_safe(content: str) -> tuple:
    """
    Returns (is_safe: bool, reason: str).
    Rejects content matching injection patterns or exceeding length limit.
    """
    if len(content) > MAX_MEMORY_ENTRY_LENGTH:
        return False, f"Memory entry too long ({len(content)} chars, max {MAX_MEMORY_ENTRY_LENGTH})"
    for pattern_re in _THREAT_RE:
        if pattern_re.search(content):
            return False, f"Content rejected: matches injection pattern"
    return True, ""


class UserMemory:
    """
    Manages user memory for a single user_id.

    Usage:
        um = UserMemory("user_1")
        um.add("User prefers Python", "preference")
        block = um.format_for_prompt()     # inject into planner input
        soul  = um.format_soul_for_prompt() # prepend to system prompt
    """

    def __init__(self, user_id: str = "user_1"):
        self.user_id = user_id
        self.db      = get_db()

    # ── Memory Entries ────────────────────────────────────────────────

    def add(self, content: str, category: str = "general") -> dict:
        """
        Add a memory entry after security scan.
        Returns the saved entry dict, or {"error": reason} if rejected.
        """
        content = content.strip()
        if not content:
            return {"error": "Empty content"}
        safe, reason = _is_safe(content)
        if not safe:
            return {"error": reason}
        return self.db.add_memory(content, self.user_id, category)

    def get_all(self) -> list:
        """Return all memory entries for this user, newest first."""
        return self.db.get_memory(self.user_id)

    def delete(self, entry_id: str):
        """Delete a specific memory entry by ID."""
        self.db.delete_memory(entry_id)

    def clear_category(self, category: str):
        """Bulk-delete all entries of a given category (e.g. 'fact')."""
        entries = self.get_all()
        for e in entries:
            if e.get("category") == category:
                self.delete(e["id"])

    def format_for_prompt(self) -> str:
        """
        Format memory entries as a structured context block for the planner.
        Groups by category. Returns empty string if no entries exist.

        Example output:
            === USER MEMORY (use this to personalise responses) ===

            Preferences:
              • User prefers Python over JavaScript
              • User wants concise responses without bullet points

            Facts:
              • User's name is Bhumesh
            === END USER MEMORY ===
        """
        entries = self.get_all()
        if not entries:
            return ""

        by_cat: dict = {}
        for e in entries:
            cat = e.get("category", "general")
            by_cat.setdefault(cat, []).append(e["content"])

        _LABELS = {
            "preference": "Preferences",
            "fact":       "Facts",
            "correction": "Corrections",
            "general":    "General",
        }

        lines = ["=== USER MEMORY (use this to personalise responses) ==="]
        for cat, items in by_cat.items():
            lines.append(f"\n{_LABELS.get(cat, cat.title())}:")
            for item in items:
                lines.append(f"  \u2022 {item}")
        lines.append("=== END USER MEMORY ===")
        return "\n".join(lines)

    # ── User Profile (Markdown) ───────────────────────────────────────

    def get_profile_md(self) -> str:
        return self.db.get_profile(self.user_id).get("profile_md", "")

    def update_profile_md(self, content: str):
        self.db.update_profile(self.user_id, profile_md=content)

    # ── SOUL.md Personality ───────────────────────────────────────────

    def get_soul_md(self) -> str:
        return self.db.get_profile(self.user_id).get("soul_md", "")

    def update_soul_md(self, content: str):
        self.db.update_profile(self.user_id, soul_md=content)

    def format_soul_for_prompt(self) -> str:
        """
        Format SOUL.md as a system-prompt prefix block.
        Returns empty string if SOUL.md is not set.
        """
        soul = self.get_soul_md().strip()
        if not soul:
            return ""
        return f"=== PERSONALITY OVERRIDE ===\n{soul}\n=== END PERSONALITY ===\n"

    # ── Proactive Extraction ──────────────────────────────────────────

    def proactive_extract(
        self,
        user_message: str,
        hermes_response: str,
        llm,
    ) -> list:
        """
        After each conversation turn, ask the LLM to identify facts worth
        remembering about the user from this exchange.

        - Inspired by NousResearch memory nudge system.
        - Saves max 3 facts per turn to avoid flooding memory.
        - Each fact is security-scanned before storage.
        - Runs silently; never crashes chat flow (all exceptions caught).

        Returns list of strings that were actually saved.
        """
        prompt = (
            "Scan this conversation turn for facts worth saving about the user.\n"
            "Save ONLY: explicit preferences, personal facts (name, location, job), "
            "corrections to Hermes behaviour, strong opinions.\n"
            "Skip: trivial info, things easily re-discovered, session ephemera.\n\n"
            f"User said: {user_message[:300]}\n"
            f"Hermes said: {hermes_response[:300]}\n\n"
            "Output a JSON array of strings (facts to save), or [] if nothing important.\n"
            "Each string max 100 chars. Examples:\n"
            '  ["User prefers concise responses", "User\'s GitHub is bhumeshtiruveedhula1"]\n'
            "Output JSON only."
        )
        try:
            from langchain_core.messages import SystemMessage, HumanMessage
            response = llm.invoke([
                SystemMessage(content="Extract memorable user facts. Output JSON array only."),
                HumanMessage(content=prompt),
            ])
            raw = response.content.strip()
            # Strip markdown code fences if LLM wrapped the JSON
            if raw.startswith("```"):
                raw = "\n".join(raw.split("\n")[1:-1])
            facts = json.loads(raw)
            if not isinstance(facts, list):
                return []

            saved = []
            for fact in facts[:3]:  # cap at 3 per turn
                if isinstance(fact, str) and len(fact.strip()) > 10:
                    result = self.add(fact.strip(), "preference")
                    if "error" not in result and not result.get("duplicate"):
                        saved.append(fact.strip())
            return saved
        except Exception:
            return []   # proactive extraction must never crash chat flow
