import subprocess
import sys
from pathlib import Path

def print_header(title: str):
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
    except Exception as e:
        print(f"\n[X] ERROR: Failed to run {name}: {e}")
        return False

def main():
    root = Path(__file__).resolve().parents[1]
    
    print_header("QHome AI Agent - Full Quality Check")
    
    steps = [
        ("Unit & Integration Tests", [sys.executable, "-m", "unittest", "discover", "-s", str(root / "tests"), "-v"]),
        ("100-Point Evaluation Suite", [sys.executable, str(root / "run.py"), "eval"])
    ]
    
    all_passed = True
    for name, cmd in steps:
        if not run_step(name, cmd):
            all_passed = False
            
    print_header("Quality Check Summary")
    if all_passed:
        print("[V] SUCCESS: All quality checks passed. Ready for submission.")
        sys.exit(0)
    else:
        print("[X] FAILURE: One or more quality checks failed. Please fix before submitting.")
        sys.exit(1)

if __name__ == "__main__":
    main()
