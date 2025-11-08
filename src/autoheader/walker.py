# src/autoheader/walker.py

from __future__ import annotations

from pathlib import Path
import sys

ROOT_MARKERS = [
    ".gitignore",
    "README.md",
    "README.rst",
    "pyproject.toml",
]

def detect_project_root(min_matches: int = 2) -> tuple[bool, int, Path]:
    """Return (looks_like_root, match_count, cwd)."""
    cwd = Path.cwd()
    matches = sum(1 for m in ROOT_MARKERS if (cwd / m).exists())
    return (matches >= min_matches, matches, cwd)

def confirm_continue(auto_yes: bool = False) -> bool:
    """Ask user whether to continue when root detection fails."""
    if auto_yes:
        return True

    while True:
        resp = input(
            "autoheader: Could not confidently detect project root.\n"
            "Are you sure you want to continue? [y/N]: "
        ).strip().lower()
        if resp in ("y", "yes"):
            return True
        if resp in ("n", "no", ""):
            return False

def ensure_root_or_confirm(auto_yes: bool = False) -> bool:
    """Use at the start of your tool to verify project root."""
    looks_like_root, matches, _ = detect_project_root()

    if looks_like_root:
        print(f"autoheader: Project root confirmed ({matches} markers found).")
        return True

    # Otherwise fallback to user confirmation
    print(f"autoheader: Warning: only {matches} project markers found.")
    return confirm_continue(auto_yes=auto_yes)

if __name__ == "__main__":
    ok = ensure_root_or_confirm()
    if ok:
        print("Continuing execution...")
    else:
        print("Aborted by user.")
        sys.exit(1)
