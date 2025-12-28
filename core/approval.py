# core/approval.py
from colorama import Fore
import json


def approval_prompt(tool_design: dict) -> bool:
    print(Fore.MAGENTA + "\n🛠️ NEW TOOL DESIGN PROPOSED")
    print(Fore.CYAN + "\n📋 Tool Design (raw JSON):\n")
    print(json.dumps(tool_design, indent=2))

    while True:
        choice = input(
            Fore.CYAN + "\nApprove this tool design? [y/n]: "
        ).strip().lower()

        if choice == "y":
            return True
        if choice == "n":
            return False
