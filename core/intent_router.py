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


def is_system_control_request(text: str) -> bool:
    text = text.lower().strip()
    return (
        text == "list agents"
        or text == "run scheduler"
        or text == "audit replay"
        or text.startswith("enable agent")
        or text.startswith("disable agent")
    )
