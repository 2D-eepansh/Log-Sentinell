#!/usr/bin/env python
"""
Quick reference: Running Phase 1 tests.

Execute this file or use the commands below directly.
"""

import subprocess
import sys


def run_tests():
    """Run all Phase 1 tests."""
    
    print("=" * 70)
    print("RUNNING PHASE 1 TEST SUITE")
    print("=" * 70)
    print()
    
    commands = [
        ("Unit Tests - Schema", "pytest tests/unit/test_schema.py -v"),
        ("Unit Tests - Parsers", "pytest tests/unit/test_parsers.py -v"),
        ("Unit Tests - Normalizers", "pytest tests/unit/test_normalizers.py -v"),
        ("Unit Tests - Aggregation", "pytest tests/unit/test_aggregation.py -v"),
        ("Unit Tests - Features", "pytest tests/unit/test_features.py -v"),
        ("Integration Tests - Pipeline", "pytest tests/integration/test_data_pipeline.py -v"),
        ("All Tests with Coverage", "pytest tests/ -v --cov=src/data --cov-report=html"),
    ]
    
    for name, cmd in commands:
        print(f"\n{'='*70}")
        print(f"{name}")
        print(f"{'='*70}")
        print(f"Command: {cmd}\n")
        result = subprocess.run(cmd, shell=True)
        if result.returncode != 0:
            print(f"❌ {name} failed")
        else:
            print(f"✓ {name} passed")


def run_specific_tests():
    """Run specific test groups."""
    
    print("\nQuick test commands:")
    print("  pytest tests/unit/ -v          # All unit tests")
    print("  pytest tests/integration/ -v   # All integration tests")
    print("  pytest tests/ -v               # All tests")
    print("  pytest tests/ -v -k schema     # Tests matching 'schema'")
    print("  pytest tests/ -v --tb=short    # Short traceback format")
    print("  pytest tests/ --co             # List test collection (no run)")


if __name__ == "__main__":
    run_tests()
    run_specific_tests()
