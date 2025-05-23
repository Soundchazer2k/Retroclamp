"""
Automated Plugin Test Discovery and Runner for RetroClamp Tools
--------------------------------------------------------------
Discovers and runs all plugin test files in the tools/ directory that match
the pattern test_*.py. This script can be run to execute all plugin tests at once.
"""

import os
import sys
import unittest

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    # Add tools directory to sys.path for imports
    sys.path.insert(0, TOOLS_DIR)
    # Discover all test_*.py files in the tools directory
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=TOOLS_DIR, pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    # Exit with appropriate code for CI integration
    sys.exit(not result.wasSuccessful())
