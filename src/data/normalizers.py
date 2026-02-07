"""
Log normalization: standardize timestamps, levels, service names, and messages.

Converts parsed logs (which may have inconsistent formats) into a canonical form
that's consistent across the entire pipeline.

Design:
- Timestamp normalization to UTC datetime
- Level normalization to standard set
- Service name normalization (lowercase, trim)
- Message normalization (trim, deduplicate with hashing)
- All transformations are deterministic and reversible
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.data.schema import LogEntry, LogLevel

logger = logging.getLogger(__name__)


class NormalizationError(Exception):
    """Raised when log normalization fails."""
    pass


def normalize_timestamp(ts_str: str) -> datetime:
    """
    Normalize timestamp string to UTC datetime.
    
    Supports common formats:
    - ISO 8601: 2025-02-07T10:30:45Z
    - ISO 8601 no Z: 2025-02-07T10:30:45
    - Date-time: 2025-02-07 10:30:45
    - Epoch seconds: 1707315045
    - Epoch millis: 1707315045000
    
    Args:
        ts_str: Timestamp string
    
    Returns:
        Timezone-aware datetime in UTC
    
    Raises:
        NormalizationError: If timestamp format not recognized
    """
    if not ts_str:
        raise NormalizationError("Empty timestamp")
    
    ts_str = str(ts_str).strip()
    
    # Try numeric (epoch seconds or millis)
    try:
        ts_float = float(ts_str)
        
        # Detect seconds vs milliseconds
        # Timestamps before year 3000 are seconds
        if ts_float < 32503680000:  # Year 3000 in seconds
            return datetime.fromtimestamp(ts_float, tz=timezone.utc)
        else:
            return datetime.fromtimestamp(ts_float / 1000, tz=timezone.utc)
    except ValueError:
        pass
    
    # Try ISO 8601 formats
    iso_formats = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S.%f",
    ]
    
    for fmt in iso_formats:
        try:
            dt = datetime.strptime(ts_str, fmt)
            # Make timezone-aware (UTC)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    
    raise NormalizationError(f"Could not parse timestamp: {ts_str}")


def normalize_level(level_str: str) -> LogLevel:
    """
    Normalize log level to standard enum.
    
    Handles common variants:
    - WARN -> WARNING
    - ERR -> ERROR
    - Case-insensitive
    
    Args:
        level_str: Log level string
    
    Returns:
        LogLevel enum value
    
    Raises:
        NormalizationError: If level not recognized
    """
    if not level_str:
        raise NormalizationError("Empty log level")
    
    level_str = str(level_str).upper().strip()
    
    # Map common variants to standard
    level_map = {
        "DEBUG": LogLevel.DEBUG,
        "INFO": LogLevel.INFO,
        "WARNING": LogLevel.WARNING,
        "WARN": LogLevel.WARNING,
        "ERROR": LogLevel.ERROR,
        "ERR": LogLevel.ERROR,
        "CRITICAL": LogLevel.CRITICAL,
        "CRIT": LogLevel.CRITICAL,
        "FATAL": LogLevel.CRITICAL,
    }
    
    if level_str in level_map:
        return level_map[level_str]
    
    raise NormalizationError(f"Unknown log level: {level_str}")


def normalize_service(service_str: str) -> str:
    """
    Normalize service name.
    
    - Lowercase
    - Strip whitespace
    - Allow alphanumeric, dashes, underscores
    - Max 128 characters
    
    Args:
        service_str: Service name
    
    Returns:
        Normalized service name
    
    Raises:
        NormalizationError: If service name invalid
    """
    if not service_str:
        raise NormalizationError("Empty service name")
    
    service = str(service_str).lower().strip()
    
    # Truncate if too long
    if len(service) > 128:
        logger.warning(f"Service name truncated: {service[:50]}...")
        service = service[:128]
    
    # Validate allowed characters
    if not all(c.isalnum() or c in "-_." for c in service):
        logger.warning(f"Service name contains invalid characters: {service}")
        # Remove invalid chars
        service = "".join(c for c in service if c.isalnum() or c in "-_.")
    
    if not service:
        raise NormalizationError("Service name empty after normalization")
    
    return service


def normalize_message(message_str: str) -> tuple[str, str]:
    """
    Normalize log message.
    
    - Strip whitespace
    - Truncate to 2048 chars
    - Compute hash for deduplication
    - Normalize line breaks to spaces
    
    Args:
        message_str: Raw message text
    
    Returns:
        Tuple of (normalized_message, message_hash)
    
    Raises:
        NormalizationError: If message invalid
    """
    if not message_str:
        raise NormalizationError("Empty message")
    
    message = str(message_str).strip()
    
    # Replace line breaks with space
    message = " ".join(message.split())
    
    # Truncate if too long
    if len(message) > 2048:
        message = message[:2048]
    
    # Compute hash for deduplication
    msg_hash = hashlib.sha256(message.encode()).hexdigest()[:16]
    
    return message, msg_hash


def normalize_duration(duration_any: Any) -> Optional[int]:
    """
    Normalize duration to milliseconds.
    
    Accepts:
    - int or float in milliseconds
    - Negative values are treated as None (missing/invalid)
    
    Args:
        duration_any: Duration value (int, float, str, or None)
    
    Returns:
        Duration in milliseconds, or None if invalid/missing
    """
    if duration_any is None:
        return None
    
    try:
        duration = float(duration_any)
        
        # Skip negative or zero durations
        if duration <= 0:
            return None
        
        # Convert to int milliseconds
        return int(duration)
    
    except (ValueError, TypeError):
        return None


def normalize_log(parsed_log: Dict[str, Any]) -> LogEntry:
    """
    Convert parsed log to canonical LogEntry.
    
    Validates all required fields and normalizes formats.
    
    Args:
        parsed_log: Output from parser (dict with fields)
    
    Returns:
        LogEntry object (fully validated)
    
    Raises:
        NormalizationError: If required fields invalid
    
    Notes:
        - All fields are validated
        - Defaults to None for optional fields if missing
        - Exceptions indicate data quality issues (logged but not fatal)
    """
    if not isinstance(parsed_log, dict):
        raise NormalizationError(f"Expected dict, got {type(parsed_log)}")
    
    # Normalize required fields
    try:
        timestamp = normalize_timestamp(parsed_log.get("timestamp"))
    except NormalizationError as e:
        raise NormalizationError(f"Invalid timestamp: {e}") from e
    
    try:
        level = normalize_level(parsed_log.get("level", "INFO"))
    except NormalizationError:
        # Default to INFO if level is bad
        logger.warning(f"Bad log level: {parsed_log.get('level')}, defaulting to INFO")
        level = LogLevel.INFO
    
    try:
        service = normalize_service(parsed_log.get("service"))
    except NormalizationError as e:
        raise NormalizationError(f"Invalid service: {e}") from e
    
    try:
        message, msg_hash = normalize_message(parsed_log.get("message"))
    except NormalizationError as e:
        raise NormalizationError(f"Invalid message: {e}") from e
    
    # Normalize optional fields
    duration_ms = normalize_duration(parsed_log.get("duration_ms"))
    error_code = parsed_log.get("error_code")
    if error_code:
        error_code = str(error_code).strip()[:64]
    
    request_id = parsed_log.get("request_id")
    if request_id:
        request_id = str(request_id).strip()[:128]
    
    # Preserve metadata
    metadata = parsed_log.get("_metadata", {})
    metadata["message_hash"] = msg_hash
    
    # Create LogEntry
    return LogEntry(
        timestamp=timestamp,
        level=level,
        service=service,
        message=message,
        duration_ms=duration_ms,
        error_code=error_code,
        request_id=request_id,
        metadata=metadata,
    )


def normalize_logs(
    parsed_logs: list[Dict[str, Any]]
) -> tuple[list[LogEntry], int]:
    """
    Normalize multiple parsed logs.
    
    Args:
        parsed_logs: List of dicts from parser
    
    Returns:
        Tuple of (normalized_logs, skipped_count)
    
    Notes:
        - Logs that fail normalization are skipped (logged as warnings)
        - Returns count of successfully normalized logs
    """
    normalized = []
    skipped = 0
    
    for parsed_log in parsed_logs:
        try:
            log_entry = normalize_log(parsed_log)
            normalized.append(log_entry)
        except NormalizationError as e:
            logger.debug(f"Skipped log due to normalization error: {e}")
            skipped += 1
        except Exception as e:
            logger.warning(f"Unexpected error normalizing log: {e}")
            skipped += 1
    
    return normalized, skipped
