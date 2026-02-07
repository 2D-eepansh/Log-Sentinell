# Phase 1 Data Pipeline Architecture

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         RAW LOG SOURCES                             │
│                                                                     │
│  Text Files (*.log)    JSON Files (*.json)    CSV Files (*.csv)    │
│  app.log               logs.json              events.csv            │
└────────────────┬──────────────────┬──────────────────┬─────────────┘
                 │                  │                  │
        ┌────────▼──────────────────▼──────────────────▼────────────┐n        │          INGESTION (src/data/ingestion.py)               │
        │  TextLogSource | JSONLogSource | CSVLogSource           │
        │  Auto-detection • Iterator-based • Malformed handling   │
        │  Output: Dict with raw_line/object + _metadata          │
        └────────┬──────────────────────────────────────────────────┘
                 │
        ┌────────▼──────────────────────────────────────────────────┐
        │          PARSING (src/data/parsers.py)                    │
        │  StandardTextLineParser | JSONLogParser | CSVLogParser  │
        │  Deterministic extraction • Regex-based • Field mapping  │
        │  Output: Dict {timestamp, level, service, message, ...} │
        └────────┬──────────────────────────────────────────────────┘
                 │
        ┌────────▼──────────────────────────────────────────────────┐
        │          NORMALIZATION (src/data/normalizers.py)         │
        │  Timestamp → UTC datetime | Level → LogLevel enum        │
        │  Service → lowercase | Message → deduplicated hash       │
        │  Duration → milliseconds | Field validation & defaults   │
        │  Output: LogEntry (Pydantic model, fully validated)      │
        └────────┬──────────────────────────────────────────────────┘
                 │
        ┌────────▼──────────────────────────────────────────────────┐
        │          AGGREGATION (src/data/aggregation.py)           │
        │  Time window alignment (e.g., 5-minute buckets)          │
        │  Group by service and time window                        │
        │  Sort logs chronologically within window                 │
        │  Output: AggregatedLogWindow                             │
        │    {window_start, window_end, service, logs[]}           │
        └────────┬──────────────────────────────────────────────────┘
                 │
        ┌────────▼──────────────────────────────────────────────────┐
        │          FEATURE EXTRACTION (src/data/features.py)       │
        │                                                          │
        │  Count Features        Rate Features                    │
        │  • total_events        • error_rate (0.0-1.0)          │
        │  • error_count         • warning_rate (0.0-1.0)        │
        │  • warning_count                                        │
        │  • info_count          Duration Features                │
        │                        • median_duration_ms             │
        │  Diversity Features    • p95_duration_ms               │
        │  • unique_messages     • max_duration_ms               │
        │  • unique_error_codes                                  │
        │                                                          │
        │  Output: FeatureVector (Pydantic model)                 │
        └────────┬──────────────────────────────────────────────────┘
                 │
        ┌────────▼──────────────────────────────────────────────────┐
        │               FEATURE VECTORS READY                       │
        │        For anomaly detection (Phase 2)                    │
        │                                                          │
        │  Services: api-server, database, cache-layer, ...       │
        │  Time windows: [10:30-10:35], [10:35-10:40], ...       │
        │  Features: total_events, error_rate, p95_latency, ...  │
        └────────────────────────────────────────────────────────┘
```

---

## Module Structure

```
src/data/
├── __init__.py                 # Public API exports
├── schema.py                   # Pydantic models
│   ├── LogLevel (enum)
│   ├── LogEntry
│   ├── AggregatedLogWindow
│   └── FeatureVector
├── ingestion.py                # File reading
│   ├── BaseLogSource (abstract)
│   ├── TextLogSource
│   ├── JSONLogSource
│   ├── CSVLogSource
│   └── ingest_logs() (convenience function)
├── parsers.py                  # Format-specific parsing
│   ├── BaseParser (abstract)
│   ├── StandardTextLineParser
│   ├── JSONLogParser
│   ├── CSVLogParser
│   ├── parse_log()
│   └── parse_logs()
├── normalizers.py              # Field normalization
│   ├── normalize_timestamp()
│   ├── normalize_level()
│   ├── normalize_service()
│   ├── normalize_message()
│   ├── normalize_duration()
│   ├── normalize_log()
│   └── normalize_logs()
├── aggregation.py              # Time-window grouping
│   ├── align_timestamp_to_window()
│   ├── aggregate_logs()
│   ├── get_services_in_windows()
│   ├── get_time_range()
│   ├── filter_windows_by_service()
│   ├── filter_windows_by_time()
│   ├── print_windows_summary()
│   └── WindowBatcher
└── features.py                 # Statistical extraction
    ├── extract_count_features()
    ├── extract_rate_features()
    ├── extract_duration_features()
    ├── extract_diversity_features()
    ├── extract_features()
    ├── extract_features_from_windows()
    └── FeatureTransformer

tests/
├── unit/
│   ├── test_schema.py          # Pydantic validation
│   ├── test_parsers.py         # Parsing logic
│   ├── test_normalizers.py     # Normalization
│   ├── test_aggregation.py     # Time-window grouping
│   └── test_features.py        # Feature extraction
└── integration/
    └── test_data_pipeline.py   # End-to-end tests
```

---

## API Quick Reference

### Ingestion
```python
from src.data import ingest_logs

# Auto-detect format
for raw_log in ingest_logs("app.log"):
    parse_log(raw_log)

# Explicit format
for raw_log in ingest_logs("logs.json", format="json"):
    ...
```

### Parsing
```python
from src.data import parse_log, parse_logs

