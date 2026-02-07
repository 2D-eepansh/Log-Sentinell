"""
Anomaly module: Statistical anomaly detection for Phase 2.

Implements deterministic baselines, detectors, scoring, and anomaly events.
"""

from .baselines import BaselinePair, EWMABaselineEstimator, RollingStatsEstimator
from .detectors import RateOfChangeDetector, ZScoreDetector
from .engine import AnomalyEngine
from .schema import AnomalyEvent, AnomalySeverity, BaselineStats, FeatureAnomaly
from .scoring import SeverityMapper, combine_scores, overall_severity

__all__ = [
	"AnomalyEngine",
	"AnomalyEvent",
	"AnomalySeverity",
	"BaselineStats",
	"FeatureAnomaly",
	"BaselinePair",
	"RollingStatsEstimator",
	"EWMABaselineEstimator",
	"ZScoreDetector",
	"RateOfChangeDetector",
	"SeverityMapper",
	"combine_scores",
	"overall_severity",
]
