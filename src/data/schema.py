"""
Canonical internal log schema for the anomaly detection pipeline.

This module defines the standardized representation of a single log entry
after parsing and normalization. All log sources are converted to this schema
before feature extraction or anomaly detection.

Design rationale:
- Minimal fields (only what's needed for anomaly detection)
- All timestamps in UTC for consistency
- Severity levels normalized to standard set
- Extensible metadata dict for additional context
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class LogLevel(str, Enum):
    """
    Standardized log severity levels.
    
    Normalized from common variants (e.g., "warn" -> "WARNING", "err" -> "ERROR")
    """
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogEntry(BaseModel):
    """
    Canonical representation of a single log entry.
    
    This is the internal format produced by all parsers and used throughout
    the pipeline for aggregation and feature extraction.
    
    Attributes:
        timestamp: UTC datetime when the event occurred
        level: Severity level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        service: Name of the service/component that generated the log
        message: Log message text (may be truncated or normalized)
        duration_ms: Request/operation duration in milliseconds (optional)
        error_code: Application-specific error code (optional)
        request_id: Correlation ID for distributed tracing (optional)
        metadata: Additional fields not covered by standard schema
    
    Notes:
        - All fields are validated at instantiation
        - Timestamps are always UTC
        - message is the primary feature for LLM explanation (Phase 2)
        - metadata preserves raw fields for debugging/extension
    """
    
    timestamp: datetime = Field(
        ...,
        description="UTC timestamp of the event"
    )
    
    level: LogLevel = Field(
        ...,
        description="Severity level (normalized)"
    )
    
    service: str = Field(
        ...,
        description="Service or component name",
        min_length=1,
        max_length=128
    )
    
    message: str = Field(
        ...,
        description="Log message text",
        min_length=1,
        max_length=2048
    )
    
    duration_ms: Optional[int] = Field(
        default=None,
        ge=0,
        description="Operation duration in milliseconds"
    )
    
    error_code: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Application-specific error code"
    )
    
    request_id: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Correlation ID for tracing"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional unstructured fields"
    )
    
    class Config:
        """Pydantic model configuration."""
        # Allow use in tests and logging
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class AggregatedLogWindow(BaseModel):
    """
    Aggregated logs within a fixed time window.
    
    This is produced by the aggregation step and fed to feature extraction.
    Groups logs by service and window, preserving raw entries for inspection.
    
    Attributes:
        window_start: UTC start of the time window
        window_end: UTC end of the time window (exclusive)
        window_size_seconds: Duration of the window
        service: Service name
        logs: List of LogEntry objects in this window
    
    Notes:
        - window_end is exclusive (typical for time ranges)
        - Logs within a window are in chronological order
        - Useful for debugging / understanding feature values
    """
    
    window_start: datetime = Field(
        ...,
        description="UTC start of time window"
    )
    
    window_end: datetime = Field(
        ...,
        description="UTC end of time window (exclusive)"
    )
    
    window_size_seconds: int = Field(
        ...,
        ge=1,
        description="Duration of the window in seconds"
    )
    
    service: str = Field(
        ...,
        description="Service name"
    )
    
    logs: list[LogEntry] = Field(
        default_factory=list,
        description="Logs in this window for this service"
    )
    
    class Config:
        """Pydantic model configuration."""
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
    
    @property
    def log_count(self) -> int:
        """Total number of logs in this window."""
        return len(self.logs)


class FeatureVector(BaseModel):
    """
    Extracted features for a time window and service.
    
    Produced by feature extraction and used by anomaly detection.
    All features are deterministic functions of the log data.
    
    Attributes:
        window_start: UTC start of time window
        service: Service name
        
        # Count features
        total_events: Total number of events
        error_count: Number of ERROR and CRITICAL level logs
        warning_count: Number of WARNING level logs
        info_count: Number of INFO level logs
        
        # Rate features
        error_rate: error_count / total_events (0.0 - 1.0)
        warning_rate: warning_count / total_events (0.0 - 1.0)
        
        # Temporal features
        median_duration_ms: Median duration of timestamped operations
        p95_duration_ms: 95th percentile duration
        max_duration_ms: Maximum duration observed
        
        # Diversity features
        unique_messages: Number of distinct message texts
        unique_error_codes: Number of distinct error codes
        
        # Metadata
        metadata: Additional computed values for debugging
    
    Notes:
        - All rates are in [0.0, 1.0]
        - All duration stats default to None if no duration data
        - Features are designed to be robust to scale differences
        - Easy to add more features without breaking downstream
    """
    
    window_start: datetime = Field(
        ...,
        description="UTC start of time window"
    )
    
    service: str = Field(
        ...,
        description="Service name"
    )
    
    # Count features
    total_events: int = Field(
        ...,
        ge=0,
        description="Total number of events"
    )
    
    error_count: int = Field(
        ...,
        ge=0,
        description="Count of ERROR + CRITICAL logs"
    )
    
    warning_count: int = Field(
        ...,
        ge=0,
        description="Count of WARNING logs"
    )
    
    info_count: int = Field(
        ...,
        ge=0,
        description="Count of INFO logs"
    )
    
    # Rate features
    error_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Fraction of events that are errors (0.0-1.0)"
    )
    
    warning_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Fraction of events that are warnings (0.0-1.0)"
    )
    
    # Temporal features (optional if no duration data)
    median_duration_ms: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Median operation duration in ms"
    )
    
    p95_duration_ms: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="95th percentile operation duration in ms"
    )
    
    max_duration_ms: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Maximum operation duration in ms"
    )
    
    # Diversity features
    unique_messages: int = Field(
        ...,
        ge=0,
        description="Number of distinct message texts"
    )
    
    unique_error_codes: int = Field(
        ...,
        ge=0,
        description="Number of distinct error codes"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional debugging info"
    )
    
    class Config:
        """Pydantic model configuration."""
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
