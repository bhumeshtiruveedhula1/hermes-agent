# core/audit/audit_replay.py

from typing import List, Optional
from core.audit.audit_logger import AuditLogger


class AuditReplay:
    """
    Read-only audit replay.
    NEVER executes tools.
    NEVER modifies state.
    """

    def __init__(self):
        self.audit = AuditLogger()

    def last(self, n: int = 10) -> List[dict]:
        events = self.audit.load_events()
        return events[-n:]

    def filter(
        self,
        phase: Optional[str] = None,
        tool_name: Optional[str] = None,
        decision: Optional[str] = None,
    ) -> List[dict]:
        events = self.audit.load_events()
        result = []

        for e in events:
            if phase and e.get("phase") != phase:
                continue
            if tool_name and e.get("tool_name") != tool_name:
                continue
            if decision and e.get("decision") != decision:
                continue
            result.append(e)

        return result


# ✅ TOP-LEVEL FUNCTION (IMPORTABLE)
def replay_audit(limit: int = 10) -> str:
    logger = AuditLogger()
    events = logger.last_events(limit)

    if not events:
        return "No audit events."

    return "\n".join(
        f"[{e.get('timestamp')}] {e.get('phase')} | {e.get('action')} | {e.get('decision')} | {e.get('tool_name') or '-'}"
        for e in events
    )
