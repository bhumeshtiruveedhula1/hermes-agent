# core/browser/session.py
# Global browser session — one instance shared across all requests

from core.browser.engine import BrowserEngine
import threading
import asyncio


class BrowserSession:
    """
    Singleton browser session.
    Stays alive across multiple chat messages.
    """
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.engine = BrowserEngine(headless=False)
        self._started = False
        self._loop = None
        self._thread = None
        self._start_background_loop()

    def _start_background_loop(self):
        """Start a dedicated background thread with its own ProactorEventLoop."""
        def run_loop():
            self._loop = asyncio.ProactorEventLoop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()

        self._thread = threading.Thread(target=run_loop, daemon=True)
        self._thread.start()

        # Wait for loop to start
        import time
        while self._loop is None:
            time.sleep(0.01)

    def _run(self, coro):
        """Submit a coroutine to the background loop and wait for result."""
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=60)

    def ensure_started(self):
        if not self._started:
            self._run(self.engine.start())
            self._started = True

    def execute(self, *, action: str, target: str = "", value: str = "", agent: str = "hermes") -> str:
        from core.audit.audit_logger import AuditLogger
        from core.audit.audit_event import AuditEvent
        from core.browser.capability import BrowserCapability

        BLOCKED_DOMAINS = ["localhost", "127.0.0.1", "0.0.0.0", "169.254", "192.168", "10.0", "172.16"]

        audit = AuditLogger()

        try:
            # Block local network
            if action == "navigate":
                for blocked in BLOCKED_DOMAINS:
                    if blocked in target:
                        raise ValueError(f"Access to local network blocked: {target}")

            self.ensure_started()

            if action == "navigate":
                if not target.startswith("http"):
                    target = "https://" + target
                result = self._run(self.engine.navigate(target))

            elif action == "get_text":
                result = self._run(self.engine.get_text())

            elif action == "screenshot":
                result = self._run(self.engine.screenshot())

            elif action == "click":
                result = self._run(self.engine.click(target))

            elif action == "fill":
                result = self._run(self.engine.fill(target, value))

            elif action == "press":
                result = self._run(self.engine.press(target))

            elif action == "scroll":
                result = self._run(self.engine.scroll(target or "down"))

            elif action == "url":
                result = self._run(self.engine.current_url())

            elif action == "headless_on":
                result = self._run(self.engine.set_headless(True))

            elif action == "headless_off":
                result = self._run(self.engine.set_headless(False))

            elif action == "close":
                self._run(self.engine.stop())
                self._started = False
                result = "Browser closed."

            else:
                raise ValueError(f"Unknown browser action: {action}")

            audit.log(AuditEvent(
                phase="browser", action=action, tool_name="browser",
                decision="allowed", metadata={"target": target[:100], "agent": agent}
            ))
            return result

        except Exception as e:
            audit.log(AuditEvent(
                phase="browser", action=action, tool_name="browser",
                decision="blocked", metadata={"target": target[:100], "agent": agent, "reason": str(e)}
            ))
            return f"[BLOCKED] {str(e)}"

    @classmethod
    def get(cls):
        """Get or create the singleton session."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = BrowserSession()
            return cls._instance