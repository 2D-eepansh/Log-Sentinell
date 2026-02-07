"""
Log ingestion from various file formats.

Supports text, JSON, and CSV log sources. Gracefully handles malformed entries
by skipping them and logging warnings. All ingested logs are returned as raw
dictionaries for subsequent parsing.

Design:
- Format detection (optional) or explicit format specification
- Iterator-based for memory efficiency with large files
- Bad rows logged but don't crash the pipeline
- Returns raw dicts, not parsed LogEntry objects
"""

import csv
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Union

logger = logging.getLogger(__name__)


class LogIngestionError(Exception):
    """Base exception for log ingestion failures."""
    pass


class BaseLogSource(ABC):
    """
    Abstract base class for log sources.
    
    Each source type (text, JSON, CSV) implements this interface.
    Subclasses handle format-specific parsing and error handling.
    """
    
    def __init__(self, filepath: Union[str, Path], encoding: str = "utf-8"):
        """
        Initialize log source.
        
        Args:
            filepath: Path to log file
            encoding: File encoding (default utf-8)
        
        Raises:
            LogIngestionError: If file doesn't exist
        """
        self.filepath = Path(filepath)
        self.encoding = encoding
        
        if not self.filepath.exists():
            raise LogIngestionError(f"Log file not found: {self.filepath}")
    
    @abstractmethod
    def ingest(self) -> Iterator[Dict[str, Any]]:
        """
        Ingest logs from source.
        
        Yields:
            Dict representing a single log entry (format-dependent)
        """
        pass


class TextLogSource(BaseLogSource):
    """
    Ingests unstructured text logs (one log per line).
    
    Example input:
        2025-02-07T10:30:45Z INFO auth-service User login successful
        2025-02-07T10:30:46Z ERROR api-server Connection timeout (5000ms)
    
    Each line is returned as a raw string in a dict.
    Parsing is deferred to the parser layer.
    """
    
    def ingest(self) -> Iterator[Dict[str, Any]]:
        """
        Read text log file line by line.
        
        Yields:
            Dict with key "raw_line" containing the log line
        
        Notes:
            - Empty lines are skipped
            - Each line is stripped of leading/trailing whitespace
        """
        try:
            with open(self.filepath, "r", encoding=self.encoding) as f:
                for line_num, line in enumerate(f, start=1):
                    line = line.strip()
                    
                    # Skip empty lines
                    if not line:
                        continue
                    
                    yield {
                        "raw_line": line,
                        "_metadata": {
                            "source": str(self.filepath),
                            "line_number": line_num,
                            "format": "text"
                        }
                    }
        except Exception as e:
            logger.error(f"Error reading text log file {self.filepath}: {e}")
            raise LogIngestionError(f"Failed to read text log: {e}") from e


