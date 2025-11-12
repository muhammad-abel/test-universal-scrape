# Setup Guide - Hybrid Scraper v0.1

## Quick Start

### 1. Install Python Dependencies

```bash
cd trial_hybrid
pip install -r requirements.txt
```

### 2. Install Playwright Browser (for --browser mode)

Playwright requires additional browser binaries. Install them with:

```bash
playwright install chromium
```

Or install all browsers:

```bash
playwright install
```

**Note:** This will download ~300MB of Chromium browser.

### 3. Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and add your LiteLLM credentials:

```env
LITELLM_API_BASE=https://your-proxy-url
LITELLM_API_KEY=sk-your-api-key
LITELLM_MODEL=openai/gpt-4o-mini
```

## Usage Modes

### Mode 1: Standard HTTP (Fast, but may get blocked)

```bash
python run_trial.py
```

### Mode 2: Browser Mode (Bypasses anti-bot)

```bash
python run_trial.py --browser
```

**Recommended for Moneycontrol** - Uses real Chromium browser to bypass anti-bot protection.

### Mode 3: Offline Mode (No network)

```bash
python run_trial.py --offline
```

Uses saved HTML fixture from `fixtures/sample_listing.html`.

### Mode 4: Save Fixture

```bash
python run_trial.py --browser --save-fixture
```

Fetches HTML and saves it for future offline use.

## Troubleshooting

### Error: "403 Forbidden"

**Solution:** Use browser mode to bypass anti-bot protection:

```bash
python run_trial.py --browser
```

### Error: "Playwright not installed"

**Solution:** Install Playwright browsers:

```bash
pip install playwright
playwright install chromium
```

### Error: "LITELLM_API_KEY not set"

The scraper can run without LLM (pattern-only mode), but for best results:

1. Get LiteLLM credentials from your provider
2. Add them to `.env` file
3. Run the scraper again

### Error: "No candidates found"

The website structure may have changed. Options:

1. Save a fixture manually and inspect HTML
2. Adjust parser heuristics in `core/parser.py`
3. Try a different target URL

## Performance

### HTTP Mode
- Speed: ~2 seconds
- Success rate: Low (often blocked)
- Use for: Testing with cooperative sites

### Browser Mode
- Speed: ~10-15 seconds
- Success rate: High (bypasses most anti-bot)
- Use for: Production scraping with anti-bot sites

### Offline Mode
- Speed: <1 second
- Success rate: 100% (deterministic)
- Use for: Development and testing

## Browser Mode Details

Browser mode (Playwright) provides:

✅ **JavaScript execution** - Handles dynamic content
✅ **Anti-bot bypass** - Real browser fingerprint
✅ **Cloudflare bypass** - Passes most challenges
✅ **Cookie handling** - Automatic cookie management
✅ **Realistic headers** - Genuine Chrome headers

### Browser Options

You can customize browser behavior in `core/browser_fetcher.py`:

```python
# Run in visible mode (see browser window)
headless=False

# Wait for specific selector
wait_for_selector="article.news-card"

# Increase timeout for slow sites
timeout=60000  # 60 seconds
```

## Recommendations

For **Moneycontrol scraping**:

1. ✅ Use `--browser` flag (bypasses 403 errors)
2. ✅ Use `--save-fixture` to save HTML for development
3. ✅ Test with offline mode after saving fixture
4. ✅ Configure LiteLLM for best data quality

## Next Steps

After successful setup:

1. Run with browser mode: `python run_trial.py --browser --save-fixture`
2. Check output in `outputs/moneycontrol_listing_page1.jsonl`
3. Review acceptance criteria in terminal output
4. Adjust parser/prompts as needed

## System Requirements

- **Python**: 3.10 or higher
- **RAM**: 2GB+ (4GB recommended for browser mode)
- **Disk**: 500MB (mostly for Chromium browser)
- **OS**: Windows, macOS, or Linux

## Architecture

```
Fetch Methods:
┌─────────────────┬──────────────────┬─────────────────┐
│ HTTP (httpx)    │ Browser (PW)     │ Offline         │
├─────────────────┼──────────────────┼─────────────────┤
│ Fast            │ Reliable         │ Instant         │
│ May get blocked │ Bypasses anti-bot│ Deterministic   │
│ No JS execution │ Full JS support  │ No network      │
└─────────────────┴──────────────────┴─────────────────┘
```

Choose the method that fits your needs!
