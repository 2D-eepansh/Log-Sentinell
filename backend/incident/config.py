"""
Configuration for Phase 3 incident context builder.

All settings are deterministic and bounded to avoid over-aggregation
and oversized context payloads.
"""

from __future__ import annotations

from typing import Dict

from pydantic import BaseModel, Field


class IncidentConfig(BaseModel):
    """
    Incident grouping and context configuration.

    Notes:
    - max_gap_seconds: maximum time gap between anomaly windows to group.
    - window_size_seconds: assumed window duration for end_time computation.
    - require_feature_family_overlap: if True, only group events sharing feature families.
    - context_window_seconds: extra time before/after incident for context attachment.
    - max_log_patterns: cap on distinct log patterns to attach.
    - max_operational_events: cap on operational events to attach.
    """

    max_gap_seconds: int = Field(600, ge=0)
    window_size_seconds: int = Field(300, ge=1)
    require_feature_family_overlap: bool = True
    context_window_seconds: int = Field(300, ge=0)
    max_log_patterns: int = Field(10, ge=1)
    max_operational_events: int = Field(10, ge=0)

    feature_families: Dict[str, str] = Field(
        default_factory=lambda: {
            "total_events": "count",
            "error_count": "count",
            "warning_count": "count",
            "info_count": "count",
            "error_rate": "rate",
            "warning_rate": "rate",
            "median_duration_ms": "duration",
            "p95_duration_ms": "duration",
            "max_duration_ms": "duration",
            "unique_messages": "diversity",
            "unique_error_codes": "diversity",
        }
    )

