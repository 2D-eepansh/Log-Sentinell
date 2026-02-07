"""
Detectors for statistical deviations.

Implements explainable methods:
- Z-score detection
- Rate-of-change detection
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .schema import BaselineStats


@dataclass
class ZScoreDetector:
    """
    Z-score detector with conservative defaults.

    If baseline std is too small, detection is suppressed to avoid noisy alerts.
    """

    min_std: float

    def compute(self, observed: float, baseline: BaselineStats) -> Optional[float]:
        if baseline.std < self.min_std:
            return None
        return (observed - baseline.mean) / baseline.std


@dataclass
class RateOfChangeDetector:
    """
    Relative rate-of-change detector.

    Computes |delta| / max(|prev|, epsilon) to avoid division by zero.
    """

    epsilon: float = 1e-6

    def compute(self, observed: float, previous: Optional[float]) -> Optional[float]:
        if previous is None:
            return None
        delta = observed - previous
        denom = max(abs(previous), self.epsilon)
        return abs(delta) / denom

