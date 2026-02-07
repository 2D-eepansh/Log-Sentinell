"""
Unit tests for LLM prompt construction.
"""

from datetime import datetime, timezone

from backend.incident.schema import Incident, MetricsSummary
from backend.incident.schema import LogPattern, OperationalEvent
from llm.prompt import build_prompt


def _make_incident():
    return Incident(
        incident_id="inc-1",
        service="api",
        start_time=datetime(2025, 2, 7, 12, 0, tzinfo=timezone.utc),
        end_time=datetime(2025, 2, 7, 12, 5, tzinfo=timezone.utc),
        anomalies=[],
        metrics_summary=MetricsSummary(
            anomaly_count=1,
            feature_count=1,
            max_score=0.7,
            severity_counts={},
        ),
        log_patterns=[LogPattern(key="hash1", count=2, sample_message="Error")],
        operational_context=[
            OperationalEvent(
                event_type="deployment",
                timestamp=datetime(2025, 2, 7, 11, 55, tzinfo=timezone.utc),
                description="Deploy",
            )
        ],
    )


def test_prompt_contains_allowed_lists():
    incident = _make_incident()
    prompt = build_prompt(
        incident,
        allowed_causes=["unknown"],
        allowed_evidence=["service=api"],
        allowed_steps=["Check logs"],
    )

    assert "ALLOWED_CAUSES" in prompt
    assert "ALLOWED_EVIDENCE" in prompt
    assert "ALLOWED_STEPS" in prompt
    assert "RETURN_JSON_ONLY" in prompt
