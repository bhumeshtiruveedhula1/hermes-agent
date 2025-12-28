# core/audit/audit_event.py

from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime
import uuid


@dataclass
class AuditEvent:
    """
    Immutable audit record.
    NEVER contains secrets.
    """
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    session_id: Optional[str] = None

    actor: str = "hermes"              # hermes | user | system
    phase: str = ""                    # planning | tool_design | approval | execution
    action: str = ""                   # design | approve | block | execute
    tool_name: Optional[str] = None

    decision: Optional[str] = None     # allowed | blocked | rejected | approved
    reason: Optional[str] = None

    metadata: Dict = field(default_factory=dict)
