"""
Unit tests for LoRA training dataset schema utilities.
"""

from datetime import datetime, timezone

from backend.incident.schema import Incident, MetricsSummary
from llm.schema import Explanation
from llm.training.schema import TrainingSample
from llm.training.dataset import build_training_prompt, format_completion


def _make_sample():
    incident = Incident(
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
    explanation = Explanation(
        incident_id="inc-1",
        summary="Summary long enough for validation.",
        probable_causes=["unknown"],
        supporting_evidence=["service=api"],
        confidence_score=0.2,
        recommended_next_steps=["Validate incident scope and confirm if impact persists"],
        limitations="Limitations long enough for validation.",
    )
    return TrainingSample(incident=incident, explanation=explanation)


def test_training_prompt_and_completion():
    sample = _make_sample()
    prompt = build_training_prompt(sample)
    completion = format_completion(sample)

    assert "RETURN_JSON_ONLY" in prompt
    assert completion.startswith("{")
    assert "incident_id" in completion
