"""
Browser-based fetcher using Playwright for sites with anti-bot protection.

This fetcher uses a real browser (Chromium) to bypass:
- JavaScript challenges
- Cloudflare protection
- User-Agent validation
- Cookie/session requirements
"""
from pathlib import Path
from playwright.async_api import async_playwright, Browser, Page


async def fetch_html_with_browser(
    url: str,
    timeout: int = 30000,
    save_fixture: bool = False,
    headless: bool = True,
    wait_for_selector: str | None = None
) -> str:
    """
    Fetch HTML content using a real browser (Playwright/Chromium).

    Args:
        url: The URL to fetch
        timeout: Page load timeout in milliseconds (default: 30000 = 30s)
        save_fixture: If True, save HTML to fixtures/ directory for offline testing
        headless: Run browser in headless mode (default: True)
        wait_for_selector: Optional CSS selector to wait for before extracting HTML

    Returns:
        HTML content as string

    Raises:
        Exception: If the browser navigation fails
    """
    async with async_playwright() as p:
        # Launch Chromium browser
        browser: Browser = await p.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',  # Hide automation
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )

        # Create context with realistic browser fingerprint
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York',
        )

        # Create new page
        page: Page = await context.new_page()

        try:
            print(f"  → Opening browser and navigating to {url}")

            # Navigate to URL
            response = await page.goto(url, timeout=timeout, wait_until='networkidle')

            if response is None:
                raise Exception(f"Failed to navigate to {url}")

            # Check if we got blocked (403, 503, etc)
            if response.status >= 400:
                print(f"  ⚠ Response status: {response.status}")

            # Optional: wait for specific content to load
            if wait_for_selector:
                print(f"  → Waiting for selector: {wait_for_selector}")
                await page.wait_for_selector(wait_for_selector, timeout=timeout)

            # Small delay to ensure JavaScript has executed
            await page.wait_for_timeout(2000)  # 2 seconds

            # Extract HTML
            html = await page.content()

            print(f"  ✓ Fetched {len(html)} characters via browser")

            # Optionally save HTML for offline testing
            if save_fixture:
                fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_listing.html"
                fixture_path.write_text(html, encoding="utf-8")
                print(f"  ✓ Saved HTML fixture to {fixture_path}")

            return html

        finally:
            # Always close browser
            await context.close()
            await browser.close()


async def fetch_html_with_screenshot(
    url: str,
    timeout: int = 30000,
    screenshot_path: str | None = None
) -> tuple[str, bytes]:
    """
    Fetch HTML and take a screenshot (useful for debugging).

    Args:
        url: The URL to fetch
        timeout: Page load timeout in milliseconds
        screenshot_path: Optional path to save screenshot

    Returns:
        Tuple of (html_content, screenshot_bytes)
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        )
        page = await context.new_page()

        try:
            await page.goto(url, timeout=timeout, wait_until='networkidle')
            await page.wait_for_timeout(2000)

            html = await page.content()
            screenshot = await page.screenshot(full_page=True)

            if screenshot_path:
                Path(screenshot_path).write_bytes(screenshot)
                print(f"  ✓ Saved screenshot to {screenshot_path}")

            return html, screenshot

        finally:
            await context.close()
            await browser.close()
