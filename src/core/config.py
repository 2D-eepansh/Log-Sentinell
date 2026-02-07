"""
Application configuration for the Anomaly Detection Copilot.

Provides environment-aware settings with conservative defaults. All anomaly
thresholds are configurable to avoid hard-coded "magic numbers".
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AnomalyThresholds(BaseModel):
	"""
	Thresholds for statistical detectors.

	Rationale:
	- Z-score thresholds are conservative to reduce false positives in bursty logs.
	- Rate-of-change thresholds guard against sudden spikes, which can be noisy.
	"""

	zscore_low: float = Field(2.5, ge=0.0, description="Lower bound for z-score alerts")
	zscore_medium: float = Field(3.5, ge=0.0, description="Medium severity z-score")
	zscore_high: float = Field(5.0, ge=0.0, description="High severity z-score")
	zscore_critical: float = Field(7.0, ge=0.0, description="Critical severity z-score")

	rate_change_low: float = Field(
		0.75, ge=0.0, description="Low severity relative change (e.g., 75% increase)"
	)
	rate_change_medium: float = Field(
		1.25, ge=0.0, description="Medium severity relative change (125% increase)"
	)
	rate_change_high: float = Field(
		2.0, ge=0.0, description="High severity relative change (200% increase)"
	)
	rate_change_critical: float = Field(
		3.0, ge=0.0, description="Critical severity relative change (300% increase)"
	)


class BaselineConfig(BaseModel):
	"""
	Configuration for baseline estimation.

	Notes:
	- window_size: number of recent points for rolling stats.
	- min_points: warm-up points before detection begins.
	- std_floor: lower bound for std to avoid division by tiny values.
	- ewma_alpha: decay factor for EWMA (higher means more reactive).
	"""

	window_size: int = Field(20, ge=3)
	min_points: int = Field(10, ge=3)
	std_floor: float = Field(1e-6, gt=0.0)
	ewma_alpha: float = Field(0.2, gt=0.0, lt=1.0)
	strategy: str = Field(
		"hybrid",
		description="Baseline strategy: 'rolling', 'ewma', or 'hybrid'",
	)


class ScoringConfig(BaseModel):
	"""
	Scoring configuration.

	Notes:
	- zscore_weight and rate_change_weight control relative influence.
	- score_floor keeps minor deviations from producing alerts.
	"""

	zscore_weight: float = Field(0.7, ge=0.0, le=1.0)
	rate_change_weight: float = Field(0.3, ge=0.0, le=1.0)
	score_floor: float = Field(0.2, ge=0.0, le=1.0)


class AnomalyConfig(BaseModel):
	"""
	Phase 2 anomaly detection configuration.
	"""

	thresholds: AnomalyThresholds = AnomalyThresholds()
	baselines: BaselineConfig = BaselineConfig()
	scoring: ScoringConfig = ScoringConfig()
	suppress_redundant: bool = True

	feature_families: Dict[str, str] = Field(
		default_factory=lambda: {
			"total_events": "count",
			"error_count": "count",
			"warning_count": "count",
			"info_count": "count",
			"error_rate": "rate",
			"warning_rate": "rate",
			"median_duration_ms": "duration",
			"p95_duration_ms": "duration",
			"max_duration_ms": "duration",
			"unique_messages": "diversity",
			"unique_error_codes": "diversity",
		}
	)


class Config(BaseSettings):
	"""
	Global configuration with environment overrides.
	"""

	model_config = SettingsConfigDict(env_prefix="DERIV_", env_file=".env", extra="ignore")

	log_level: str = Field("INFO", description="Default logging level")
	logs_dir: Path = Field(Path("logs"), description="Directory for log files")
	anomaly: AnomalyConfig = AnomalyConfig()

	def model_post_init(self, __context: object) -> None:
		self.logs_dir.mkdir(parents=True, exist_ok=True)


config = Config()

