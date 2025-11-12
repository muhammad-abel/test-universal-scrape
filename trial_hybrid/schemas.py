"""
Pydantic schemas for the hybrid scraper.
"""
from typing import Literal
from pydantic import BaseModel, Field, HttpUrl


class NewsItem(BaseModel):
    """
    Schema for a news item from Moneycontrol markets listing.
    """
    source: Literal["moneycontrol"] = "moneycontrol"
    category: Literal["markets"] = "markets"
    headline: str
    url: HttpUrl
    summary: str | None = None
    published_label: str | None = None
    confidence: float = Field(ge=0, le=1, default=0.0)
    evidence: dict | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "source": "moneycontrol",
                    "category": "markets",
                    "headline": "Stock markets rally on positive earnings",
                    "url": "https://www.moneycontrol.com/news/business/markets/example-123.html",
                    "summary": "Major indices posted gains as tech companies reported strong earnings.",
                    "published_label": "2 hours ago",
                    "confidence": 0.95,
                    "evidence": {
                        "snippet": "Stock markets rally on positive earnings. Major indices posted gains..."
                    }
                }
            ]
        }
    }
