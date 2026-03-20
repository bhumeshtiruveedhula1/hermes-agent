# core/filesystem/capability.py

from core.filesystem.validator import FilesystemValidator
from core.filesystem.sandbox import SandboxResolver
from core.filesystem.adapter_local import LocalFilesystemAdapter
from core.audit.audit_event import AuditEvent
from core.audit.audit_logger import AuditLogger

class FilesystemCapability:
    def __init__(self):
        self.adapter = LocalFilesystemAdapter()
        self.audit = AuditLogger()

    def execute(self, *, action: str, path: str, user_id: str, agent: str):
        try:
            FilesystemValidator.validate_path(path)
            physical_path = SandboxResolver.resolve(user_id, path)

            if action == "list":
                result = self.adapter.list(physical_path)
            elif action == "read":
                result = self.adapter.read(physical_path)
            else:
                raise ValueError("Unsupported filesystem action")

            self.audit.log(AuditEvent(
                phase="filesystem",
                action=action,
                tool_name="filesystem",
                decision="allowed",
                metadata={"user_id": user_id, "agent": agent, "path": path}
            ))

            return result

        except Exception as e:
            self.audit.log(AuditEvent(
                phase="filesystem",
                action=action,
                tool_name="filesystem",
                decision="blocked",
                metadata={"user_id": user_id, "agent": agent, "path": path, "reason": str(e)}
            ))
            return f"[BLOCKED] {str(e)}"