"""
Unit tests for log schema.

Tests the Pydantic models and schema definitions.
"""

import pytest
from datetime import datetime, timezone

from src.data.schema import LogEntry, LogLevel, AggregatedLogWindow, FeatureVector


class TestLogLevel:
    """Test LogLevel enum."""
    
    def test_valid_levels(self):
        """Test that all standard levels exist."""
        assert LogLevel.DEBUG == "DEBUG"
        assert LogLevel.INFO == "INFO"
        assert LogLevel.WARNING == "WARNING"
        assert LogLevel.ERROR == "ERROR"
        assert LogLevel.CRITICAL == "CRITICAL"


class TestLogEntry:
    """Test LogEntry model."""
    
    def test_minimal_valid_entry(self):
        """Test creating a minimal valid LogEntry."""
        ts = datetime(2025, 2, 7, 10, 30, 45, tzinfo=timezone.utc)
        
        entry = LogEntry(
            timestamp=ts,
            level=LogLevel.INFO,
            service="api-server",
            message="Request processed"
        )
        
        assert entry.timestamp == ts
        assert entry.level == LogLevel.INFO
        assert entry.service == "api-server"
        assert entry.message == "Request processed"
        assert entry.duration_ms is None
        assert entry.error_code is None
        assert entry.request_id is None
    
    def test_full_entry(self):
        """Test creating a LogEntry with all fields."""
        ts = datetime(2025, 2, 7, 10, 30, 45, tzinfo=timezone.utc)
        
        entry = LogEntry(
            timestamp=ts,
            level=LogLevel.ERROR,
            service="database",
            message="Connection timeout",
            duration_ms=5000,
            error_code="TIMEOUT",
            request_id="req-12345",
            metadata={"retry_count": 3}
        )
        
        assert entry.duration_ms == 5000
        assert entry.error_code == "TIMEOUT"
        assert entry.request_id == "req-12345"
        assert entry.metadata["retry_count"] == 3
    
    def test_invalid_service_empty(self):
        """Test that empty service is rejected."""
        ts = datetime(2025, 2, 7, 10, 30, 45, tzinfo=timezone.utc)
        
        with pytest.raises(ValueError):
            LogEntry(
                timestamp=ts,
                level=LogLevel.INFO,
                service="",
                message="Test"
            )
    
    def test_invalid_message_empty(self):
        """Test that empty message is rejected."""
        ts = datetime(2025, 2, 7, 10, 30, 45, tzinfo=timezone.utc)
        
        with pytest.raises(ValueError):
            LogEntry(
                timestamp=ts,
                level=LogLevel.INFO,
                service="api",
                message=""
            )
    
    def test_negative_duration_rejected(self):
        """Test that negative duration is rejected."""
        ts = datetime(2025, 2, 7, 10, 30, 45, tzinfo=timezone.utc)
        
        with pytest.raises(ValueError):
            LogEntry(
                timestamp=ts,
                level=LogLevel.INFO,
                service="api",
                message="Test",
                duration_ms=-100
            )


class TestAggregatedLogWindow:
    """Test AggregatedLogWindow model."""
    
    def test_empty_window(self):
        """Test creating an empty window."""
        ts_start = datetime(2025, 2, 7, 10, 30, 0, tzinfo=timezone.utc)
        ts_end = datetime(2025, 2, 7, 10, 35, 0, tzinfo=timezone.utc)
        
        window = AggregatedLogWindow(
            window_start=ts_start,
            window_end=ts_end,
            window_size_seconds=300,
            service="api-server",
            logs=[]
        )
        
        assert window.log_count == 0
        assert window.service == "api-server"
        assert window.window_size_seconds == 300
    
    def test_window_with_logs(self):
        """Test window containing logs."""
        ts_start = datetime(2025, 2, 7, 10, 30, 0, tzinfo=timezone.utc)
        ts_end = datetime(2025, 2, 7, 10, 35, 0, tzinfo=timezone.utc)
        
        log1 = LogEntry(
            timestamp=ts_start,
            level=LogLevel.INFO,
            service="api-server",
            message="Request 1"
        )
        log2 = LogEntry(
            timestamp=ts_start + __import__("datetime").timedelta(seconds=30),
            level=LogLevel.ERROR,
            service="api-server",
            message="Request 2"
        )
        
        window = AggregatedLogWindow(
            window_start=ts_start,
            window_end=ts_end,
            window_size_seconds=300,
            service="api-server",
            logs=[log1, log2]
        )
        
        assert window.log_count == 2
        assert len(window.logs) == 2


class TestFeatureVector:
    """Test FeatureVector model."""
    
    def test_minimal_feature_vector(self):
        """Test creating a minimal FeatureVector."""
        ts = datetime(2025, 2, 7, 10, 30, 0, tzinfo=timezone.utc)
        
        fv = FeatureVector(
            window_start=ts,
            service="api-server",
            total_events=100,
            error_count=5,
            warning_count=10,
            info_count=85,
            error_rate=0.05,
            warning_rate=0.10,
            unique_messages=20,
            unique_error_codes=2
        )
        
        assert fv.total_events == 100
        assert fv.error_count == 5
        assert fv.error_rate == 0.05
        assert fv.unique_messages == 20
    
    def test_feature_vector_with_durations(self):
        """Test FeatureVector with duration stats."""
        ts = datetime(2025, 2, 7, 10, 30, 0, tzinfo=timezone.utc)
        
        fv = FeatureVector(
            window_start=ts,
            service="api-server",
            total_events=50,
            error_count=2,
            warning_count=3,
            info_count=45,
            error_rate=0.04,
            warning_rate=0.06,
            median_duration_ms=150.0,
            p95_duration_ms=800.0,
            max_duration_ms=2000.0,
            unique_messages=15,
            unique_error_codes=1
        )
        
        assert fv.median_duration_ms == 150.0
        assert fv.p95_duration_ms == 800.0
        assert fv.max_duration_ms == 2000.0
    
    def test_invalid_error_rate(self):
        """Test that error rate outside [0, 1] is rejected."""
        ts = datetime(2025, 2, 7, 10, 30, 0, tzinfo=timezone.utc)
        
        with pytest.raises(ValueError):
            FeatureVector(
                window_start=ts,
                service="api-server",
                total_events=100,
                error_count=5,
                warning_count=10,
                info_count=85,
                error_rate=1.5,  # Invalid: > 1.0
                warning_rate=0.10,
                unique_messages=20,
                unique_error_codes=2
            )
    
    def test_invalid_negative_count(self):
        """Test that negative counts are rejected."""
        ts = datetime(2025, 2, 7, 10, 30, 0, tzinfo=timezone.utc)
        
        with pytest.raises(ValueError):
            FeatureVector(
                window_start=ts,
                service="api-server",
                total_events=-5,  # Invalid: negative
                error_count=0,
                warning_count=0,
                info_count=0,
                error_rate=0.0,
                warning_rate=0.0,
                unique_messages=0,
                unique_error_codes=0
            )
