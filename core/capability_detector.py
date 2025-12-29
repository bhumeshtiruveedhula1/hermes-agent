# core/capability_detector.py

from enum import Enum


class CapabilityType(str, Enum):
    DATA_FETCH = "data_fetch"
    AUTOMATION = "automation"
    CREDENTIAL_REQUIRED = "credential_required"


DATA_FETCH_KEYWORDS = [
    "news",
    "summarize",
    "summary",
    "research",
    "monitor",
    "track",
    "watch",
    "daily news",
    "ai news",
    "top news"
]

CREDENTIAL_KEYWORDS = [
    "login",
    "password",
    "gmail",
    "email",
    "inbox",
    "account",
    "oauth",
    "credentials"
]


def detect_capability(user_input: str) -> CapabilityType:
    text = user_input.lower()

    # 🚨 Explicit credential intent → HARD BLOCK LATER
    for kw in CREDENTIAL_KEYWORDS:
        if kw in text:
            return CapabilityType.CREDENTIAL_REQUIRED

    # ✅ Safe autonomous agents
    for kw in DATA_FETCH_KEYWORDS:
        if kw in text:
            return CapabilityType.DATA_FETCH

    # Default: automation but still safe
    return CapabilityType.AUTOMATION


def is_capability_request(user_input: str) -> bool:
    text = user_input.lower()
    return "create agent" in text or "create an agent" in text
