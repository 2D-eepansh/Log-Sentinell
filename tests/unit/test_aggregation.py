"""
Unit tests for log aggregation.

Tests time-window grouping of normalized logs.
"""

import pytest
from datetime import datetime, timezone, timedelta

from src.data.schema import LogEntry, LogLevel, AggregatedLogWindow
from src.data.aggregation import (
    align_timestamp_to_window,
    aggregate_logs,
    get_services_in_windows,
    get_time_range,
    filter_windows_by_service,
    filter_windows_by_time,
)


class TestAlignTimestampToWindow:
    """Test timestamp alignment to window boundaries."""
    
    def test_align_to_5min_window_middle(self):
        """Test alignment when timestamp is in middle of window."""
        ts = datetime(2025, 2, 7, 10, 32, 30, tzinfo=timezone.utc)
        
        result = align_timestamp_to_window(ts, 300)  # 5 min window
        
        # Should align down to 10:30:00
        assert result.hour == 10
        assert result.minute == 30
        assert result.second == 0
    
    def test_align_to_5min_window_boundary(self):
        """Test alignment when timestamp is already aligned."""
        ts = datetime(2025, 2, 7, 10, 30, 0, tzinfo=timezone.utc)
        
        result = align_timestamp_to_window(ts, 300)
        
        assert result == ts
    
    def test_align_to_1min_window(self):
        """Test alignment with 1-minute window."""
        ts = datetime(2025, 2, 7, 10, 30, 45, tzinfo=timezone.utc)
        
        result = align_timestamp_to_window(ts, 60)
        
        # Should align down to 10:30:00
        assert result.second == 0
        assert result.minute == 30
    
    def test_align_to_hourly_window(self):
        """Test alignment with hourly window."""
        ts = datetime(2025, 2, 7, 10, 45, 30, tzinfo=timezone.utc)
        
        result = align_timestamp_to_window(ts, 3600)
        
        # Should align down to 10:00:00
        assert result.hour == 10
        assert result.minute == 0
        assert result.second == 0


class TestAgregateLogs:
    """Test log aggregation into time windows."""
    
    def test_aggregate_single_service_single_window(self):
        """Test aggregating logs from single service into one window."""
        ts_base = datetime(2025, 2, 7, 10, 30, 0, tzinfo=timezone.utc)
        
        logs = [
            LogEntry(
                timestamp=ts_base,
                level=LogLevel.INFO,
                service="api-server",
                message="Request 1"
            ),
            LogEntry(
                timestamp=ts_base + timedelta(seconds=30),
                level=LogLevel.INFO,
                service="api-server",
                message="Request 2"
            ),
        ]
        
        windows = aggregate_logs(logs, window_size_seconds=300)
        
        assert len(windows) == 1
        window = list(windows.values())[0]
        assert window.service == "api-server"
        assert window.log_count == 2
    
    def test_aggregate_multiple_services(self):
        """Test aggregating logs from multiple services."""
        ts_base = datetime(2025, 2, 7, 10, 30, 0, tzinfo=timezone.utc)
        
        logs = [
            LogEntry(
                timestamp=ts_base,
                level=LogLevel.INFO,
                service="api-server",
                message="API request"
            ),
            LogEntry(
                timestamp=ts_base,
                level=LogLevel.INFO,
                service="database",
                message="DB query"
            ),
        ]
        
        windows = aggregate_logs(logs, window_size_seconds=300)
        
        assert len(windows) == 2
        services = {w.service for w in windows.values()}
        assert services == {"api-server", "database"}
    
    def test_aggregate_multiple_windows(self):
        """Test aggregating logs across multiple time windows."""
        ts_base = datetime(2025, 2, 7, 10, 30, 0, tzinfo=timezone.utc)
        
        logs = [
            LogEntry(
                timestamp=ts_base,
                level=LogLevel.INFO,
                service="api-server",
                message="Request 1"
            ),
            LogEntry(
                timestamp=ts_base + timedelta(minutes=10),  # 10 minutes later
                level=LogLevel.INFO,
                service="api-server",
                message="Request 2"
            ),
        ]
        
        windows = aggregate_logs(logs, window_size_seconds=300)  # 5 min windows
        
        assert len(windows) == 2  # Two windows (10:30-10:35, 10:40-10:45)
    
    def test_aggregate_invalid_window_size(self):
        """Test that invalid window size raises error."""
        logs = []
        
        with pytest.raises(Exception):  # AggregationError
            aggregate_logs(logs, window_size_seconds=0)
    
    def test_aggregate_preserves_log_order(self):
        """Test that logs within window are sorted chronologically."""
        ts_base = datetime(2025, 2, 7, 10, 30, 0, tzinfo=timezone.utc)
        
        logs = [
            LogEntry(
                timestamp=ts_base + timedelta(seconds=200),
                level=LogLevel.INFO,
                service="api",
                message="Request 3"
            ),
            LogEntry(
                timestamp=ts_base + timedelta(seconds=100),
                level=LogLevel.INFO,
                service="api",
                message="Request 2"
            ),
            LogEntry(
                timestamp=ts_base,
                level=LogLevel.INFO,
                service="api",
                message="Request 1"
            ),
        ]
        
        windows = aggregate_logs(logs, window_size_seconds=300)
        window = list(windows.values())[0]
        
        # Logs should be sorted chronologically
        assert window.logs[0].message == "Request 1"
        assert window.logs[1].message == "Request 2"
        assert window.logs[2].message == "Request 3"


