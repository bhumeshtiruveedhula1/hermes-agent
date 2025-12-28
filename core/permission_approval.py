# core/permission_approval.py

from colorama import Fore


def permission_prompt(tool_name: str, permissions: list) -> bool:
    print(Fore.MAGENTA + "\n🔐 Permission Request")
    print(Fore.WHITE + f"Tool: {tool_name}")
    print(Fore.WHITE + "Requested permissions:")

    for perm in permissions:
        print(Fore.YELLOW + f" - {perm}")

    while True:
        choice = input(
            Fore.CYAN + "\nAllow? [y] allow / [n] deny: "
        ).strip().lower()

        if choice == "y":
            return True
        if choice == "n":
            return False
