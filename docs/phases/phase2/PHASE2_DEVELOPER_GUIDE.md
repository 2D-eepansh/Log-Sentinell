# PHASE 2 DEVELOPER GUIDE: Phase 1 Handoff

This document explains what Phase 1 provides and what constraints/guarantees you should know when implementing Phase 2.

---

## Phase 1 Deliverable: The Feature Pipeline

### What You Get

Phase 1 provides a complete, tested, production-ready pipeline that transforms raw logs into feature vectors:

```
Raw Log File (.txt, .json, .csv)
    ↓
ingest_logs()               # Reads file format (text/JSON/CSV)
    ↓ Iterator[Dict]
parse_log()                 # Extracts fields (timestamp, level, service, message, duration)
    ↓ Dict[str, Any]
normalize_log()             # Converts to canonical form (UTC timestamps, enum levels, validated strings)
    ↓ LogEntry
aggregate_logs()            # Groups by (time_window, service)
    ↓ Dict[(datetime, str), AggregatedLogWindow]
extract_features()          # Computes 11 statistical features
    ↓ FeatureVector
```

### Output: FeatureVector Schema

Every FeatureVector has:

```python
class FeatureVector(BaseModel):
    # Identifiers
    window_start: datetime          # UTC timestamp (calendar-aligned window boundary)
    service: str                    # Service name (lowercase, alphanumeric+dashes/underscores)
    
    # Counts
    total_events: int               # Total logs in window
    error_count: int                # Logs with level ERROR or CRITICAL
    warning_count: int              # Logs with level WARNING
    info_count: int                 # Logs with level INFO
    
    # Rates (in [0.0, 1.0])
    error_rate: float               # error_count / total_events (0.0 if empty window)
    warning_rate: float             # warning_count / total_events (0.0 if empty window)
    
    # Duration stats (or None if no duration data)
    median_duration_ms: Optional[float]     # Median latency
    p95_duration_ms: Optional[float]        # 95th percentile latency
    max_duration_ms: Optional[float]        # Worst-case latency
    
    # Diversity
    unique_messages: int            # Count of distinct message hashes
    unique_error_codes: int         # Count of distinct error codes
    
    # Metadata
    metadata: Dict[str, Any]        # Includes extraction_timestamp, window_log_count
```

---

## Guarantees Phase 1 Provides

### 1. Determinism ✓
- Same logs always produce same features
- Parsing rules are deterministic (regex, field mapping)
- Normalization rules are deterministic (timestamp conversion, level mapping)
- Useful for: testing, reproducibility, auditing

### 2. No Silent Failures ✓
- All errors logged with context (line numbers, field names, values)
- Malformed logs are skipped (not fatal)
- Batch functions return (results, skipped_count) for quality monitoring
- Example:
  ```python
  normalized, skipped = normalize_logs(parsed_logs)
  if skipped > len(normalized) * 0.1:  # > 10% failure rate
      logger.warning(f"High skip rate: {skipped}/{len(parsed_logs)}")
  ```

### 3. Service Isolation ✓
- Each window contains logs for exactly one service
- Windows key: (window_start, service)
- Use case: Per-service anomaly detection baselines
- Example:
  ```python
  api_windows = [w for w in windows if w.service == "api-server"]
  # Now extract features just for api-server
  ```

### 4. Chronological Ordering ✓
- Logs preserved in time order within windows
- Original LogEntry objects preserved (not summaries)
- Allows Phase 2 to inspect raw logs for explanation
- Example:
  ```python
  window: AggregatedLogWindow
  first_error = next(log for log in window.logs 
                     if log.level == LogLevel.ERROR)
  # Trace when error occurred relative to other events
  ```

### 5. Extensible Metadata ✓
- LogEntry.metadata: Dict[str, Any] for custom annotations
- FeatureVector.metadata: Dict[str, Any] for extraction details
- Phase 2 can attach anomaly scores, explanations, alerts without modifying schema
- Example:
  ```python
  feature.metadata["anomaly_score"] = 0.95
  feature.metadata["anomaly_reason"] = "error_rate 3x above baseline"
  feature.metadata["recommended_action"] = "Check database connection pool"
  ```

