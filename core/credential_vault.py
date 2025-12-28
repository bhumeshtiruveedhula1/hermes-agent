# core/credential_vault.py

from typing import Dict


class CredentialVault:
    """
    Secure credential storage abstraction.

    IMPORTANT:
    - LLMs NEVER access this
    - Credentials are injected ONLY at runtime
    - No raw secrets are ever logged or returned
    """

    def __init__(self):
        # Internal store (placeholder, no real secrets)
        self._store: Dict[str, Dict[str, str]] = {}

    def register_placeholder(self, tool_name: str, credential_type: str):
        """
        Register that a tool requires credentials.
        No actual secret is stored here.
        """
        if tool_name not in self._store:
            self._store[tool_name] = {}

        self._store[tool_name][credential_type] = "__PENDING__"

    def has_credentials(self, tool_name: str) -> bool:
        """
        Check if credentials exist for a tool.
        """
        return tool_name in self._store

    def inject(self, tool_name: str) -> Dict[str, str]:
        """
        Inject credentials at runtime.

        NOTE:
        - This returns a COPY
        - Real implementation will decrypt secrets here
        """
        if tool_name not in self._store:
            raise RuntimeError(
                f"No credentials registered for tool '{tool_name}'"
            )

        # Never return internal reference
        return dict(self._store[tool_name])
