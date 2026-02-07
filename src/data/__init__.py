"""
Data module: Log ingestion, parsing, normalization, aggregation, and feature extraction.

Responsible for converting raw logs into clean, feature-extracted data suitable
for anomaly detection. Pipeline:

    Raw logs (text/JSON/CSV)
        ↓
    Ingestion (src/data/ingestion.py)
        ↓
    Parsing (src/data/parsers.py)
        ↓
    Normalization (src/data/normalizers.py) → LogEntry
        ↓
    Aggregation (src/data/aggregation.py) → AggregatedLogWindow
        ↓
    Feature Extraction (src/data/features.py) → FeatureVector
        ↓
    Ready for anomaly detection (Phase 2)
"""

from src.data.aggregation import (
    aggregate_logs,
    align_timestamp_to_window,
    filter_windows_by_service,
    filter_windows_by_time,
)
from src.data.features import (
    FeatureTransformer,
    extract_features,
    extract_features_from_windows,
)
from src.data.ingestion import (
    CSVLogSource,
    JSONLogSource,
    LogIngestionError,
    TextLogSource,
    ingest_logs,
)
from src.data.normalizers import (
    NormalizationError,
    normalize_log,
    normalize_logs,
)
from src.data.parsers import (
    CSVLogParser,
    JSONLogParser,
    ParsingError,
    StandardTextLineParser,
    parse_log,
    parse_logs,
)
from src.data.schema import (
    AggregatedLogWindow,
    FeatureVector,
    LogEntry,
    LogLevel,
)

__all__ = [
    # Schema
    "LogEntry",
    "LogLevel",
    "AggregatedLogWindow",
    "FeatureVector",
    
    # Ingestion
    "ingest_logs",
    "TextLogSource",
    "JSONLogSource",
    "CSVLogSource",
    "LogIngestionError",
    
    # Parsing
    "parse_log",
    "parse_logs",
    "StandardTextLineParser",
    "JSONLogParser",
    "CSVLogParser",
    "ParsingError",
    
    # Normalization
    "normalize_log",
    "normalize_logs",
    "NormalizationError",
    
    # Aggregation
    "aggregate_logs",
    "align_timestamp_to_window",
    "filter_windows_by_service",
    "filter_windows_by_time",
    
    # Features
    "extract_features",
    "extract_features_from_windows",
    "FeatureTransformer",
]
