"""
Schema for LLM-generated incident explanations.

All fields are bounded, factual, and validated before use.
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class Explanation(BaseModel):
    """
    Structured incident explanation.

    Fields:
    - incident_id: incident identifier
    - summary: short factual summary (bounded length)
    - probable_causes: ranked list from allowed options
    - supporting_evidence: list of allowed evidence strings
    - confidence_score: [0.0, 1.0]
    - recommended_next_steps: bounded list from allowed options
    - limitations: explicit uncertainty or data gaps
    """

    incident_id: str
    summary: str = Field(min_length=10, max_length=500)
    probable_causes: List[str] = Field(min_length=1, max_length=5)
    supporting_evidence: List[str] = Field(min_length=1, max_length=10)
    confidence_score: float = Field(ge=0.0, le=1.0)
    recommended_next_steps: List[str] = Field(min_length=1, max_length=5)
    limitations: str = Field(min_length=10, max_length=500)
