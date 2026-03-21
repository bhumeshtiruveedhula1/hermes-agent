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
        return await self.smart_click(selector)

    async def smart_click(self, target: str) -> str:
        """Try multiple click strategies intelligently."""

        # Strategy 1 — direct CSS selector
        try:
            await self._page.click(target, timeout=4000)
            await self._page.wait_for_load_state("domcontentloaded")
            return f"Clicked: {target}"
        except Exception:
            pass

        # Strategy 2 — find by text content
        try:
            await self._page.get_by_text(target, exact=False).first.click(timeout=4000)
            await self._page.wait_for_load_state("domcontentloaded")
            return f"Clicked by text: {target}"
        except Exception:
            pass

        # Strategy 3 — find link by text
        try:
            clean = target[:30].replace("'", "")
            await self._page.locator(f"a:has-text('{clean}')").first.click(timeout=4000)
            await self._page.wait_for_load_state("domcontentloaded")
            return f"Clicked link: {target}"
        except Exception:
            pass

        # Strategy 4 — JavaScript click on element containing text
        try:
            clean_js = target[:40].replace('"', '').replace("'", "")
            await self._page.evaluate(f"""
                const els = document.querySelectorAll('a, button, [role="link"], ytd-video-renderer, ytd-compact-video-renderer');
                for (const el of els) {{
                    if (el.textContent.includes("{clean_js}")) {{
                        el.click();
                        break;
                    }}
                }}
            """)
            await self._page.wait_for_load_state("domcontentloaded")
            return f"Clicked via JS: {target}"
        except Exception:
            pass

        # Strategy 5 — extract URL from description and navigate directly
        try:
            import re
            url_match = re.search(r'https?://[^\s]+', target)
            if url_match:
                url = url_match.group(0)
                await self._page.goto(url, wait_until="domcontentloaded", timeout=15000)
                return f"Navigated to: {self._page.url}"
        except Exception:
            pass

        return f"[BLOCKED] Could not interact with: {target}"

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