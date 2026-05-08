# core/integration_builder.py — Phase 16: Auto-Integration Builder
# Orchestrates the full build pipeline for unknown integrations.
#
# IMPORTANT: Generated Python class MUST match the exact pattern in:
#   - core/integrations/slack.py   (module-level _get_token, lazy client, keyword-only execute)
#   - core/integrations/spotify.py (module-level _get_config, lazy client, keyword-only execute)
#
# Generated JSON spec MUST match the exact format in:
#   - plugins/active/slack.json    (executor.action_map with action + parse per tool)
#   - plugins/active/spotify.json  (same)
#
# Plugin.execute() calls: instance.execute(action=action, query=query, **kwargs)
# So execute() signature MUST be: execute(self, *, action: str, query: str = "", **kwargs)

import ast
import json
import subprocess
import sys
from pathlib import Path
from langchain_core.messages import SystemMessage, HumanMessage

PLUGINS_ACTIVE_DIR = Path("plugins/active")
INTEGRATIONS_DIR   = Path("core/integrations")


class IntegrationBuilder:
    """
    Builds a complete integration from API research info.
    Generates JSON spec + Python capability class,
    validates syntax, auto-fixes once if broken, installs pip packages.
    """

    def __init__(self, llm):
        self.llm = llm

    def build(self, name: str, api_info: dict) -> dict:
        """
        Build a complete integration from API research info.

        Returns:
          {
            success: bool,
            plugin_name: str,
            json_path: str | None,
            py_path: str | None,
            env_vars: dict,
            installed_packages: list,
            errors: list
          }
        """
        plugin_name = (
            name.lower()
                .strip()
                .replace(" ", "_")
                .replace("-", "_")
        )
        print(f"[BUILDER] Building: {plugin_name}")

        result = {
            "success":            False,
            "plugin_name":        plugin_name,
            "json_path":          None,
            "py_path":            None,
            "env_vars":           api_info.get("env_vars", {}),
            "installed_packages": [],
            "errors":             []
        }

        # ── Step 1: Install pip packages ──────────────────────────────
        packages = api_info.get("pip_packages", [])
        if packages:
            install_result = self._install_packages(packages)
            result["installed_packages"] = install_result["installed"]
            if install_result["failed"]:
                # Non-fatal — continue, but note the failure
                result["errors"].append(
                    f"Package install failed: {install_result['failed']}"
                )

        # ── Step 2: Generate Python capability class ──────────────────
        py_code = self._generate_python(plugin_name, api_info)
        if not py_code:
            result["errors"].append("Python code generation returned empty output")
            return result

        # ── Step 3: Validate syntax + auto-fix once if broken ─────────
        py_code = self._validate_and_fix(py_code, plugin_name)
        if not py_code:
            result["errors"].append(
                "Python syntax validation failed after 1 auto-fix attempt"
            )
            return result

        # ── Step 4: Generate JSON plugin spec ─────────────────────────
        json_spec = self._generate_json(plugin_name, api_info)
        if not json_spec:
            result["errors"].append("JSON spec generation failed")
            return result

        # ── Step 5: Write files ───────────────────────────────────────
        py_path   = INTEGRATIONS_DIR   / f"{plugin_name}.py"
        json_path = PLUGINS_ACTIVE_DIR / f"{plugin_name}.json"

        try:
            INTEGRATIONS_DIR.mkdir(parents=True, exist_ok=True)
            PLUGINS_ACTIVE_DIR.mkdir(parents=True, exist_ok=True)
            py_path.write_text(py_code,                        encoding="utf-8")
            json_path.write_text(json.dumps(json_spec, indent=2), encoding="utf-8")
            result["json_path"] = str(json_path)
            result["py_path"]   = str(py_path)
            result["success"]   = True
            print(f"[BUILDER] Written: {py_path}")
            print(f"[BUILDER] Written: {json_path}")
        except Exception as e:
            result["errors"].append(f"File write failed: {e}")
            return result

        # ── Step 6: Import test (Bug 6 — non-fatal) ───────────────────
        # Catches LLM-generated bad imports, wrong class names, or missing
        # dependencies before the hot_activator tries to load the module.
        class_name = (
            "".join(w.capitalize() for w in plugin_name.split("_"))
            + "Capability"
        )
        try:
            import importlib.util as _ilu
            _spec = _ilu.spec_from_file_location(plugin_name, py_path)
            _mod  = _ilu.module_from_spec(_spec)
            _spec.loader.exec_module(_mod)
            _cls  = getattr(_mod, class_name)
            _cls()   # instantiate — raises if missing required imports
            print(f"[BUILDER] Import test ✓ — {class_name} instantiated OK")
        except Exception as e:
            # Non-fatal: file is written, user sees the warning in the feed
            warn = f"Import test warning: {e}"
            print(f"[BUILDER] {warn}")
            result["errors"].append(warn)
            # success stays True — file is on disk and may still work at runtime

        return result

    # ── Private helpers ───────────────────────────────────────────────────────

    def _install_packages(self, packages: list) -> dict:
        """Install pip packages. Returns {installed: [...], failed: [...]}."""
        installed, failed = [], []
        for pkg in packages:
            try:
                print(f"[BUILDER] pip install {pkg} ...")
                proc = subprocess.run(
                    [sys.executable, "-m", "pip", "install", pkg, "--quiet"],
                    capture_output=True, text=True, timeout=120
                )
                if proc.returncode == 0:
                    installed.append(pkg)
                    print(f"[BUILDER]   {pkg} ✓")
                else:
                    failed.append(pkg)
                    print(f"[BUILDER]   {pkg} ✗ — {proc.stderr[:120]}")
            except subprocess.TimeoutExpired:
                failed.append(f"{pkg} (timeout)")
            except Exception as e:
                failed.append(f"{pkg} ({e})")
        return {"installed": installed, "failed": failed}

    def _generate_python(self, plugin_name: str, api_info: dict) -> str | None:
        """Generate Python capability class via LLM — must match Hermes pattern."""
        class_name = (
            "".join(w.capitalize() for w in plugin_name.split("_"))
            + "Capability"
        )

        # Build __init__ env-var reading lines
        env_vars  = api_info.get("env_vars", {})
        env_lines = "\n".join(
            f'        self.{k.lower()} = os.getenv("{k}", "")'
            for k in env_vars.keys()
        ) or "        pass  # zero-credential integration"

        endpoints  = api_info.get("key_endpoints", [])
        base_url   = api_info.get("base_url", "")
        packages   = api_info.get("pip_packages", ["requests"])
        main_pkg   = packages[0] if packages else "requests"
        auth_type  = api_info.get("auth_type", "api_key")
        notes      = api_info.get("notes", "")

        # Summarise endpoints for prompt
        ep_summary = json.dumps(
            [{"name": e["name"], "method": e.get("method","GET"),
              "path": e.get("path",""), "description": e.get("description","")}
             for e in endpoints[:6]],
            indent=2
        )

        prompt = f"""Write a Python integration class for: {plugin_name}

API details:
- Base URL: {base_url}
- Auth type: {auth_type}
- Main pip package: {main_pkg}
- Endpoints to implement: {ep_summary}
- Env vars needed: {list(env_vars.keys())}
- Notes: {notes}

You MUST follow this EXACT pattern — no deviations:

```python
# core/integrations/{plugin_name}.py
import os
import re
# import {main_pkg}  (or relevant imports)
from core.audit.audit_logger import AuditLogger
from core.audit.audit_event import AuditEvent


def _get_config() -> dict:
    \"\"\"Read credentials from environment (os.getenv).\"\"\"
    return {{
{chr(10).join(f'        "{k}": os.getenv("{k}", ""),' for k in env_vars.keys()) or '        # no credentials needed'}
    }}


class {class_name}:
    def __init__(self):
        self.audit   = AuditLogger()
        self._client = None  # lazy init

    def _get_client(self):
        \"\"\"Lazy client init — checks credentials before connecting.\"\"\"
        if self._client:
            return self._client
        cfg = _get_config()
        # Validate required credentials
        # ... set up client using main_pkg
        return self._client

    def execute(self, *, action: str, query: str = "", **kwargs) -> str:
        \"\"\"
        IMPORTANT: signature is (self, *, action, query, **kwargs) — keyword-only.
        All actions return strings — never dicts, never None.
        \"\"\"
        try:
            client = self._get_client()

            if action == "first_action":
                # implement
                return "result string"

            elif action == "second_action":
                # parse params from query using re.search()
                return "result string"

            return f"[ERROR] Unknown action: {{action}}"

        except Exception as e:
            self.audit.log(AuditEvent(
                phase="plugin", action=action,
                tool_name="{plugin_name}", decision="blocked",
                metadata={{"reason": str(e)}}
            ))
            return f"[ERROR] {plugin_name}: {{e}}"
```

STRICT RULES:
1. execute() MUST be keyword-only: def execute(self, *, action: str, query: str = "", **kwargs) -> str
2. Every branch MUST return a plain string — never dict, list, or None
3. Parse all parameters from the query string using re.search() regex
4. Wrap the entire execute() body in ONE try/except block
5. If credentials missing in _get_config(), raise ValueError with clear message
6. Keep it focused: implement exactly the {len(endpoints)} actions listed above
7. Output ONLY Python code — no markdown fences, no explanations

Actions to implement: {[e['name'] for e in endpoints[:6]]}
"""
        response = self.llm.invoke([
            SystemMessage(content=(
                "You write Python classes for an AI agent integration system. "
                "Output Python code only — no markdown, no explanation. /no_think"
            )),
            HumanMessage(content=prompt)
        ])

        code = response.content.strip()
        # Strip markdown fences if model added them
        if code.startswith("```"):
            lines = code.split("\n")
            # Remove first line (```python) and last line (```)
            start = 1
            end   = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
            code  = "\n".join(lines[start:end]).strip()

        return code if code else None

    def _validate_and_fix(self, code: str, plugin_name: str,
                           attempt: int = 0) -> str | None:
        """
        Validate Python syntax.
        Auto-fix once via LLM if broken.
        Returns fixed code or None if fix also fails.
        """
        try:
            ast.parse(code)
            print(f"[BUILDER] Syntax OK ✓")
            return code
        except SyntaxError as e:
            if attempt >= 1:
                print(f"[BUILDER] Syntax fix failed (attempt {attempt}): {e}")
                return None

            print(f"[BUILDER] Syntax error: {e} — attempting LLM fix...")
            fix_prompt = f"""Fix the Python syntax error below.
Error: {e}

Output ONLY the complete corrected Python code. No explanation. No markdown.

Code:
{code}
"""
            response = self.llm.invoke([
                SystemMessage(content=(
                    "You fix Python syntax errors. "
                    "Output corrected code only — no markdown. /no_think"
                )),
                HumanMessage(content=fix_prompt)
            ])
            fixed = response.content.strip()
            if fixed.startswith("```"):
                lines = fixed.split("\n")
                start = 1
                end   = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
                fixed = "\n".join(lines[start:end]).strip()

            return self._validate_and_fix(fixed, plugin_name, attempt + 1)

    def _generate_json(self, plugin_name: str, api_info: dict) -> dict | None:
        """
        Generate plugin JSON spec matching the exact working format.
        Mirrors: plugins/active/slack.json and spotify.json
        Structure: name, version, status, description, auth, tools[], executor{action_map}
        """
        class_name = (
            "".join(w.capitalize() for w in plugin_name.split("_"))
            + "Capability"
        )
        endpoints  = api_info.get("key_endpoints", [])
        env_vars   = api_info.get("env_vars", {})
        auth_type  = api_info.get("auth_type", "api_key")

        # Determine auth env var — first key in env_vars
        auth_env_var = next(iter(env_vars.keys()), "") if env_vars else ""

        # Decide which tools need approval (write/send/create/delete operations)
        _WRITE_WORDS = {"send", "post", "create", "delete", "write",
                        "update", "remove", "publish", "submit"}

        tools      = []
        action_map = {}

        for ep in endpoints[:8]:
            tool_name   = ep.get("name", f"{plugin_name}_action")
            description = ep.get("description", f"{plugin_name} action")
            action      = tool_name  # action name == tool name by convention

            # Approval for write-like operations
            needs_approval = any(
                w in description.lower() for w in _WRITE_WORDS
            ) or any(
                w in tool_name.lower() for w in _WRITE_WORDS
            )

            # Parse mode: query for most things, none for no-arg actions
            parse_mode = "none"
            desc_lower = description.lower()
            if any(kw in desc_lower for kw in
                   ["search", "find", "get", "fetch", "read", "list", "check"]):
                parse_mode = "query"

            planner_hint = (
                f"Use to {description.lower()}. "
                + ("No arguments needed." if parse_mode == "none"
                   else f"Format: query=your search term")
            )

            tools.append({
                "name":              tool_name,
                "description":       description,
                "planner_hint":      planner_hint,
                "requires_approval": needs_approval
            })

            action_map[tool_name] = {
                "action": action,
                "parse":  parse_mode
            }

        # Fallback if no endpoints
        if not tools:
            fallback_name = f"{plugin_name}_query"
            tools = [{
                "name":              fallback_name,
                "description":       f"Query the {plugin_name} API",
                "planner_hint":      f"Use to query {plugin_name}. Format: query=your input",
                "requires_approval": False
            }]
            action_map[fallback_name] = {"action": "query", "parse": "query"}

        spec = {
            "name":        plugin_name,
            "version":     "1.0",
            "status":      "active",
            "description": f"Auto-built {plugin_name} integration (Phase 16)",
            "auth": {
                "type":    "none" if not auth_env_var else auth_type,
                "env_var": auth_env_var
            },
            "tools": tools,
            "executor": {
                "module":     f"core.integrations.{plugin_name}",
                "class":      class_name,
                "action_map": action_map
            }
        }
        return spec
