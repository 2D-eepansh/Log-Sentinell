"""
Unit tests for feature extraction.

Tests conversion of aggregated windows into feature vectors for anomaly detection.
"""

import pytest
from datetime import datetime, timezone, timedelta

from src.data.schema import LogEntry, LogLevel, AggregatedLogWindow, FeatureVector
from src.data.features import (
    extract_count_features,
    extract_rate_features,
    extract_duration_features,
    extract_diversity_features,
    extract_features,
    extract_features_from_windows,
    FeatureTransformer,
)


class TestCountFeatures:
    """Test count-based feature extraction."""
    
    def test_count_features_all_info(self):
        """Test counting when all logs are INFO level."""
        ts_base = datetime(2025, 2, 7, 10, 30, 0, tzinfo=timezone.utc)
        logs = [
            LogEntry(timestamp=ts_base, level=LogLevel.INFO, service="api", message=f"Msg {i}")
            for i in range(10)
        ]
        window = AggregatedLogWindow(
            window_start=ts_base,
            window_end=ts_base + timedelta(minutes=5),
            window_size_seconds=300,
            service="api",
            logs=logs
        )
        
        features = extract_count_features(window)
        
        assert features["total_events"] == 10
        assert features["error_count"] == 0
        assert features["warning_count"] == 0
        assert features["info_count"] == 10
    
    def test_count_features_mixed_levels(self):
        """Test counting with mixed log levels."""
        ts_base = datetime(2025, 2, 7, 10, 30, 0, tzinfo=timezone.utc)
        logs = [
            LogEntry(timestamp=ts_base, level=LogLevel.INFO, service="api", message="Info 1"),
            LogEntry(timestamp=ts_base, level=LogLevel.INFO, service="api", message="Info 2"),
            LogEntry(timestamp=ts_base, level=LogLevel.WARNING, service="api", message="Warn 1"),
            LogEntry(timestamp=ts_base, level=LogLevel.ERROR, service="api", message="Error 1"),
            LogEntry(timestamp=ts_base, level=LogLevel.CRITICAL, service="api", message="Crit 1"),
        ]
        window = AggregatedLogWindow(
            window_start=ts_base,
            window_end=ts_base + timedelta(minutes=5),
            window_size_seconds=300,
            service="api",
            logs=logs
        )
        
        features = extract_count_features(window)
        
        assert features["total_events"] == 5
        assert features["info_count"] == 2
        assert features["warning_count"] == 1
        assert features["error_count"] == 2  # ERROR + CRITICAL


class TestRateFeatures:
    """Test rate-based feature extraction."""
    
    def test_rate_features_no_errors(self):
        """Test rates when no errors occur."""
        ts_base = datetime(2025, 2, 7, 10, 30, 0, tzinfo=timezone.utc)
        logs = [
            LogEntry(timestamp=ts_base, level=LogLevel.INFO, service="api", message=f"Msg {i}")
            for i in range(100)
        ]
        window = AggregatedLogWindow(
            window_start=ts_base,
            window_end=ts_base + timedelta(minutes=5),
            window_size_seconds=300,
            service="api",
            logs=logs
        )
        
        features = extract_rate_features(window)
        
        assert features["error_rate"] == 0.0
        assert features["warning_rate"] == 0.0
    
    def test_rate_features_with_errors(self):
        """Test rates with errors present."""
        ts_base = datetime(2025, 2, 7, 10, 30, 0, tzinfo=timezone.utc)
        logs = []
        
        # 80 info logs
        for i in range(80):
            logs.append(
                LogEntry(timestamp=ts_base, level=LogLevel.INFO, service="api", message=f"Info {i}")
            )
        
        # 10 warning logs
        for i in range(10):
            logs.append(
                LogEntry(timestamp=ts_base, level=LogLevel.WARNING, service="api", message=f"Warn {i}")
            )
        
        # 10 error logs
        for i in range(10):
            logs.append(
                LogEntry(timestamp=ts_base, level=LogLevel.ERROR, service="api", message=f"Error {i}")
            )
        
        window = AggregatedLogWindow(
            window_start=ts_base,
            window_end=ts_base + timedelta(minutes=5),
            window_size_seconds=300,
            service="api",
            logs=logs
        )
        
        features = extract_rate_features(window)
        
        assert features["error_rate"] == pytest.approx(0.1)
        assert features["warning_rate"] == pytest.approx(0.1)
    
    def test_rate_features_empty_window(self):
        """Test rates for empty window."""
        ts_base = datetime(2025, 2, 7, 10, 30, 0, tzinfo=timezone.utc)
        window = AggregatedLogWindow(
            window_start=ts_base,
            window_end=ts_base + timedelta(minutes=5),
            window_size_seconds=300,
            service="api",
            logs=[]
        )
        
        features = extract_rate_features(window)
        
        assert features["error_rate"] == 0.0
        assert features["warning_rate"] == 0.0


