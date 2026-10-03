"""
Master Test Runner for TI AWR1843 Door Sensor Project
======================================================
Discovers and executes all unit tests across the codebase.
"""

import unittest
import sys
import os

if __name__ == "__main__":
    test_dir = os.path.dirname(os.path.abspath(__file__))
    print("\n========================================================")
    print("  TI AWR1843 Door Sensor - Automated Test Suite")
    print("========================================================\n")

    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=test_dir, pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    sys.exit(0 if result.wasSuccessful() else 1)
