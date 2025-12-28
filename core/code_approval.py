# core/code_approval.py

from colorama import Fore


def code_approval_prompt(tool_code: dict) -> bool:
    print(Fore.CYAN + "\n🧩 GENERATED TOOL CODE")
    print(Fore.WHITE + f"Tool Name: {tool_code.get('tool_name')}")
    print(Fore.WHITE + f"Description: {tool_code.get('description')}\n")

    print(Fore.YELLOW + "📄 Python Code:\n")
    print(tool_code.get("python_code"))

    print(Fore.YELLOW + "\n🔐 Security Notes:")
    for note in tool_code.get("security_notes", []):
        print(f" - {note}")

    while True:
        choice = input(
            Fore.CYAN + "\nApprove this code? [y/n]: "
        ).strip().lower()

        if choice == "y":
            return True
        if choice == "n":
            return False
