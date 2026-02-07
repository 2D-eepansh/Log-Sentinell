"""
Feature extraction from aggregated log windows.

Converts AggregatedLogWindow objects into FeatureVector objects suitable
for anomaly detection. Features are deterministic and designed to capture
interesting patterns in log data.

Design:
- All features are statistical (counts, rates, percentiles)
- No ML preprocessing or scaling here
- Features are computed independently per window
- Easy to add new features without breaking downstream
"""

import logging
import statistics
from typing import Dict, List, Optional

from src.data.schema import AggregatedLogWindow, FeatureVector, LogLevel

logger = logging.getLogger(__name__)


class FeatureExtractionError(Exception):
    """Raised when feature extraction fails."""
    pass


def extract_count_features(window: AggregatedLogWindow) -> Dict[str, int]:
    """
    Extract count-based features from logs.
    
    Args:
        window: AggregatedLogWindow to process
    
    Returns:
        Dict with keys: total_events, error_count, warning_count, info_count
    """
    total = len(window.logs)
    
    error_count = sum(
        1 for log in window.logs
        if log.level in [LogLevel.ERROR, LogLevel.CRITICAL]
    )
    
    warning_count = sum(
        1 for log in window.logs
        if log.level == LogLevel.WARNING
    )
    
    info_count = sum(
        1 for log in window.logs
        if log.level == LogLevel.INFO
    )
    
    return {
        "total_events": total,
        "error_count": error_count,
        "warning_count": warning_count,
        "info_count": info_count,
    }


def extract_rate_features(window: AggregatedLogWindow) -> Dict[str, float]:
    """
    Extract rate-based features (fractions).
    
    Args:
        window: AggregatedLogWindow to process
    
    Returns:
        Dict with keys: error_rate, warning_rate
    
    Notes:
        - Rates are in [0.0, 1.0]
        - If total_events is 0, rates are 0.0
    """
    total = len(window.logs)
    
    if total == 0:
        return {
            "error_rate": 0.0,
            "warning_rate": 0.0,
        }
    
    error_count = sum(
        1 for log in window.logs
        if log.level in [LogLevel.ERROR, LogLevel.CRITICAL]
    )
    
    warning_count = sum(
        1 for log in window.logs
        if log.level == LogLevel.WARNING
    )
    
    return {
        "error_rate": error_count / total,
        "warning_rate": warning_count / total,
    }


def extract_duration_features(window: AggregatedLogWindow) -> Dict[str, Optional[float]]:
    """
    Extract duration-based features (latency statistics).
    
    Args:
        window: AggregatedLogWindow to process
    
    Returns:
        Dict with keys: median_duration_ms, p95_duration_ms, max_duration_ms
    
    Notes:
        - Only logs with duration_ms are considered
        - If no durations, all values are None
        - Statistics are computed from raw durations (no normalization)
    """
    durations = [
        log.duration_ms for log in window.logs
        if log.duration_ms is not None
    ]
    
    if not durations:
        return {
            "median_duration_ms": None,
            "p95_duration_ms": None,
            "max_duration_ms": None,
        }
    
    # Sort for percentile calculation
    sorted_durations = sorted(durations)
    
    # Median
    median = statistics.median(sorted_durations)
    
    # 95th percentile
    p95_index = int(0.95 * len(sorted_durations))
    p95 = sorted_durations[min(p95_index, len(sorted_durations) - 1)]
    
    # Max
    max_duration = max(sorted_durations)
    
    return {
        "median_duration_ms": median,
        "p95_duration_ms": p95,
        "max_duration_ms": max_duration,
    }


def extract_diversity_features(window: AggregatedLogWindow) -> Dict[str, int]:
    """
    Extract diversity-based features (uniqueness).
    
    Args:
        window: AggregatedLogWindow to process
    
    Returns:
        Dict with keys: unique_messages, unique_error_codes
    
    Notes:
        - Uses message_hash from metadata for deduplication
        - Error codes are checked even if None
    """
    # Count unique messages (by hash)
    message_hashes = set()
    for log in window.logs:
        msg_hash = log.metadata.get("message_hash")
        if msg_hash:
            message_hashes.add(msg_hash)
    
    unique_messages = len(message_hashes)
    
    # Count unique error codes
    error_codes = set()
    for log in window.logs:
        if log.error_code:
            error_codes.add(log.error_code)
    
    unique_error_codes = len(error_codes)
    
    return {
        "unique_messages": unique_messages,
        "unique_error_codes": unique_error_codes,
    }


