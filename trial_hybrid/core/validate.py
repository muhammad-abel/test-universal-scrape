"""
Validation utilities for news items.
"""
from urllib.parse import urlparse
from typing import Dict, Any


def is_valid_news(item: Dict[str, Any], min_confidence: float = 0.0) -> bool:
    """
    Validate a news item dictionary.

    Args:
        item: News item dictionary
        min_confidence: Minimum confidence threshold (0.0-1.0)

    Returns:
        True if valid, False otherwise
    """
    try:
        # Check headline
        headline = (item.get("headline") or "").strip()
        if not headline or len(headline) < 5:
            return False
        if len(headline) > 240:
            return False

        # Check URL
        url = (item.get("url") or "").strip()
        if not url:
            return False

        parsed_url = urlparse(url)
        if not parsed_url.scheme or parsed_url.scheme not in ["http", "https"]:
            return False
        if not parsed_url.netloc:
            return False
        if "moneycontrol.com" not in parsed_url.netloc:
            return False

        # Check confidence
        confidence = item.get("confidence", 0.0)
        if not isinstance(confidence, (int, float)):
            return False
        if confidence < min_confidence:
            return False
        if confidence < 0.0 or confidence > 1.0:
            return False

        # Check summary length if present
        summary = item.get("summary")
        if summary and len(summary) > 300:
            # Truncate but don't reject
            item["summary"] = summary[:297] + "..."

        # Check source and category
        if item.get("source") != "moneycontrol":
            return False
        if item.get("category") != "markets":
            return False

        return True

    except Exception as e:
        print(f"Validation error: {e}")
        return False


def validate_and_fix(item: Dict[str, Any]) -> Dict[str, Any] | None:
    """
    Validate and attempt to fix common issues in a news item.

    Args:
        item: News item dictionary

    Returns:
        Fixed item dictionary or None if unfixable
    """
    try:
        # Create a copy to avoid modifying the original
        fixed = item.copy()

        # Fix headline
        headline = (fixed.get("headline") or "").strip()
        if not headline or len(headline) < 5:
            return None
        if len(headline) > 240:
            fixed["headline"] = headline[:237] + "..."

        # Validate URL (can't fix, only validate)
        url = (fixed.get("url") or "").strip()
        if not url:
            return None
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return None
        if "moneycontrol.com" not in parsed.netloc:
            return None

        # Fix confidence
        confidence = fixed.get("confidence", 0.5)
        if not isinstance(confidence, (int, float)):
            fixed["confidence"] = 0.5
        else:
            fixed["confidence"] = max(0.0, min(1.0, float(confidence)))

        # Fix summary
        summary = fixed.get("summary")
        if summary:
            summary = str(summary).strip()
            if len(summary) > 300:
                summary = summary[:297] + "..."
            fixed["summary"] = summary if summary else None
        else:
            fixed["summary"] = None

        # Fix published_label
        published_label = fixed.get("published_label")
        if published_label:
            published_label = str(published_label).strip()
            fixed["published_label"] = published_label if published_label else None
        else:
            fixed["published_label"] = None

        # Ensure source and category
        fixed["source"] = "moneycontrol"
        fixed["category"] = "markets"

        # Ensure evidence exists
        if not fixed.get("evidence"):
            snippet = fixed.get("summary") or fixed.get("headline") or ""
            fixed["evidence"] = {"snippet": snippet[:240]}

        return fixed

    except Exception as e:
        print(f"Fix error: {e}")
        return None
