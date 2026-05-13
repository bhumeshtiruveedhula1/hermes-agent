# core/context_compressor.py — Phase 17: Context Compression
# Compresses long conversations to stay within practical LLM context limits.
#
# Algorithm (adapted from NousResearch trajectory_compressor.py):
#   1. If messages <= THRESHOLD → return unchanged (no overhead)
#   2. Protect first PROTECT_FIRST messages (system context, initial request)
#   3. Protect last PROTECT_LAST messages (active turn)
#   4. Summarize the MIDDLE block via a single auxiliary LLM call
#   5. Replace middle with one "system (summary)" placeholder message
#
# Key difference from NousResearch version:
#   - NousResearch operates on training trajectories (token-budget driven)
#   - Hermes version is chat-session driven (message-count threshold)
#   - No tokenizer dependency — count messages, not tokens (simpler, no deps)
#   - Summary placeholder is a first-class message dict matching our schema
#
# The compressor is called inside build_contextual_input() in context_manager.py.
# It is ALWAYS given a copy of the message list — it never mutates the DB.

PROTECT_FIRST      = 3    # Always keep: sets context for the session
PROTECT_LAST       = 8    # Always keep: active conversation window
COMPRESS_THRESHOLD = PROTECT_FIRST + PROTECT_LAST + 2   # 13 messages triggers


def should_compress(messages: list) -> bool:
    """Return True if the message list is long enough to warrant compression."""
    return len(messages) > COMPRESS_THRESHOLD


def compress(messages: list, llm) -> list:
    """
    Compress messages that exceed COMPRESS_THRESHOLD.

    Returns a shorter list structured as:
      [first PROTECT_FIRST messages]
      + [SUMMARY placeholder]
      + [last PROTECT_LAST messages]

    If the LLM call for summarization fails, the summary placeholder contains
    a fallback string so compression still succeeds (shorter context is better
    than crashing).

    Args:
        messages: Full conversation message list (dicts with role, text/content).
        llm:      The manager LLM instance (langchain-compatible .invoke()).

    Returns:
        Compressed message list (may be same as input if no middle block).
    """
    if not should_compress(messages):
        return messages

    first_block = messages[:PROTECT_FIRST]
    last_block  = messages[-PROTECT_LAST:]
    middle      = messages[PROTECT_FIRST: len(messages) - PROTECT_LAST]

    if not middle:
        return messages  # No middle block to compress (shouldn't happen, but safe)

    summary_text = _summarize_middle(middle, llm)

    # Build the summary placeholder — matches our message dict schema.
    # is_summary=True tells context_manager.py to render it differently.
    summary_msg = {
        "role":       "system",
        "content":    f"[CONVERSATION SUMMARY — {len(middle)} messages compressed]\n{summary_text}",
        "text":       f"[CONVERSATION SUMMARY — {len(middle)} messages compressed]\n{summary_text}",
        "tools":      [],
        "ts":         middle[-1].get("ts", ""),
        "is_summary": True,
    }

    compressed = first_block + [summary_msg] + last_block
    print(
        f"[COMPRESS] {len(messages)} messages → {len(compressed)} "
        f"(middle {len(middle)} → 1 summary)"
    )
    return compressed


def _summarize_middle(middle: list, llm) -> str:
    """
    Ask LLM to summarize the middle block of a conversation.

    Preserves: key decisions, tools used, results, file names, anything
    the user or Hermes would need to reference later.
    Falls back gracefully on any exception.
    """
    # Build a readable text representation of the middle messages
    lines = []
    for msg in middle:
        role  = msg.get("role", "unknown").upper()
        text  = msg.get("text", msg.get("content", ""))
        tools = msg.get("tools", [])

        # Truncate very long individual messages for the summary prompt
        if len(text) > 600:
            text = text[:400] + "...[truncated]..." + text[-100:]

        tool_info = f" [tools: {', '.join(tools)}]" if tools else ""
        lines.append(f"{role}{tool_info}: {text}")

    middle_text = "\n\n".join(lines)

    system_prompt = (
        "Summarize this conversation section concisely (max 200 words).\n"
        "Preserve: key decisions, tools used, files written, important results, "
        "any data the user may reference later.\n"
        "Write in past tense, third-person (e.g. 'Hermes searched for ...').\n"
        "No bullet points. Plain prose."
    )

    try:
        from langchain_core.messages import SystemMessage, HumanMessage
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=middle_text[:3000]),   # Hard cap on prompt size
        ])
        return response.content.strip()
    except Exception as exc:
        # Compression must never crash — return a minimal fallback summary
        tool_names = []
        for m in middle:
            tool_names.extend(m.get("tools", []))
        tool_str = f" Tools mentioned: {', '.join(set(tool_names))}." if tool_names else ""
        return (
            f"[Summary unavailable: {exc}] "
            f"Previous {len(middle)} messages covered earlier parts of this conversation.{tool_str}"
        )
