# core/hot_activator.py — Phase 16: Auto-Integration Builder
# Hot-activates an integration after credentials are detected in .env.
# Called by CredentialWatcher from a daemon thread — so broadcast uses
# asyncio.run_coroutine_threadsafe to safely cross the thread boundary.
#
# PluginLoader internals used:
#   _plugins: dict[str, Plugin]  — keyed by plugin name
#   _loaded: bool                — reset to False to force reload
#   load()                       — re-scans plugins/active/*.json

import asyncio
import importlib
import json
import sys
from pathlib import Path


class HotActivator:
    """
    Full activation sequence after credentials detected:
      1. Reload .env vars into os.environ
      2. Reload (or import) the Python capability module
      3. PluginLoader hot-reload — no server restart
      4. Run smoke test (first read-only tool)
      5. Broadcast integration_live via WebSocket
    """

    def __init__(self, broadcast_fn=None):
        """
        broadcast_fn: the async broadcast() from api.py.
        May be None when unit-testing.
        """
        self.broadcast = broadcast_fn

    def activate(self, integration_name: str) -> dict:
        """
        Full activation sequence.
        Designed to be called from a daemon thread (CredentialWatcher).
        Returns: {success: bool, message: str, tools: list, test_result: str}
        """
        print(f"[ACTIVATOR] Activating: {integration_name}")

        # Normalise to a valid Python module identifier — the builder writes files with
        # this same normalisation (spaces→_, hyphens→_, lowercase).
        # e.g. "add discord in chat" → "add_discord_in_chat"
        plugin_name = (
            integration_name.lower().strip()
            .replace(" ", "_")
            .replace("-", "_")
        )

        # ── Step 1: Reload .env into os.environ ──────────────────────
        try:
            from dotenv import load_dotenv
            load_dotenv(override=True)
            print(f"[ACTIVATOR] .env reloaded ✓")
        except ImportError:
            # python-dotenv not installed — parse manually
            self._manual_env_reload()

        # ── Step 2: Reload Python module ─────────────────────────────
        module_name = f"core.integrations.{plugin_name}"
        try:
            if module_name in sys.modules:
                module = importlib.reload(sys.modules[module_name])
                print(f"[ACTIVATOR] Reloaded module: {module_name} ✓")
            else:
                module = importlib.import_module(module_name)
                print(f"[ACTIVATOR] Imported module: {module_name} ✓")
        except Exception as e:
            msg = f"Module load failed for {module_name}: {e}"
            print(f"[ACTIVATOR] {msg}")
            self._broadcast_sync({
                "type":  "integration_failed",
                "name":  integration_name,  # human-readable for UI
                "error": msg
            })
            return {"success": False, "message": msg, "tools": [], "test_result": ""}

        # ── Step 3: Hot-reload PluginLoader ───────────────────────────
        # Remove old registration, then re-run load() on the JSON spec.
        try:
            from core.plugin_loader import PluginLoader
            # Drop the old plugin entry (if any) to avoid stale state
            PluginLoader._plugins.pop(plugin_name, None)
            # Force reload flag — load() won't run if _loaded is True
            PluginLoader._loaded = False
            # Re-load only if the JSON spec file exists
            json_path = Path(f"plugins/active/{plugin_name}.json")
            if json_path.exists():
                PluginLoader.load()   # re-scans all active plugins
                print(f"[ACTIVATOR] PluginLoader reloaded ✓ — "
                      f"plugins: {list(PluginLoader._plugins.keys())}")
            else:
                print(f"[ACTIVATOR] Warning: {json_path} not found — "
                      f"plugin not registered in loader")
        except Exception as e:
            # Non-fatal — log and continue
            print(f"[ACTIVATOR] PluginLoader reload error (non-fatal): {e}")

        # ── Step 4: Read tool list from JSON spec ─────────────────────
        tools: list[str] = []
        try:
            spec  = json.loads(
                Path(f"plugins/active/{plugin_name}.json").read_text(encoding="utf-8")
            )
            tools = [t["name"] for t in spec.get("tools", [])]
        except Exception as e:
            print(f"[ACTIVATOR] Could not read tools from spec: {e}")

        # ── Step 5: Smoke test ────────────────────────────────────────
        test_result = self._smoke_test(plugin_name, tools)
        print(f"[ACTIVATOR] Smoke test → {test_result}")

        # ── Step 6: Broadcast integration_live ───────────────────────
        self._broadcast_sync({
            "type":        "integration_live",
            "name":        integration_name,
            "tools":       tools,
            "test_result": test_result
        })

        return {
            "success":     True,
            "message":     f"✅ {integration_name} is now live! Tools: {tools}",
            "tools":       tools,
            "test_result": test_result
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    def _smoke_test(self, integration_name: str, tools: list) -> str:
        """
        Run the first read-only tool to verify credentials work.
        Uses integration_knowledge for test config where available.
        Returns a human-readable result string.
        """
        try:
            from core.integration_knowledge import get_known
            config      = get_known(integration_name)
            test_tool   = config.get("test_tool",   tools[0] if tools else "") if config else ""
            test_desc   = config.get("test_description", "") if config else ""

            if not test_tool:
                return "No smoke test configured"

            from core.plugin_loader import PluginLoader
            plugin = PluginLoader.get_plugin_for_tool(test_tool)
            if not plugin:
                return f"Plugin not found in loader for tool '{test_tool}'"

            result = plugin.execute(test_tool, test_desc, {})

            if result and not result.startswith("[ERROR]") and not result.startswith("[BLOCKED]"):
                return f"✓ Connected: {str(result)[:120]}"
            else:
                return f"⚠ Test returned: {str(result)[:120]}"

        except Exception as e:
            return f"⚠ Smoke test exception: {e}"

    def _broadcast_sync(self, event: dict):
        """
        Thread-safe broadcast — called from daemon thread.
        Uses run_coroutine_threadsafe to cross the thread→event-loop boundary.

        Bug 2 fix:
          - asyncio.get_event_loop() is deprecated in Python 3.10+ from threads
            and returns a *new* loop, not the server's running loop.
          - We use asyncio.get_running_loop() which raises RuntimeError if called
            from outside an async context — exactly the signal we need to fall back.
          - future.result(timeout=5) ensures errors surface rather than fire-and-forget.
        """
        if not self.broadcast:
            return
        try:
            # get_running_loop() returns the ACTUAL running event loop (uvicorn's loop)
            # when called via run_coroutine_threadsafe from a thread.
            # If no loop is running it raises RuntimeError — caught below.
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running loop in this thread — try get_event_loop as last resort
                loop = asyncio.get_event_loop()

            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(self.broadcast(event), loop)
                try:
                    future.result(timeout=5)   # wait up to 5s; surfaces exceptions
                except Exception as fe:
                    print(f"[ACTIVATOR] Broadcast future error: {fe}")
            else:
                # Fallback: run synchronously (e.g. unit tests)
                loop.run_until_complete(self.broadcast(event))
        except Exception as e:
            print(f"[ACTIVATOR] Broadcast error (non-fatal): {e}")


    def _manual_env_reload(self):
        """
        Fallback if python-dotenv not installed.
        Manually parses .env and updates os.environ.
        """
        import os
        env_file = Path(".env")
        if not env_file.exists():
            return
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                os.environ[key.strip()] = value.strip().strip('"').strip("'")
            print("[ACTIVATOR] .env reloaded manually (python-dotenv not available)")
        except Exception as e:
            print(f"[ACTIVATOR] Manual env reload failed: {e}")
