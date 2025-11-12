#!/usr/bin/env python3
"""
Main runner script for the Hybrid Scraper v0.1 trial.

This script demonstrates the hybrid approach:
1. Pattern-based extraction from HTML
2. LLM normalization and validation
3. Structured output to JSONL

Usage:
    python run_trial.py [--offline] [--save-fixture] [--browser]

Options:
    --offline       Use saved HTML fixture instead of fetching from web
    --save-fixture  Save fetched HTML to fixtures/ for offline testing
    --browser       Use real browser (Playwright) to bypass anti-bot protection
"""
import os
import sys
import json
import asyncio
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.fetcher import fetch_html, load_fixture
from core.parser import extract_listing_candidates
from core.normalizer import normalize_item
from core.llm import normalize_with_llm
from core.validate import is_valid_news, validate_and_fix
from schemas import NewsItem

# Browser fetcher (optional - only imported if --browser flag is used)
try:
    from core.browser_fetcher import fetch_html_with_browser
    BROWSER_AVAILABLE = True
except ImportError:
    BROWSER_AVAILABLE = False

# Configuration
URL = "https://www.moneycontrol.com/news/business/markets/page-1/"
OUTPUT_FILE = Path(__file__).parent / "outputs" / "moneycontrol_listing_page1.jsonl"
MAX_ITEMS = 20


async def process_candidate(
    candidate: Dict[str, Any],
    use_llm: bool = True
) -> Dict[str, Any] | None:
    """
    Process a single candidate item.

    Args:
        candidate: Candidate dictionary
        use_llm: Whether to use LLM for normalization

    Returns:
        Validated and normalized item or None if invalid
    """
    try:
        # Pre-normalize (clean text, resolve URLs)
        normalized = normalize_item(candidate, URL)

        # LLM normalization (optional)
        if use_llm:
            record = await normalize_with_llm(normalized)
        else:
            # Use candidate directly without LLM
            record = normalized.copy()
            record.setdefault("confidence", 0.5)
            record.setdefault("evidence", {
                "snippet": (normalized.get("summary") or normalized.get("headline") or "")[:240]
            })

        # Validate and fix if needed
        fixed = validate_and_fix(record)
        if not fixed:
            print(f"  ✗ Validation failed for: {candidate.get('headline', 'Unknown')[:50]}")
            return None

        if not is_valid_news(fixed, min_confidence=0.0):
            print(f"  ✗ Invalid news item: {candidate.get('headline', 'Unknown')[:50]}")
            return None

        # Validate with Pydantic schema
        try:
            news_item = NewsItem(**fixed)
            print(f"  ✓ Validated: {news_item.headline[:60]}... (confidence: {news_item.confidence:.2f})")
            return news_item.model_dump(mode='json')
        except Exception as e:
            print(f"  ✗ Schema validation failed: {e}")
            return None

    except Exception as e:
        print(f"  ✗ Error processing candidate: {e}")
        return None


