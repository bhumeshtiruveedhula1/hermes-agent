# core/permissions.py

from typing import Dict, List


class PermissionStore:
    """
    Stores user-approved permissions for tools.
    Permissions are explicit, revocable, and tool-scoped.
    """

    def __init__(self):
        # Example:
        # {
        #   "check_inbox": ["read_email"],
        #   "daily_gmail_monitor": ["read_email", "background_execution"]
        # }
        self._permissions: Dict[str, List[str]] = {}

    def has_permission(self, tool_name: str, permission: str) -> bool:
        return permission in self._permissions.get(tool_name, [])

    def grant(self, tool_name: str, permissions: List[str]):
        self._permissions[tool_name] = permissions

    def list_permissions(self, tool_name: str) -> List[str]:
        return self._permissions.get(tool_name, [])
