#!/usr/bin/env python3
"""
Deployment verification script for GGAL Monitor.
Checks that all files are in place and properly structured.
Does NOT require Flask/numpy to be installed.
"""

import os
import sys
from pathlib import Path

def check_file_exists(filepath, description):
    """Check if a file exists and return status."""
    exists = os.path.exists(filepath)
    status = "✓" if exists else "✗"
    print(f"  {status} {description}: {filepath}")
    return exists

def check_file_content(filepath, search_terms):
    """Check if file contains expected terms."""
    if not os.path.exists(filepath):
        return False

    try:
        with open(filepath, 'r') as f:
            content = f.read()
            for term in search_terms:
                if term not in content:
                    print(f"    ⚠ Missing expected content: '{term}'")
                    return False
        return True
    except Exception as e:
        print(f"    ⚠ Error reading file: {e}")
        return False

def main():
    print("=" * 70)
    print("GGAL Monitor - Deployment Verification")
    print("=" * 70)
    print()

    all_checks_passed = True

    # Check required files
    print("1. Checking Required Files:")
    required_files = {
        'app.py': 'Main Flask application',
        'forecaster.py': 'ML forecasting module',
        'requirements.txt': 'Python dependencies',
        'templates/index.html': 'Frontend HTML',
        'test_app.py': 'Test suite',
        'CLAUDE.md': 'Documentation for Claude Code',
        '.gitignore': 'Git ignore file'
    }

    for filepath, description in required_files.items():
        if not check_file_exists(filepath, description):
            all_checks_passed = False

    print()

    # Check app.py content
    print("2. Checking app.py Structure:")
    app_checks = check_file_content('app.py', [
        'from forecaster import GGALForecaster',
        'MonitorGGAL',
        '@app.route(\'/api/forecast\')',
        '@app.route(\'/api/trading-signal\')',
        'forecaster = GGALForecaster'
    ])
    if app_checks:
        print("  ✓ app.py has all required components")
    else:
        print("  ✗ app.py is missing components")
        all_checks_passed = False

    print()

    # Check forecaster.py content
    print("3. Checking forecaster.py Structure:")
    forecaster_checks = check_file_content('forecaster.py', [
        'class KalmanFilter',
        'class GGALForecaster',
        'def predict(',
        'def update(',
        'forecast',
        'generate_trading_signal',
        'get_velocity'
    ])
    if forecaster_checks:
        print("  ✓ forecaster.py has Kalman Filter implementation")
    else:
        print("  ✗ forecaster.py is missing Kalman components")
        all_checks_passed = False

    print()

    # Check requirements.txt
    print("4. Checking Dependencies:")
    deps_checks = check_file_content('requirements.txt', [
        'Flask',
        'requests',
        'gunicorn',
        'numpy'
    ])
    if deps_checks:
        print("  ✓ requirements.txt has all dependencies")
    else:
        print("  ✗ requirements.txt is missing dependencies")
        all_checks_passed = False

    print()

    # Check test suite
    print("5. Checking Test Suite:")
    test_checks = check_file_content('test_app.py', [
        'TestKalmanFilter',
        'TestMonitorGGAL',
        'TestGGALForecaster',
        'TestFlaskAPI',
        'TestIntegration'
    ])
    if test_checks:
        print("  ✓ test_app.py has all test classes (incl. Kalman tests)")
    else:
        print("  ✗ test_app.py is missing test classes")
        all_checks_passed = False

    print()

    # Check frontend
    print("6. Checking Frontend Updates:")
    html_checks = check_file_content('templates/index.html', [
        'GGAL Monitor',
        'Kalman',
        '/api/forecast',
        '/api/trading-signal',
        'forecast5min',
        'signalDetails',
        'signalStrength',
        'signalConfidence',
        '#0a0e27'  # Dark background color
    ])
    if html_checks:
        print("  ✓ index.html has Kalman UI with simplified signal display")
    else:
        print("  ✗ index.html is missing UI components")
        all_checks_passed = False

    print()

    # Check file sizes (basic sanity check)
    print("7. Checking File Sizes:")
    size_checks = {
        'app.py': (2000, 9000),  # Larger due to gunicorn config integration
        'forecaster.py': (8000, 12000),  # Smaller with Kalman only
        'test_app.py': (12000, 16000),   # Updated for Kalman tests
        'templates/index.html': (12000, 16000)  # Simplified without Chart.js
    }

    for filepath, (min_size, max_size) in size_checks.items():
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            if min_size <= size <= max_size:
                print(f"  ✓ {filepath}: {size} bytes (within expected range)")
            else:
                print(f"  ⚠ {filepath}: {size} bytes (expected {min_size}-{max_size})")
                if size < min_size:
                    print(f"    File may be incomplete")
                    all_checks_passed = False

    print()

    # Count lines of code
    print("8. Code Statistics:")
    total_lines = 0
    for filepath in ['app.py', 'forecaster.py', 'test_app.py']:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                lines = len(f.readlines())
                total_lines += lines
                print(f"  • {filepath}: {lines} lines")
    print(f"  Total Python code: {total_lines} lines")

    print()

    # API endpoint summary
    print("9. API Endpoints Available:")
    endpoints = [
        ('GET', '/', 'Dashboard HTML'),
        ('GET', '/api/precio-actual', 'Current price'),
        ('GET', '/api/historial', 'Price history'),
        ('GET', '/api/estadisticas', 'Statistics'),
        ('GET', '/api/health', 'Health check'),
        ('GET', '/api/debug', 'Debug info'),
        ('GET', '/api/forecast', 'Kalman Filter predictions (1/5/10 min)'),
        ('GET', '/api/trading-signal', 'Trading signal (0-100 strength)')
    ]
    for method, path, desc in endpoints:
        print(f"  • {method:4} {path:25} - {desc}")

    print()
    print("=" * 70)

    if all_checks_passed:
        print("✅ ALL CHECKS PASSED - Ready for deployment!")
        print()
        print("Next steps:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Run tests: python test_app.py")
        print("  3. Set API key: export FINNHUB_API_KEY='your_key'")
        print("  4. Run locally: python app.py")
        print("  5. Deploy to Render: git push origin main")
        print("=" * 70)
        return 0
    else:
        print("❌ SOME CHECKS FAILED - Please review errors above")
        print("=" * 70)
        return 1

if __name__ == '__main__':
    sys.exit(main())