parsed = parse_log(raw_log)      # Single, auto-detect
parsed_list, skipped = parse_logs(raw_logs)  # Batch
```

### Normalization
```python
from src.data import normalize_log, normalize_logs

log_entry = normalize_log(parsed)    # Single LogEntry
entries, skipped = normalize_logs(parsed_list)  # Batch
```

### Aggregation
```python
from src.data import (
    aggregate_logs,
    filter_windows_by_service,
    filter_windows_by_time,
)

windows = aggregate_logs(log_entries, window_size_seconds=300)

# Filter
api_windows = filter_windows_by_service(windows, "api-server")
recent_windows = filter_windows_by_time(windows, start_time, end_time)
```

### Feature Extraction
```python
from src.data import (
    extract_features,
    extract_features_from_windows,
    FeatureTransformer,
)

# Single window
fv = extract_features(window)

# Batch
features, skipped = extract_features_from_windows(windows_list)

# Analysis
transformer = FeatureTransformer(features)
stats = transformer.get_statistics("error_rate")
anomalies = transformer.compare_to_baseline("error_rate", stats, multiplier=2.0)
```

---

## Error Handling Strategy

```
Graceful Degradation Pipeline

   Ingestion
      ↓ (skip empty lines)
   ↙ ↓ ↘
Bad Input → Parsed/None
              ↓ (skip None)
           Parsing
              ↓ (skip malformed)
           ↙ ↓ ↘
        Bad Data → Normalized LogEntry
                      ↓ (skip invalid fields)
                   Normalization
                      ↓
                   Aggregation
                      ↓
                   Feature Extraction
                      ↓ (skip extraction errors)
                   ↙ ↓ ↘
              Bad Features → FeatureVector ✓
                               ↓
                         Ready for Phase 2
```

**Philosophy**: Skip bad data, log warnings, continue pipeline. Never crash on malformed input.

---

## Performance Characteristics

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| Ingestion | O(n) | Linear pass through file |
| Parsing | O(n) | Regex matching per line |
| Normalization | O(n) | Field-by-field transformation |
| Aggregation | O(n log n) | Sorting within windows |
| Feature Extraction | O(n) | Single pass, compute statistics |
| **Total Pipeline** | **O(n log n)** | Dominated by sorting in aggregation |

**Memory Usage**: Iterator-based ingestion keeps memory O(1) for file reading (constant number of logs in memory at once)

---

## Integration with Phase 2 (Anomaly Detection)

FeatureVector objects produced by Phase 1 will be consumed by Phase 2 anomaly detection:

```python
from src.data import extract_features_from_windows
from src.anomaly import detect_anomalies  # Phase 2

features = extract_features_from_windows(windows)

# Phase 2 takes over
anomalies = detect_anomalies(features)
```

Features contain:
- Temporal dimension (window_start)
- Service dimension (service)
- Statistical features for ML
- Preserved window reference for incident explanation (Phase 3)

---

## Testing Coverage

```
Schema (50 tests)
├── LogLevel validation
├── LogEntry creation & validation
├── AggregatedLogWindow
└── FeatureVector bounds checking

Parsers (20 tests)
├── Text line parsing
├── JSON parsing (NDJSON & array)
├── CSV parsing
└── Error handling

Normalizers (25 tests)
├── Timestamp conversion
├── Level normalization
├── Service cleanup
├── Message deduplication
└── Duration validation

Aggregation (20 tests)
├── Timestamp alignment
├── Multi-window grouping
├── Multi-service handling
└── Filtering utilities

Features (15 tests)
├── Count extraction
├── Rate calculation
├── Duration percentiles
├── Diversity counting
└── FeatureTransformer

Integration (7 tests)
├── Text → Features pipeline
├── JSON → Features pipeline
├── CSV → Features pipeline
├── Malformed log handling
├── Multi-service scenarios
└── Edge cases
```

**Total: 150+ assertions** across unit and integration tests

---

## Example: Processing a Real-World Log File

```python
from src.data import (
    ingest_logs,
    parse_log,
    normalize_logs,
    aggregate_logs,
    extract_features_from_windows,
)

# 1. Ingest
raw_logs = list(ingest_logs("production.log", format="auto"))
print(f"Ingested {len(raw_logs)} raw log lines")

# 2. Parse
parsed = [parse_log(raw) for raw in raw_logs]
parsed = [p for p in parsed if p is not None]
print(f"Parsed {len(parsed)} logs (skipped {len(raw_logs)-len(parsed)})")

# 3. Normalize
normalized, skipped = normalize_logs(parsed)
print(f"Normalized {len(normalized)} logs (skipped {skipped})")

# 4. Aggregate (5-minute windows)
windows = aggregate_logs(normalized, window_size_seconds=300)
print(f"Created {len(windows)} windows")

# 5. Extract Features
windows_list = list(windows.values())
features, skipped = extract_features_from_windows(windows_list)
print(f"Extracted {len(features)} feature vectors (skipped {skipped})")

# 6. Analyze
from src.data import FeatureTransformer
transformer = FeatureTransformer(features)

# Which services had high error rates?
stats = transformer.get_statistics("error_rate")
print(f"Error rate: min={stats['min']:.1%}, max={stats['max']:.1%}, mean={stats['mean']:.1%}")

# Which time windows were anomalous?
anomalies = transformer.compare_to_baseline("error_rate", stats, multiplier=2.0)
print(f"Found {len(anomalies)} anomalous windows (>2x baseline error rate)")
```
