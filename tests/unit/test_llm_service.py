"""
Unit tests for LLM service validation and fallback.
"""

from datetime import datetime, timezone

from backend.incident.schema import Incident, MetricsSummary
from llm.schema import Explanation
from backend.llm_service import IncidentExplanationService


class _FakeModel:
    def __init__(self, output: str):
        self._output = output

    def generate(self, prompt: str) -> str:
        return self._output


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
        log_patterns=[],
        operational_context=[],
    )


def test_fallback_on_invalid_json():
    incident = _make_incident()
    service = IncidentExplanationService(model=_FakeModel("not json"))
    explanation = service.explain(incident)

    assert isinstance(explanation, Explanation)
    assert explanation.incident_id == incident.incident_id
    assert explanation.confidence_score == 0.0


def test_rejects_disallowed_values():
    incident = _make_incident()
    bad_json = """
    {
        "incident_id": "inc-1",
        "summary": "This is a test summary with enough length.",
        "probable_causes": ["made_up"],
        "supporting_evidence": ["fake"],
        "confidence_score": 0.5,
        "recommended_next_steps": ["made_up"],
        "limitations": "Test limitations with enough length."
    }
    """
    service = IncidentExplanationService(model=_FakeModel(bad_json))
    explanation = service.explain(incident)

    assert explanation.probable_causes == ["unknown"]
    assert explanation.confidence_score == 0.0
