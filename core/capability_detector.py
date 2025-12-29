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


def is_capability_request(text: str) -> bool:
    text = text.lower()
    triggers = [
        "create agent",
        "create an agent",
        "build agent",
        "summarize news",
        "summarises news",
        "summarise the news",
        "automation",
    ]
    return any(t in text for t in triggers)
