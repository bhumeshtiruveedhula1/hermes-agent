# core/auto_tool_builder.py
# When Hermes hits an unknown tool, this kicks in.

import json
from colorama import Fore
from core.tool_designer import ToolDesignerAgent
from core.tool_registry import ToolRegistry, ToolMeta
from core.audit.audit_logger import AuditLogger
from core.audit.audit_event import AuditEvent


class AutoToolBuilder:
    """
    Automatically designs and registers tools when Hermes
    encounters an unknown tool name.

    SAFE MODE ON  → design + approval prompt → register + run
    SAFE MODE OFF → design → auto-register → run
    """

    def __init__(self, llm, tool_registry: ToolRegistry, safe_mode: bool = True):
        self.llm = llm
        self.tool_registry = tool_registry
        self.designer = ToolDesignerAgent(llm)
        self.audit = AuditLogger()
        self.safe_mode = safe_mode

    def attempt(self, tool_name: str, description: str) -> dict | None:
        """
        Try to auto-build a tool for the given tool_name.
        Returns tool design dict if successful, None if rejected/failed.
        """
        print(Fore.YELLOW + f"\n⚡ Unknown tool '{tool_name}' — Auto-builder activated.")

        try:
            # Ask LLM to design the tool
            user_input = f"Create a tool called '{tool_name}' that does: {description}"

            tool_design = self.designer.design_tool(
                user_input=user_input,
                available_tools=self.tool_registry.list_tools(),
                forced_tool_type="simple",
                allow_credentials=False
            )

            # Force the tool name to match what was requested
            tool_design["tool_name"] = tool_name

            print(Fore.CYAN + f"\n📐 Auto-designed tool: {tool_name}")
            print(Fore.CYAN + f"   Purpose: {tool_design.get('purpose', 'unknown')}")

            if self.safe_mode:
                # Show design and ask approval
                print(Fore.YELLOW + "\n⚠️  SAFE MODE — Approval required:")
                print(Fore.WHITE + json.dumps(tool_design, indent=2)[:400])
                answer = input(Fore.CYAN + "\n  Approve this tool? (yes/no): ").strip().lower()

                if answer not in ("yes", "y"):
                    print(Fore.RED + "❌ Auto-tool rejected.")
                    self.audit.log(AuditEvent(
                        phase="auto_build",
                        action="tool_design",
                        tool_name=tool_name,
                        decision="blocked",
                        reason="user_rejected"
                    ))
                    return None

            # Register the tool as inactive (no function — LLM will handle execution)
            self.tool_registry.register_generated_tool(
                name=tool_name,
                function=None
            )

            self.audit.log(AuditEvent(
                phase="auto_build",
                action="tool_registered",
                tool_name=tool_name,
                decision="allowed",
                metadata={
                    "safe_mode": self.safe_mode,
                    "purpose": tool_design.get("purpose", "")
                }
            ))

            print(Fore.GREEN + f"✅ Tool '{tool_name}' registered.")
            return tool_design

        except Exception as e:
            print(Fore.RED + f"❌ Auto-build failed: {e}")
            self.audit.log(AuditEvent(
                phase="auto_build",
                action="tool_design",
                tool_name=tool_name,
                decision="failed",
                reason=str(e)
            ))
            return None