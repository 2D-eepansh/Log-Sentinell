"""
Schema definitions for Phase 2 anomaly detection.

All anomaly outputs are deterministic and explainable. Each anomaly references
its observed value, baseline statistics, and computed deviations.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class AnomalySeverity(str, Enum):
    """Severity levels for anomalies."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BaselineStats(BaseModel):
    """
    Baseline statistics for a single feature.

    Fields:
    - mean: central tendency
    - std: dispersion (>= std_floor)
    - count: number of points used
    - method: baseline strategy used
    """

    mean: float
    std: float
    count: int
    method: str


class FeatureAnomaly(BaseModel):
    """
    Anomaly result for a single feature within a window.

    Fields:
    - feature: name of the feature
    - observed: observed value in the window
    - baseline_mean/std: baseline reference values
    - z_score: standardized deviation (None if unavailable)
    - rate_change: relative change vs previous value (None if unavailable)
    - score: combined anomaly score in [0.0, 1.0]
    - severity: categorical severity
    - direction: "high" or "low" relative to baseline
    - suppressed: True if suppressed by redundancy rules
    - suppression_reason: optional reason for suppression
    """

    feature: str
    observed: float
    baseline_mean: float
    baseline_std: float
    z_score: Optional[float] = None
    rate_change: Optional[float] = None
    score: float = Field(ge=0.0, le=1.0)
    severity: AnomalySeverity
    direction: str
    suppressed: bool = False
    suppression_reason: Optional[str] = None


class AnomalyEvent(BaseModel):
    """
    Aggregated anomaly event for a service and time window.

    Fields:
    - event_id: unique identifier
    - service: service name
    - window_start: window start timestamp
    - detected_at: detection timestamp
    - severity: highest severity among anomalies
    - score: highest score among anomalies
    - anomalies: list of feature anomalies
    """

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    service: str
    window_start: datetime
    detected_at: datetime
    severity: AnomalySeverity
    score: float = Field(ge=0.0, le=1.0)
    anomalies: List[FeatureAnomaly]

