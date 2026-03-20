# core/secure_executor.py

from langchain_core.messages import SystemMessage, HumanMessage
from core.audit.audit_logger import AuditLogger
from core.audit.audit_event import AuditEvent

FS_TOOLS = {"fs_list", "fs_read"}


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
        system_prompt: str,
        execution_enabled: bool = False  # 🔒 default OFF
    ):
        self.llm = llm
        self.tool_registry = tool_registry
        self.permission_store = permission_store
        self.credential_vault = credential_vault
        self.system_prompt = system_prompt
        self.audit = AuditLogger()
        self.execution_enabled = execution_enabled

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
                self.audit.log(AuditEvent(
                    phase="execution",
                    action="llm_reasoning",
                    decision="allowed",
                    metadata={"description": description[:120]}
                ))
                results.append(response.content)
                continue

            # ---------------- FILESYSTEM TOOLS (skip registry checks) ----------------
            if tool_name in FS_TOOLS:

                # Still enforce execution gate
                if not self.execution_enabled:
                    self.audit.log(AuditEvent(
                        phase="filesystem",
                        action="tool_call",
                        tool_name=tool_name,
                        decision="blocked",
                        reason="execution_disabled"
                    ))
                    results.append("[BLOCKED] Execution disabled by system")
                    continue

                try:
                    from core.filesystem.capability import FilesystemCapability
                    import re
                    fs = FilesystemCapability()
                    action = "list" if tool_name == "fs_list" else "read"

                    # Extract virtual path from description
                    # Planner sometimes sends "List files in /documents/" instead of just "/documents/"
                    path_match = re.search(r'(/[^\s]*)', description)
                    clean_path = path_match.group(1) if path_match else description

                    result = fs.execute(
                        action=action,
                        path=clean_path,
                        user_id="user_1",
                        agent="hermes"
                    )
                    results.append(str(result))

                except Exception as e:
                    results.append(f"[ERROR] Filesystem error: {e}")
                    self.audit.log(AuditEvent(
                        phase="filesystem",
                        action="tool_call",
                        tool_name=tool_name,
                        decision="failed",
                        reason=str(e)
                    ))

                continue  # done with this step

            # ---------------- TOOL EXISTS (standard tools) ----------------
            if not self.tool_registry.get(tool_name):
                self.audit.log(AuditEvent(
                    phase="execution",
                    action="tool_call",
                    tool_name=tool_name,
                    decision="blocked",
                    reason="unknown_tool"
                ))
                results.append(f"[BLOCKED] Unknown tool: {tool_name}")
                continue

            # ---------------- TOOL APPROVED ----------------
            if not self.tool_registry.is_allowed(tool_name):
                self.audit.log(AuditEvent(
                    phase="execution",
                    action="tool_call",
                    tool_name=tool_name,
                    decision="blocked",
                    reason="tool_not_approved"
                ))
                results.append(f"[BLOCKED] Tool not approved: {tool_name}")
                continue

            # ---------------- PERMISSION CHECK ----------------
            required_permission = "default"
            if not self.permission_store.has_permission(tool_name, required_permission):
                self.audit.log(AuditEvent(
                    phase="execution",
                    action="tool_call",
                    tool_name=tool_name,
                    decision="blocked",
                    reason="permission_denied",
                    metadata={"required_permission": required_permission}
                ))
                results.append(
                    f"[BLOCKED] Permission '{required_permission}' not granted for {tool_name}"
                )
                continue

            # ---------------- CREDENTIAL CHECK ----------------
            if self.tool_registry._tools[tool_name].requires_credentials:
                if not self.credential_vault.has_credentials(tool_name):
                    self.audit.log(AuditEvent(
                        phase="execution",
                        action="tool_call",
                        tool_name=tool_name,
                        decision="blocked",
                        reason="missing_credentials"
                    ))
                    results.append(f"[BLOCKED] Missing credentials for tool: {tool_name}")
                    continue

            # ================== 🔒 ABSOLUTE EXECUTION GATE ==================
            if not self.execution_enabled:
                self.audit.log(AuditEvent(
                    phase="execution",
                    action="tool_call",
                    tool_name=tool_name,
                    decision="blocked",
                    reason="execution_disabled"
                ))
                results.append("[BLOCKED] Execution disabled by system")
                continue
            # =================================================================

            # ---------------- REAL TOOL EXECUTION ----------------
            try:
                credentials = {}
                if self.tool_registry._tools[tool_name].requires_credentials:
                    credentials = self.credential_vault.inject(tool_name)

                tool_fn = self.tool_registry.get(tool_name)

                if tool_name == "speak_out_loud":
                    payload = {"text": description}
                else:
                    payload = {**credentials, "query": description}

                result = tool_fn.invoke(payload)
                results.append(str(result))

                self.audit.log(AuditEvent(
                    phase="execution",
                    action="tool_call",
                    tool_name=tool_name,
                    decision="executed",
                    reason="success"
                ))

            except Exception as e:
                results.append(f"[ERROR] Tool execution failed: {e}")
                self.audit.log(AuditEvent(
                    phase="execution",
                    action="tool_call",
                    tool_name=tool_name,
                    decision="failed",
                    reason=str(e)
                ))

        # 🔒 ABSOLUTE CONTRACT: ALWAYS RETURN STRING
        return "\n\n".join(results)
