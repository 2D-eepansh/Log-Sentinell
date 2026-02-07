"""
Unit tests for log normalization.

Tests conversion of parsed logs into canonical LogEntry format.
"""

import pytest
from datetime import datetime, timezone

from src.data.normalizers import (
    normalize_timestamp,
    normalize_level,
    normalize_service,
    normalize_message,
    normalize_duration,
    normalize_log,
    NormalizationError,
)
from src.data.schema import LogLevel


class TestNormalizeTimestamp:
    """Test timestamp normalization."""
    
    def test_normalize_iso8601_with_z(self):
        """Test ISO 8601 format with Z."""
        result = normalize_timestamp("2025-02-07T10:30:45Z")
        
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 2
        assert result.day == 7
        assert result.hour == 10
        assert result.minute == 30
    
    def test_normalize_iso8601_without_z(self):
        """Test ISO 8601 format without Z."""
        result = normalize_timestamp("2025-02-07T10:30:45")
        
        assert result.year == 2025
        assert result.tzinfo == timezone.utc
    
    def test_normalize_date_time_format(self):
        """Test date-time format."""
        result = normalize_timestamp("2025-02-07 10:30:45")
        
        assert result.year == 2025
        assert result.hour == 10
    
    def test_normalize_epoch_seconds(self):
        """Test epoch seconds."""
        # 1707315045 = 2024-02-07T10:30:45Z
        result = normalize_timestamp("1707315045")
        
        assert result.year == 2024
        assert result.tzinfo == timezone.utc
    
    def test_normalize_epoch_milliseconds(self):
        """Test epoch milliseconds."""
        # 1707315045000 = 2024-02-07T10:30:45Z
        result = normalize_timestamp("1707315045000")
        
        assert result.year == 2024
        assert result.tzinfo == timezone.utc
    
    def test_normalize_invalid_timestamp(self):
        """Test that invalid timestamp raises error."""
        with pytest.raises(NormalizationError):
            normalize_timestamp("not-a-timestamp")
    
    def test_normalize_empty_timestamp(self):
        """Test that empty timestamp raises error."""
        with pytest.raises(NormalizationError):
            normalize_timestamp("")


class TestNormalizeLevel:
    """Test log level normalization."""
    
    def test_normalize_standard_levels(self):
        """Test normalization of standard levels."""
        assert normalize_level("DEBUG") == LogLevel.DEBUG
        assert normalize_level("INFO") == LogLevel.INFO
        assert normalize_level("WARNING") == LogLevel.WARNING
        assert normalize_level("ERROR") == LogLevel.ERROR
        assert normalize_level("CRITICAL") == LogLevel.CRITICAL
    
    def test_normalize_level_case_insensitive(self):
        """Test that normalization is case-insensitive."""
        assert normalize_level("info") == LogLevel.INFO
        assert normalize_level("Error") == LogLevel.ERROR
    
    def test_normalize_common_variants(self):
        """Test normalization of common variants."""
        assert normalize_level("WARN") == LogLevel.WARNING
        assert normalize_level("ERR") == LogLevel.ERROR
        assert normalize_level("CRIT") == LogLevel.CRITICAL
    
    def test_normalize_invalid_level(self):
        """Test that invalid level raises error."""
        with pytest.raises(NormalizationError):
            normalize_level("UNKNOWN")
    
    def test_normalize_empty_level(self):
        """Test that empty level raises error."""
        with pytest.raises(NormalizationError):
            normalize_level("")


class TestNormalizeService:
    """Test service name normalization."""
    
    def test_normalize_standard_service(self):
        """Test normalization of standard service names."""
        result = normalize_service("API-Server")
        
        assert result == "api-server"
    
    def test_normalize_removes_whitespace(self):
        """Test that whitespace is trimmed."""
        result = normalize_service("  api-server  ")
        
        assert result == "api-server"
    
    def test_normalize_truncates_long_service(self):
        """Test that very long service names are truncated."""
        long_name = "a" * 200
        result = normalize_service(long_name)
        
        assert len(result) == 128
    
    def test_normalize_invalid_characters_removed(self):
        """Test that invalid characters are removed."""
        result = normalize_service("api@server#123")
        
        # Invalid chars (@, #) should be removed
        assert "@" not in result
        assert "#" not in result
        assert "api" in result
        assert "server" in result
        assert "123" in result
    
    def test_normalize_empty_service_raises_error(self):
        """Test that empty service raises error."""
        with pytest.raises(NormalizationError):
            normalize_service("")


