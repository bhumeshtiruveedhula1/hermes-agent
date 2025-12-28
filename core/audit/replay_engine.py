# core/audit/replay_engine.py

import json
from pathlib import Path


class ReplayEngine:
    """
    Safe replay of audit events.
    NO execution, NO credentials.
    """

    def __init__(self, log_path: str = "memory/audit.log"):
        self.log_path = Path(log_path)

    def replay_last(self, n: int = 5):
        if not self.log_path.exists():
            return []

        with self.log_path.open("r", encoding="utf-8") as f:
            lines = f.readlines()[-n:]

        return [json.loads(line) for line in lines]
