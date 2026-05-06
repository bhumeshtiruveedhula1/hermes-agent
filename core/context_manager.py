# core/context_manager.py
# Phase 9 — Conversation Context Memory
# Formats recent conversation history for injection into planner

from typing import List, Optional


# Max messages to include (user+hermes pairs)
CONTEXT_WINDOW = 6  # last 3 exchanges

# Truncation limits
# Bug 3: raised from 400 → 800. fs_read results are never truncated.
DEFAULT_TRUNCATION = 800
_FS_READ_TOOLS = {"fs_read"}


def format_context(messages: list) -> str:
    """
    Takes a PRE-CURRENT-TURN message list and returns a context string
    to prepend to the user's current message.

    NOTE: api.py now passes conv_messages_before (snapshot taken BEFORE
    saving the current user turn), so we do NOT do messages[:-1] here —
    the list is already clean.
    """
    if not messages:
        return ""

    # Keep last CONTEXT_WINDOW messages from the pre-current-turn history
    history = messages[-CONTEXT_WINDOW:]

    if not history:
        return ""

    lines = ["=== CONVERSATION HISTORY (use this as context) ==="]
    for msg in history:
        role  = msg.get("role", "")
        text  = msg.get("text", "")
        tools = msg.get("tools", [])

        if role == "user":
            lines.append(f"USER: {text}")
        elif role == "hermes":
            # Bug 3: fs_read results are never truncated — full content
            # must be available so the LLM can recall it without re-reading.
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
    lines.append("")  # blank line separator
    return "\n".join(lines)


def build_contextual_input(user_message: str, conv_messages: list) -> str:
    """
    Combines conversation history with the current user message.

    conv_messages must be the history BEFORE the current user turn
    (api.py snapshots this BEFORE calling add_message — Bug Fix for
    double-message / context ordering issues).

    Bug 2 fix: If history is empty (very first message in a conversation),
    return user_message unchanged — nothing meaningful to inject.
    """
    if not conv_messages:
        return user_message  # first message — no history to inject

    context = format_context(conv_messages)
    if not context:
        return user_message
    return f"{context}\nCURRENT REQUEST: {user_message}"
