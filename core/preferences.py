# core/preferences.py

import re

def detect_preferences(text: str) -> dict:
    """
    Detect explicit user preferences from input text.
    Returns a dict of {preference_key: value}
    """
    prefs = {}

    t = text.lower()

    # Writing style
    if re.search(r"\b(concise|short answer|brief)\b", t):
        prefs["verbosity"] = "low"
        prefs["writing_style"] = "concise"

    if re.search(r"\b(detailed|deep|explain clearly|in detail)\b", t):
        prefs["verbosity"] = "high"
        prefs["writing_style"] = "detailed"

    # Coding style
    if re.search(r"\b(no comments|without comments)\b", t):
        prefs["coding_style"] = "minimal, no comments"

    if re.search(r"\b(production ready|clean code|best practices)\b", t):
        prefs["coding_style"] = "clean, production-ready"

    return prefs
