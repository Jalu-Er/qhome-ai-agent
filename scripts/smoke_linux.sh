#!/bin/bash
set -e

echo "================================================================================"
echo " Running QHome AI Agent Smoke Tests (Linux/macOS)"
echo "================================================================================"

# Get absolute path to the directory containing this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
ROOT="$(dirname "$DIR")"

echo "Checking Python 3 availability..."
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not installed."
    exit 1
fi

echo "Running Full Quality Check..."
python3 "$ROOT/scripts/run_full_quality_check.py"

echo "Running a mock workflow to verify end-to-end routing..."
python3 "$ROOT/run.py" run --ticket-id="damaged-ceramic-delivery"

echo "================================================================================"
echo " Smoke test completed successfully!"
echo "================================================================================"
