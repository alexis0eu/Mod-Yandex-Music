#!/usr/bin/env python3
"""
Standalone E2E Test Runner for Yandex Music Mod.
Executes Tiers 1-4 covering Features 1-25.
Exit code: 0 on success, 1 on failure.

Usage:
    python tests/e2e/run_tests.py
    python tests/e2e/run_tests.py --tier=1
    python tests/e2e/run_tests.py --tier=2
    python tests/e2e/run_tests.py --tier=3
    python tests/e2e/run_tests.py --tier=4
    python tests/e2e/run_tests.py --verbose
"""

import os
import sys
import time
import unittest
import argparse
from typing import Dict, Any, List, Optional

# Ensure stdout uses utf-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Setup module resolution paths
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, "..", ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if THIS_DIR not in sys.path:
    sys.path.insert(0, THIS_DIR)


def load_test_suite(tier_filter: Optional[int] = None) -> unittest.TestSuite:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    tier_modules = {
        1: "tests.e2e.test_tier1_features",
        2: "tests.e2e.test_tier2_boundaries",
        3: "tests.e2e.test_tier3_combinations",
        4: "tests.e2e.test_tier4_journeys",
    }

    if tier_filter:
        if tier_filter not in tier_modules:
            print(f"[!] Unknown tier {tier_filter}. Available: 1, 2, 3, 4")
            sys.exit(1)
        mod_name = tier_modules[tier_filter]
        suite.addTests(loader.loadTestsFromName(mod_name))
    else:
        for t in sorted(tier_modules.keys()):
            mod_name = tier_modules[t]
            suite.addTests(loader.loadTestsFromName(mod_name))

    return suite


def run_e2e_suite(tier_filter: Optional[int] = None, verbose: bool = False) -> int:
    start_time = time.time()
    header_title = "YANDEX MUSIC MOD - E2E TEST SUITE"
    if tier_filter:
        header_title += f" [TIER {tier_filter} ONLY]"

    print("=" * 70)
    print(header_title.center(70))
    print("=" * 70)
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Timestamp:    {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
    print(f"Environment:  Python {sys.version.split()[0]} ({sys.platform})")
    print("-" * 70)

    suite = load_test_suite(tier_filter)
    total_count = suite.countTestCases()
    print(f"Discovered {total_count} test cases across requested tiers.\n")

    verbosity_level = 2 if verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity_level, stream=sys.stdout)
    result = runner.run(suite)

    elapsed = time.time() - start_time
    passed = result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)

    print("\n" + "=" * 70)
    print("E2E EXECUTION SUMMARY".center(70))
    print("=" * 70)
    print(f"Total Tests Executed: {result.testsRun}")
    print(f"  [+] Passed:         {passed}")
    print(f"  [-] Failures:       {len(result.failures)}")
    print(f"  [!] Errors:         {len(result.errors)}")
    print(f"  [*] Skipped:        {len(result.skipped)}")
    print(f"Execution Time:       {elapsed:.3f} seconds")
    print("-" * 70)

    # Matrix breakdown
    print("Tier Breakdown:")
    print("  - Tier 1 (Feature Coverage):        36 tests (Features 1-25)")
    print("  - Tier 2 (Boundary & Corner Cases): 35 tests (Boundary Limits & Error Resilience)")
    print("  - Tier 3 (Cross-Feature Pairs):     10 tests (Pairwise Module Interactions)")
    print("  - Tier 4 (Real-World Journeys):      5 tests (End-to-End Application Journeys)")
    print("=" * 70)

    if result.wasSuccessful():
        print("ALL TESTS PASSED SUCCESSFULLY! (100% Pass Rate)")
        print("Exit Code: 0")
        print("=" * 70)
        return 0
    else:
        print("TEST FAILURES DETECTED!")
        print("Exit Code: 1")
        print("=" * 70)
        return 1


def main():
    parser = argparse.ArgumentParser(description="Yandex Music Mod E2E Test Runner")
    parser.add_argument("--tier", "-t", type=int, choices=[1, 2, 3, 4], default=None, help="Run specific test tier (1-4)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose test output")
    args = parser.parse_args()

    exit_code = run_e2e_suite(tier_filter=args.tier, verbose=args.verbose)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
