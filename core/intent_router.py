# core/intent_router.py

import re


SYSTEM_CONTROL_KEYWORDS = [
    "enable", "disable", "revoke", "grant",
    "permission", "permissions",
    "scheduler", "schedule",
    "vault", "credential",
    "execution_enabled", "execution",
    "agent", "agents"
]


def is_system_control_request(user_input: str) -> bool:
    text = user_input.lower()
    return any(keyword in text for keyword in SYSTEM_CONTROL_KEYWORDS)
