# core/audit/audit_logger.py

import json
from pathlib import Path
from core.audit.audit_event import AuditEvent
import os
from typing import List

class AuditLogger:
    """
    Append-only audit logger.
    Must NEVER raise exceptions upward.
    """

    def __init__(self, log_path: str = "memory/audit.log"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: AuditEvent):
        try:
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event.__dict__) + "\n")
        except Exception:
            # Audit must never break the system
            pass
        
        
    def load_events(self) -> List[dict]:
        """
        Read all audit events from storage.
        """
        if not self.log_path.exists():
            return []

        with self.log_path.open("r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    

    def last_events(self, n: int = 10) -> List[dict]:
        """
        Return last N audit events.
        """
        events = self.load_events()
        return events[-n:]