"""
Prompt construction for local Mistral inference.

The prompt strictly constrains output to JSON that adheres to the Explanation schema
and references only the provided incident context and allowed option lists.
"""

from __future__ import annotations

import json
from typing import List

from backend.incident.schema import Incident


def build_prompt(
    incident: Incident,
    allowed_causes: List[str],
    allowed_evidence: List[str],
    allowed_steps: List[str],
) -> str:
    """
    Build a strict JSON-only prompt for the local LLM.

    The model must select probable_causes, supporting_evidence, and
    recommended_next_steps from the provided allowed lists only.
    """

    incident_payload = json.dumps(incident.model_dump(), sort_keys=True, default=str)

    instructions = {
        "task": "Explain the incident using only provided facts.",
        "constraints": [
            "Return a single JSON object only.",
            "Do NOT include any text outside JSON.",
            "Use only allowed values for probable_causes, supporting_evidence, and recommended_next_steps.",
            "Do NOT invent facts beyond the incident data.",
            "If uncertain, state limitations clearly.",
        ],
        "schema": {
            "incident_id": "string",
            "summary": "string",
            "probable_causes": "list[string]",
            "supporting_evidence": "list[string]",
            "confidence_score": "float in [0,1]",
            "recommended_next_steps": "list[string]",
            "limitations": "string",
        },
    }

    prompt = (
        "You are a reliability assistant. Use ONLY the incident data and allowed lists.\n"
        f"INSTRUCTIONS: {json.dumps(instructions, sort_keys=True)}\n"
        f"INCIDENT: {incident_payload}\n"
        f"ALLOWED_CAUSES: {json.dumps(sorted(allowed_causes))}\n"
        f"ALLOWED_EVIDENCE: {json.dumps(sorted(allowed_evidence))}\n"
        f"ALLOWED_STEPS: {json.dumps(sorted(allowed_steps))}\n"
        "RETURN_JSON_ONLY:"
    )

    return prompt
