"""
Dataset utilities for Phase 5 LoRA fine-tuning.

Converts Incident + Explanation pairs into supervised prompt-completion samples.
"""

from __future__ import annotations

import json
from typing import Iterable, List

from backend.incident.schema import Incident
from llm.prompt import build_prompt
from llm.schema import Explanation

from .schema import TrainingSample


def load_training_samples(path: str) -> List[TrainingSample]:
    """
    Load JSONL training samples from disk.

    Each line must be a JSON object with keys: incident, explanation.
    """

    samples: List[TrainingSample] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            payload = json.loads(line)
            samples.append(TrainingSample(**payload))
    return samples


def build_training_prompt(sample: TrainingSample) -> str:
    """
    Build the training prompt using the same strict template as inference.
    """

    incident = sample.incident
    allowed_causes = _allowed_causes(incident)
    allowed_evidence = _allowed_evidence(incident)
    allowed_steps = _allowed_steps(incident, allowed_causes)

    return build_prompt(incident, allowed_causes, allowed_evidence, allowed_steps)


def format_completion(sample: TrainingSample) -> str:
    """
    Format the target completion as JSON for supervised fine-tuning.
    """

    return json.dumps(sample.explanation.model_dump(), sort_keys=True)


def _allowed_causes(incident: Incident) -> List[str]:
    causes = {"unknown"}

    for event in incident.anomalies:
        for anomaly in event.anomalies:
            feature = anomaly.feature
            if feature in {"error_rate", "error_count"}:
                causes.add("error_rate_spike")
            if feature in {"warning_rate", "warning_count"}:
                causes.add("warning_spike")
            if feature in {"median_duration_ms", "p95_duration_ms", "max_duration_ms"}:
                causes.add("latency_regression")
            if feature in {"total_events", "info_count"}:
                causes.add("traffic_spike")
            if feature in {"unique_messages", "unique_error_codes"}:
                causes.add("error_variation")

    for op in incident.operational_context:
        if "deploy" in op.event_type.lower():
            causes.add("deployment_change")

    return sorted(causes)


def _allowed_evidence(incident: Incident) -> List[str]:
    evidence = set()
    evidence.add(f"service={incident.service}")
    evidence.add(f"start_time={incident.start_time.isoformat()}")
    evidence.add(f"end_time={incident.end_time.isoformat()}")
    evidence.add(f"max_score={incident.metrics_summary.max_score:.2f}")

    for event in incident.anomalies:
        evidence.add(f"window_start={event.window_start.isoformat()}")
        evidence.add(f"severity={event.severity}")
        for anomaly in event.anomalies:
            evidence.add(f"feature={anomaly.feature}")
            evidence.add(f"direction={anomaly.direction}")

    for pattern in incident.log_patterns:
        evidence.add(f"log_pattern={pattern.key}|count={pattern.count}")

    for op in incident.operational_context:
        evidence.add(f"op_event={op.event_type}|time={op.timestamp.isoformat()}")

    return sorted(evidence)


def _allowed_steps(incident: Incident, causes: List[str]) -> List[str]:
    steps = set()

    if "deployment_change" in causes:
        steps.add("Review recent deployments in the incident window")
    if "error_rate_spike" in causes or "warning_spike" in causes:
        steps.add("Inspect error and warning logs for the affected service")
    if "latency_regression" in causes:
        steps.add("Check latency metrics and downstream dependencies")
    if "traffic_spike" in causes:
        steps.add("Verify traffic sources and request patterns")
    if "error_variation" in causes:
        steps.add("Group errors by code to identify new patterns")

    steps.add("Validate incident scope and confirm if impact persists")
    return sorted(steps)
