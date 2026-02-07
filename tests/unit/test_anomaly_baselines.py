"""
Unit tests for baseline estimators.
"""

from math import isclose

from src.anomaly.baselines import EWMABaselineEstimator, RollingStatsEstimator


def test_rolling_stats_warmup_and_values():
    estimator = RollingStatsEstimator(window_size=4, min_points=3, std_floor=1e-6)

    estimator.update(1.0)
    estimator.update(2.0)
    assert estimator.peek() is None  # warm-up

    estimator.update(3.0)
    stats = estimator.peek()
    assert stats is not None
    assert isclose(stats.mean, 2.0, rel_tol=1e-6)

    estimator.update(4.0)
    stats = estimator.peek()
    assert stats is not None
    assert isclose(stats.mean, 2.5, rel_tol=1e-6)
    assert stats.std > 0.0


def test_ewma_stats_warmup_and_monotonic_mean():
    estimator = EWMABaselineEstimator(alpha=0.5, min_points=3, std_floor=1e-6)

    estimator.update(10.0)
    estimator.update(20.0)
    assert estimator.peek() is None

    estimator.update(30.0)
    stats = estimator.peek()
    assert stats is not None
    assert stats.mean >= 10.0
    assert stats.mean <= 30.0
    assert stats.std >= 0.0

