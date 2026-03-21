# core/autocorrect.py
# Spell-check and correct user input before it hits the planner

from spellchecker import SpellChecker

# Words Hermes should NEVER correct — technical terms, names, commands
PROTECTED_WORDS = {
    # Tools
    "fs_list", "fs_read", "fs_write", "fs_delete",
    "browser_go", "browser_read", "browser_click",
    "browser_fill", "browser_shot", "browser_scroll",
    "gmail_list", "gmail_read", "gmail_send", "gmail_search",
    "calendar_list", "calendar_today", "calendar_search", "calendar_create",
    "github_repos", "github_issues", "github_prs", "github_commits",
    "telegram_send", "telegram_read",
    "weather_current", "weather_forecast",
    "search_web", "speak_out_loud",
    # Commands
    "hermes", "plugin", "plugins", "scheduler", "audit",
    "enable", "disable", "sandbox",
    # Names / places
    "bangalore", "bengaluru", "mumbai", "delhi", "hyderabad",
    "github", "gmail", "telegram", "spotify", "notion",
    "qwen", "ollama", "fastapi", "react", "vite",
    # Common tech words spellchecker gets wrong
    "api", "url", "json", "html", "css", "llm", "ai",
    "oauth", "token", "repo", "repos", "pr", "prs",
}

spell = SpellChecker()


def autocorrect(text: str) -> tuple[str, list[str]]:
    """
    Correct spelling in user input.
    Returns (corrected_text, list_of_corrections_made)
    """
    if not text or not text.strip():
        return text, []

    words = text.split()
    corrected_words = []
    corrections = []

    for word in words:
        # Strip punctuation for checking but preserve it
        clean = word.strip(".,!?;:'\"()[]{}").lower()

        # Skip protected words, short words, numbers, URLs
        if (clean in PROTECTED_WORDS
                or len(clean) <= 2
                or clean.isdigit()
                or clean.startswith("http")
                or "/" in clean
                or "_" in clean
                or "@" in clean):
            corrected_words.append(word)
            continue

        # Check if misspelled
        misspelled = spell.unknown([clean])
        if misspelled:
            correction = spell.correction(clean)
            if correction and correction != clean and len(correction) > 2:
                # Preserve original casing
                if word[0].isupper():
                    correction = correction.capitalize()
                corrected_words.append(correction)
                corrections.append(f"{clean} → {correction}")
            else:
                corrected_words.append(word)
        else:
            corrected_words.append(word)

    corrected_text = " ".join(corrected_words)
    return corrected_text, corrections