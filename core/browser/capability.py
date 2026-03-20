# core/browser/capability.py

import asyncio
from core.browser.engine import BrowserEngine
from core.audit.audit_logger import AuditLogger
from core.audit.audit_event import AuditEvent


class BrowserCapability:
    """
    Safe wrapper around BrowserEngine.
    All actions are audited.
    Blocks dangerous URLs.
    """

    BLOCKED_DOMAINS = [
        "localhost", "127.0.0.1", "0.0.0.0",
        "169.254", "192.168", "10.0", "172.16"
    ]

    def __init__(self):
        self.engine = BrowserEngine(headless=False)
        self.audit = AuditLogger()
        self._started = False

    def _check_url(self, url: str):
        for blocked in self.BLOCKED_DOMAINS:
            if blocked in url:
                raise ValueError(f"Access to local network blocked: {url}")

    async def _ensure_started(self):
        if not self._started:
            await self.engine.start()
            self._started = True

    def execute(self, *, action: str, target: str = "", value: str = "", agent: str = "hermes") -> str:
        """Sync wrapper — runs async browser actions safely from any context."""
        import threading

        result_container = {"result": None, "error": None}

        def run_in_thread():
            import asyncio
            # Windows requires ProactorEventLoop for subprocess (Playwright)
            loop = asyncio.ProactorEventLoop()
            asyncio.set_event_loop(loop)
            try:
                result_container["result"] = loop.run_until_complete(
                    self._execute_async(action=action, target=target, value=value, agent=agent)
                )
            except Exception as e:
                result_container["error"] = str(e)
            finally:
                loop.close()

        thread = threading.Thread(target=run_in_thread)
        thread.start()
        thread.join(timeout=60)

        if result_container["error"]:
            return f"[BLOCKED] {result_container['error']}"
        if result_container["result"] is None:
            return "[ERROR] Browser timed out"
        return result_container["result"]
    async def _execute_async(self, *, action: str, target: str, value: str, agent: str) -> str:
        try:
            await self._ensure_started()

            if action == "navigate":
                self._check_url(target)
                result = await self.engine.navigate(target)

            elif action == "screenshot":
                result = await self.engine.screenshot()

            elif action == "get_text":
                result = await self.engine.get_text()

            elif action == "click":
                result = await self.engine.click(target)

            elif action == "fill":
                result = await self.engine.fill(target, value)

            elif action == "press":
                result = await self.engine.press(target)

            elif action == "scroll":
                result = await self.engine.scroll(target or "down")

            elif action == "url":
                result = await self.engine.current_url()

            elif action == "headless_on":
                result = await self.engine.set_headless(True)

            elif action == "headless_off":
                result = await self.engine.set_headless(False)

            elif action == "close":
                await self.engine.stop()
                self._started = False
                result = "Browser closed."

            else:
                raise ValueError(f"Unknown browser action: {action}")

            self.audit.log(AuditEvent(
                phase="browser",
                action=action,
                tool_name="browser",
                decision="allowed",
                metadata={"target": target[:100], "agent": agent}
            ))

            return result

        except Exception as e:
            self.audit.log(AuditEvent(
                phase="browser",
                action=action,
                tool_name="browser",
                decision="blocked",
                metadata={"target": target[:100], "agent": agent, "reason": str(e)}
            ))
            return f"[BLOCKED] {str(e)}"