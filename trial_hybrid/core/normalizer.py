"""
Data normalization utilities.
"""
import re
from urllib.parse import urljoin, urlparse
from typing import Dict, Any


def normalize_item(item: Dict[str, Any], base_url: str) -> Dict[str, Any]:
    """
    Normalize a candidate item before sending to LLM.

    Args:
        item: Candidate dictionary
        base_url: Base URL for resolving relative links

    Returns:
        Normalized item dictionary
    """
    normalized = item.copy()

    # Normalize URL to absolute
    if "url" in normalized and normalized["url"]:
        normalized["url"] = urljoin(base_url, normalized["url"])

    # Trim and clean text fields
    for field in ["headline", "summary", "published_label"]:
        if field in normalized and normalized[field]:
            # Remove extra whitespace
            text = re.sub(r'\s+', ' ', str(normalized[field])).strip()
            normalized[field] = text if text else None

    # Truncate summary if too long (to save LLM tokens)
    if normalized.get("summary") and len(normalized["summary"]) > 500:
        normalized["summary"] = normalized["summary"][:497] + "..."

    # Ensure required fields exist
    normalized.setdefault("source", "moneycontrol")
    normalized.setdefault("category", "markets")
    normalized.setdefault("headline", "")
    normalized.setdefault("url", "")
    normalized.setdefault("summary", None)
    normalized.setdefault("published_label", None)

    return normalized


def clean_text(text: str, max_length: int | None = None) -> str:
    """
    Clean and normalize text.

    Args:
        text: Input text
        max_length: Optional maximum length to truncate to

    Returns:
        Cleaned text
    """
    if not text:
        return ""

    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    # Remove control characters
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)

    # Truncate if needed
    if max_length and len(text) > max_length:
        text = text[:max_length - 3] + "..."

    return text


def is_valid_url(url: str, required_domain: str = "moneycontrol.com") -> bool:
    """
    Check if a URL is valid and from the expected domain.

    Args:
        url: URL to validate
        required_domain: Required domain in the URL

    Returns:
        True if valid, False otherwise
    """
    try:
        parsed = urlparse(url)
        if not parsed.scheme or parsed.scheme not in ["http", "https"]:
            return False
        if not parsed.netloc:
            return False
        if required_domain and required_domain not in parsed.netloc:
            return False
        return True
    except Exception:
        return False
