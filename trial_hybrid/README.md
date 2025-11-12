# Hybrid Scraper v0.1 - Trial Implementation

A proof-of-concept web scraper that combines **pattern-based extraction** with **LLM normalization** to extract structured news data from Moneycontrol's markets listing page.

## Overview

This project demonstrates a hybrid approach to web scraping:

1. **Pattern-based extraction** - Uses heuristics to identify news cards in HTML
2. **LLM normalization** - Uses LiteLLM to normalize and validate extracted data
3. **Structured output** - Saves validated data to JSONL format

## Features

- ✅ Extracts news articles from listing pages (no pagination, single page only)
- ✅ Heuristic-based HTML parsing with multiple fallback strategies
- ✅ LLM-powered data normalization with confidence scoring
- ✅ Anti-hallucination prompts to ensure accuracy
- ✅ Pydantic schema validation
- ✅ JSONL output format for easy downstream processing
- ✅ Offline mode with HTML fixtures for testing
- ✅ Comprehensive validation and error handling

## Project Structure

```
trial_hybrid/
├── core/
│   ├── __init__.py
│   ├── fetcher.py      # HTTP client (httpx)
│   ├── parser.py       # HTML parsing and extraction
│   ├── normalizer.py   # Text normalization utilities
│   ├── llm.py          # LiteLLM integration
│   └── validate.py     # Validation logic
├── outputs/            # JSONL output files
├── fixtures/           # Saved HTML for offline testing
├── schemas.py          # Pydantic data models
├── prompts.py          # LLM prompt templates
├── run_trial.py        # Main runner script
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variables template
└── README.md           # This file
```

## Installation

### 1. Prerequisites

- Python 3.10 or higher
- pip or poetry

### 2. Clone and Setup

```bash
# Navigate to the project directory
cd trial_hybrid

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (required for --browser mode)
playwright install chromium
```

### 3. Configure LiteLLM

Copy the example environment file and configure your LiteLLM credentials:

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```env
LITELLM_API_BASE=https://your-proxy-url
LITELLM_API_KEY=sk-your-api-key
LITELLM_MODEL=openai/gpt-4o-mini
```

## Usage

### Browser Mode (Recommended for Anti-Bot Sites)

Use a real browser to bypass anti-bot protection like Cloudflare:

```bash
python run_trial.py --browser
```

This uses Playwright/Chromium to render JavaScript and bypass 403 errors.

### Basic Usage (HTTP Client)

Run the scraper with standard HTTP client:

```bash
python run_trial.py
```

**Note:** May get blocked (403 Forbidden) on sites with anti-bot protection.

### Offline Mode

Use a saved HTML fixture (useful for testing without network calls):

```bash
python run_trial.py --offline
```

### Save Fixture

Fetch HTML with browser and save it for future offline use:

```bash
python run_trial.py --browser --save-fixture
```

## Output

The scraper produces a JSONL file at `outputs/moneycontrol_listing_page1.jsonl`.

### Example Output

Each line is a JSON object representing a news article:

```json
{
  "source": "moneycontrol",
  "category": "markets",
  "headline": "Stock markets rally on positive earnings",
  "url": "https://www.moneycontrol.com/news/business/markets/...",
  "summary": "Major indices posted gains as tech companies reported...",
  "published_label": "2 hours ago",
  "confidence": 0.95,
  "evidence": {
    "snippet": "Stock markets rally on positive earnings. Major indices..."
  }
}
```

### Data Schema

Field | Type | Description
------|------|------------
`source` | string | Always "moneycontrol"
`category` | string | Always "markets"
`headline` | string | Article headline (required)
`url` | string | Absolute URL to article (required)
`summary` | string | Brief summary (optional)
`published_label` | string | Time label like "2 hours ago" (optional)
`confidence` | float | LLM confidence score 0.0-1.0
`evidence` | object | Snippet of text used for extraction

## Acceptance Criteria

The implementation is considered successful if:

- ✅ Minimum **10 validated items** extracted from listing page
- ✅ All URLs are **absolute** (not relative)
- ✅ **≥95%** items parse without LLM errors
- ✅ Average **confidence ≥0.7** for complete candidates

## Architecture Details

### 1. Fetcher (`core/fetcher.py`)

- Uses `httpx` for async HTTP requests
- Custom User-Agent headers for politeness
- Optional fixture saving for offline testing

### 2. Parser (`core/parser.py`)

- Multiple heuristic strategies to find news cards
- Looks for common HTML patterns (articles, divs with news classes)
- Fallback strategies if initial patterns fail
- Deduplication by URL

### 3. Normalizer (`core/normalizer.py`)

- Converts relative URLs to absolute
- Cleans whitespace and control characters
- Truncates overly long text
- Validates URL format

### 4. LLM (`core/llm.py`)

- Integrates with LiteLLM for model flexibility
- Anti-hallucination prompts
- JSON-mode output for reliability
- Confidence scoring based on data quality
- Graceful fallback on errors

### 5. Validator (`core/validate.py`)

- Checks headline length (5-240 chars)
- Validates URL format and domain
- Ensures confidence is in valid range (0.0-1.0)
- Auto-fixes common issues when possible

## Configuration

### Environment Variables

Variable | Required | Default | Description
---------|----------|---------|------------
`LITELLM_API_BASE` | Yes | - | LiteLLM proxy base URL
`LITELLM_API_KEY` | Yes | - | API key for authentication
`LITELLM_MODEL` | No | `openai/gpt-4o-mini` | Model to use

### Constants (in `run_trial.py`)

```python
URL = "https://www.moneycontrol.com/news/business/markets/page-1/"
MAX_ITEMS = 20  # Maximum items to extract
```

## Legal & Ethics

- ⚠️ **Respect robots.txt** - Always check site's robots.txt
- ⚠️ **Respect ToS** - Review site's Terms of Service
- ⚠️ **Politeness** - Limited to 1 page, custom User-Agent
- ⚠️ **Attribution** - Data is from Moneycontrol

This is a proof-of-concept for educational purposes. Always ensure you have permission before scraping websites.

## Troubleshooting

### No items extracted

- Check if the website structure has changed
- Try saving a fixture and inspecting the HTML
- Adjust parser heuristics in `core/parser.py`

### LLM errors

- Verify your LiteLLM credentials in `.env`
- Check API quota/limits
- Try a different model
- Use `--offline` mode to test without LLM

### Low confidence scores

- Parser may be extracting incomplete data
- Review the HTML structure and adjust selectors
- Check `evidence.snippet` to see what text was used

### Validation failures

- Check headline length requirements (5-240 chars)
- Ensure URLs are absolute and from moneycontrol.com
- Review validation rules in `core/validate.py`

## Next Steps

Future enhancements could include:

- 🔄 Multi-page crawling with pagination
- 🔍 Following links to detail pages
- 📊 Comparison between pattern-only vs pattern+LLM accuracy
- 🎯 More sophisticated parser selectors
- 📅 Date/time parsing for `published_label`
- 🧪 Comprehensive test suite
- 📈 Metrics and analytics dashboard

## Reference

This implementation follows the specifications in `prp.md` (Product Requirements Page).

## License

This is a proof-of-concept trial implementation for educational purposes.
