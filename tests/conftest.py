"""
Pytest configuration and shared fixtures.

Provides test configuration instances and sample data for unit and integration tests.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd

from src.core.config import Config


@pytest.fixture
def mock_config():
    """
    Fixture providing test configuration with minimal values.
    
    Used to override environment-based config in unit tests.
    Ensures tests run consistently regardless of .env settings.
    
    Returns:
        Config: Test instance with sensible defaults for testing
    """
    # Create test config with explicit values (not from .env)
    test_config = Config(
        app_name="Test Anomaly Copilot",
        environment="test",
        debug=True,
        device="cpu",  # Always CPU for testing
        dtype="float32",  # Use float32 for test stability
        model_name="gpt2",  # Small model for fast tests (not Mistral)
        max_tokens=128,  # Reduced for testing
        lora_enabled=False,  # Disable LoRA in tests
        anomaly_threshold=0.75,
        lookback_window=60,
        log_level="WARNING",  # Reduce noise in test output
    )
    return test_config


@pytest.fixture
def sample_log_data() -> List[Dict[str, Any]]:
    """
    Fixture providing realistic sample log data for testing.
    
    Generates synthetic log entries with timestamps, severity levels,
    and message patterns typical of production logs.
    
    Returns:
        List[Dict]: List of log dictionaries with keys:
            - timestamp: ISO format datetime
            - level: Log level (INFO, WARNING, ERROR, DEBUG)
            - message: Log message text
            - service: Service/component name
            - request_id: Correlation ID
            - duration_ms: Request duration
    """
    base_time = datetime.utcnow()
    logs = []
    
    # Generate 100 sample logs over the past hour
    for i in range(100):
        # Create realistic timestamps
        timestamp = base_time - timedelta(seconds=i * 36)
        
        # Normal logs (70%)
        if i % 10 != 0:
            level = "INFO"
            duration = 50 + (i % 50)  # 50-100ms
            message = f"Request processed successfully"
            service = "api-server" if i % 2 == 0 else "auth-service"
        # Warning logs (20%)
        elif i % 10 == 0 and i % 20 != 0:
            level = "WARNING"
            duration = 150 + (i % 100)  # 150-250ms
            message = f"Request took longer than expected"
            service = "database" if i % 2 == 0 else "cache-layer"
        # Error logs (10%)
        else:
            level = "ERROR"
            duration = 500 + (i % 200)  # 500-700ms
            message = f"Request failed with status 500"
            service = "api-server"
        
        logs.append({
            "timestamp": timestamp.isoformat(),
            "level": level,
            "message": message,
            "service": service,
            "request_id": f"req-{i:06d}",
            "duration_ms": duration,
        })
    
    return logs


@pytest.fixture
def sample_log_dataframe(sample_log_data) -> pd.DataFrame:
    """
    Fixture providing sample log data as a pandas DataFrame.
    
    Convenience fixture for tests that prefer DataFrame format.
    Automatically converts sample_log_data to DataFrame.
    
    Returns:
        pd.DataFrame: Log data with parsed datetime index
    """
    df = pd.DataFrame(sample_log_data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.set_index("timestamp", inplace=True)
    return df


def pytest_configure(config):
    """
    Pytest hook for custom configuration.
    
    Registers custom markers used throughout tests.
    """
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running (deferred CI)"
    )
