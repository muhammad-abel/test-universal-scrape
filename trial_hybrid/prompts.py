"""
LLM prompt templates for the hybrid scraper.

This module contains carefully crafted prompts designed to minimize hallucination
and ensure accurate data normalization.
"""

SYSTEM_PROMPT_NORMALIZER = """You are a strict JSON normalizer for news data extraction.

Your task is to normalize and validate news article data from web scraping candidates.

Rules:
1. Return ONLY valid JSON matching the NewsItem schema - no additional text or explanation
2. Use ONLY the information provided in the CANDIDATE data - never add or invent information
3. If a field is unclear or missing in the candidate, set it to null
4. Assign a confidence score (0.0-1.0) based on data quality:
   - 0.9-1.0: All fields clear and well-formed
   - 0.7-0.9: Most fields clear, some minor issues
   - 0.5-0.7: Some fields missing or unclear
   - 0.0-0.5: Poor quality or mostly missing data
5. Include evidence.snippet showing the text you used from the candidate
6. Ensure summary is ≤200 characters and concise
7. Never modify URLs - use them exactly as provided
"""

USER_PROMPT_TEMPLATE = """SCHEMA (target format):
{schema_example}

CANDIDATE (raw extracted data):
{candidate_data}

INSTRUCTIONS:
1. Normalize the CANDIDATE data to match the SCHEMA format
2. Use only text from CANDIDATE - do not add new information
3. Set confidence based on data completeness and quality
4. Include evidence.snippet from the candidate text (headline or summary)
5. Keep summary ≤200 characters
6. Return ONLY the JSON object, no other text

Output the normalized JSON:"""

# Anti-hallucination guidelines embedded in prompts
ANTI_HALLUCINATION_RULES = """
CRITICAL ANTI-HALLUCINATION RULES:
- NEVER invent or add information not present in the candidate
- NEVER enhance or embellish the headline or summary
- NEVER change the meaning or add context
- NEVER correct spelling or grammar (preserve original text)
- NEVER add dates, times, or numbers not in the candidate
- If uncertain about any field, set it to null
- If summary is missing, set to null (do NOT create one from headline)
- Preserve exact URLs without modification
"""

CONFIDENCE_SCORING_GUIDE = """
CONFIDENCE SCORING GUIDE:

0.9 - 1.0 (Excellent):
- Headline is clear and complete (>10 chars, <200 chars)
- URL is well-formed and absolute
- Summary is present and meaningful (>20 chars)
- Published label is present with clear time indicator

0.7 - 0.9 (Good):
- Headline is clear
- URL is valid
- Summary OR published_label is present
- Minor formatting issues

0.5 - 0.7 (Acceptable):
- Headline is present but may be truncated
- URL is valid
- Summary and published_label may be missing
- Some data quality concerns

0.3 - 0.5 (Poor):
- Headline is very short or unclear
- URL may be relative or questionable
- Most optional fields missing

0.0 - 0.3 (Very Poor):
- Headline is missing or nonsensical
- URL is missing or invalid
- Likely not a news article
"""


def build_normalization_prompt(candidate: dict, schema_example: dict) -> str:
    """
    Build a complete normalization prompt.

    Args:
        candidate: Candidate data dictionary
        schema_example: Example schema dictionary

    Returns:
        Formatted prompt string
    """
    import json

    candidate_data = {
        "headline": candidate.get("headline"),
        "url": candidate.get("url"),
        "summary": candidate.get("summary"),
        "published_label": candidate.get("published_label"),
    }

    return USER_PROMPT_TEMPLATE.format(
        schema_example=json.dumps(schema_example, indent=2, ensure_ascii=False),
        candidate_data=json.dumps(candidate_data, indent=2, ensure_ascii=False)
    )