class TestWindowFiltering:
    """Test filtering of aggregated windows."""
    
    def setup_method(self):
        """Create test windows."""
        ts_base = datetime(2025, 2, 7, 10, 30, 0, tzinfo=timezone.utc)
        
        log1 = LogEntry(
            timestamp=ts_base,
            level=LogLevel.INFO,
            service="api-server",
            message="API request"
        )
        log2 = LogEntry(
            timestamp=ts_base + timedelta(minutes=10),
            level=LogLevel.INFO,
            service="database",
            message="DB query"
        )
        
        self.windows = aggregate_logs([log1, log2], window_size_seconds=300)
    
    def test_filter_by_service(self):
        """Test filtering windows by service."""
        filtered = filter_windows_by_service(self.windows, "api-server")
        
        assert len(filtered) == 1
        window = list(filtered.values())[0]
        assert window.service == "api-server"
    
    def test_filter_by_service_empty(self):
        """Test filtering for non-existent service."""
        filtered = filter_windows_by_service(self.windows, "nonexistent")
        
        assert len(filtered) == 0
    
    def test_filter_by_time(self):
        """Test filtering windows by time range."""
        ts_start = datetime(2025, 2, 7, 10, 30, 0, tzinfo=timezone.utc)
        ts_end = datetime(2025, 2, 7, 10, 35, 0, tzinfo=timezone.utc)
        
        filtered = filter_windows_by_time(self.windows, ts_start, ts_end)
        
        # Should get the first window (10:30-10:35)
        assert len(filtered) == 1


class TestWindowAnalytics:
    """Test utilities for window analysis."""
    
    def setup_method(self):
        """Create test windows."""
        ts_base = datetime(2025, 2, 7, 10, 30, 0, tzinfo=timezone.utc)
        
        logs = [
            LogEntry(
                timestamp=ts_base,
                level=LogLevel.INFO,
                service="api-server",
                message="Request 1"
            ),
            LogEntry(
                timestamp=ts_base + timedelta(seconds=30),
                level=LogLevel.INFO,
                service="api-server",
                message="Request 2"
            ),
            LogEntry(
                timestamp=ts_base + timedelta(minutes=10),
                level=LogLevel.INFO,
                service="database",
                message="Query 1"
            ),
        ]
        
        self.windows = aggregate_logs(logs, window_size_seconds=300)
    
    def test_get_services_in_windows(self):
        """Test extracting unique services."""
        services = get_services_in_windows(self.windows)
        
        assert len(services) == 2
        assert "api-server" in services
        assert "database" in services
    
    def test_get_time_range(self):
        """Test extracting time range of windows."""
        min_time, max_time = get_time_range(self.windows)
        
        assert min_time is not None
        assert max_time is not None
        assert max_time > min_time
    
    def test_get_time_range_empty_windows(self):
        """Test time range for empty windows dict."""
        min_time, max_time = get_time_range({})
        
        assert min_time is None
        assert max_time is None
