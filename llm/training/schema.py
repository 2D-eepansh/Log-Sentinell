"""
Training dataset schema for Phase 5.

Each sample contains:
- Incident context (Phase 3 output)
- Target explanation (Phase 4 schema)

All samples are inspectable JSON objects in JSONL format.
"""

from __future__ import annotations

from pydantic import BaseModel

from backend.incident.schema import Incident
from llm.schema import Explanation


class TrainingSample(BaseModel):
    """
    Single training sample for LoRA fine-tuning.
    """

    incident: Incident
    explanation: Explanation
