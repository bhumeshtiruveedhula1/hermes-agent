# core/plugin_loader.py
# Dynamic plugin system — reads JSON specs and auto-wires tools

import json
import importlib
import re
from pathlib import Path
from colorama import Fore
from core.audit.audit_logger import AuditLogger
from core.audit.audit_event import AuditEvent

PLUGINS_DIR = Path("plugins")
ACTIVE_DIR  = PLUGINS_DIR / "active"
PENDING_DIR = PLUGINS_DIR / "pending"



class PluginTool:
    """Represents a single tool from a plugin."""
    def __init__(self, data: dict, plugin_name: str):
        self.name             = data["name"]
        self.description      = data["description"]
        self.planner_hint     = data.get("planner_hint", data["description"])
        self.requires_approval= data.get("requires_approval", False)
        self.plugin_name      = plugin_name


class Plugin:
    """Represents a loaded plugin with all its tools and executor."""
    def __init__(self, spec: dict):
        self.name        = spec["name"]
        self.version     = spec.get("version", "1.0")
        self.description = spec.get("description", "")
        self.status      = spec.get("status", "active")
        self.auth        = spec.get("auth", {})
        self.tools       = [PluginTool(t, self.name) for t in spec.get("tools", [])]
        self.executor    = spec.get("executor", {})
        self._instance   = None

    def get_tool_names(self) -> set:
        return {t.name for t in self.tools}

    def get_tool(self, name: str) -> PluginTool | None:
        return next((t for t in self.tools if t.name == name), None)

    def _get_instance(self):
        if self._instance:
            return self._instance
        module_path = self.executor.get("module")
        class_name  = self.executor.get("class")
        if not module_path or not class_name:
            raise ValueError(f"Plugin '{self.name}' has no executor defined.")
        module = importlib.import_module(module_path)
        cls    = getattr(module, class_name)
        self._instance = cls()
        return self._instance

    def execute(self, tool_name: str, description: str, step: dict) -> str:
        """Execute a tool from this plugin."""
        audit  = AuditLogger()
        action_map = self.executor.get("action_map", {})

        if tool_name not in action_map:
            return f"[ERROR] Tool '{tool_name}' not found in plugin '{self.name}'"

        tool_spec  = action_map[tool_name]
        action     = tool_spec.get("action", tool_name)
        parse_mode = tool_spec.get("parse", "")

        # Parse arguments from description based on parse mode
        kwargs = {"action": action}

        if parse_mode == "query":
            import re
            query = description
            # Remove everything before the actual location/query
            # Strip common action prefixes
            cleaned = re.sub(
                r'^(?:get|check|show|fetch|find|tell me|what is|what\'s|give me)\s+',
                '', query, flags=re.IGNORECASE
            )
            cleaned = re.sub(
                r'^(?:the\s+)?(?:current\s+)?(?:weather|forecast|temperature)\s+(?:for|in|of|at)\s+',
                '', cleaned, flags=re.IGNORECASE
            )
            cleaned = re.sub(
                r'^(?:\d+-day\s+)?forecast\s+(?:for|in)\s+',
                '', cleaned, flags=re.IGNORECASE
            )
            kwargs["query"] = cleaned.strip() or query

        elif parse_mode == "repo":
            repo_match = re.search(r'[\w\-\.]+/[\w\-\.]+', description)
            kwargs["repo"] = repo_match.group(0) if repo_match else description.strip()

        elif parse_mode == "repo+title+body":
            repo_match  = re.search(r'repo=([\w\-\.]+/[\w\-\.]+)', description)
            title_match = re.search(r'title=(.+?)(?:\s+body=|$)', description)
            body_match  = re.search(r'body=(.+)', description)
            kwargs["repo"]  = repo_match.group(1).strip()  if repo_match  else ""
            kwargs["title"] = title_match.group(1).strip() if title_match else ""
            kwargs["body"]  = body_match.group(1).strip()  if body_match  else ""

        elif parse_mode == "path":
            path_match = re.search(r'(/[^\s]+)', description)
            kwargs["path"] = path_match.group(1) if path_match else description

        elif parse_mode == "email_send":
            to_match      = re.search(r'to=([^\s]+)',          description)
            subject_match = re.search(r'subject=(.+?)(?:body=|$)', description)
            body_match    = re.search(r'body=(.+)',             description)
            kwargs["to"]      = to_match.group(1).strip()      if to_match      else ""
            kwargs["subject"] = subject_match.group(1).strip() if subject_match else ""
            kwargs["body"]    = body_match.group(1).strip()    if body_match    else ""

        elif parse_mode == "msg_id":
            kwargs["msg_id"] = description.strip().split()[-1]

        # Execute
        try:
            instance = self._get_instance()
            result   = instance.execute(**kwargs)

            audit.log(AuditEvent(
                phase="plugin",
                action=action,
                tool_name=tool_name,
                decision="allowed",
                metadata={"plugin": self.name}
            ))
            return result

        except Exception as e:
            audit.log(AuditEvent(
                phase="plugin",
                action=action,
                tool_name=tool_name,
                decision="failed",
                metadata={"plugin": self.name, "reason": str(e)}
            ))
            return f"[ERROR] Plugin '{self.name}' execution failed: {e}"