class TestNormalizeMessage:
    """Test message normalization."""
    
    def test_normalize_standard_message(self):
        """Test normalization of standard message."""
        message, msg_hash = normalize_message("User login successful")
        
        assert message == "User login successful"
        assert len(msg_hash) == 16  # SHA256 truncated to 16 chars
    
    def test_normalize_strips_whitespace(self):
        """Test that leading/trailing whitespace is stripped."""
        message, _ = normalize_message("   Error occurred   ")
        
        assert message == "Error occurred"
    
    def test_normalize_collapses_whitespace(self):
        """Test that multiple spaces are collapsed."""
        message, _ = normalize_message("Multiple    spaces    here")
        
        assert message == "Multiple spaces here"
    
    def test_normalize_truncates_long_message(self):
        """Test that long messages are truncated."""
        long_msg = "a" * 3000
        message, _ = normalize_message(long_msg)
        
        assert len(message) == 2048
    
    def test_normalize_message_deduplication(self):
        """Test that identical messages have same hash."""
        _, hash1 = normalize_message("Same message")
        _, hash2 = normalize_message("Same message")
        
        assert hash1 == hash2
    
    def test_normalize_different_messages_different_hash(self):
        """Test that different messages have different hashes."""
        _, hash1 = normalize_message("Message A")
        _, hash2 = normalize_message("Message B")
        
        assert hash1 != hash2
    
    def test_normalize_empty_message_raises_error(self):
        """Test that empty message raises error."""
        with pytest.raises(NormalizationError):
            normalize_message("")


class TestNormalizeDuration:
    """Test duration normalization."""
    
    def test_normalize_valid_duration(self):
        """Test normalization of valid duration."""
        result = normalize_duration(1500)
        
        assert result == 1500
    
    def test_normalize_duration_from_float(self):
        """Test conversion from float."""
        result = normalize_duration(1500.5)
        
        assert result == 1500
        assert isinstance(result, int)
    
    def test_normalize_duration_from_string(self):
        """Test conversion from string."""
        result = normalize_duration("2000")
        
        assert result == 2000
    
    def test_normalize_zero_duration_returns_none(self):
        """Test that zero duration returns None."""
        result = normalize_duration(0)
        
        assert result is None
    
    def test_normalize_negative_duration_returns_none(self):
        """Test that negative duration returns None."""
        result = normalize_duration(-100)
        
        assert result is None
    
    def test_normalize_none_duration_returns_none(self):
        """Test that None duration returns None."""
        result = normalize_duration(None)
        
        assert result is None
    
    def test_normalize_invalid_duration_returns_none(self):
        """Test that invalid duration returns None (doesn't crash)."""
        result = normalize_duration("not-a-number")
        
        assert result is None


class TestNormalizeLog:
    """Test full log normalization."""
    
    def test_normalize_valid_parsed_log(self):
        """Test normalization of valid parsed log."""
        parsed = {
            "timestamp": "2025-02-07T10:30:45Z",
            "level": "INFO",
            "service": "API-Server",
            "message": "Request processed successfully",
            "duration_ms": 150,
        }
        
        result = normalize_log(parsed)
        
        assert result.timestamp.year == 2025
        assert result.level == LogLevel.INFO
        assert result.service == "api-server"
        assert result.duration_ms == 150
    
    def test_normalize_log_with_defaults(self):
        """Test that optional fields default to None."""
        parsed = {
            "timestamp": "2025-02-07T10:30:45Z",
            "level": "INFO",
            "service": "api",
            "message": "Test",
        }
        
        result = normalize_log(parsed)
        
        assert result.duration_ms is None
        assert result.error_code is None
        assert result.request_id is None
    
    def test_normalize_log_bad_level_defaults_to_info(self):
        """Test that bad level defaults to INFO (not error)."""
        parsed = {
            "timestamp": "2025-02-07T10:30:45Z",
            "level": "INVALID",
            "service": "api",
            "message": "Test",
        }
        
        result = normalize_log(parsed)
        
        assert result.level == LogLevel.INFO  # Defaulted
    
    def test_normalize_log_missing_required_field(self):
        """Test that missing required field raises error."""
        parsed = {
            "timestamp": "2025-02-07T10:30:45Z",
            "level": "INFO",
            # Missing service and message
        }
        
        with pytest.raises(NormalizationError):
            normalize_log(parsed)
