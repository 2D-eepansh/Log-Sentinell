"""
Backend service layer for Phase 4 LLM inference.

Converts Incident objects into validated Explanation objects using a local Mistral model.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
import logging
from typing import Dict, List, Optional

from backend.incident.schema import Incident
from llm.config import LLMConfig
from llm.mistral import MistralLocalModel
from llm.prompt import build_prompt
from llm.schema import Explanation

logger = logging.getLogger("backend.llm")


@dataclass
class IncidentExplanationService:
    """
    Phase 4 explanation service.

    - Builds strict prompts.
    - Runs local inference.
    - Validates output schema.
    - Enforces allowed choices to prevent hallucinations.
    """

    model: MistralLocalModel

    def explain(self, incident: Incident) -> Explanation:
        allowed_causes = self._allowed_causes(incident)
        allowed_evidence = self._allowed_evidence(incident)
        allowed_steps = self._allowed_steps(incident, allowed_causes)

        prompt = build_prompt(incident, allowed_causes, allowed_evidence, allowed_steps)
        try:
            raw = self.model.generate(prompt)
        except Exception as exc:
            logger.exception("LLM generation failed: %s", exc)
            return self._fallback_explanation(incident, allowed_evidence)

        try:
            parsed = self._parse_json(raw)
            explanation = Explanation(**parsed)
        except Exception:
            return self._fallback_explanation(incident, allowed_evidence)

        if not self._validate_allowed(explanation, allowed_causes, allowed_evidence, allowed_steps):
            return self._fallback_explanation(incident, allowed_evidence)

        return explanation

    def _allowed_causes(self, incident: Incident) -> List[str]:
        causes = set(["unknown"])

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

    def _allowed_evidence(self, incident: Incident) -> List[str]:
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

    def _allowed_steps(self, incident: Incident, causes: List[str]) -> List[str]:
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

    def _parse_json(self, raw: str) -> Dict[str, object]:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON object found in LLM output")
        payload = raw[start : end + 1]
        return json.loads(payload)

    def _validate_allowed(
        self,
        explanation: Explanation,
        allowed_causes: List[str],
        allowed_evidence: List[str],
        allowed_steps: List[str],
    ) -> bool:
        if not set(explanation.probable_causes).issubset(set(allowed_causes)):
            return False
        if not set(explanation.supporting_evidence).issubset(set(allowed_evidence)):
            return False
        if not set(explanation.recommended_next_steps).issubset(set(allowed_steps)):
            return False
        return True

    def _fallback_explanation(self, incident: Incident, allowed_evidence: List[str]) -> Explanation:
        evidence = allowed_evidence[:3] if allowed_evidence else [f"service={incident.service}"]
        return Explanation(
            incident_id=incident.incident_id,
            summary="Incident explanation unavailable; fallback generated from known facts.",
            probable_causes=["unknown"],
            supporting_evidence=evidence,
            confidence_score=0.0,
            recommended_next_steps=["Validate incident scope and confirm if impact persists"],
            limitations="LLM output was invalid or unavailable; returned minimal factual summary.",
        )


def create_explanation_service(model_path: str) -> IncidentExplanationService:
    """
    Factory for explanation service with local Mistral model.
    """

    config = LLMConfig(model_path=model_path)
    model = MistralLocalModel(config=config)
    return IncidentExplanationService(model=model)
