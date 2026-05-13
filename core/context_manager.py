# core/context_manager.py — Phase 17 upgrade
# Builds context-aware planner input including:
#   1. SOUL.md personality overlay (prepended as system context)
#   2. User memory entries (preferences, facts, corrections)
#   3. Conversation history with compression for long sessions
#   4. Current user message
#
# Backward compatibility: build_contextual_input() keeps its existing
# 2-argument signature (user_message, conv_messages) — the new optional
# kwargs (user_id, llm) are additive and never break existing callers.
#
# Context window and truncation constants from Phase 9 are preserved
# because planner.py and other callers may depend on them (DO NOT TOUCH rule).

from typing import List, Optional

# ── Phase 9 constants — preserved for backward compat ────────────────────────
CONTEXT_WINDOW     = 6     # last N messages from history
DEFAULT_TRUNCATION = 800   # chars; raised from 400 in Phase 9 Bug 3
_FS_READ_TOOLS     = {"fs_read"}


def format_context(messages: list, llm=None) -> str:
    """
    Format conversation history as a context block for the planner.

    Phase 17 upgrade:
    - Accepts optional `llm` for context compression on long sessions.
    - Summary placeholder messages are rendered with [SUMMARY] prefix.
    - All Phase 9 formatting (tool info, fs_read no-truncate) is preserved.

    NOTE: api.py passes conv_messages_before (history BEFORE current turn).
    No [:-1] slice is needed here — the list is already clean.
    """
    if not messages:
        return ""

    # Phase 17: apply compression if the session is long and LLM is available
    working = messages
    if llm is not None:
        try:
            from core.context_compressor import should_compress, compress
            if should_compress(working):
                working = compress(working, llm)
        except Exception:
            pass  # compression failure must never break context generation

    history = working[-CONTEXT_WINDOW:]
    if not history:
        return ""

    lines = ["=== CONVERSATION HISTORY (use this as context) ==="]

    # Phase 10 Task 5: inject current browser URL
    try:
        from core.browser.session import BrowserSession
        if BrowserSession._instance is not None:
            url = BrowserSession._instance.get_current_url()
            if url and not url.startswith("about:") and url != "No page open":
                lines.append(f"BROWSER CURRENTLY AT: {url}")
    except Exception:
        pass  # never break context generation over browser state

    for msg in history:
        role       = msg.get("role", "")
        text       = msg.get("text", msg.get("content", ""))
        tools      = msg.get("tools", [])
        is_summary = msg.get("is_summary", False)

        if is_summary:
            # Compression summary placeholder
            lines.append(f"SYSTEM (SUMMARY): {text[:500]}")
        elif role == "user":
            lines.append(f"USER: {text[:300]}")
        elif role == "hermes":
            # Phase 9 Bug 3: fs_read results are never truncated
            is_fs_read = bool(set(tools) & _FS_READ_TOOLS)
            if is_fs_read:
                truncated = text
            elif len(text) > DEFAULT_TRUNCATION:
                truncated = text[:DEFAULT_TRUNCATION] + "..."
            else:
                truncated = text
            tool_info = f" [used: {', '.join(tools)}]" if tools else ""
            lines.append(f"HERMES{tool_info}: {truncated}")

    lines.append("=== END HISTORY ===")
    lines.append("")  # blank line separator (Phase 9 original)
    return "\n".join(lines)


def build_contextual_input(
    user_message: str,
    conv_messages: list,
    user_id: str = "user_1",
    llm=None,
) -> str:
    """
    Build the full context-aware input for the planner.

    Phase 17 upgrade adds:
    - SOUL.md personality prefix
    - User memory entries block
    - LLM-powered context compression for long sessions

    The function is fully backward compatible: callers that pass only
    (user_message, conv_messages) receive the same behaviour as Phase 9,
    just without the memory/soul blocks (those are empty by default).

    conv_messages must be the history BEFORE the current user turn
    (api.py snapshots this BEFORE add_message — Phase 9 bug fix preserved).

    Returns user_message unchanged if conv_messages is empty AND no
    memory/soul content is available (first message, clean session).
    """
    parts = []

    # ── 1. SOUL.md personality overlay ───────────────────────────────
    try:
        from core.user_memory import UserMemory
        um   = UserMemory(user_id)
        soul = um.format_soul_for_prompt()
        if soul:
            parts.append(soul)
    except Exception:
        um = None
        pass  # never crash planner input over memory init

    # ── 2. User memory entries ────────────────────────────────────────
    try:
        if um is not None:
            memory_block = um.format_for_prompt()
            if memory_block:
                parts.append(memory_block)
    except Exception:
        pass

    # ── 3. Conversation history (with optional compression) ───────────
    if conv_messages:
        context = format_context(conv_messages, llm)
        if context:
            parts.append(context)

    # ── 4. Current request ────────────────────────────────────────────
    parts.append(f"CURRENT REQUEST: {user_message}")

    # If only the current request is present (no history, no memory),
    # return user_message directly — no extra framing needed.
    if len(parts) == 1:
        return user_message

    return "\n\n".join(parts)
