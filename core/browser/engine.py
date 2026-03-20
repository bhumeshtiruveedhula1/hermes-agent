# core/browser/engine.py

import asyncio
import base64
from pathlib import Path
from playwright.async_api import async_playwright, Browser, Page


class BrowserEngine:
    """
    Controls a real Chromium browser.
    Headless mode can be toggled at any time.
    """

    def __init__(self, headless: bool = False):
        self.headless = headless
        self._playwright = None
        self._browser: Browser | None = None
        self._page: Page | None = None

    async def start(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=["--start-maximized"]
        )
        context = await self._browser.new_context(
            viewport={"width": 1280, "height": 800}
        )
        self._page = await context.new_page()

    async def stop(self):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._browser = None
        self._page = None

    async def navigate(self, url: str) -> str:
        if not url.startswith("http"):
            url = "https://" + url
        await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
        return f"Navigated to: {self._page.url}"

    async def screenshot(self) -> str:
        """Returns base64 encoded PNG screenshot."""
        shot = await self._page.screenshot(type="png")
        return base64.b64encode(shot).decode("utf-8")

    async def get_text(self) -> str:
        """Extract visible text from current page."""
        text = await self._page.evaluate("""() => {
            const elements = document.querySelectorAll('p, h1, h2, h3, h4, li, span, a, button, label');
            return Array.from(elements)
                .map(e => e.innerText?.trim())
                .filter(t => t && t.length > 1)
                .slice(0, 150)
                .join('\\n');
        }""")
        return text[:3000]

    async def click(self, selector: str) -> str:
        await self._page.click(selector, timeout=10000)
        await self._page.wait_for_load_state("domcontentloaded")
        return f"Clicked: {selector}"

    async def fill(self, selector: str, value: str) -> str:
        await self._page.fill(selector, value)
        return f"Filled '{selector}' with '{value}'"

    async def press(self, key: str) -> str:
        await self._page.keyboard.press(key)
        return f"Pressed: {key}"

    async def scroll(self, direction: str = "down") -> str:
        delta = 600 if direction == "down" else -600
        await self._page.evaluate(f"window.scrollBy(0, {delta})")
        return f"Scrolled {direction}"

    async def current_url(self) -> str:
        return self._page.url if self._page else "No page open"

    async def set_headless(self, headless: bool):
        """Toggle headless mode — restarts browser."""
        was_url = self._page.url if self._page else None
        await self.stop()
        self.headless = headless
        await self.start()
        if was_url:
            await self.navigate(was_url)
        return f"Headless mode: {headless}"

    @property
    def is_running(self) -> bool:
        return self._browser is not None