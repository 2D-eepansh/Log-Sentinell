"""
Unit tests for Phase 3 incident context builder.
"""

from datetime import datetime, timezone, timedelta

from src.anomaly.schema import AnomalyEvent, AnomalySeverity, FeatureAnomaly

from backend.incident.builder import IncidentBuilder
from backend.incident.config import IncidentConfig
from backend.incident.schema import OperationalEvent


def _make_event(service: str, window_start: datetime, feature: str, score: float = 0.6):
    anomaly = FeatureAnomaly(
        feature=feature,
        observed=1.0,
        baseline_mean=0.5,
        baseline_std=0.1,
        z_score=5.0,
        rate_change=2.0,
        score=score,
        severity=AnomalySeverity.HIGH,
        direction="high",
    )
    return AnomalyEvent(
        service=service,
        window_start=window_start,
        detected_at=window_start,
        severity=AnomalySeverity.HIGH,
        score=score,
        anomalies=[anomaly],
    )


def test_single_anomaly_creates_single_incident():
    builder = IncidentBuilder()
    t0 = datetime(2025, 2, 7, 12, 0, tzinfo=timezone.utc)
    events = [_make_event("api", t0, "error_rate")]

    incidents = builder.build_incidents(events)
    assert len(incidents) == 1
    assert incidents[0].service == "api"
    assert incidents[0].start_time == t0


def test_time_gap_splits_incidents():
    config = IncidentConfig(max_gap_seconds=60, require_feature_family_overlap=False)
    builder = IncidentBuilder(config)
    t0 = datetime(2025, 2, 7, 12, 0, tzinfo=timezone.utc)
    events = [
        _make_event("api", t0, "error_rate"),
        _make_event("api", t0 + timedelta(seconds=120), "error_rate"),
    ]

    incidents = builder.build_incidents(events)
    assert len(incidents) == 2


def test_feature_family_overlap_required():
    config = IncidentConfig(max_gap_seconds=600, require_feature_family_overlap=True)
    builder = IncidentBuilder(config)
    t0 = datetime(2025, 2, 7, 12, 0, tzinfo=timezone.utc)

    events = [
        _make_event("api", t0, "error_rate"),
        _make_event("api", t0 + timedelta(seconds=120), "max_duration_ms"),
    ]

    incidents = builder.build_incidents(events)
    assert len(incidents) == 2


def test_operational_context_is_bounded():
    config = IncidentConfig(max_operational_events=1, context_window_seconds=60)
    builder = IncidentBuilder(config)
    t0 = datetime(2025, 2, 7, 12, 0, tzinfo=timezone.utc)
    events = [_make_event("api", t0, "error_rate")]

    op_events = [
        OperationalEvent(
            event_type="deployment",
            timestamp=t0 - timedelta(seconds=30),
            description="Deploy v1",
        ),
        OperationalEvent(
            event_type="deployment",
            timestamp=t0 + timedelta(seconds=30),
            description="Deploy v2",
        ),
    ]

    incidents = builder.build_incidents(events, operational_events=op_events)
    assert len(incidents[0].operational_context) == 1

