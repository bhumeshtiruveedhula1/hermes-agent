# core/approval.py

from colorama import Fore
import json
from core.audit.audit_logger import AuditLogger
from core.audit.audit_event import AuditEvent


def approval_prompt(tool_design: dict) -> bool:
    print(Fore.MAGENTA + "\n🛠️ NEW TOOL DESIGN PROPOSED")
    print(Fore.CYAN + "\n📋 Tool Design (raw JSON):\n")
    print(json.dumps(tool_design, indent=2))

    audit = AuditLogger()

    while True:
        choice = input(
            Fore.CYAN + "\nApprove this tool design? [y/n]: "
        ).strip().lower()

        if choice == "y":
            audit.log(
                AuditEvent(
                    phase="approval",
                    action="tool_design",
                    tool_name=tool_design.get("tool_name"),
                    decision="approved",
                    reason="user_decision"
                )
            )
            return True

        if choice == "n":
            audit.log(
                AuditEvent(
                    phase="approval",
                    action="tool_design",
                    tool_name=tool_design.get("tool_name"),
                    decision="rejected",
                    reason="user_decision"
                )
            )
            return False