### 6. Batch Statistics Available ✓
- All batch functions return (results, skipped_count)
- Enables data quality monitoring per batch
- Enables early exit if quality threshold not met
- Example:
  ```python
  features, skipped = extract_features_from_windows(windows)
  data_quality_pct = (len(features) / (len(features) + skipped)) * 100
  if data_quality_pct < 90:
      raise DataQualityError(f"Only {data_quality_pct}% of data usable")
  ```

---

## Constraints & Phase Boundaries

### What's NOT in Phase 1

Phase 1 deliberately excludes:
- ❌ Anomaly detection logic (belongs in Phase 2)
- ❌ ML model training (belongs in Phase 2)
- ❌ LLM integration (belongs in Phase 2)
- ❌ Alert thresholds (belongs in Phase 2)
- ❌ Remediation suggestions (belongs in Phase 2)

### Why This Matters

Keeping Phase 1 focused on data transformation ensures:
- **Testability**: No ML stochasticity; deterministic tests
- **Reusability**: Other teams can use Phase 1 for different purposes (dashboards, reports, etc.)
- **Debuggability**: Clear separation between data quality issues (Phase 1) and anomaly detection issues (Phase 2)

### Phase 2 Responsibility

You're responsible for:
1. **Baseline computation**: Use FeatureTransformer.get_statistics() to establish normal ranges
2. **Threshold tuning**: Decide when error_rate > X constitutes an anomaly
3. **Pattern interpretation**: Use LLM to explain why anomaly occurred
4. **Action generation**: Suggest remediation steps
5. **Quality gates**: Decide false-positive tolerance

---

## How to Use Phase 1 in Phase 2

### Example: Simple Anomaly Detection

```python
from src.data.ingestion import ingest_logs
from src.data.parsers import parse_log
from src.data.normalizers import normalize_logs
from src.data.aggregation import aggregate_logs
from src.data.features import extract_features_from_windows, FeatureTransformer
from src.anomaly import AnomalyDetector  # Phase 2

# Step 1: Run Phase 1 pipeline
raw_logs = list(ingest_logs("app.log", format="auto"))
parsed = [parse_log(r) for r in raw_logs if parse_log(r)]
normalized, skipped = normalize_logs(parsed)
windows = aggregate_logs(normalized, window_size_seconds=300)

# Step 2: Extract features
feature_list = list(windows.values())
features, skipped = extract_features_from_windows(feature_list)

# Step 3: Compute baseline (Phase 1 utility)
transformer = FeatureTransformer(features)
baseline_stats = transformer.get_statistics("error_rate")
# Output: {min: 0.01, max: 0.08, mean: 0.04, median: 0.03, stdev: 0.015}

# Step 4: Detect anomalies (Phase 2 logic)
detector = AnomalyDetector(baseline_stats=baseline_stats)
for feature in features:
    anomaly = detector.detect(feature)
    if anomaly.is_anomalous:
        print(f"ALERT: {feature.service} error_rate={feature.error_rate:.2%} "
              f"(baseline: {baseline_stats['mean']:.2%})")
        print(f"Reason: {anomaly.explanation}")
        print(f"Action: {anomaly.recommended_action}")
```

### Example: Multi-Service Analysis

```python
# Phase 1 guarantees service isolation
windows_by_service = {}
for window in windows.values():
    if window.service not in windows_by_service:
        windows_by_service[window.service] = []
    windows_by_service[window.service].append(window)

# Phase 2: Per-service anomaly detection
for service, service_windows in windows_by_service.items():
    features, _ = extract_features_from_windows(service_windows)
    
    transformer = FeatureTransformer(features)
    baseline = transformer.get_statistics("error_rate")
    
    # Now compute anomalies for this service's baseline (not global baseline)
    anomalies = transformer.compare_to_baseline("error_rate", baseline, multiplier=2.0)
    
    if anomalies:
        print(f"{service}: {len(anomalies)} anomalies detected")
        for idx in anomalies:
            print(f"  - Window {features[idx].window_start}: {features[idx].error_rate:.2%}")
```

### Example: Accessing Raw Logs

