"""
Unit tests for anomaly detectors.
"""

from src.anomaly.detectors import RateOfChangeDetector, ZScoreDetector
from src.anomaly.schema import BaselineStats


def test_zscore_detector_computes_value():
    detector = ZScoreDetector(min_std=1e-6)
    baseline = BaselineStats(mean=10.0, std=2.0, count=10, method="rolling")

    z = detector.compute(14.0, baseline)
    assert z is not None
    assert abs(z - 2.0) < 1e-6


def test_zscore_detector_suppresses_small_std():
    detector = ZScoreDetector(min_std=1.0)
    baseline = BaselineStats(mean=10.0, std=0.5, count=10, method="rolling")

    z = detector.compute(12.0, baseline)
    assert z is None


def test_rate_of_change_detector():
    detector = RateOfChangeDetector()
    roc = detector.compute(observed=20.0, previous=10.0)
    assert roc is not None
    assert abs(roc - 1.0) < 1e-6

    assert detector.compute(observed=10.0, previous=None) is None

