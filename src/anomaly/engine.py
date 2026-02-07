"""
Phase 2 anomaly detection engine.

Consumes Phase 1 FeatureVector objects, estimates baselines, detects deviations,
computes scores, and aggregates anomalies into events.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Tuple

from src.core.config import config
from src.data.schema import FeatureVector

from .baselines import BaselinePair, EWMABaselineEstimator, RollingStatsEstimator
from .detectors import RateOfChangeDetector, ZScoreDetector
from .schema import AnomalyEvent, AnomalySeverity, FeatureAnomaly
from .scoring import SeverityMapper, combine_scores, overall_severity


@dataclass
class AnomalyEngine:
    """
    Deterministic anomaly detection engine.

    Notes:
    - Uses conservative thresholds to reduce false positives.
    - Warm-up period enforced via baseline config.
    - Supports redundancy suppression by feature families.
    """

    def __post_init__(self) -> None:
        self._baselines: Dict[Tuple[str, str], BaselinePair] = {}
        self._z_detector = ZScoreDetector(min_std=config.anomaly.baselines.std_floor)
        self._roc_detector = RateOfChangeDetector()
        self._severity_mapper = SeverityMapper(config.anomaly.thresholds)

    def detect(self, features: Iterable[FeatureVector]) -> List[AnomalyEvent]:
        events: List[AnomalyEvent] = []

        for fv in features:
            event = self._detect_window(fv)
            if event is not None:
                events.append(event)

        return events

    def _detect_window(self, fv: FeatureVector) -> Optional[AnomalyEvent]:
        anomalies: List[FeatureAnomaly] = []

        for feature_name, value in self._iter_feature_values(fv):
            anomaly = self._detect_feature(fv, feature_name, value)
            if anomaly is not None and anomaly.severity != AnomalySeverity.NONE:
                anomalies.append(anomaly)

        if not anomalies:
            return None

        if config.anomaly.suppress_redundant:
            self._suppress_redundant(anomalies)

        active = [a for a in anomalies if not a.suppressed]
        if not active:
            return None

        max_score = max(a.score for a in active)
        max_severity = overall_severity(*(a.severity for a in active))

        return AnomalyEvent(
            service=fv.service,
            window_start=fv.window_start,
            detected_at=datetime.now(timezone.utc),
            severity=max_severity,
            score=max_score,
            anomalies=active,
        )

    def _detect_feature(
        self, fv: FeatureVector, feature_name: str, observed: float
    ) -> Optional[FeatureAnomaly]:
        key = (fv.service, feature_name)
        baseline_pair = self._baselines.get(key)
        if baseline_pair is None:
            baseline_pair = self._create_baseline_pair()
            self._baselines[key] = baseline_pair

        baseline = baseline_pair.peek(config.anomaly.baselines.strategy)
        previous_value = baseline_pair.last_value

        if baseline is None:
            baseline_pair.update(observed)
            return None

        zscore = self._z_detector.compute(observed, baseline)
        roc = self._roc_detector.compute(observed, previous_value)

        score = combine_scores(
            zscore=zscore,
            rate_change=roc,
            thresholds=config.anomaly.thresholds,
            scoring=config.anomaly.scoring,
        )

        if score < config.anomaly.scoring.score_floor:
            baseline_pair.update(observed)
            return None

        z_sev = self._severity_mapper.zscore_severity(zscore)
        roc_sev = self._severity_mapper.rate_change_severity(roc)
        severity = overall_severity(z_sev, roc_sev)

        direction = "high" if observed >= baseline.mean else "low"

        anomaly = FeatureAnomaly(
            feature=feature_name,
            observed=observed,
            baseline_mean=baseline.mean,
            baseline_std=baseline.std,
            z_score=zscore,
            rate_change=roc,
            score=score,
            severity=severity,
            direction=direction,
        )

        baseline_pair.update(observed)
        return anomaly

    def _create_baseline_pair(self) -> BaselinePair:
        rolling = RollingStatsEstimator(
            window_size=config.anomaly.baselines.window_size,
            min_points=config.anomaly.baselines.min_points,
            std_floor=config.anomaly.baselines.std_floor,
        )
        ewma = EWMABaselineEstimator(
            alpha=config.anomaly.baselines.ewma_alpha,
            min_points=config.anomaly.baselines.min_points,
            std_floor=config.anomaly.baselines.std_floor,
        )
        return BaselinePair(rolling=rolling, ewma=ewma)

    def _iter_feature_values(self, fv: FeatureVector) -> Iterable[Tuple[str, float]]:
        data = fv.model_dump()
        feature_fields = [
            "total_events",
            "error_count",
            "warning_count",
            "info_count",
            "error_rate",
            "warning_rate",
            "median_duration_ms",
            "p95_duration_ms",
            "max_duration_ms",
            "unique_messages",
            "unique_error_codes",
        ]

        for name in feature_fields:
            value = data.get(name)
            if value is None:
                continue
            yield name, float(value)

    def _suppress_redundant(self, anomalies: List[FeatureAnomaly]) -> None:
        families: Dict[str, List[FeatureAnomaly]] = {}
        for anomaly in anomalies:
            family = config.anomaly.feature_families.get(anomaly.feature, "other")
            families.setdefault(family, []).append(anomaly)

        for family, items in families.items():
            if len(items) <= 1:
                continue
            items.sort(key=lambda a: a.score, reverse=True)
            for redundant in items[1:]:
                redundant.suppressed = True
                redundant.suppression_reason = f"suppressed_by_{family}_family"

