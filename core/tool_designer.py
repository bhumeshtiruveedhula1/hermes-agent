# core/tool_designer.py

import json
from langchain_core.messages import SystemMessage, HumanMessage
from core.audit.audit_logger import AuditLogger
from core.audit.audit_event import AuditEvent


class ToolDesignerAgent:
    def __init__(self, llm):
        self.llm = llm
        self.system_prompt = SystemMessage(
            content="""
You are the ToolDesignerAgent for an autonomous AI system called Hermes.

Your responsibility is to DESIGN new tools when a user requests
automation, agents, monitoring, or background systems.

IMPORTANT:
- If this agent is invoked, a new tool IS REQUIRED.
- You MUST return COMPLETE, VALID JSON.

YOU MUST NOT:
- Execute tools
- Write files
- Request credentials
- Perform side effects

STRICT RULES:
- Writing text, explanations, essays are NOT tools
- Tools must be single-purpose
- Output JSON ONLY, no explanations

ABSOLUTE SECURITY RULES:
- NEVER include usernames, passwords, tokens, API keys, or credentials in inputs
- Assume credentials are managed securely by the platform
- Mention credentials ONLY in risks or execution_constraints
- Violating this rule is a FAILURE

Required JSON schema:

{
  "tool_required": true,
  "tool_name": "string",
  "purpose": "string",
  "use_cases": ["string"],
  "inputs": [
    {
      "name": "string",
      "type": "string",
      "sensitive": false
    }
  ],
  "actions": ["string"],
  "output": "string",
  "risks": ["string"],
  "tool_type": "side_effect | data_fetch | automation",
  "execution_constraints": [
    "requires_user_approval",
    "no_auto_execution",
    "credentials_managed_by_platform"
  ]
}
"""
        )

    def design_tool(self, user_input: str, available_tools: list) -> dict:
        """Design a new tool based on user request"""

        response = self.llm.invoke([
            self.system_prompt,
            HumanMessage(
                content=f"""
User request:
{user_input}

Available tools:
{available_tools}

Design a NEW TOOL.
Return VALID JSON ONLY.
"""
            ),
        ])

        # ---------- STRICT JSON PARSE ----------
        try:
            data = json.loads(response.content)
        except Exception:
            raise RuntimeError("❌ ToolDesignerAgent returned invalid JSON")
        # ---------- HARD SECURITY VALIDATION ----------
        for inp in data.get("inputs", []):
          name = inp.get("name", "").lower()
          if any(x in name for x in ["password", "token", "secret", "key", "username"]):
            raise RuntimeError(
              "❌ SECURITY VIOLATION: ToolDesignerAgent included credentials in inputs"
            )


        audit = AuditLogger()

        audit.log(
            AuditEvent(
                phase="tool_design",
                action="design",
                tool_name=data.get("tool_name"),
                decision="generated",
                metadata={
                    "tool_type": data.get("tool_type"),
                    "inputs_count": len(data.get("inputs", []))
                }
            )
        )


        # ---------- HARD SCHEMA VALIDATION ----------
        required_fields = [
            "tool_required",
            "tool_name",
            "purpose",
            "use_cases",
            "inputs",
            "actions",
            "output",
            "risks",
            "tool_type",
            "execution_constraints",
        ]

        missing = [
            field for field in required_fields
            if field not in data or not data[field]
        ]

        if missing:
            raise RuntimeError(
                f"❌ ToolDesignerAgent missing required fields: {missing}"
            )

        return data
