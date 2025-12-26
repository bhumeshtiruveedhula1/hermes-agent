# core/capability_detector.py

CAPABILITY_KEYWORDS = [
    "create an agent",
    "build an agent",
    "monitor",
    "automate",
    "run daily",
    "background",
    "bot",
    "system that",
    "set up an agent"
]


def is_capability_request(user_input: str) -> bool:
    text = user_input.lower()
    return any(keyword in text for keyword in CAPABILITY_KEYWORDS)
