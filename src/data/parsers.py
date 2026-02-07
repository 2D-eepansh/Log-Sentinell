"""
Log parsing rules and strategies.

Converts raw log data (text strings, JSON, CSV) into structured dictionaries
with standardized fields. Parsing is deterministic and may fail gracefully
for malformed logs.

Design:
- Each parser is a callable that takes raw log data
- Parsers extract fields: timestamp, level, service, message, duration_ms, etc.
- Missing fields are left as None
- Parser errors are caught and logged
- Pipeline continues with next log
"""

import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class ParsingError(Exception):
    """Raised when log parsing fails."""
    pass


class BaseParser(ABC):
    """
    Abstract base for log parsers.
    
    Each parser handles a specific log format or pattern.
    """
    
    @abstractmethod
    def parse(self, raw_log: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a raw log entry.
        
        Args:
            raw_log: Raw log dict from ingestion (may have _metadata)
        
        Returns:
            Dict with parsed fields: timestamp, level, service, message, etc.
        
        Raises:
            ParsingError: If parsing fails
        """
        pass


class StandardTextLineParser(BaseParser):
    """
    Parses text logs with standard format:
    
        TIMESTAMP LEVEL SERVICE MESSAGE [EXTRA]
    
    Examples:
        2025-02-07T10:30:45Z INFO auth-service User login successful
        2025-02-07T10:30:46Z ERROR api-server Connection timeout (5000ms)
    
    Pattern:
    - Timestamp: ISO 8601 or common variants
    - Level: DEBUG, INFO, WARNING, ERROR, CRITICAL (case-insensitive)
    - Service: identifier (alphanumeric + dashes/underscores)
    - Message: remaining text
    """
    
    def __init__(self):
        """Initialize parser with regex patterns."""
        # ISO 8601 and common timestamp formats
        self.timestamp_pattern = re.compile(
            r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z?)"
        )
        
        # Log level (case-insensitive)
        self.level_pattern = re.compile(
            r"\s+(DEBUG|INFO|WARNING|ERROR|CRITICAL|WARN|ERR|NOTICE)\s+",
            re.IGNORECASE
        )
        
        # Service name (alphanumeric, dashes, underscores)
        self.service_pattern = re.compile(
            r"([a-zA-Z0-9_-]+)"
        )
        
        # Duration in milliseconds
        self.duration_pattern = re.compile(
            r"\((\d+)m?s?\)"
        )
    
    def parse(self, raw_log: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a text log line.
        
        Args:
            raw_log: Dict with "raw_line" key containing log text
        
        Returns:
            Parsed fields dict
        """
        if "raw_line" not in raw_log:
            raise ParsingError("raw_line not found in log dict")
        
        line = raw_log["raw_line"].strip()
        if not line:
            raise ParsingError("Empty log line")
        
        parsed = {
            "timestamp": None,
            "level": None,
            "service": None,
            "message": None,
            "duration_ms": None,
        }
        
        # Extract timestamp
        ts_match = self.timestamp_pattern.match(line)
        if ts_match:
            parsed["timestamp"] = ts_match.group(1)
            remaining = line[ts_match.end():].strip()
        else:
            raise ParsingError(f"No timestamp found in: {line[:50]}")
        
        # Extract level
        level_match = self.level_pattern.search(remaining)
        if level_match:
            parsed["level"] = level_match.group(1).upper()
            remaining = remaining[level_match.end():].strip()
        else:
            raise ParsingError(f"No log level found in: {line[:50]}")
        
        # Extract service
        service_match = self.service_pattern.match(remaining)
        if service_match:
            parsed["service"] = service_match.group(1)
            remaining = remaining[service_match.end():].strip()
        else:
            raise ParsingError(f"No service found in: {line[:50]}")
        
        # Remaining text is the message
        if remaining:
            parsed["message"] = remaining
        else:
            parsed["message"] = f"[No message] {line[:100]}"
        
        # Try to extract duration from message
        duration_match = self.duration_pattern.search(parsed["message"])
        if duration_match:
            try:
                parsed["duration_ms"] = int(duration_match.group(1))
            except ValueError:
                pass  # Silently ignore bad duration
        
        # Preserve source metadata
        if "_metadata" in raw_log:
            parsed["_metadata"] = raw_log["_metadata"]
        
        return parsed


class JSONLogParser(BaseParser):
    """
    Parses JSON-formatted logs.
    
    Expects JSON objects with fields like:
        - timestamp / time / ts
        - level / severity / level_name
        - service / app / component
        - message / msg / text
        - duration_ms / duration / latency_ms
    
    Field names are flexible and checked in order of likelihood.
    """
    
    def parse(self, raw_log: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a JSON log object.
        
        Args:
            raw_log: Dict from JSON ingestion
        
        Returns:
            Standardized fields dict
        """
        if not isinstance(raw_log, dict):
            raise ParsingError(f"Expected dict, got {type(raw_log)}")
        
        parsed = {
            "timestamp": None,
            "level": None,
            "service": None,
            "message": None,
            "duration_ms": None,
        }
        
        # Extract timestamp (try common field names)
        for key in ["timestamp", "time", "ts", "@timestamp"]:
            if key in raw_log:
                parsed["timestamp"] = raw_log[key]
                break
        
        # Extract level
        for key in ["level", "severity", "level_name", "log_level"]:
            if key in raw_log:
                level_val = str(raw_log[key]).upper()
                parsed["level"] = level_val
                break
        
        # Extract service
        for key in ["service", "app", "component", "source"]:
            if key in raw_log:
                parsed["service"] = str(raw_log[key])
                break
        
        # Extract message
        for key in ["message", "msg", "text", "log_message"]:
            if key in raw_log:
                parsed["message"] = str(raw_log[key])
                break
        
        # Extract duration
        for key in ["duration_ms", "duration", "latency_ms", "duration_milliseconds"]:
            if key in raw_log:
                try:
                    parsed["duration_ms"] = int(raw_log[key])
                except (ValueError, TypeError):
                    pass
                break
        
        # Validate minimum required fields
        if parsed["timestamp"] is None:
            raise ParsingError("No timestamp found in JSON")
        if parsed["message"] is None:
            raise ParsingError("No message found in JSON")
        
        # Preserve source metadata
        if "_metadata" in raw_log:
            parsed["_metadata"] = raw_log["_metadata"]
        
        return parsed


class CSVLogParser(BaseParser):
    """
    Parses CSV logs.
    
    Assumes CSV rows are already parsed into dicts with column headers as keys.
    Maps common column names to standardized fields.
    """
    
    def parse(self, raw_log: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a CSV log row dict.
        
        Args:
            raw_log: Dict from CSV ingestion
        
        Returns:
            Standardized fields dict
        """
        if not isinstance(raw_log, dict):
            raise ParsingError(f"Expected dict, got {type(raw_log)}")
        
        parsed = {
            "timestamp": None,
            "level": None,
            "service": None,
            "message": None,
            "duration_ms": None,
        }
        
        # Map CSV columns to standard fields
        # Try common column names
        for csv_col, std_field in [
            (["timestamp", "time", "ts"], "timestamp"),
            (["level", "severity", "log_level"], "level"),
            (["service", "app", "component"], "service"),
            (["message", "msg", "text"], "message"),
            (["duration_ms", "duration"], "duration_ms"),
        ]:
            for col in csv_col:
                if col in raw_log and raw_log[col]:
                    if std_field == "duration_ms":
                        try:
                            parsed[std_field] = int(raw_log[col])
                        except (ValueError, TypeError):
                            pass
                    else:
                        parsed[std_field] = str(raw_log[col])
                    break
        
        # Validate minimum fields
        if parsed["timestamp"] is None:
            raise ParsingError("No timestamp found in CSV")
        if parsed["message"] is None:
            raise ParsingError("No message found in CSV")
        
        # Preserve source metadata
        if "_metadata" in raw_log:
            parsed["_metadata"] = raw_log["_metadata"]
        
        return parsed


def parse_log(
    raw_log: Dict[str, Any],
    parser: Optional[BaseParser] = None
) -> Optional[Dict[str, Any]]:
    """
    Parse a raw log with appropriate parser.
    
    If no parser specified, attempts to auto-detect based on log format.
    
    Args:
        raw_log: Raw log dict from ingestion
        parser: Specific parser to use (optional)
    
    Returns:
        Parsed log dict, or None if parsing failed
    
    Notes:
        - Parsing errors are logged but don't crash pipeline
        - Returns None on failure so caller can skip
    """
    if parser is None:
        # Auto-detect parser based on log format
        if "raw_line" in raw_log:
            parser = StandardTextLineParser()
        elif "format" in raw_log.get("_metadata", {}):
            format_type = raw_log["_metadata"]["format"]
            if format_type in ["json_array", "ndjson"]:
                parser = JSONLogParser()
            elif format_type == "csv":
                parser = CSVLogParser()
            else:
                parser = StandardTextLineParser()
        else:
            # Default to text parser
            parser = StandardTextLineParser()
    
    try:
        return parser.parse(raw_log)
    except ParsingError as e:
        logger.debug(f"Failed to parse log: {e}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error parsing log: {e}")
        return None


def parse_logs(
    raw_logs: list[Dict[str, Any]],
    parser: Optional[BaseParser] = None
) -> tuple[list[Dict[str, Any]], int]:
    """
    Parse multiple logs, collecting results and skip count.
    
    Args:
        raw_logs: List of raw logs from ingestion
        parser: Optional specific parser
    
    Returns:
        Tuple of (parsed_logs, skipped_count)
    
    Example:
        parsed, skipped = parse_logs(raw_logs)
        logger.info(f"Parsed {len(parsed)} logs, skipped {skipped}")
    """
    parsed_logs = []
    skipped = 0
    
    for raw_log in raw_logs:
        result = parse_log(raw_log, parser)
        if result is not None:
            parsed_logs.append(result)
        else:
            skipped += 1
    
    return parsed_logs, skipped
