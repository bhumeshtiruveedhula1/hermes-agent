# core/plugin_designer.py
# AI-assisted plugin creation — Hermes designs its own integrations

import json
import re
from pathlib import Path
from langchain_core.messages import SystemMessage, HumanMessage
from core.audit.audit_logger import AuditLogger
from core.audit.audit_event import AuditEvent

PENDING_DIR = Path("plugins/pending")
INTEGRATIONS_DIR = Path("core/integrations")


class PluginDesigner:
    """
    Uses LLM to design a plugin JSON spec and Python implementation
    from a natural language description.
    """

    def __init__(self, llm):
        self.llm = llm
        self.audit = AuditLogger()

    def design(self, description: str) -> dict:
        """
        Design a complete plugin from natural language description.
        Returns dict with plugin_spec and python_code.
        Saves to plugins/pending/ for approval.
        """

        # Step 1 — Design the JSON spec
        spec = self._design_spec(description)

        # Step 2 — Design the Python code
        code = self._design_code(spec, description)

        # Step 3 — Save to pending
        # Step 2.5 — Syntax check the generated code
        plugin_name = spec.get("name", "unknown_plugin")
        syntax_ok, syntax_error = self._check_syntax(code)

        if not syntax_ok:
            print(f"[PLUGIN DESIGNER] Syntax error in generated code: {syntax_error}")
            print(f"[PLUGIN DESIGNER] Attempting to fix...")
            code = self._fix_code(code, syntax_error)
            syntax_ok, syntax_error = self._check_syntax(code)
            if not syntax_ok:
                raise ValueError(f"Generated code has syntax errors: {syntax_error}")

        # Step 3 — Save to pending
        self._save_pending(plugin_name, spec, code)

        self.audit.log(AuditEvent(
            phase="plugin_designer",
            action="design",
            tool_name=plugin_name,
            decision="pending",
            metadata={"description": description[:120]}
        ))

        return {
            "plugin_name": plugin_name,
            "spec": spec,
            "code": code,
            "status": "pending",
            "message": f"Plugin '{plugin_name}' designed and saved to pending. Approve it from the Plugins tab."
        }

    def _design_spec(self, description: str) -> dict:
        response = self.llm.invoke([
            SystemMessage(content="""
You are a plugin designer for an AI agent platform called Hermes.
Your job is to design a plugin JSON specification from a description.

Output ONLY valid JSON in this EXACT format:
{
  "name": "plugin_name_lowercase_underscores",
  "version": "1.0",
  "status": "pending",
  "description": "One line description",
  "auth": {
    "type": "none | api_key | oauth",
    "env_var": "ENV_VAR_NAME_IF_NEEDED"
  },
  "tools": [
    {
      "name": "tool_name",
      "description": "What this tool does",
      "planner_hint": "When to use this tool and how to format the description field",
      "requires_approval": false
    }
  ],
  "executor": {
    "module": "core.integrations.plugin_name",
    "class": "PluginNameCapability",
    "action_map": {
      "tool_name": {"action": "method_name", "parse": "query | repo | path | none"}
    }
  }
}

Rules:
- Keep tool names lowercase with underscores
- Keep it simple — 2-4 tools max
- requires_approval: true for write/send/delete actions, false for read actions
- parse modes: "query" (pass description as query), "repo" (extract owner/repo), "path" (extract path), "none" (no args)
- Output JSON ONLY. No explanations.

/no_think
"""),
            HumanMessage(content=f"Design a plugin for: {description}")
        ])

        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        return json.loads(raw)

    def _design_code(self, spec: dict, description: str) -> str:
        plugin_name = spec.get("name", "plugin")
        class_name = spec.get("executor", {}).get("class", "PluginCapability")
        tools = spec.get("tools", [])
        auth = spec.get("auth", {})

        tool_list = "\n".join([f"        - {t['name']}: {t['description']}" for t in tools])
        auth_code = ""
        if auth.get("type") == "api_key":
            env_var = auth.get("env_var", "API_KEY")
            auth_code = f"""
    def _get_token(self) -> str:
        import os
        from pathlib import Path
        env_file = Path(".env")
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("{env_var}="):
                    return line.split("=", 1)[1].strip()
        token = os.environ.get("{env_var}", "")
        if not token:
            raise ValueError("{env_var} not found in .env file")
        return token
"""

        response = self.llm.invoke([
            SystemMessage(content=f"""
You are writing a Python integration module for an AI agent platform.

Write a Python class called {class_name} with an execute() method.

The class must:
1. Have __init__ that sets up self.audit = AuditLogger()
2. Have execute(self, *, action: str, query: str = "", **kwargs) -> str method
3. Handle these actions:
{tool_list}
4. Return plain text strings always
5. Log to audit using AuditLogger and AuditEvent
6. Handle exceptions gracefully — return "[ERROR] message" on failure

Import structure:
from core.audit.audit_logger import AuditLogger
from core.audit.audit_event import AuditEvent

{f'The class needs API authentication via {auth.get("env_var")}.' if auth.get("type") == "api_key" else "No authentication needed."}

Output ONLY the Python code. No explanations. No markdown.
/no_think
"""),
            HumanMessage(content=f"Write the {class_name} class for: {description}")
        ])

        code = response.content.strip()
        if code.startswith("```"):
            code = code.split("```")[1]
            if code.startswith("python"):
                code = code[6:]
            code = code.strip()

        return code

    def _save_pending(self, plugin_name: str, spec: dict, code: str):
        PENDING_DIR.mkdir(parents=True, exist_ok=True)
        INTEGRATIONS_DIR.mkdir(parents=True, exist_ok=True)

        # Save JSON spec
        spec_file = PENDING_DIR / f"{plugin_name}.json"
        spec_file.write_text(json.dumps(spec, indent=2), encoding="utf-8")

        # Save Python code
        code_file = INTEGRATIONS_DIR / f"{plugin_name}.py"
        code_file.write_text(
            f"# core/integrations/{plugin_name}.py\n# Auto-generated by Hermes Plugin Designer\n\n{code}",
            encoding="utf-8"
        )

        print(f"[PLUGIN DESIGNER] Saved: {spec_file} + {code_file}")
    def _check_syntax(self, code: str) -> tuple[bool, str]:
        """Check Python syntax without executing."""
        import ast
        try:
            ast.parse(code)
            return True, ""
        except SyntaxError as e:
            return False, str(e)

    def _fix_code(self, code: str, error: str) -> str:
        """Ask LLM to fix syntax errors in generated code."""
        response = self.llm.invoke([
            SystemMessage(content="""
You are a Python expert. Fix the syntax error in the code below.
Output ONLY the fixed Python code. No explanations. No markdown.
/no_think
"""),
            HumanMessage(content=f"Fix this syntax error: {error}\n\nCode:\n{code}")
        ])
        fixed = response.content.strip()
        if fixed.startswith("```"):
            fixed = fixed.split("```")[1]
            if fixed.startswith("python"):
                fixed = fixed[6:]
            fixed = fixed.strip()
        return fixed