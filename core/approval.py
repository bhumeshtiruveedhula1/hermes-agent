# core/approval.py

from colorama import Fore


def approval_prompt(tool_design: dict) -> bool:
    print(Fore.MAGENTA + "\n🛠️ NEW TOOL DESIGN PROPOSED")
    print(Fore.WHITE + f"Tool Name : {tool_design.get('tool_name')}")
    print(Fore.WHITE + f"Purpose   : {tool_design.get('purpose')}")
    print(Fore.WHITE + f"Type      : {tool_design.get('tool_type')}")

    print(Fore.YELLOW + "\n⚠️ Risks:")
    for risk in tool_design.get("risks", []):
        print(f" - {risk}")

    while True:
        choice = input(
            Fore.CYAN + "\nApprove this tool design? [y/n/v]: "
        ).strip().lower()

        if choice == "y":
            return True
        if choice == "n":
            return False
        if choice == "v":
            print("\n📋 Full Design:\n")
            print(tool_design)