class TestDurationFeatures:
    """Test duration-based feature extraction."""
    
    def test_duration_features_with_data(self):
        """Test duration statistics."""
        ts_base = datetime(2025, 2, 7, 10, 30, 0, tzinfo=timezone.utc)
        logs = [
            LogEntry(timestamp=ts_base, level=LogLevel.INFO, service="api", message="Msg 1", duration_ms=100),
            LogEntry(timestamp=ts_base, level=LogLevel.INFO, service="api", message="Msg 2", duration_ms=200),
            LogEntry(timestamp=ts_base, level=LogLevel.INFO, service="api", message="Msg 3", duration_ms=500),
            LogEntry(timestamp=ts_base, level=LogLevel.INFO, service="api", message="Msg 4", duration_ms=800),
        ]
        window = AggregatedLogWindow(
            window_start=ts_base,
            window_end=ts_base + timedelta(minutes=5),
            window_size_seconds=300,
            service="api",
            logs=logs
        )
        
        features = extract_duration_features(window)
        
        assert features["median_duration_ms"] == 350.0  # (200 + 500) / 2
        assert features["max_duration_ms"] == 800
        assert features["p95_duration_ms"] is not None
    
    def test_duration_features_no_data(self):
        """Test duration features when no durations exist."""
        ts_base = datetime(2025, 2, 7, 10, 30, 0, tzinfo=timezone.utc)
        logs = [
            LogEntry(timestamp=ts_base, level=LogLevel.INFO, service="api", message="Msg 1"),
            LogEntry(timestamp=ts_base, level=LogLevel.INFO, service="api", message="Msg 2"),
        ]
        window = AggregatedLogWindow(
            window_start=ts_base,
            window_end=ts_base + timedelta(minutes=5),
            window_size_seconds=300,
            service="api",
            logs=logs
        )
        
        features = extract_duration_features(window)
        
        assert features["median_duration_ms"] is None
        assert features["max_duration_ms"] is None
        assert features["p95_duration_ms"] is None


class TestDiversityFeatures:
    """Test diversity-based feature extraction."""
    
    def test_diversity_features_unique_messages(self):
        """Test counting unique messages."""
        ts_base = datetime(2025, 2, 7, 10, 30, 0, tzinfo=timezone.utc)
        logs = [
            LogEntry(
                timestamp=ts_base,
                level=LogLevel.INFO,
                service="api",
                message="Unique msg 1",
                metadata={"message_hash": "hash1"}
            ),
            LogEntry(
                timestamp=ts_base,
                level=LogLevel.INFO,
                service="api",
                message="Unique msg 2",
                metadata={"message_hash": "hash2"}
            ),
            LogEntry(
                timestamp=ts_base,
                level=LogLevel.INFO,
                service="api",
                message="Duplicate",
                metadata={"message_hash": "hash1"}
            ),
        ]
        window = AggregatedLogWindow(
            window_start=ts_base,
            window_end=ts_base + timedelta(minutes=5),
            window_size_seconds=300,
            service="api",
            logs=logs
        )
        
        features = extract_diversity_features(window)
        
        assert features["unique_messages"] == 2  # hash1 and hash2
    
    def test_diversity_features_unique_error_codes(self):
        """Test counting unique error codes."""
        ts_base = datetime(2025, 2, 7, 10, 30, 0, tzinfo=timezone.utc)
        logs = [
            LogEntry(timestamp=ts_base, level=LogLevel.ERROR, service="api", message="Error 1", error_code="E001"),
            LogEntry(timestamp=ts_base, level=LogLevel.ERROR, service="api", message="Error 2", error_code="E001"),
            LogEntry(timestamp=ts_base, level=LogLevel.ERROR, service="api", message="Error 3", error_code="E002"),
        ]
        window = AggregatedLogWindow(
            window_start=ts_base,
            window_end=ts_base + timedelta(minutes=5),
            window_size_seconds=300,
            service="api",
            logs=logs
        )
        
        features = extract_diversity_features(window)
        
        assert features["unique_error_codes"] == 2  # E001 and E002


class TestExtractFeatures:
    """Test full feature extraction."""
    
    def test_extract_features_complete(self):
        """Test extracting all features from a window."""
        ts_base = datetime(2025, 2, 7, 10, 30, 0, tzinfo=timezone.utc)
        logs = [
            LogEntry(
                timestamp=ts_base,
                level=LogLevel.INFO,
                service="api",
                message="Success",
                duration_ms=100
            ),
            LogEntry(
                timestamp=ts_base,
                level=LogLevel.ERROR,
                service="api",
                message="Error",
                error_code="E001"
            ),
        ]
        window = AggregatedLogWindow(
            window_start=ts_base,
            window_end=ts_base + timedelta(minutes=5),
            window_size_seconds=300,
            service="api",
            logs=logs
        )
        
        fv = extract_features(window)
        
        assert isinstance(fv, FeatureVector)
        assert fv.total_events == 2
        assert fv.error_count == 1
        assert fv.service == "api"


class TestFeatureTransformer:
    """Test feature analysis utilities."""
    
    def setup_method(self):
        """Create sample feature vectors."""
        ts_base = datetime(2025, 2, 7, 10, 30, 0, tzinfo=timezone.utc)
        self.features = [
            FeatureVector(
                window_start=ts_base,
                service="api",
                total_events=100,
                error_count=5,
                warning_count=10,
                info_count=85,
                error_rate=0.05,
                warning_rate=0.10,
                unique_messages=20,
                unique_error_codes=1
            ),
            FeatureVector(
                window_start=ts_base + timedelta(minutes=5),
                service="api",
                total_events=100,
                error_count=20,  # Much higher
                warning_count=10,
                info_count=70,
                error_rate=0.20,
                warning_rate=0.10,
                unique_messages=25,
                unique_error_codes=3
            ),
        ]
    
    def test_feature_transformer_get_statistics(self):
        """Test computing statistics for a feature."""
        transformer = FeatureTransformer(self.features)
        stats = transformer.get_statistics("error_rate")
        
        assert "min" in stats
        assert "max" in stats
        assert "mean" in stats
        assert stats["min"] == 0.05
        assert stats["max"] == 0.20
    
    def test_feature_transformer_compare_to_baseline(self):
        """Test detecting anomalies vs baseline."""
        transformer = FeatureTransformer(self.features)
        baseline = transformer.get_statistics("error_rate")
        
        # Find vectors with error_rate > 2x baseline mean
        anomalies = transformer.compare_to_baseline("error_rate", baseline, multiplier=1.5)
        
        # Should detect the second vector (0.20) as anomalous
        assert len(anomalies) > 0