class JSONLogSource(BaseLogSource):
    """
    Ingests JSON-formatted logs (one JSON object per line or array).
    
    Supports:
    - NDJSON format (newline-delimited JSON)
    - JSON array format
    
    Example NDJSON:
        {"timestamp": "2025-02-07T10:30:45Z", "level": "INFO", "message": "..."}
        {"timestamp": "2025-02-07T10:30:46Z", "level": "ERROR", "message": "..."}
    """
    
    def ingest(self) -> Iterator[Dict[str, Any]]:
        """
        Read JSON logs from file.
        
        Handles both NDJSON (one object per line) and JSON array formats.
        Bad JSON lines are logged and skipped.
        
        Yields:
            Dict representing a single log object
        
        Notes:
            - Malformed JSON on a line is skipped with warning
            - File-level JSON errors are fatal (raise LogIngestionError)
        """
        try:
            with open(self.filepath, "r", encoding=self.encoding) as f:
                content = f.read().lstrip("\ufeff").strip()
            
            # Try parsing as JSON array first
            if content.startswith("["):
                try:
                    logs = json.loads(content)
                    if not isinstance(logs, list):
                        raise LogIngestionError("JSON must be array or NDJSON")
                    
                    for idx, log in enumerate(logs):
                        if isinstance(log, dict):
                            log["_metadata"] = {
                                "source": str(self.filepath),
                                "index": idx,
                                "format": "json_array"
                            }
                            yield log
                        else:
                            logger.warning(f"Non-dict entry at index {idx}: {type(log)}")
                
                except json.JSONDecodeError as e:
                    raise LogIngestionError(f"Invalid JSON array: {e}") from e
            
            # Fall back to NDJSON (one object per line)
            else:
                for line_num, line in enumerate(content.split("\n"), start=1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        log = json.loads(line)
                        if isinstance(log, dict):
                            log["_metadata"] = {
                                "source": str(self.filepath),
                                "line_number": line_num,
                                "format": "ndjson"
                            }
                            yield log
                        else:
                            logger.warning(f"NDJSON line {line_num} not a dict: {type(log)}")
                    except json.JSONDecodeError:
                        logger.warning(f"Malformed JSON at line {line_num}: {line[:100]}")
        
        except LogIngestionError:
            raise
        except Exception as e:
            logger.error(f"Error reading JSON log file {self.filepath}: {e}")
            raise LogIngestionError(f"Failed to read JSON log: {e}") from e


class CSVLogSource(BaseLogSource):
    """
    Ingests CSV-formatted logs.
    
    Assumes first row contains headers.
    
    Example:
        timestamp,level,service,message,duration_ms
        2025-02-07T10:30:45Z,INFO,auth-service,User login,50
        2025-02-07T10:30:46Z,ERROR,api-server,Timeout,5000
    """
    
    def __init__(
        self,
        filepath: Union[str, Path],
        encoding: str = "utf-8",
        delimiter: str = ","
    ):
        """
        Initialize CSV log source.
        
        Args:
            filepath: Path to CSV file
            encoding: File encoding
            delimiter: CSV delimiter (default comma)
        """
        super().__init__(filepath, encoding)
        self.delimiter = delimiter
    
    def ingest(self) -> Iterator[Dict[str, Any]]:
        """
        Read CSV log file.
        
        First row must contain headers.
        Malformed rows are logged and skipped.
        
        Yields:
            Dict mapping column names to values
        """
        try:
            with open(self.filepath, "r", encoding=self.encoding) as f:
                reader = csv.DictReader(f, delimiter=self.delimiter)
                
                if reader.fieldnames is None:
                    raise LogIngestionError("CSV file is empty")

                # Normalize BOM in header if present
                normalized = []
                for name in reader.fieldnames:
                    if isinstance(name, str):
                        normalized.append(name.lstrip("\ufeff"))
                    else:
                        normalized.append(name)
                reader.fieldnames = normalized
                
                for line_num, row in enumerate(reader, start=2):  # Start at 2 (row 1 is header)
                    if row is None or all(v is None for v in row.values()):
                        logger.warning(f"Empty row at line {line_num}")
                        continue
                    
                    row["_metadata"] = {
                        "source": str(self.filepath),
                        "line_number": line_num,
                        "format": "csv"
                    }
                    yield row
        
        except Exception as e:
            logger.error(f"Error reading CSV log file {self.filepath}: {e}")
            raise LogIngestionError(f"Failed to read CSV log: {e}") from e


def ingest_logs(
    filepath: Union[str, Path],
    format: str = "auto"
) -> Iterator[Dict[str, Any]]:
    """
    Convenience function to ingest logs from a file.
    
    Args:
        filepath: Path to log file
        format: Log format ("text", "json", "csv", or "auto" for detection)
    
    Yields:
        Raw log dict from ingestion source
    
    Raises:
        LogIngestionError: If file not found or format unsupported
    
    Example:
        for raw_log in ingest_logs("app.log", format="text"):
            parsed = parse_log(raw_log)
            ...
    """
    filepath = Path(filepath)
    
    # Auto-detect format from file extension
    if format == "auto":
        suffix = filepath.suffix.lower()
        if suffix == ".json":
            format = "json"
        elif suffix == ".csv":
            format = "csv"
        else:
            format = "text"
    
    # Select appropriate source
    if format == "text":
        source = TextLogSource(filepath)
    elif format == "json":
        source = JSONLogSource(filepath)
    elif format == "csv":
        source = CSVLogSource(filepath)
    else:
        raise LogIngestionError(f"Unknown format: {format}")
    
    # Yield logs
    yield from source.ingest()
