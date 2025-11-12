"""
HTTP fetcher for retrieving web pages.
"""
import httpx
from pathlib import Path

# Using a realistic browser User-Agent to avoid bot detection
# Note: Some sites may still block scrapers. Always respect robots.txt and ToS.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}


async def fetch_html(url: str, timeout: int = 15, save_fixture: bool = False) -> str:
    """
    Fetch HTML content from a URL.

    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds
        save_fixture: If True, save HTML to fixtures/ directory for offline testing

    Returns:
        HTML content as string

    Raises:
        httpx.HTTPError: If the request fails
    """
    async with httpx.AsyncClient(
        headers=HEADERS,
        timeout=timeout,
        follow_redirects=True
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        html = response.text

        # Optionally save HTML for offline testing
        if save_fixture:
            fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_listing.html"
            fixture_path.write_text(html, encoding="utf-8")
            print(f"Saved HTML fixture to {fixture_path}")

        return html


def load_fixture(filename: str = "sample_listing.html") -> str:
    """
    Load HTML from fixtures directory for offline testing.

    Args:
        filename: Name of the fixture file

    Returns:
        HTML content as string
    """
    fixture_path = Path(__file__).parent.parent / "fixtures" / filename
    return fixture_path.read_text(encoding="utf-8")
