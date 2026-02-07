"""
Scoring and severity mapping for anomalies.

Maps deviations to severity levels with configurable thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.core.config import AnomalyThresholds, ScoringConfig

from .schema import AnomalySeverity


@dataclass
class SeverityMapper:
    """
    Maps deviation metrics to severity levels.
    """

    thresholds: AnomalyThresholds

    def zscore_severity(self, zscore: Optional[float]) -> AnomalySeverity:
        if zscore is None:
            return AnomalySeverity.NONE
        z = abs(zscore)
        if z >= self.thresholds.zscore_critical:
            return AnomalySeverity.CRITICAL
        if z >= self.thresholds.zscore_high:
            return AnomalySeverity.HIGH
        if z >= self.thresholds.zscore_medium:
            return AnomalySeverity.MEDIUM
        if z >= self.thresholds.zscore_low:
            return AnomalySeverity.LOW
        return AnomalySeverity.NONE

    def rate_change_severity(self, rate_change: Optional[float]) -> AnomalySeverity:
        if rate_change is None:
            return AnomalySeverity.NONE
        r = abs(rate_change)
        if r >= self.thresholds.rate_change_critical:
            return AnomalySeverity.CRITICAL
        if r >= self.thresholds.rate_change_high:
            return AnomalySeverity.HIGH
        if r >= self.thresholds.rate_change_medium:
            return AnomalySeverity.MEDIUM
        if r >= self.thresholds.rate_change_low:
            return AnomalySeverity.LOW
        return AnomalySeverity.NONE


def combine_scores(
    zscore: Optional[float],
    rate_change: Optional[float],
    thresholds: AnomalyThresholds,
    scoring: ScoringConfig,
) -> float:
    """
    Combine z-score and rate-of-change into a single score in [0, 1].

    Uses weighted normalization against critical thresholds, then clamps.
    """

    z_norm = 0.0
    r_norm = 0.0

    if zscore is not None and thresholds.zscore_critical > 0:
        z_norm = min(abs(zscore) / thresholds.zscore_critical, 1.0)

    if rate_change is not None and thresholds.rate_change_critical > 0:
        r_norm = min(abs(rate_change) / thresholds.rate_change_critical, 1.0)

    score = (scoring.zscore_weight * z_norm) + (scoring.rate_change_weight * r_norm)
    return min(max(score, 0.0), 1.0)


def overall_severity(*severities: AnomalySeverity) -> AnomalySeverity:
    """
    Return the highest severity among inputs.
    """

    order = [
        AnomalySeverity.NONE,
        AnomalySeverity.LOW,
        AnomalySeverity.MEDIUM,
        AnomalySeverity.HIGH,
        AnomalySeverity.CRITICAL,
    ]
    highest_index = max(order.index(s) for s in severities)
    return order[highest_index]