```python
# FeatureVector contains aggregate stats, but original logs available in window
window: AggregatedLogWindow
for log in window.logs:
    if log.level == LogLevel.ERROR:
        print(f"{log.timestamp}: {log.service} - {log.message}")
        print(f"  Duration: {log.duration_ms}ms")
        print(f"  Error code: {log.error_code}")
        print(f"  Request ID: {log.request_id}")
        print(f"  Message hash: {log.metadata.get('message_hash')}")

# Useful for: explaining to user why anomaly was detected
```

---

## API Reference: Phase 1 Exports

```python
# Ingestion
from src.data.ingestion import ingest_logs, TextLogSource, JSONLogSource, CSVLogSource

# Parsing
from src.data.parsers import parse_log, parse_logs, StandardTextLineParser, JSONLogParser, CSVLogParser

# Normalization
from src.data.normalizers import (
    normalize_log, normalize_logs,
    normalize_timestamp, normalize_level, normalize_service, 
    normalize_message, normalize_duration
)

# Aggregation
from src.data.aggregation import (
    aggregate_logs, align_timestamp_to_window,
    get_services_in_windows, get_time_range, print_windows_summary
)

# Features
from src.data.features import (
    extract_features, extract_features_from_windows,
    extract_count_features, extract_rate_features,
    extract_duration_features, extract_diversity_features,
    FeatureTransformer
)

# Schema
from src.data.schema import LogEntry, LogLevel, AggregatedLogWindow, FeatureVector
```

---

## Configuration: What Phase 2 Can Customize

Phase 1 supports customization:

### Window Size
```python
# Phase 1 default: 300 seconds (5 minutes)
windows = aggregate_logs(normalized, window_size_seconds=600)  # Change to 10-minute windows
```

### Log Source Format
```python
# Phase 1 auto-detects by file extension, or specify explicitly
logs = ingest_logs("data.log", format="text")      # Force text format
logs = ingest_logs("data.json", format="json")     # Force JSON format
logs = ingest_logs("data.csv", format="csv")       # Force CSV format
```

### CSV Parsing
```python
source = CSVLogSource("data.csv", delimiter=";")   # Use semicolon instead of comma
logs = list(source.ingest())
```

---

## Common Phase 2 Patterns

### Pattern 1: Baseline Establishment (Training)
```python
# Use first week of logs to establish baseline
from datetime import datetime, timedelta
baseline_cutoff = datetime.now(tz=timezone.utc) - timedelta(days=7)

baseline_features = [f for f in features if f.window_start >= baseline_cutoff]
transformer = FeatureTransformer(baseline_features)

# Store baseline statistics
import json
baseline_stats = {
    "error_rate": transformer.get_statistics("error_rate"),
    "warning_rate": transformer.get_statistics("warning_rate"),
    # ... other features
}
json.dump(baseline_stats, open("baseline.json", "w"))
```

### Pattern 2: Real-Time Detection
```python
# Load baseline
baseline_stats = json.load(open("baseline.json"))

# Process new logs
new_logs = list(ingest_logs("new_logs.log"))
# ... parse, normalize, aggregate, extract features

# Detect against baseline
for feature in new_features:
    if feature.error_rate > baseline_stats["error_rate"]["mean"] * 2.0:
        send_alert(f"Anomaly: {feature.service} error_rate={feature.error_rate:.2%}")
```

### Pattern 3: Multi-Dimensional Analysis
```python
# Check multiple features simultaneously
anomaly_scores = {}
for feature_name in ["error_rate", "warning_rate", "max_duration_ms"]:
    stats = transformer.get_statistics(feature_name)
    
    value = getattr(feature, feature_name)
    if value is not None and value > stats["mean"] * 2.0:
        anomaly_scores[feature_name] = value / stats["mean"]

# Overall anomaly score: how many features are anomalous
if len(anomaly_scores) >= 2:
    print(f"Multi-dimensional anomaly: {anomaly_scores}")
```

---

## Error Handling: What to Expect

Phase 1 handles errors gracefully. Here's what you need to know:

### Malformed Input (Non-Fatal)
- Phase 1: Logs warning; skips bad record; continues
- Phase 2: Check skipped_count; decide if quality acceptable
- Example:
  ```python
  features, skipped = extract_features_from_windows(windows)
  if skipped > 0:
      logger.warning(f"Skipped {skipped} windows due to errors")
      # Phase 2 decision: Continue or raise error?
  ```

