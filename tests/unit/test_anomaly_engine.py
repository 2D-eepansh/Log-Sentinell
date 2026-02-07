"""
Unit tests for anomaly detection engine.
"""

from datetime import datetime, timezone

from src.anomaly.engine import AnomalyEngine
from src.anomaly.schema import AnomalySeverity
from src.data.schema import FeatureVector


def _make_feature_vector(window_start: datetime, service: str, **overrides) -> FeatureVector:
    data = {
        "window_start": window_start,
        "service": service,
        "total_events": 100,
        "error_count": 1,
        "warning_count": 1,
        "info_count": 98,
        "error_rate": 0.01,
        "warning_rate": 0.01,
        "median_duration_ms": 100.0,
        "p95_duration_ms": 200.0,
        "max_duration_ms": 300.0,
        "unique_messages": 10,
        "unique_error_codes": 1,
    }
    data.update(overrides)
    return FeatureVector(**data)


def test_engine_warmup_and_detection():
    engine = AnomalyEngine()
    service = "api"
    t0 = datetime(2025, 2, 7, 10, 0, tzinfo=timezone.utc)

    # Warm-up period (should not emit anomalies)
    warmup = [
        _make_feature_vector(t0, service, error_rate=0.01) for _ in range(10)
    ]
    events = engine.detect(warmup)
    assert events == []

    # Introduce spike
    spike = _make_feature_vector(t0, service, error_rate=0.5, error_count=50)
    events = engine.detect([spike])

    assert len(events) == 1
    event = events[0]
    assert event.service == service
    assert event.severity in {AnomalySeverity.MEDIUM, AnomalySeverity.HIGH, AnomalySeverity.CRITICAL}
    assert any(a.feature == "error_rate" for a in event.anomalies)


def test_engine_redundancy_suppression():
    engine = AnomalyEngine()
    service = "auth"
    t0 = datetime(2025, 2, 7, 11, 0, tzinfo=timezone.utc)

    # Warm-up
    warmup = [
        _make_feature_vector(t0, service, error_rate=0.02, warning_rate=0.01) for _ in range(10)
    ]
    _ = engine.detect(warmup)

    # Spike both rate features (same family)
    spike = _make_feature_vector(t0, service, error_rate=0.6, warning_rate=0.5)
    events = engine.detect([spike])

    assert len(events) == 1
    event = events[0]
    rate_anomalies = [a for a in event.anomalies if a.feature in {"error_rate", "warning_rate"}]

    # Suppression should keep only the top rate anomaly
    assert len(rate_anomalies) == 1

