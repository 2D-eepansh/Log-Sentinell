"""
Integration test for the full log processing pipeline.

Tests end-to-end flow from raw logs to feature vectors.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta

from src.data.ingestion import ingest_logs
from src.data.parsers import parse_log
from src.data.normalizers import normalize_log
from src.data.aggregation import aggregate_logs
from src.data.features import extract_features_from_windows


class TestFullPipeline:
    """Test end-to-end pipeline from raw logs to features."""
    
    def test_pipeline_text_logs_to_features(self):
        """Test full pipeline with text-format logs."""
        # Create temporary log file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write("2025-02-07T10:30:00Z INFO api-server User login successful\n")
            f.write("2025-02-07T10:30:15Z INFO api-server Request processed (150ms)\n")
            f.write("2025-02-07T10:30:30Z WARNING api-server Response time high (800ms)\n")
            f.write("2025-02-07T10:30:45Z ERROR database Connection timeout (5000ms)\n")
            temp_file = f.name
        
        try:
            # Step 1: Ingest
            raw_logs = list(ingest_logs(temp_file, format="text"))
            assert len(raw_logs) == 4
            
            # Step 2: Parse
            parsed_logs = []
            for raw_log in raw_logs:
                parsed = parse_log(raw_log)
                if parsed:
                    parsed_logs.append(parsed)
            assert len(parsed_logs) == 4
            
            # Step 3: Normalize
            from src.data.normalizers import normalize_logs
            normalized_logs, skipped = normalize_logs(parsed_logs)
            assert len(normalized_logs) == 4
            assert skipped == 0
            
            # Step 4: Aggregate
            windows = aggregate_logs(normalized_logs, window_size_seconds=300)
            assert len(windows) > 0  # Should have at least one window
            
            # Step 5: Extract features
            windows_list = list(windows.values())
            features, skipped_features = extract_features_from_windows(windows_list)
            assert len(features) > 0
            assert skipped_features == 0
            
            # Verify features
            feature = features[0]
            assert feature.total_events > 0
            assert feature.error_count >= 0
            assert feature.error_rate >= 0.0 and feature.error_rate <= 1.0
        
        finally:
            # Clean up
            Path(temp_file).unlink()
    
    def test_pipeline_json_logs_to_features(self):
        """Test full pipeline with JSON-format logs."""
        import json
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            logs = [
                {
                    "timestamp": "2025-02-07T10:30:00Z",
                    "level": "INFO",
                    "service": "auth-service",
                    "message": "User authenticated",
                    "duration_ms": 50
                },
                {
                    "timestamp": "2025-02-07T10:30:15Z",
                    "level": "ERROR",
                    "service": "auth-service",
                    "message": "Invalid credentials",
                    "error_code": "AUTH001"
                },
                {
                    "timestamp": "2025-02-07T10:30:30Z",
                    "level": "INFO",
                    "service": "database",
                    "message": "Query executed",
                    "duration_ms": 200
                },
            ]
            json.dump(logs, f)
            temp_file = f.name
        
        try:
            # Full pipeline
            raw_logs = list(ingest_logs(temp_file, format="json"))
            assert len(raw_logs) == 3
            
            parsed_logs = [parse_log(raw) for raw in raw_logs]
            parsed_logs = [p for p in parsed_logs if p is not None]
            assert len(parsed_logs) == 3
            
            from src.data.normalizers import normalize_logs
            normalized_logs, _ = normalize_logs(parsed_logs)
            assert len(normalized_logs) == 3
            
            windows = aggregate_logs(normalized_logs, window_size_seconds=300)
            windows_list = list(windows.values())
            features, _ = extract_features_from_windows(windows_list)
            
            assert len(features) > 0
            # Should have features for both services
            services = {f.service for f in features}
            assert "auth-service" in services or "database" in services
        
        finally:
            Path(temp_file).unlink()
    
    def test_pipeline_csv_logs_to_features(self):
        """Test full pipeline with CSV-format logs."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("timestamp,level,service,message,duration_ms\n")
            f.write("2025-02-07T10:30:00Z,INFO,cache-layer,Cache hit,25\n")
            f.write("2025-02-07T10:30:15Z,WARNING,cache-layer,Cache miss,1500\n")
            f.write("2025-02-07T10:30:30Z,ERROR,cache-layer,Cache flush failed,3000\n")
            temp_file = f.name
        
        try:
            raw_logs = list(ingest_logs(temp_file, format="csv"))
            assert len(raw_logs) == 3
            
            parsed_logs = [parse_log(raw) for raw in raw_logs]
            parsed_logs = [p for p in parsed_logs if p is not None]
            assert len(parsed_logs) == 3
            
            from src.data.normalizers import normalize_logs
            normalized_logs, _ = normalize_logs(parsed_logs)
            assert len(normalized_logs) == 3
            
            windows = aggregate_logs(normalized_logs, window_size_seconds=300)
            windows_list = list(windows.values())
            features, _ = extract_features_from_windows(windows_list)
            
            assert len(features) > 0
            assert features[0].service == "cache-layer"
            assert features[0].error_count > 0
        
        finally:
            Path(temp_file).unlink()
    
    def test_pipeline_handles_malformed_logs(self):
        """Test that pipeline handles bad logs gracefully."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write("2025-02-07T10:30:00Z INFO api-server Valid log\n")
            f.write("This is completely malformed\n")
            f.write("2025-02-07T10:30:15Z INFO api-server Another valid log\n")
            f.write("\n")  # Empty line
            temp_file = f.name
        
        try:
            raw_logs = list(ingest_logs(temp_file, format="text"))
            assert len(raw_logs) == 3  # Empty line skipped during ingestion
            
            parsed_logs = []
            for raw_log in raw_logs:
                parsed = parse_log(raw_log)
                if parsed:
                    parsed_logs.append(parsed)
            
            # Should have 2 valid logs (malformed skipped)
            assert len(parsed_logs) == 2
            
            from src.data.normalizers import normalize_logs
            normalized_logs, skipped = normalize_logs(parsed_logs)
            assert len(normalized_logs) == 2
            assert skipped == 0
            
            # Rest of pipeline should work
            windows = aggregate_logs(normalized_logs, window_size_seconds=300)
            assert len(windows) > 0
        
        finally:
            Path(temp_file).unlink()
    
    def test_pipeline_multiple_services_multiple_windows(self):
        """Test pipeline with multiple services and windows."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            base_time = datetime(2025, 2, 7, 10, 30, 0, tzinfo=timezone.utc)
            
            # Generate logs across 15 minutes from two services
            for minute in range(0, 15, 5):  # 0, 5, 10 minutes
                for service in ["api-server", "database"]:
                    for i in range(10):
                        ts = base_time + timedelta(minutes=minute, seconds=i*30)
                        level = "INFO" if i < 8 else "ERROR"
                        duration = 100 if level == "INFO" else 2000
                        f.write(
                            f"{ts.isoformat().replace('+00:00', 'Z')} {level} {service} "
                            f"Event {i} ({duration}ms)\n"
                        )
            temp_file = f.name
        
        try:
            # Full pipeline
            raw_logs = list(ingest_logs(temp_file, format="text"))
            assert len(raw_logs) == 60  # 3 time points * 2 services * 10 logs
            
            parsed_logs = [parse_log(raw) for raw in raw_logs]
            parsed_logs = [p for p in parsed_logs if p is not None]
            assert len(parsed_logs) == 60
            
            from src.data.normalizers import normalize_logs
            normalized_logs, _ = normalize_logs(parsed_logs)
            assert len(normalized_logs) == 60
            
            windows = aggregate_logs(normalized_logs, window_size_seconds=300)
            # Should have 3 windows * 2 services = 6 windows (potentially fewer if different times)
            assert len(windows) >= 2
            
            windows_list = list(windows.values())
            features, _ = extract_features_from_windows(windows_list)
            assert len(features) >= 2
            
            # Verify features are computed
            for feature in features:
                assert feature.total_events > 0
                assert 0 <= feature.error_rate <= 1.0
                assert 0 <= feature.warning_rate <= 1.0
        
        finally:
            Path(temp_file).unlink()


class TestPipelineEdgeCases:
    """Test edge cases in the pipeline."""
    
    def test_pipeline_empty_file(self):
        """Test pipeline with empty log file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            temp_file = f.name
        
        try:
            raw_logs = list(ingest_logs(temp_file, format="text"))
            assert len(raw_logs) == 0
        
        finally:
            Path(temp_file).unlink()
    
    def test_pipeline_single_log(self):
        """Test pipeline with single log entry."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write("2025-02-07T10:30:00Z INFO api-server Single log entry\n")
            temp_file = f.name
        
        try:
            raw_logs = list(ingest_logs(temp_file, format="text"))
            assert len(raw_logs) == 1
            
            parsed = parse_log(raw_logs[0])
            assert parsed is not None
            
            from src.data.normalizers import normalize_log
            normalized = normalize_log(parsed)
            assert normalized is not None
            
            windows = aggregate_logs([normalized], window_size_seconds=300)
            assert len(windows) == 1
            
            windows_list = list(windows.values())
            features, _ = extract_features_from_windows(windows_list)
            assert len(features) == 1
            assert features[0].total_events == 1
        
        finally:
            Path(temp_file).unlink()