def extract_features(window: AggregatedLogWindow) -> FeatureVector:
    """
    Extract all features from an aggregated log window.
    
    Combines count, rate, duration, and diversity features into a
    single FeatureVector for anomaly detection.
    
    Args:
        window: AggregatedLogWindow to process
    
    Returns:
        FeatureVector with all computed features
    
    Raises:
        FeatureExtractionError: If feature computation fails
    """
    try:
        # Extract all feature groups
        count_feats = extract_count_features(window)
        rate_feats = extract_rate_features(window)
        duration_feats = extract_duration_features(window)
        diversity_feats = extract_diversity_features(window)
        
        # Combine into metadata for debugging
        metadata = {
            "window_log_count": len(window.logs),
            "extraction_timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        }
        
        # Create FeatureVector
        return FeatureVector(
            window_start=window.window_start,
            service=window.service,
            total_events=count_feats["total_events"],
            error_count=count_feats["error_count"],
            warning_count=count_feats["warning_count"],
            info_count=count_feats["info_count"],
            error_rate=rate_feats["error_rate"],
            warning_rate=rate_feats["warning_rate"],
            median_duration_ms=duration_feats["median_duration_ms"],
            p95_duration_ms=duration_feats["p95_duration_ms"],
            max_duration_ms=duration_feats["max_duration_ms"],
            unique_messages=diversity_feats["unique_messages"],
            unique_error_codes=diversity_feats["unique_error_codes"],
            metadata=metadata,
        )
    
    except Exception as e:
        raise FeatureExtractionError(
            f"Failed to extract features for service {window.service}: {e}"
        ) from e


def extract_features_from_windows(
    windows: List[AggregatedLogWindow]
) -> tuple[List[FeatureVector], int]:
    """
    Extract features from multiple windows.
    
    Args:
        windows: List of AggregatedLogWindow objects
    
    Returns:
        Tuple of (feature_vectors, skipped_count)
    
    Notes:
        - Windows that fail feature extraction are skipped (logged)
        - Useful for batch processing large log datasets
    """
    features = []
    skipped = 0
    
    for window in windows:
        try:
            feature_vector = extract_features(window)
            features.append(feature_vector)
        except FeatureExtractionError as e:
            logger.warning(f"Skipped window due to extraction error: {e}")
            skipped += 1
        except Exception as e:
            logger.warning(f"Unexpected error extracting features: {e}")
            skipped += 1
    
    return features, skipped


class FeatureTransformer:
    """
    Helper for computing aggregate statistics across multiple features.
    
    Useful for understanding feature distributions and detecting
    abnormal patterns (e.g., "error rate is 3x higher than usual").
    """
    
    def __init__(self, features: List[FeatureVector]):
        """
        Initialize transformer with feature vectors.
        
        Args:
            features: List of FeatureVector objects (typically for one service)
        """
        self.features = features
    
    def get_statistics(self, feature_name: str) -> Dict[str, float]:
        """
        Compute statistics for a specific feature.
        
        Args:
            feature_name: Feature to analyze (e.g., "error_rate")
        
        Returns:
            Dict with keys: min, max, mean, median, stdev
        
        Raises:
            ValueError: If feature not found or no data
        """
        values = []
        
        for fv in self.features:
            value = getattr(fv, feature_name, None)
            if value is not None:
                values.append(float(value))
        
        if not values:
            raise ValueError(f"No data for feature: {feature_name}")
        
        sorted_vals = sorted(values)
        
        return {
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / len(values),
            "median": statistics.median(sorted_vals),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
        }
    
    def compare_to_baseline(
        self,
        feature_name: str,
        baseline_stats: Dict[str, float],
        multiplier: float = 2.0
    ) -> List[int]:
        """
        Find feature vectors that deviate significantly from baseline.
        
        Identifies vectors where feature value is > multiplier * baseline_mean.
        
        Args:
            feature_name: Feature to check
            baseline_stats: Stats dict (from get_statistics)
            multiplier: Threshold multiplier (default 2x)
        
        Returns:
            List of indices in self.features that are anomalous
        """
        baseline_mean = baseline_stats["mean"]
        threshold = baseline_mean * multiplier
        
        anomalies = []
        for idx, fv in enumerate(self.features):
            value = getattr(fv, feature_name, None)
            if value is not None and value > threshold:
                anomalies.append(idx)
        
        return anomalies
