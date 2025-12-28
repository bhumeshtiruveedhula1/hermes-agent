# core/permission_store.py

class PermissionStore:
    """
    Tracks user-granted permissions for tools.
    """

    def __init__(self):
        self._permissions = {}

    def grant(self, tool_name: str, permission: str):
        self._permissions.setdefault(tool_name, set()).add(permission)

    def has_permission(self, tool_name: str, permission: str) -> bool:
        return permission in self._permissions.get(tool_name, set())
