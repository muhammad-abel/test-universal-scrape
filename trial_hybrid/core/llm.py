"""
LLM wrapper using LiteLLM for normalizing extracted data.
"""
import os
import json
from typing import Dict, Any
from litellm import acompletion

# Configuration from environment variables
MODEL = os.getenv("LITELLM_MODEL", "openai/gpt-4o-mini")
API_BASE = os.getenv("LITELLM_API_BASE")
API_KEY = os.getenv("LITELLM_API_KEY")

SYSTEM_PROMPT = """You are a strict JSON normalizer for news data extraction.

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


def build_user_prompt(candidate: Dict[str, Any]) -> str:
    """
    Build the user prompt for LLM normalization.

    Args:
        candidate: Candidate data dictionary

    Returns:
        Formatted prompt string
    """
    schema_example = {
        "source": "moneycontrol",
        "category": "markets",
        "headline": "Example headline text",
        "url": "https://www.moneycontrol.com/news/...",
        "summary": "Brief summary of the article",
        "published_label": "2 hours ago",
        "confidence": 0.9,
        "evidence": {
            "snippet": "Text snippet used from candidate"
        }
    }

    candidate_data = {
        "headline": candidate.get("headline"),
        "url": candidate.get("url"),
        "summary": candidate.get("summary"),
        "published_label": candidate.get("published_label"),
    }

    prompt = f"""SCHEMA (target format):
{json.dumps(schema_example, indent=2, ensure_ascii=False)}

CANDIDATE (raw extracted data):
{json.dumps(candidate_data, indent=2, ensure_ascii=False)}

INSTRUCTIONS:
1. Normalize the CANDIDATE data to match the SCHEMA format
2. Use only text from CANDIDATE - do not add new information
3. Set confidence based on data completeness and quality
4. Include evidence.snippet from the candidate text (headline or summary)
5. Keep summary ≤200 characters
6. Return ONLY the JSON object, no other text

Output the normalized JSON:"""

    return prompt


async def normalize_with_llm(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a candidate item using LLM.

    Args:
        candidate: Candidate dictionary with extracted fields

    Returns:
        Normalized dictionary matching NewsItem schema

    Raises:
        Exception: If LLM call fails or returns invalid JSON
    """
    prompt = build_user_prompt(candidate)

    try:
        response = await acompletion(
            model=MODEL,
            api_base=API_BASE,
            api_key=API_KEY,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        # Ensure required fields are present with fallbacks
        data.setdefault("source", "moneycontrol")
        data.setdefault("category", "markets")
        data.setdefault("confidence", 0.5)

        # Ensure evidence.snippet exists
        if not data.get("evidence") or not data["evidence"].get("snippet"):
            snippet = candidate.get("summary") or candidate.get("headline") or ""
            data["evidence"] = {"snippet": snippet[:240]}

        return data

    except json.JSONDecodeError as e:
        # If JSON parsing fails, return a fallback with low confidence
        print(f"JSON decode error: {e}")
        return {
            "source": "moneycontrol",
            "category": "markets",
            "headline": candidate.get("headline", ""),
            "url": candidate.get("url", ""),
            "summary": candidate.get("summary"),
            "published_label": candidate.get("published_label"),
            "confidence": 0.0,
            "evidence": {"snippet": "JSON parse error"}
        }
    except Exception as e:
        print(f"LLM error: {e}")
        raise
