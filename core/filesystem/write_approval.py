# core/filesystem/write_approval.py

from colorama import Fore


def write_approval_prompt(action: str, path: str, content: str = "") -> bool:
    """
    Ask the user to approve a write or delete action.
    Returns True if approved, False if rejected.
    """
    print(Fore.YELLOW + "\n⚠️  FILESYSTEM WRITE APPROVAL REQUIRED")
    print(Fore.YELLOW + "─" * 50)
    print(Fore.WHITE  + f"  Action  : {action.upper()}")
    print(Fore.WHITE  + f"  Path    : {path}")

    if action == "write" and content:
        preview = content[:120] + ("..." if len(content) > 120 else "")
        print(Fore.WHITE  + f"  Content : {preview}")

    print(Fore.YELLOW + "─" * 50)
    print(Fore.RED + "  This will modify the filesystem.")

    answer = input(Fore.CYAN + "\n  Approve? (yes/no): ").strip().lower()
    return answer in ("yes", "y")