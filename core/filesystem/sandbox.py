# core/filesystem/sandbox.py

from pathlib import Path

# Use absolute path from the start — resolve relative to this file's location
SANDBOX_ROOT = Path(__file__).parent.parent.parent / "sandboxes"

class SandboxResolver:
    @staticmethod
    def resolve(user_id: str, virtual_path: str) -> Path:
        base = (SANDBOX_ROOT / user_id).resolve()
        physical = (base / virtual_path.lstrip("/")).resolve()

        if not str(physical).startswith(str(base)):
            raise ValueError("Sandbox escape attempt")

        return physical 