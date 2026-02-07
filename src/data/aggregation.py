"""
Time-window aggregation for logs.

Groups normalized logs into fixed time windows (e.g., 5-minute buckets)
and aggregates by service. Produces AggregatedLogWindow objects suitable
for feature extraction.

Design:
- Fixed window size (configurable, typically 5-10 minutes)
- Windows aligned to calendar boundaries (e.g., 00:00, 00:05, 00:10, ...)
- Each service gets its own window
- Windows preserve original log entries for inspection
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from src.data.schema import AggregatedLogWindow, LogEntry

logger = logging.getLogger(__name__)


class AggregationError(Exception):
    """Raised when aggregation fails."""
    pass


def align_timestamp_to_window(
    ts: datetime,
    window_size_seconds: int
) -> datetime:
    """
    Align timestamp to start of window boundary.
    
    Example with 5-minute window (300s):
    - 10:32:00 -> 10:30:00 (aligned down)
    - 10:30:00 -> 10:30:00 (already aligned)
    
    Args:
        ts: Timestamp to align
        window_size_seconds: Window size in seconds
    
    Returns:
        Aligned timestamp at window start (UTC)
    """
    # Convert to epoch seconds
    epoch_seconds = int(ts.replace(tzinfo=timezone.utc).timestamp())
    
    # Align down to window boundary
    aligned_epoch = (epoch_seconds // window_size_seconds) * window_size_seconds
    
    # Convert back to datetime
    return datetime.fromtimestamp(aligned_epoch, tz=timezone.utc)


def aggregate_logs(
    logs: List[LogEntry],
    window_size_seconds: int = 300
) -> Dict[tuple, AggregatedLogWindow]:
    """
    Aggregate logs into time windows, grouped by service.
    
    Args:
        logs: List of normalized LogEntry objects
        window_size_seconds: Window duration in seconds (default 5 minutes)
    
    Returns:
        Dict mapping (window_start, service) -> AggregatedLogWindow
    
    Notes:
        - Logs are sorted chronologically within each window
        - Empty windows are not created
        - Windows are keyed by (start_time, service_name) for deduplication
    
    Raises:
        AggregationError: If logs are invalid
    """
    if window_size_seconds <= 0:
        raise AggregationError("Window size must be positive")
    
    windows: Dict[tuple, AggregatedLogWindow] = {}
    
    for log in logs:
        # Align log timestamp to window
        window_start = align_timestamp_to_window(log.timestamp, window_size_seconds)
        window_end = window_start + timedelta(seconds=window_size_seconds)
        
        # Key for this window+service combo
        key = (window_start, log.service)
        
        # Create window if it doesn't exist
        if key not in windows:
            windows[key] = AggregatedLogWindow(
                window_start=window_start,
                window_end=window_end,
                window_size_seconds=window_size_seconds,
                service=log.service,
                logs=[]
            )
        
        # Add log to window
        windows[key].logs.append(log)
    
    # Sort logs within each window chronologically
    for window in windows.values():
        window.logs.sort(key=lambda l: l.timestamp)
    
    return windows


def get_window_key(window: AggregatedLogWindow) -> tuple:
    """
    Get dict key for a window (for grouping).
    
    Args:
        window: AggregatedLogWindow object
    
    Returns:
        Tuple (window_start, service)
    """
    return (window.window_start, window.service)


def get_services_in_windows(
    windows: Dict[tuple, AggregatedLogWindow]
) -> set:
    """
    Get all unique services across all windows.
    
    Args:
        windows: Dict of aggregated windows
    
    Returns:
        Set of service names
    """
    return {window.service for window in windows.values()}


def get_time_range(
    windows: Dict[tuple, AggregatedLogWindow]
) -> tuple:
    """
    Get min and max window times across all windows.
    
    Args:
        windows: Dict of aggregated windows
    
    Returns:
        Tuple of (min_start, max_end), or (None, None) if empty
    """
    if not windows:
        return None, None
    
    window_list = list(windows.values())
    min_start = min(w.window_start for w in window_list)
    max_end = max(w.window_end for w in window_list)
    
    return min_start, max_end


def print_windows_summary(
    windows: Dict[tuple, AggregatedLogWindow]
) -> str:
    """
    Create a human-readable summary of aggregated windows.
    
    Args:
        windows: Dict of aggregated windows
    
    Returns:
        String summary
    
    Example output:
        Aggregated 150 logs into 4 windows
        - api-server: 3 windows (50 logs)
        - auth-service: 1 window (100 logs)
        Time range: 2025-02-07 10:30:00 UTC to 10:45:00 UTC
    """
    if not windows:
        return "No windows"
    
    total_logs = sum(len(w.logs) for w in windows.values())
    services_dict: Dict[str, tuple] = {}  # service -> (window_count, log_count)
    
    for window in windows.values():
        service = window.service
        if service not in services_dict:
            services_dict[service] = (0, 0)
        
        current_windows, current_logs = services_dict[service]
        services_dict[service] = (current_windows + 1, current_logs + len(window.logs))
    
    lines = [f"Aggregated {total_logs} logs into {len(windows)} windows"]
    
    for service in sorted(services_dict.keys()):
        w_count, l_count = services_dict[service]
        lines.append(f"  - {service}: {w_count} window(s) ({l_count} logs)")
    
    min_start, max_end = get_time_range(windows)
    if min_start and max_end:
        lines.append(
            f"Time range: {min_start.isoformat()} to {max_end.isoformat()}"
        )
    
    return "\n".join(lines)


def filter_windows_by_service(
    windows: Dict[tuple, AggregatedLogWindow],
    service: str
) -> Dict[tuple, AggregatedLogWindow]:
    """
    Filter windows to only those for a specific service.
    
    Args:
        windows: Dict of aggregated windows
        service: Service name to filter by
    
    Returns:
        Filtered dict of windows
    """
    return {k: v for k, v in windows.items() if v.service == service}


def filter_windows_by_time(
    windows: Dict[tuple, AggregatedLogWindow],
    start_time: datetime,
    end_time: datetime
) -> Dict[tuple, AggregatedLogWindow]:
    """
    Filter windows to only those within a time range.
    
    Args:
        windows: Dict of aggregated windows
        start_time: Start of time range (inclusive)
        end_time: End of time range (exclusive)
    
    Returns:
        Filtered dict of windows
    """
    return {
        k: v for k, v in windows.items()
        if start_time <= v.window_start < end_time
    }


class WindowBatcher:
    """
    Helper for processing windows in batches.
    
    Useful for streaming large log datasets.
    """
    
    def __init__(self, logs: List[LogEntry], window_size_seconds: int = 300):
        """
        Initialize window batcher.
        
        Args:
            logs: List of logs (typically from one file)
            window_size_seconds: Window size
        """
        self.logs = logs
        self.window_size_seconds = window_size_seconds
    
    def process(self) -> List[AggregatedLogWindow]:
        """
        Process all logs into windows.
        
        Returns:
            List of AggregatedLogWindow objects (sorted by time and service)
        """
        windows_dict = aggregate_logs(self.logs, self.window_size_seconds)
        
        # Convert dict to sorted list
        windows_list = list(windows_dict.values())
        windows_list.sort(key=lambda w: (w.window_start, w.service))
        
        return windows_list
    
    def process_by_time(self) -> Dict[datetime, List[AggregatedLogWindow]]:
        """
        Process logs, grouping windows by time.
        
        Returns:
            Dict mapping window_start -> list of windows for that time
        
        Useful for time-series analysis where all services at time T
        are processed together.
        """
        windows_dict = aggregate_logs(self.logs, self.window_size_seconds)
        
        # Group by window time
        by_time: Dict[datetime, List[AggregatedLogWindow]] = {}
        for window in windows_dict.values():
            if window.window_start not in by_time:
                by_time[window.window_start] = []
            by_time[window.window_start].append(window)
        
        # Sort each time's windows by service
        for time_key in by_time:
            by_time[time_key].sort(key=lambda w: w.service)
        
        return dict(sorted(by_time.items()))
