"""
Browser-based fetcher using Playwright for sites with anti-bot protection.

This fetcher uses a real browser (Chromium) to bypass:
- JavaScript challenges
- Cloudflare protection
- User-Agent validation
- Cookie/session requirements
"""
import random
from pathlib import Path
from playwright.async_api import async_playwright, Browser, Page


# Stealth script to hide automation indicators
STEALTH_SCRIPT = """
() => {
    // Override the navigator.webdriver property
    Object.defineProperty(navigator, 'webdriver', {
        get: () => false,
    });

    // Override Chrome detection
    window.chrome = {
        runtime: {},
    };

    // Override permissions API
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
    );

    // Override plugins length
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5],
    });

    // Override languages
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en'],
    });
}
"""


async def fetch_html_with_browser(
    url: str,
    timeout: int = 45000,
    save_fixture: bool = False,
    headless: bool = True,
    wait_for_selector: str | None = None
) -> str:
    """
    Fetch HTML content using a real browser (Playwright/Chromium) with stealth mode.

    Args:
        url: The URL to fetch
        timeout: Page load timeout in milliseconds (default: 45000 = 45s)
        save_fixture: If True, save HTML to fixtures/ directory for offline testing
        headless: Run browser in headless mode (default: True)
        wait_for_selector: Optional CSS selector to wait for before extracting HTML

    Returns:
        HTML content as string

    Raises:
        Exception: If the browser navigation fails
    """
    async with async_playwright() as p:
        # Launch Chromium browser with stealth args
        browser: Browser = await p.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-infobars',
                '--window-size=1920,1080',
                '--disable-notifications',
            ]
        )

        # Create context with realistic browser fingerprint
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York',
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
            }
        )

        # Create new page
        page: Page = await context.new_page()

        # Inject stealth script before navigation
        await page.add_init_script(STEALTH_SCRIPT)

        try:
            print(f"  → Opening browser and navigating to {url}")

            # Navigate to URL with longer timeout
            response = await page.goto(url, timeout=timeout, wait_until='domcontentloaded')

            if response is None:
                raise Exception(f"Failed to navigate to {url}")

            # Check response status
            status = response.status
            print(f"  → Response status: {status}")

            # If blocked (403, 503), still try to get content
            if status >= 400:
                print(f"  ⚠ Got status {status}, but attempting to extract content anyway...")

                # Wait a bit longer for any redirects or challenges
                await page.wait_for_timeout(5000)  # 5 seconds

                # Check if we got redirected or page changed
                current_url = page.url
                if current_url != url:
                    print(f"  → Redirected to: {current_url}")

            # Human-like behavior: random scroll
            try:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 4)")
                await page.wait_for_timeout(random.randint(500, 1500))
                await page.evaluate("window.scrollTo(0, 0)")
            except:
                pass  # Ignore scroll errors

            # Optional: wait for specific content to load (only if status < 400)
            if wait_for_selector and status < 400:
                try:
                    print(f"  → Waiting for selector: {wait_for_selector}")
                    await page.wait_for_selector(wait_for_selector, timeout=10000)
                except Exception as e:
                    print(f"  ⚠ Selector wait failed: {e}")
                    # Continue anyway

            # Additional wait for dynamic content
            await page.wait_for_timeout(3000)  # 3 seconds

            # Extract HTML
            html = await page.content()

            print(f"  ✓ Fetched {len(html)} characters via browser")

            # Check if we got a meaningful page or just an error page
            if len(html) < 1000 and status >= 400:
                print(f"  ⚠ Warning: Small HTML size ({len(html)} chars) - might be blocked")

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
