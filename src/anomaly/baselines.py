"""
Baseline estimation utilities for Phase 2.

Provides rolling statistics and EWMA baselines. Both are deterministic and
conservative by default to reduce false positives in bursty log data.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import sqrt
from typing import Deque, Optional

from .schema import BaselineStats


@dataclass
class RollingStatsEstimator:
    """
    Rolling mean/std estimator.

    Warm-up: returns None until min_points are collected.
    """

    window_size: int
    min_points: int
    std_floor: float
    _values: Deque[float] = None

    def __post_init__(self) -> None:
        self._values = deque(maxlen=self.window_size)

    def peek(self) -> Optional[BaselineStats]:
        if len(self._values) < self.min_points:
            return None
        values = list(self._values)
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = max(sqrt(variance), self.std_floor)
        return BaselineStats(mean=mean, std=std, count=len(values), method="rolling")

    def update(self, value: float) -> None:
        self._values.append(float(value))

    @property
    def last_value(self) -> Optional[float]:
        return self._values[-1] if self._values else None


@dataclass
class EWMABaselineEstimator:
    """
    Exponentially Weighted Moving Average (EWMA) estimator.

    Uses EWMA mean and variance for smooth baselines. Warm-up requires min_points.
    """

    alpha: float
    min_points: int
    std_floor: float
    _count: int = 0
    _mean: Optional[float] = None
    _var: Optional[float] = None
    _last: Optional[float] = None

    def peek(self) -> Optional[BaselineStats]:
        if self._count < self.min_points or self._mean is None or self._var is None:
            return None
        std = max(sqrt(self._var), self.std_floor)
        return BaselineStats(mean=self._mean, std=std, count=self._count, method="ewma")

    def update(self, value: float) -> None:
        value = float(value)
        if self._mean is None:
            self._mean = value
            self._var = 0.0
        else:
            # EWMA update for mean
            self._mean = self.alpha * value + (1.0 - self.alpha) * self._mean
            # EWMA update for variance (using updated mean)
            delta = value - self._mean
            self._var = self.alpha * (delta**2) + (1.0 - self.alpha) * self._var
        self._last = value
        self._count += 1

    @property
    def last_value(self) -> Optional[float]:
        return self._last


@dataclass
class BaselinePair:
    """
    Holds both rolling and EWMA baselines for a feature.
    """

    rolling: RollingStatsEstimator
    ewma: EWMABaselineEstimator

    def peek(self, strategy: str) -> Optional[BaselineStats]:
        rolling_stats = self.rolling.peek()
        ewma_stats = self.ewma.peek()

        if strategy == "rolling":
            return rolling_stats
        if strategy == "ewma":
            return ewma_stats
        if strategy == "hybrid":
            if rolling_stats and ewma_stats:
                mean = rolling_stats.mean
                std = max(rolling_stats.std, ewma_stats.std)
                count = min(rolling_stats.count, ewma_stats.count)
                return BaselineStats(mean=mean, std=std, count=count, method="hybrid")
            return rolling_stats or ewma_stats
        raise ValueError(f"Unknown baseline strategy: {strategy}")

    def update(self, value: float) -> None:
        self.rolling.update(value)
        self.ewma.update(value)

    @property
    def last_value(self) -> Optional[float]:
        return self.rolling.last_value or self.ewma.last_value

