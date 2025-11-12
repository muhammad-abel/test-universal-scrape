"""
HTML parser for extracting news listing candidates.
"""
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import List, Dict, Any


def extract_listing_candidates(html: str, base_url: str, max_items: int = 20) -> List[Dict[str, Any]]:
    """
    Extract news card candidates from a listing page using heuristic patterns.

    Args:
        html: HTML content of the page
        base_url: Base URL for resolving relative links
        max_items: Maximum number of items to extract (default: 20)

    Returns:
        List of candidate dictionaries with extracted fields
    """
    soup = BeautifulSoup(html, "lxml")
    items = []
    seen_urls = set()

    # Strategy 1: Look for common news article patterns
    # Try multiple selectors to maximize coverage
    selectors = [
        "article",
        "li[class*='clearfix']",
        "div[class*='news']",
        "div[class*='article']",
        "div[class*='story']",
        "div[class*='item']",
    ]

    for selector in selectors:
        cards = soup.select(selector)
        for card in cards:
            if len(items) >= max_items:
                break

            # Find link (headline)
            link = card.find("a", href=True)
            if not link:
                continue

            headline = link.get_text(strip=True)
            href = link.get("href", "")

            if not headline or not href or len(headline) < 5:
                continue

            # Make URL absolute
            url = urljoin(base_url, href)

            # Skip duplicates
            if url in seen_urls:
                continue

            # Look for summary/snippet
            summary = None
            for tag in ["p", "div", "span"]:
                p_tag = card.find(tag, class_=lambda x: x and any(
                    keyword in str(x).lower() for keyword in ["desc", "summary", "excerpt", "content", "intro"]
                ))
                if p_tag:
                    summary = p_tag.get_text(" ", strip=True)
                    break

            # If no summary found with class, try any p tag
            if not summary:
                p_tag = card.find("p")
                if p_tag:
                    summary = p_tag.get_text(" ", strip=True)

            # Look for time/date label
            time_label = None
            for tag in ["time", "span", "small", "em"]:
                time_tag = card.find(tag, class_=lambda x: x and any(
                    keyword in str(x).lower() for keyword in ["time", "date", "publish", "ago"]
                ))
                if time_tag:
                    time_label = time_tag.get_text(" ", strip=True)
                    break

            # If no time found with class, try time tag with datetime attribute
            if not time_label:
                time_tag = card.find("time", datetime=True)
                if time_tag:
                    time_label = time_tag.get_text(" ", strip=True) or time_tag.get("datetime", "")

            seen_urls.add(url)
            items.append({
                "headline": headline,
                "url": url,
                "summary": summary,
                "published_label": time_label,
                "source": "moneycontrol",
                "category": "markets",
            })

        if len(items) >= max_items:
            break

    # Strategy 2: If we didn't find enough items, try a more aggressive approach
    if len(items) < 5:
        # Look for all links that might be news articles
        for link in soup.find_all("a", href=True):
            if len(items) >= max_items:
                break

            headline = link.get_text(strip=True)
            href = link.get("href", "")

            if not headline or not href or len(headline) < 10:
                continue

            # Filter out navigation/non-article links
            if any(keyword in href.lower() for keyword in ["#", "javascript:", "login", "register", "search"]):
                continue

            url = urljoin(base_url, href)

            if url in seen_urls:
                continue

            # Try to find context around the link
            parent = link.find_parent()
            summary = None
            time_label = None

            if parent:
                # Look for sibling elements
                for sibling in parent.find_all(["p", "span", "div"]):
                    if sibling != link and len(sibling.get_text(strip=True)) > 20:
                        summary = sibling.get_text(" ", strip=True)
                        break

                # Look for time elements
                time_tag = parent.find(["time", "span", "small"])
                if time_tag:
                    time_label = time_tag.get_text(" ", strip=True)

            seen_urls.add(url)
            items.append({
                "headline": headline,
                "url": url,
                "summary": summary,
                "published_label": time_label,
                "source": "moneycontrol",
                "category": "markets",
            })

    return items[:max_items]
