from colorama import Fore

def code_approval_prompt(code: str) -> bool:
    print(Fore.CYAN + "\n🧩 GENERATED TOOL CODE\n")
    print(code)
    while True:
        choice = input("\nApprove this tool code? [y/n]: ").strip().lower()
        if choice == "y":
            return True
        if choice == "n":
            return False
