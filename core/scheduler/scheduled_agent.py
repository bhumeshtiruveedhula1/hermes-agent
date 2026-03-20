from dataclasses import dataclass, field
from typing import List, Dict, Any
from datetime import datetime

@dataclass
class ScheduledAgent:
    """
    Represents a background agent that runs on a schedule.
    This class holds STATE only.
    """
    name: str
    tool_name: str
    schedule: str              # "daily" | "interval:60"
    permissions: List[str]
    enabled: bool = False
    last_run_at: datetime | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)