class PluginLoader:
    """
    Singleton that loads all active plugins at startup.
    Auto-wires tools into planner, critic, and executor.
    """
    _plugins: dict[str, Plugin] = {}
    _loaded = False

    @classmethod
    def load(cls):
        """Load all active plugins from plugins/active/"""
        if cls._loaded:
            return
        ACTIVE_DIR.mkdir(parents=True, exist_ok=True)
        PENDING_DIR.mkdir(parents=True, exist_ok=True)

        for spec_file in ACTIVE_DIR.glob("*.json"):
            try:
                spec   = json.loads(spec_file.read_text())
                plugin = Plugin(spec)
                cls._plugins[plugin.name] = plugin
                print(Fore.GREEN + f"   [+] Plugin loaded: {plugin.name} ({len(plugin.tools)} tools)")
            except Exception as e:
                print(Fore.RED + f"   [!] Failed to load plugin {spec_file.name}: {e}")

        cls._loaded = True

    @classmethod
    def get_all_tool_names(cls) -> set:
        cls.load()
        tools = set()
        for plugin in cls._plugins.values():
            tools.update(plugin.get_tool_names())
        return tools

    @classmethod
    def get_plugin_for_tool(cls, tool_name: str) -> Plugin | None:
        cls.load()
        for plugin in cls._plugins.values():
            if tool_name in plugin.get_tool_names():
                return plugin
        return None

    @classmethod
    def get_planner_prompt(cls) -> str:
        """Generate the tools section for the planner system prompt."""
        cls.load()
        if not cls._plugins:
            return ""
        lines = ["\n# PLUGIN TOOLS (dynamically loaded):"]
        for plugin in cls._plugins.values():
            lines.append(f"\n## {plugin.name.upper()} PLUGIN")
            for tool in plugin.tools:
                lines.append(f"- {tool.name} → {tool.planner_hint}")
        return "\n".join(lines)

    @classmethod
    def get_all_plugins(cls) -> list[dict]:
        cls.load()
        result = []
        for plugin in cls._plugins.values():
            result.append({
                "name":        plugin.name,
                "version":     plugin.version,
                "description": plugin.description,
                "status":      plugin.status,
                "tools":       [t.name for t in plugin.tools],
                "tool_count":  len(plugin.tools),
            })
        return result

    @classmethod
    def get_pending_plugins(cls) -> list[dict]:
        result = []
        for spec_file in PENDING_DIR.glob("*.json"):
            try:
                spec = json.loads(spec_file.read_text(encoding="utf-8"))
                result.append(spec)
            except Exception:
                pass
        return result

    @classmethod
    def approve_plugin(cls, plugin_name: str) -> tuple[bool, str]:
        """Move plugin from pending to active — with import test."""
        pending_file = PENDING_DIR / f"{plugin_name}.json"
        active_file  = ACTIVE_DIR  / f"{plugin_name}.json"

        if not pending_file.exists():
            return False, "Plugin not found in pending"

        # Read spec
        spec = json.loads(pending_file.read_text(encoding="utf-8"))
        module_path = spec.get("executor", {}).get("module", "")
        class_name  = spec.get("executor", {}).get("class", "")

        # Safe import test
        if module_path and class_name:
            ok, error = cls._test_import(module_path, class_name)
            if not ok:
                return False, f"Import test failed: {error}"

        # All good — move to active
        active_file.write_text(pending_file.read_text(encoding="utf-8"), encoding="utf-8")
        pending_file.unlink()
        cls._loaded = False
        cls.load()
        return True, "ok"

    @classmethod
    def _test_import(cls, module_path: str, class_name: str) -> tuple[bool, str]:
        """Try importing the plugin module safely."""
        import importlib
        try:
            module = importlib.import_module(module_path)
            cls_obj = getattr(module, class_name, None)
            if cls_obj is None:
                return False, f"Class '{class_name}' not found in module"
            return True, ""
        except Exception as e:
            return False, str(e)

    @classmethod
    def reject_plugin(cls, plugin_name: str) -> bool:
        pending_file = PENDING_DIR / f"{plugin_name}.json"
        if not pending_file.exists():
            return False
        pending_file.unlink()
        return True
    
    @classmethod
    def disable_plugin(cls, plugin_name: str) -> bool:
        active_file = ACTIVE_DIR / f"{plugin_name}.json"
        if not active_file.exists():
            return False

        # Backup before disabling
        backup_dir = PLUGINS_DIR / "backups"
        backup_dir.mkdir(exist_ok=True)
        backup_file = backup_dir / f"{plugin_name}_backup.json"
        backup_file.write_text(active_file.read_text(encoding="utf-8"), encoding="utf-8")

        spec = json.loads(active_file.read_text(encoding="utf-8"))
        spec["status"] = "disabled"
        active_file.write_text(json.dumps(spec, indent=2), encoding="utf-8")
        cls._plugins.pop(plugin_name, None)
        print(f"[PLUGIN LOADER] Plugin '{plugin_name}' disabled. Backup saved.")
        return True

    @classmethod
    def restore_plugin(cls, plugin_name: str) -> bool:
        """Restore a disabled plugin from backup."""
        backup_dir  = PLUGINS_DIR / "backups"
        backup_file = backup_dir / f"{plugin_name}_backup.json"
        active_file = ACTIVE_DIR / f"{plugin_name}.json"

        if not backup_file.exists():
            return False

        spec = json.loads(backup_file.read_text(encoding="utf-8"))
        spec["status"] = "active"
        active_file.write_text(json.dumps(spec, indent=2), encoding="utf-8")
        cls._loaded = False
        cls.load()
        print(f"[PLUGIN LOADER] Plugin '{plugin_name}' restored from backup.")
        return True

    @classmethod
    def disable_plugin(cls, plugin_name: str) -> bool:
        active_file = ACTIVE_DIR / f"{plugin_name}.json"
        if not active_file.exists():
            return False
        spec = json.loads(active_file.read_text())
        spec["status"] = "disabled"
        active_file.write_text(json.dumps(spec, indent=2))
        cls._plugins.pop(plugin_name, None)
        return True