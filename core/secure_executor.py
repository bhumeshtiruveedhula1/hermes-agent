# core/secure_executor.py

from langchain_core.messages import SystemMessage, HumanMessage


class SecureExecutor:
    """
    Governs tool execution with:
    - approval checks
    - permission checks
    - credential injection
    - sandbox enforcement

    This class MUST be strict.
    """

    def __init__(
        self,
        llm,
        tool_registry,
        permission_store,
        credential_vault,
        system_prompt: str
    ):
        self.llm = llm
        self.tool_registry = tool_registry
        self.permission_store = permission_store
        self.credential_vault = credential_vault
        self.system_prompt = system_prompt

    def execute_plan(self, plan: dict) -> str:
        results = []

        for step in plan.get("steps", []):
            tool_name = step.get("tool")
            description = step.get("description", "")

            # ---------------- NO TOOL: LLM REASONING ----------------
            if not tool_name:
                response = self.llm.invoke([
                    SystemMessage(content=self.system_prompt),
                    HumanMessage(content=description)
                ])
                results.append(response.content)
                continue

            # ---------------- TOOL EXISTS ----------------
            if not self.tool_registry.get(tool_name):
                results.append(f"[BLOCKED] Unknown tool: {tool_name}")
                continue

            # ---------------- TOOL APPROVED ----------------
            if not self.tool_registry.is_allowed(tool_name):
                results.append(f"[BLOCKED] Tool not approved: {tool_name}")
                continue

            # ---------------- PERMISSION CHECK ----------------
            required_permission = "default"
            if not self.permission_store.has_permission(
                tool_name, required_permission
            ):
                results.append(
                    f"[BLOCKED] Permission '{required_permission}' not granted for {tool_name}"
                )
                continue

            # ---------------- CREDENTIAL CHECK ----------------
            if self.tool_registry._tools[tool_name].requires_credentials:
                if not self.credential_vault.has_credentials(tool_name):
                    results.append(
                        f"[BLOCKED] Missing credentials for tool: {tool_name}"
                    )
                    continue

            # ---------------- SANDBOXED EXECUTION (PLACEHOLDER) ----------------
            results.append(
                f"[SANDBOX] Tool '{tool_name}' passed all checks (execution disabled)"
            )

        return "\n\n".join(results)
