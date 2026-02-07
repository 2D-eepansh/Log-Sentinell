"""
Custom exceptions for the Anomaly Detection Copilot.

These exceptions provide clear error semantics across the system.
Use them to distinguish between data issues, model problems, and configuration errors.
"""


class AnomalyDetectionError(Exception):
    """Base exception for anomaly detection failures."""
    pass


class ModelInferenceError(Exception):
    """Raised when LLM inference fails (model loading, generation, etc.)."""
    pass


class DataValidationError(Exception):
    """Raised when input data fails validation or ingestion."""
    pass


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass
