# core/audit/audit_logger.py

import json
from pathlib import Path
from core.audit.audit_event import AuditEvent


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
