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
    headless: bool = False  # Phase 10: class-level mode flag (False = live/visible)

    def __init__(self):
        self.engine = BrowserEngine(headless=BrowserSession.headless)
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
                import re
                # Extract just the search value if it's a sentence
                # "fill search box with X" → extract X
                value_match = re.search(r'(?:with|value|=)\s*["\']?([^"\']+)["\']?(?:\s+and|\s*$)', value, re.IGNORECASE)
                clean_value = value_match.group(1).strip() if value_match else value

                selectors = [target] if target and not target.startswith("input[name") else []
                selectors += ["input#search", "input[name='search_query']",
                             "textarea[name='q']", "input[type='search']"]
                result = "[ERROR] Could not find input field"
                for sel in selectors:
                    try:
                        result = self._run(self.engine.fill(sel, clean_value))
                        break
                    except Exception:
                        continue

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

    @classmethod
    def set_headless(cls, val: bool):
        """
        Phase 10 Task 3 — Toggle headless mode.

        IMPORTANT: We do NOT destroy the singleton here.
        Killing _instance spawns a new background thread on next get(),
        which conflicts with the still-running daemon thread from the old
        session → Chrome window never surfaces.

        Instead we call engine.set_headless() which:
          1. Saves the current URL
          2. Stops the current Playwright browser
          3. Relaunches with the new headless setting (same thread / loop)
          4. Re-navigates to the saved URL
        """
        cls.headless = val                       # update flag for new sessions

        instance = cls._instance
        if instance is None:
            return                               # no browser running — flag is enough

        if not instance._started:
            # Session object exists but browser never launched; just patch the engine flag
            instance.engine.headless = val
            return

        # Browser is live → graceful in-place restart
        try:
            instance._run(instance.engine.set_headless(val))
        except Exception:
            # Graceful restart failed → mark stopped so ensure_started() retries cleanly
            instance._started = False
            instance.engine.headless = val

    def get_current_url(self) -> str:
        """
        Phase 10 Task 5: Return the current page URL.
        Returns empty string if browser not started.
        """
        try:
            if self._started and self.engine._page:
                return self._run(self.engine.current_url())
        except Exception:
            pass
        return ""