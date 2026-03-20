# core/filesystem/validator.py

import re

class FilesystemValidator:
    @staticmethod
    def validate_path(path: str) -> None:
        if not path:
            raise ValueError("Empty path")

        # Virtual paths must start with /
        if not path.startswith("/"):
            raise ValueError("Virtual path must start with /")

        # Block traversal attacks
        if ".." in path:
            raise ValueError("Path traversal detected")

        # Block home expansion
        if "~" in path:
            raise ValueError("Home expansion not allowed")

        # Block Windows-style paths
        if "\\" in path:
            raise ValueError("Backslashes not allowed")

        # Block null bytes
        if "\x00" in path:
            raise ValueError("Null bytes not allowed")

        # Block obvious OS root escapes
        BLOCKED_PREFIXES = ["/etc", "/sys", "/proc", "/root", "/windows", "/users"]
        path_lower = path.lower()
        for blocked in BLOCKED_PREFIXES:
            if path_lower.startswith(blocked):
                raise ValueError(f"Access to system path denied: {blocked}")
