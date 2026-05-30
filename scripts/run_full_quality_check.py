"""
run_full_quality_check.py — Full local quality gate for QHome AI Agent.

Runs unit/integration tests AND the deterministic mock eval suite.
This is the authoritative quality gate — all CI/CD and pre-submission checks
should pass this script.

Live API eval is intentionally excluded from this gate because it requires
network connectivity and is non-deterministic. Use it separately for smoke
testing only:
    python run.py eval --mode live --limit 2

Usage:
    python scripts/run_full_quality_check.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def print_header(title: str) -> None:
    print(f"\n{'=' * 80}")
    print(f" {title}")
    print(f"{'=' * 80}\n")


def run_step(name: str, cmd: list[str]) -> bool:
    print_header(f"Running: {name}")
    try:
        result = subprocess.run(cmd, check=False)
        if result.returncode != 0:
            print(f"\n[X] FAILED: {name} (exit code {result.returncode})")
            return False
        print(f"\n[V] PASSED: {name}")
        return True
    except Exception as exc:
        print(f"\n[X] ERROR: Failed to run {name}: {exc}")
        return False


def main() -> None:
    root = Path(__file__).resolve().parents[1]

    print_header("QHome AI Agent — Full Quality Gate (Mock / Deterministic)")
    print("  This gate checks:")
    print("  1. Unit & Integration Tests (56 tests)")
    print("  2. Eval Suite — 100-Point Rubric, mock mode (deterministic)")
    print()
    print("  NOTE: Live API eval is NOT part of this gate.")
    print("        Live eval is for API smoke testing only (non-deterministic).")
    print("        See: python run.py eval --mode live --limit 2")

    steps = [
        (
            "Unit & Integration Tests",
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                str(root / "tests"),
                "-v",
            ],
        ),
        (
            "100-Point Eval Suite (mock — deterministic quality gate)",
            [sys.executable, str(root / "run.py"), "eval", "--mode", "mock"],
        ),
    ]

    all_passed = True
    for name, cmd in steps:
        if not run_step(name, cmd):
            all_passed = False

    print_header("Quality Gate Summary")
    if all_passed:
        print("[V] SUCCESS: All quality checks passed. Ready for submission.")
        sys.exit(0)
    else:
        print(
            "[X] FAILURE: One or more quality checks failed."
            " Please fix before submitting."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
