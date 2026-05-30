"""
build_release.py — Build portable release ZIP for QHome AI Agent.

Usage:
    python scripts/build_release.py

Output:
    dist/qhome-ai-agent-v1.0.0.zip
"""
from __future__ import annotations

import os
import shutil
import sys
import zipfile
from pathlib import Path

VERSION = "1.0.0"
PACKAGE_NAME = f"qhome-ai-agent-v{VERSION}"

# Directories and files to include in the release
INCLUDE_DIRS = [
    "config",
    "data/seed",
    "docs",
    "scripts",
    "src",
    "tests",
    "web",
]

# Individual data files (not in seed/)
INCLUDE_DATA_FILES = [
    "data/knowledge_base.json",
    "data/sample_tickets.json",
    "data/evaluation_cases.json",
]

INCLUDE_FILES = [
    "run.py",
    "README.md",
    "pyproject.toml",
    ".env.example",
    ".gitignore",
]

# Files/patterns to exclude from data
DATA_EXCLUDES = {".db", ".sqlite"}

# Directories to always exclude
EXCLUDE_DIRS = {
    ".git", ".venv", "venv", "env", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "dist", "build", "runs", "runs-test", "outputs", "logs",
}

# File extensions to exclude
EXCLUDE_EXTS = {".log", ".tmp", ".bak", ".pyc", ".pyo"}


def should_exclude(path: Path) -> bool:
    """Return True if this path should be excluded from the release."""
    for part in path.parts:
        if part in EXCLUDE_DIRS:
            return True
    if path.suffix.lower() in EXCLUDE_EXTS:
        return True
    # Exclude runtime DB files under data/
    if path.suffix.lower() in DATA_EXCLUDES:
        return True
    # Exclude .env (not .env.example)
    if path.name == ".env":
        return True
    return False


def build_release(root: Path) -> Path:
    dist_dir = root / "dist"
    stage_dir = dist_dir / PACKAGE_NAME
    zip_path = dist_dir / f"{PACKAGE_NAME}.zip"

    # Clean previous build
    if stage_dir.exists():
        shutil.rmtree(stage_dir)
    stage_dir.mkdir(parents=True, exist_ok=True)

    file_count = 0

    # Copy directories
    for dir_name in INCLUDE_DIRS:
        src = root / dir_name
        if not src.exists():
            print(f"  [SKIP] {dir_name}/ (not found)")
            continue
        dst = stage_dir / dir_name
        for item in src.rglob("*"):
            if item.is_file() and not should_exclude(item.relative_to(root)):
                relative = item.relative_to(root)
                target = stage_dir / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)
                file_count += 1

    # Copy individual data files
    for file_name in INCLUDE_DATA_FILES:
        src = root / file_name
        if src.exists():
            target = stage_dir / file_name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
            file_count += 1
        else:
            print(f"  [SKIP] {file_name} (not found)")

    # Copy root files
    for file_name in INCLUDE_FILES:
        src = root / file_name
        if src.exists():
            shutil.copy2(src, stage_dir / file_name)
            file_count += 1
        else:
            print(f"  [SKIP] {file_name} (not found)")

    # Create ZIP
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in sorted(stage_dir.rglob("*")):
            if item.is_file():
                arcname = PACKAGE_NAME + "/" + str(item.relative_to(stage_dir))
                zf.write(item, arcname)

    # Cleanup staging dir
    shutil.rmtree(stage_dir)

    return zip_path


def main() -> None:
    root = Path(__file__).resolve().parents[1]

    print("=" * 60)
    print(f"  QHome AI Agent — Release Build v{VERSION}")
    print("=" * 60)
    print()

    zip_path = build_release(root)

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    with zipfile.ZipFile(zip_path, "r") as zf:
        file_count = len(zf.namelist())

    print(f"  Release ZIP : {zip_path}")
    print(f"  Size        : {size_mb:.2f} MB")
    print(f"  Files       : {file_count}")
    print()
    print("  Quick Start after extraction:")
    print()
    print("    Windows:")
    print(f"      cd {PACKAGE_NAME}")
    print("      copy .env.example .env")
    print("      py -3 run.py init-db")
    print("      py -3 run.py web")
    print()
    print("    Linux/macOS:")
    print(f"      cd {PACKAGE_NAME}")
    print("      cp .env.example .env")
    print("      python3 run.py init-db")
    print("      python3 run.py web")
    print()
    print("  Then open: http://127.0.0.1:8000/")
    print("=" * 60)


if __name__ == "__main__":
    main()
