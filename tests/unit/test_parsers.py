"""
Unit tests for log parsers.

Tests deterministic parsing of different log formats.
"""

import pytest
from datetime import datetime, timezone

from src.data.parsers import (
    StandardTextLineParser,
    JSONLogParser,
    CSVLogParser,
    ParsingError,
    parse_log,
)


class TestStandardTextLineParser:
    """Test text log parsing with standard format."""
    
    def test_parse_valid_info_log(self):
        """Test parsing a valid INFO log."""
        parser = StandardTextLineParser()
        raw_log = {
            "raw_line": "2025-02-07T10:30:45Z INFO api-server User login successful"
        }
        
        result = parser.parse(raw_log)
        
        assert result["timestamp"] == "2025-02-07T10:30:45Z"
        assert result["level"] == "INFO"
        assert result["service"] == "api-server"
        assert result["message"] == "User login successful"
    
    def test_parse_error_log_with_duration(self):
        """Test parsing an ERROR log with duration."""
        parser = StandardTextLineParser()
        raw_log = {
            "raw_line": "2025-02-07T10:30:46Z ERROR database Connection timeout (5000ms)"
        }
        
        result = parser.parse(raw_log)
        
        assert result["level"] == "ERROR"
        assert result["service"] == "database"
        assert "timeout" in result["message"].lower()
        assert result["duration_ms"] == 5000
    
    def test_parse_case_insensitive_level(self):
        """Test that log levels are case-insensitive."""
        parser = StandardTextLineParser()
        raw_log = {
            "raw_line": "2025-02-07T10:30:45Z warning auth-service Low memory"
        }
        
        result = parser.parse(raw_log)
        
        assert result["level"] == "WARNING"
    
    def test_parse_missing_timestamp(self):
        """Test that missing timestamp raises error."""
        parser = StandardTextLineParser()
        raw_log = {
            "raw_line": "INFO api-server No timestamp"
        }
        
        with pytest.raises(ParsingError):
            parser.parse(raw_log)
    
    def test_parse_missing_raw_line(self):
        """Test that missing raw_line key raises error."""
        parser = StandardTextLineParser()
        raw_log = {}
        
        with pytest.raises(ParsingError):
            parser.parse(raw_log)
    
    def test_parse_empty_raw_line(self):
        """Test that empty raw_line raises error."""
        parser = StandardTextLineParser()
        raw_log = {"raw_line": ""}
        
        with pytest.raises(ParsingError):
            parser.parse(raw_log)


class TestJSONLogParser:
    """Test JSON log parsing."""
    
    def test_parse_json_log_with_standard_fields(self):
        """Test parsing JSON with standard field names."""
        parser = JSONLogParser()
        raw_log = {
            "timestamp": "2025-02-07T10:30:45Z",
            "level": "INFO",
            "service": "api-server",
            "message": "Request successful",
        }
        
        result = parser.parse(raw_log)
        
        assert result["timestamp"] == "2025-02-07T10:30:45Z"
        assert result["level"] == "INFO"
        assert result["service"] == "api-server"
        assert result["message"] == "Request successful"
    
    def test_parse_json_with_alternate_field_names(self):
        """Test parsing JSON with alternate field names."""
        parser = JSONLogParser()
        raw_log = {
            "ts": "2025-02-07T10:30:45Z",
            "level_name": "ERROR",
            "app": "database",
            "msg": "Query timeout",
            "duration": 1500
        }
        
        result = parser.parse(raw_log)
        
        assert result["timestamp"] == "2025-02-07T10:30:45Z"
        assert result["level"] == "ERROR"
        assert result["service"] == "database"
        assert result["duration_ms"] == 1500
    
    def test_parse_json_missing_timestamp(self):
        """Test that missing timestamp raises error."""
        parser = JSONLogParser()
        raw_log = {
            "level": "INFO",
            "service": "api",
            "message": "Test"
        }
        
        with pytest.raises(ParsingError):
            parser.parse(raw_log)
    
    def test_parse_json_missing_message(self):
        """Test that missing message raises error."""
        parser = JSONLogParser()
        raw_log = {
            "timestamp": "2025-02-07T10:30:45Z",
            "level": "INFO",
            "service": "api"
        }
        
        with pytest.raises(ParsingError):
            parser.parse(raw_log)


class TestCSVLogParser:
    """Test CSV log parsing."""
    
    def test_parse_csv_with_standard_columns(self):
        """Test parsing CSV with standard columns."""
        parser = CSVLogParser()
        raw_log = {
            "timestamp": "2025-02-07T10:30:45Z",
            "level": "INFO",
            "service": "api-server",
            "message": "Request successful",
            "_metadata": {"format": "csv"}
        }
        
        result = parser.parse(raw_log)
        
        assert result["timestamp"] == "2025-02-07T10:30:45Z"
        assert result["level"] == "INFO"
        assert result["service"] == "api-server"
    
    def test_parse_csv_with_duration(self):
        """Test parsing CSV with duration column."""
        parser = CSVLogParser()
        raw_log = {
            "timestamp": "2025-02-07T10:30:45Z",
            "level": "ERROR",
            "service": "database",
            "message": "Query timeout",
            "duration_ms": "2500"
        }
        
        result = parser.parse(raw_log)
        
        assert result["duration_ms"] == 2500


class TestParseLogAutoDetect:
    """Test parse_log function with auto-detection."""
    
    def test_auto_detect_text_format(self):
        """Test auto-detection of text format."""
        raw_log = {
            "raw_line": "2025-02-07T10:30:45Z INFO api-server Test message"
        }
        
        result = parse_log(raw_log)
        
        assert result is not None
        assert result["level"] == "INFO"
    
    def test_auto_detect_json_format(self):
        """Test auto-detection of JSON format."""
        raw_log = {
            "timestamp": "2025-02-07T10:30:45Z",
            "level": "INFO",
            "service": "api",
            "message": "Test",
            "_metadata": {"format": "ndjson"}
        }
        
        result = parse_log(raw_log)
        
        assert result is not None
        assert result["level"] == "INFO"
    
    def test_parse_malformed_log_returns_none(self):
        """Test that malformed logs return None (not crash)."""
        raw_log = {
            "raw_line": "completely invalid log format"
        }
        
        result = parse_log(raw_log)
        
        assert result is None