async def main(args):
    """Main execution function."""
    print("=" * 80)
    print("Hybrid Scraper v0.1 - Moneycontrol Markets Listing Trial")
    print("=" * 80)
    print()

    # Ensure output directory exists
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Step 1: Fetch HTML
    print(f"[1/5] Fetching HTML...")
    try:
        if args.offline:
            print(f"  → Loading from fixture (offline mode)")
            html = load_fixture()
        elif args.browser:
            # Use browser-based fetching (Playwright)
            if not BROWSER_AVAILABLE:
                print(f"  ✗ Playwright not installed. Run: pip install playwright && playwright install chromium")
                return 1
            print(f"  → Using browser mode (Playwright)")
            html = await fetch_html_with_browser(
                URL,
                save_fixture=args.save_fixture,
                headless=True,
                wait_for_selector="article, div[class*='news'], a"  # Wait for content
            )
        else:
            print(f"  → GET {URL} (HTTP client)")
            html = await fetch_html(URL, save_fixture=args.save_fixture)
            print(f"  ✓ Fetched {len(html)} characters")
            if args.save_fixture:
                print(f"  ✓ Saved fixture for offline use")
    except Exception as e:
        print(f"  ✗ Fetch failed: {e}")
        print(f"  💡 Tip: Try --browser flag to use real browser and bypass anti-bot")
        return 1

    # Step 2: Parse candidates
    print(f"\n[2/5] Parsing HTML for news cards...")
    try:
        candidates = extract_listing_candidates(html, base_url=URL, max_items=MAX_ITEMS)
        print(f"  ✓ Found {len(candidates)} candidate items")
        if len(candidates) == 0:
            print("  ⚠ No candidates found - check parser heuristics")
            return 1
    except Exception as e:
        print(f"  ✗ Parse failed: {e}")
        return 1

    # Step 3: Show sample candidates
    print(f"\n[3/5] Sample candidates (first 3):")
    for i, cand in enumerate(candidates[:3], 1):
        print(f"\n  Candidate {i}:")
        print(f"    Headline: {cand.get('headline', 'N/A')[:70]}...")
        print(f"    URL: {cand.get('url', 'N/A')[:70]}...")
        print(f"    Summary: {cand.get('summary', 'N/A')[:70] if cand.get('summary') else 'None'}...")
        print(f"    Time: {cand.get('published_label', 'N/A')}")

    # Step 4: Process with LLM
    print(f"\n[4/5] Normalizing with LLM and validating...")
    valid_items: List[Dict[str, Any]] = []
    failed_count = 0

    # Check if LLM is configured
    use_llm = bool(os.getenv("LITELLM_API_KEY"))
    if not use_llm:
        print("  ⚠ LITELLM_API_KEY not set - skipping LLM normalization")
        print("  → Using pattern-based extraction only")

    for i, candidate in enumerate(candidates, 1):
        print(f"\n  Processing {i}/{len(candidates)}: {candidate.get('headline', 'Unknown')[:50]}...")

        result = await process_candidate(candidate, use_llm=use_llm)
        if result:
            valid_items.append(result)
        else:
            failed_count += 1

        # Small delay between LLM calls to be polite
        if use_llm and i < len(candidates):
            await asyncio.sleep(0.5)

    # Step 5: Save results
    print(f"\n[5/5] Saving results...")
    try:
        with OUTPUT_FILE.open("w", encoding="utf-8") as f:
            for item in valid_items:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        print(f"  ✓ Saved {len(valid_items)} items to {OUTPUT_FILE}")
        print(f"  → {failed_count} items failed validation")
    except Exception as e:
        print(f"  ✗ Save failed: {e}")
        return 1

    # Summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total candidates extracted: {len(candidates)}")
    print(f"Valid items saved: {len(valid_items)}")
    print(f"Failed validation: {failed_count}")
    print(f"Success rate: {len(valid_items)/len(candidates)*100:.1f}%")

    if valid_items:
        avg_confidence = sum(item['confidence'] for item in valid_items) / len(valid_items)
        print(f"Average confidence: {avg_confidence:.2f}")

        with_summary = sum(1 for item in valid_items if item.get('summary'))
        with_time = sum(1 for item in valid_items if item.get('published_label'))
        print(f"Items with summary: {with_summary}/{len(valid_items)} ({with_summary/len(valid_items)*100:.0f}%)")
        print(f"Items with time label: {with_time}/{len(valid_items)} ({with_time/len(valid_items)*100:.0f}%)")

    # Check acceptance criteria
    print("\n" + "=" * 80)
    print("ACCEPTANCE CRITERIA")
    print("=" * 80)

    criteria_met = []
    criteria_failed = []

    # Criterion 1: Minimum 10 items
    if len(valid_items) >= 10:
        criteria_met.append("✓ Minimum 10 validated items")
    else:
        criteria_failed.append(f"✗ Only {len(valid_items)}/10 validated items")

    # Criterion 2: All URLs absolute
    all_absolute = all('http' in str(item.get('url', '')) for item in valid_items)
    if all_absolute:
        criteria_met.append("✓ All URLs are absolute")
    else:
        criteria_failed.append("✗ Some URLs are not absolute")

    # Criterion 3: Average confidence >= 0.7 (if using LLM)
    if use_llm and valid_items:
        avg_conf = sum(item['confidence'] for item in valid_items) / len(valid_items)
        if avg_conf >= 0.7:
            criteria_met.append(f"✓ Average confidence {avg_conf:.2f} >= 0.7")
        else:
            criteria_failed.append(f"✗ Average confidence {avg_conf:.2f} < 0.7")

    for criterion in criteria_met:
        print(criterion)
    for criterion in criteria_failed:
        print(criterion)

    print("\n" + "=" * 80)

    if len(criteria_failed) == 0 and len(valid_items) >= 10:
        print("✓ SUCCESS: All acceptance criteria met!")
        return 0
    else:
        print("⚠ PARTIAL SUCCESS: Some criteria not met")
        return 0 if len(valid_items) > 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hybrid Scraper v0.1 Trial")
    parser.add_argument("--offline", action="store_true", help="Use saved HTML fixture")
    parser.add_argument("--save-fixture", action="store_true", help="Save HTML fixture")
    parser.add_argument("--browser", action="store_true", help="Use real browser (Playwright) to bypass anti-bot")
    args = parser.parse_args()

    try:
        exit_code = asyncio.run(main(args))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
