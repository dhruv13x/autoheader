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
