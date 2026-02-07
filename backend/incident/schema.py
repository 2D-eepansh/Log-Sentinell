"""
Schema for Phase 3 incident context builder.

Incident objects contain only factual, observable data derived from
Phase 1 (logs/features) and Phase 2 (anomaly events).
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from src.anomaly.schema import AnomalyEvent, AnomalySeverity


class LogPattern(BaseModel):
    """
    Bounded log pattern summary.

    Fields:
    - key: message hash or canonical message identifier
    - count: number of log entries matching the key
    - sample_message: optional sample message (truncated upstream if needed)
    """

    key: str
    count: int = Field(ge=1)
    sample_message: Optional[str] = None


class OperationalEvent(BaseModel):
    """
    Operational context event (e.g., deployment).

    Fields:
    - event_type: deployment, config_change, maintenance, etc.
    - timestamp: event time
    - description: short factual description
    - metadata: optional structured data
    """

    event_type: str
    timestamp: datetime
    description: str
    metadata: Dict[str, str] = Field(default_factory=dict)


class MetricsSummary(BaseModel):
    """
    Aggregated metrics for an incident.

    Fields:
    - anomaly_count: total anomaly events in this incident
    - feature_count: number of distinct features involved
    - max_score: maximum anomaly score
    - severity_counts: count of anomalies by severity
    """

    anomaly_count: int = Field(ge=1)
    feature_count: int = Field(ge=1)
    max_score: float = Field(ge=0.0, le=1.0)
    severity_counts: Dict[AnomalySeverity, int]


class Incident(BaseModel):
    """
    High-level incident object built from anomaly events.

    Required fields:
    - incident_id: stable unique identifier
    - service: service name
    - start_time: earliest time in incident window
    - end_time: latest time in incident window
    - anomalies: list of anomaly events grouped into this incident
    - metrics_summary: aggregated anomaly statistics
    - log_patterns: bounded list of log pattern summaries
    - operational_context: bounded list of operational events
    """

    incident_id: str = Field(default_factory=lambda: str(uuid4()))
    service: str
    start_time: datetime
    end_time: datetime
    anomalies: List[AnomalyEvent]
    metrics_summary: MetricsSummary
    log_patterns: List[LogPattern]
    operational_context: List[OperationalEvent]

