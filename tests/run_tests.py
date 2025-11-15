#!/usr/bin/env python3
"""
Consolidated test runner for SNES-IDE.

This script runs all consolidated tests and provides summary reporting.
Replaces the need for multiple separate test files.
"""

import unittest
import sys
import logging
from pathlib import Path
from typing import List

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


def discover_tests() -> unittest.TestSuite:
    """Discover and load all test cases."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Load consolidated test modules
    test_modules = [
        'test_core_utilities',
        'test_script_integration'
    ]
    
    for module_name in test_modules:
        try:
            module_suite = loader.loadTestsFromName(module_name)
            suite.addTest(module_suite)
            print(f"Loaded tests from {module_name}")
        except ImportError as e:
            print(f"Warning: Could not load {module_name}: {e}")
    
    return suite


def run_tests(verbosity: int = 2) -> unittest.TestResult:
    """Run all tests with specified verbosity."""
    suite = discover_tests()
    runner = unittest.TextTestRunner(
        verbosity=verbosity,
        stream=sys.stdout,
        buffer=True
    )
    
    print(f"\nRunning consolidated SNES-IDE test suite...")
    print(f"Test count: {suite.countTestCases()}")
    print("-" * 60)
    
    result = runner.run(suite)
    
    print("-" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / 
                   result.testsRun * 100) if result.testsRun > 0 else 0
    print(f"Success rate: {success_rate:.1f}%")
    
    return result


def main():
    """Main test runner entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="SNES-IDE Consolidated Test Runner")
    parser.add_argument(
        '-v', '--verbosity', 
        type=int, 
        choices=[0, 1, 2], 
        default=2,
        help='Test output verbosity (0=quiet, 1=normal, 2=verbose)'
    )
    parser.add_argument(
        '--list', 
        action='store_true',
        help='List available tests without running them'
    )
    
    args = parser.parse_args()
    
    if args.list:
        suite = discover_tests()
        print(f"Available tests ({suite.countTestCases()} total):")
        for test in suite:
            for subtest in test:
                print(f"  {subtest}")
        return
    
    result = run_tests(args.verbosity)
    
    # Exit with error code if tests failed
    if result.failures or result.errors:
        sys.exit(1)
    else:
        print("\nAll tests passed successfully!")
        sys.exit(0)


if __name__ == '__main__':
    main()