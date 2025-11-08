# 🗃️ Project Code Dump

**Generated:** 2025-11-08T18:05:07+00:00 UTC
**Version:** 9.0.0.dev0+beta2.unstable

---

## Table of Contents

1. [README.md](#readme-md)
2. [src/autoheader/core.py](#src-autoheader-core-py)
3. [src/autoheader/cli.py](#src-autoheader-cli-py)
4. [pyproject.toml](#pyproject-toml)
5. [src/autoheader/walker.py](#src-autoheader-walker-py)

---

## README.md

<a id='readme-md'></a>

```markdown
--no-dry-run
```

---

## src/autoheader/core.py

<a id='src-autoheader-core-py'></a>

```python
# src/autoheader/core.py

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import fnmatch
import re
from typing import Iterable, List

HEADER_PREFIX = "# "  # exact header line prefix
# PEP 263 encoding-cookie regex
ENCODING_RX = re.compile(r"^[ \t]*#.*coding[:=][ \t]*([-\w.]+)")

DEFAULT_EXCLUDES = {
    ".git",
    ".github",
    ".svn",
    ".hg",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    "node_modules",
}

@dataclass
class PlanItem:
    path: Path
    rel_posix: str
    action: str  # "skip-excluded" | "skip-header-exists" | "add" | "override" | "skip-nonpy"
    reason: str = ""

def is_excluded(path: Path, root: Path, extra_patterns: List[str]) -> bool:
    rel = path.relative_to(root)
    parts = rel.parts

    # folder name exclusions
    for part in parts[:-1]:
        if part in DEFAULT_EXCLUDES:
            return True

    # glob patterns (apply to the posix relpath)
    rel_posix = rel.as_posix()
    for pat in extra_patterns:
        if fnmatch.fnmatch(rel_posix, pat):
            return True

    return False

def within_depth(path: Path, root: Path, max_depth: int | None) -> bool:
    if max_depth is None:
        return True
    # depth measured as number of subdirectories below root
    # e.g. src/utils/parser.py -> parts = ["src","utils","parser.py"] -> depth directories = len(parts)-1 = 2
    rel = path.relative_to(root)
    dirs = len(rel.parts) - 1
    return dirs <= max_depth

def header_line_for(rel_posix: str) -> str:
    return f"{HEADER_PREFIX}{rel_posix}"

def read_first_two_lines(path: Path) -> tuple[str | None, str | None]:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            first = f.readline()
            second = f.readline()
            return first, second
    except Exception:
        return None, None

def has_correct_header(path: Path, root: Path) -> bool:
    rel_posix = path.relative_to(root).as_posix()
    expected = header_line_for(rel_posix)
    first, second = read_first_two_lines(path)
    if first is None:
        return False

    # If there is a shebang, header might be on line 2 (or 3 if encoding on 2)
    if first.startswith("#!"):
        if second is None:
            return False
        # If second line is encoding cookie, header could be line 3 — read it
        if ENCODING_RX.match(second):
            try:
                third = path.read_text(encoding="utf-8", errors="replace").splitlines()[2]
            except Exception:
                return False
            return third.strip() == expected
        return second.strip() == expected

    # If first line is encoding cookie, header should be on line 2
    if ENCODING_RX.match(first):
        if second is None:
            return False
        return second.strip() == expected

    # Otherwise header should be on line 1
    return first.strip() == expected

def compute_insert_index(lines: List[str]) -> int:
    """
    Determine where to insert the header, respecting shebang and PEP 263 encoding cookie.
    - If line1 is shebang, insert after it.
    - If encoding cookie is on line1 or line2, insert after whichever line has it.
    """
    if not lines:
        return 0

    i = 0
    if lines and lines[0].startswith("#!"):
        i = 1

    # encoding cookie must be on first or second line
    if i == 0 and lines and ENCODING_RX.match(lines[0] if lines else ""):
        i = 1
    if len(lines) > i and ENCODING_RX.match(lines[i]):
        i += 1

    return i

def write_with_header(path: Path, root: Path, override: bool, backup: bool, dry_run: bool) -> str:
    """
    Add or replace header.
    Returns action performed: "add" or "override".
    """
    rel_posix = path.relative_to(root).as_posix()
    expected = header_line_for(rel_posix)

    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines(keepends=False)

    # Make a working copy
    new_lines = lines[:]

    # Determine where header should go (after shebang + encoding cookie)
    insert_at = compute_insert_index(new_lines)

    # Override mode: remove existing header if present
    if override:
        # candidate header position is exactly insert_at
        if insert_at < len(new_lines) and new_lines[insert_at].startswith(HEADER_PREFIX):
            del new_lines[insert_at]

    # Insert header + one blank line after it
    new_lines.insert(insert_at, expected)
    new_lines.insert(insert_at + 1, "")

    # Rebuild file text
    new_text = "\n".join(new_lines) + "\n"

    # Optional backup
    if backup and not dry_run:
        bak = path.with_suffix(path.suffix + ".bak")
        bak.write_text(text, encoding="utf-8")

    # Write result
    if not dry_run:
        path.write_text(new_text, encoding="utf-8")

    return "override" if override else "add"
    
    
def plan_files(
    root: Path,
    *,
    depth: int | None,
    excludes: List[str],
    override: bool,
) -> List[PlanItem]:
    out: List[PlanItem] = []
    for path in root.rglob("*.py"):
        if path.is_dir():
            continue
        if is_excluded(path, root, excludes):
            out.append(PlanItem(path, path.relative_to(root).as_posix(), "skip-excluded"))
            continue
        if not within_depth(path, root, depth):
            out.append(PlanItem(path, path.relative_to(root).as_posix(), "skip-excluded", reason="depth"))
            continue

        rel_posix = path.relative_to(root).as_posix()
        if not override and has_correct_header(path, root):
            out.append(PlanItem(path, rel_posix, "skip-header-exists"))
            continue

        out.append(PlanItem(path, rel_posix, "override" if override and has_any_header(path, root) else "add"))
    return out

def has_any_header(path: Path, root: Path) -> bool:
    """True if the first logical line where header should live starts with '# '."""
    first, second = read_first_two_lines(path)
    if first is None:
        return False

    if first.startswith("#!"):
        # header candidate on line 2 or 3
        if second and second.strip().startswith("# "):
            return True
        try:
            third = path.read_text(encoding="utf-8", errors="replace").splitlines()[2]
            return third.strip().startswith("# ")
        except Exception:
            return False

    if ENCODING_RX.match(first):
        return bool(second and second.strip().startswith("# "))

    return first.strip().startswith("# ")

```

---

## src/autoheader/cli.py

<a id='src-autoheader-cli-py'></a>

```python
# src/autoheader/cli.py

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import List

from .walker import ensure_root_or_confirm
from .core import (
    DEFAULT_EXCLUDES,
    plan_files,
    write_with_header,
)

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="autoheader",
        description="Add a '# <relative/path.py>' header to Python files, safely and repeatably.",
    )

    # Dry-run by default; allow explicit --dry-run and --no-dry-run
    g = p.add_mutually_exclusive_group()
    g.add_argument("--dry-run", dest="dry_run", action="store_true", help="Do not write changes (default).")
    g.add_argument("--no-dry-run", dest="dry_run", action="store_false", help="Apply changes to files.")
    p.set_defaults(dry_run=True)

    p.add_argument("-y", "--yes", action="store_true", help="Assume yes when root detection is inconclusive.")
    p.add_argument("--depth", type=int, default=None, help="Max directory depth from root (e.g., 3).")
    p.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help="Extra glob(s) to exclude (can repeat). Defaults also exclude common dangerous paths.",
    )
    p.add_argument("--override", action="store_true", help="Rewrite existing header lines to fresh, correct ones.")
    p.add_argument("--backup", action="store_true", help="Create .bak backups before writing.")
    p.add_argument("--verbose", "-v", action="count", default=0, help="Increase verbosity.")
    p.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Root directory (default: current working directory).",
    )

    return p

def main(argv: List[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # Root confirmation
    if not ensure_root_or_confirm(auto_yes=args.yes):
        print("autoheader: Aborted.")
        return 1

    root: Path = args.root.resolve()

    if args.verbose:
        print(f"autoheader: using root = {root}")
        print(f"autoheader: dry_run = {args.dry_run}, override = {args.override}, backup = {args.backup}")
        if args.depth is not None:
            print(f"autoheader: depth guard = {args.depth}")
        print(f"autoheader: default excludes = {sorted(DEFAULT_EXCLUDES)}")
        if args.exclude:
            print(f"autoheader: extra excludes = {args.exclude}")

    plan = plan_files(
        root,
        depth=args.depth,
        excludes=args.exclude,
        override=args.override,
    )

    added = overridden = skipped_exists = skipped_excluded = 0
    for item in plan:
        rel = item.rel_posix

        if item.action in ("skip-excluded", "skip-nonpy"):
            skipped_excluded += 1
            if args.verbose:
                reason = f" ({item.reason})" if item.reason else ""
                print(f"SKIP: {rel} [excluded{reason}]")
            continue

        if item.action == "skip-header-exists":
            skipped_exists += 1
            if args.verbose:
                print(f"OK:   {rel} [header ok]")
            continue

        # write
        action_done = write_with_header(
            item.path,
            root=root,
            override=(item.action == "override"),
            backup=args.backup,
            dry_run=args.dry_run,
        )
        if action_done == "override":
            overridden += 1
            print(f"{'DRY ' if args.dry_run else ''}OVERRIDE: {rel}")
        else:
            added += 1
            print(f"{'DRY ' if args.dry_run else ''}ADD:      {rel}")

    # summary
    print(
        f"\nSummary: added={added}, overridden={overridden}, "
        f"skipped_ok={skipped_exists}, skipped_excluded={skipped_excluded}."
    )
    if args.dry_run:
        print("NOTE: this was a dry run. Use --no-dry-run to apply changes.")

    return 0

if __name__ == "__main__":
    sys.exit(main())

```

---

## pyproject.toml

<a id='pyproject-toml'></a>

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "autoheader"
version = "0.1.0"
description = "Enterprise-grade file header adder that tags each file with its repo-relative path"
readme = "README.md"
requires-python = ">=3.8"
license = {text = "MIT"}
authors = [{name = "Your Name"}]
keywords = ["headers", "cli", "utilities", "tooling"]

[project.scripts]
autoheader = "autoheader.cli:main"

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]
```

---

## src/autoheader/walker.py

<a id='src-autoheader-walker-py'></a>

```python
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

```

---