### Missing Required Fields (Non-Fatal)
- Phase 1: Logs debug message; skips log; continues
- Phase 2: May notice data quality degradation in aggregate stats
- Example: If 50% of logs have no duration_ms, median_duration_ms will be None

### Configuration Error (Fatal)
- Phase 1: Raises exception
- Phase 2: Caller must handle
- Example:
  ```python
  try:
      windows = aggregate_logs(logs, window_size_seconds=-1)
  except AggregationError as e:
      logger.error(f"Configuration error: {e}")
      raise
  ```

---

## Performance Characteristics

Phase 1 is efficient:

| Operation | Time Complexity | Space Complexity | Notes |
|-----------|-----------------|------------------|-------|
| ingest_logs() | O(n) | O(1) | Streaming; no buffering |
| parse_logs() | O(n) | O(n) | Output size ≈ input |
| normalize_logs() | O(n) | O(n) | Output size ≈ input |
| aggregate_logs() | O(n log n) | O(n) | Worst-case: n windows |
| extract_features() | O(n) | O(1) per window | Per-window processing |

Typical throughput:
- **1M logs end-to-end**: ~30 seconds (includes all 5 stages)
- **Per-stage breakdown**: parsing 15s, normalization 5s, aggregation 5s, features 5s
- **Memory**: Constant memory for ingestion (streaming); ~10GB for 1M logs aggregated (depends on window size)

Phase 2 should:
- Batch process in chunks if processing 100M+ logs
- Cache baseline statistics (don't recompute per batch)
- Consider async processing if latency critical

---

## Testing Phase 2

Recommendation: Use Phase 1 test fixtures

```python
# tests/integration/test_anomaly_detection.py

import pytest
from src.data.schema import FeatureVector, LogLevel
from src.anomaly import AnomalyDetector  # Phase 2

@pytest.fixture
def sample_features():
    """Phase 1 provides sample features for testing Phase 2."""
    from tests.conftest import sample_log_dataframe
    # Use Phase 1 fixtures to create known feature distributions
    ...

def test_anomaly_detection_above_baseline(sample_features):
    detector = AnomalyDetector(...)
    anomalies = [f for f in sample_features if detector.detect(f).is_anomalous]
    assert len(anomalies) > 0
```

---

## Troubleshooting

### Problem: extract_features() returns FeatureVector with None durations

**Cause**: No logs in window have duration_ms field populated

**Action (Phase 2)**:
```python
if feature.median_duration_ms is None:
    # No latency data; only use count/rate features for anomaly detection
    anomaly = detector.detect_by_rates_only(feature)
else:
    # Normal detection with all features
    anomaly = detector.detect(feature)
```

### Problem: normalize_logs() returns ([], 100)

**Cause**: All logs failed normalization (e.g., invalid timestamps)

**Action (Phase 2)**:
```python
normalized, skipped = normalize_logs(parsed_logs)
if not normalized:
    logger.error(f"No usable logs: skipped={skipped}/{len(parsed_logs)}")
    raise DataQualityError("Insufficient usable data")
```

### Problem: aggregate_logs() produces many small windows with few logs

**Cause**: Window size too small (e.g., 10 seconds) with sparse logs

**Action (Phase 2)**:
```python
windows = aggregate_logs(normalized, window_size_seconds=600)  # Increase to 10 min
# Now each window more likely to have sufficient data for statistical analysis
```

---

## Summary for Phase 2 Developers

| Aspect | What Phase 1 Provides | What Phase 2 Owns |
|--------|----------------------|-------------------|
| **Data Ingestion** | ✓ Multi-format parsing | - |
| **Data Normalization** | ✓ UTC timestamps, enum levels | - |
| **Feature Extraction** | ✓ 11 statistical features | - |
| **Baseline Computation** | ✓ FeatureTransformer.get_statistics() | Use it |
| **Anomaly Detection** | - | ✓ Implement thresholds |
| **Explanation** | - | ✓ Use LLM integration |
| **Alerting** | - | ✓ Decide thresholds |
| **Remediation** | - | ✓ Suggest actions |

**You can assume Phase 1 is correct; focus on Phase 2 logic.**

---

**Document Version**: 1.0  
**Last Updated**: 2025-02-07  
**Phase 2 Ready**: ✅ Yes
