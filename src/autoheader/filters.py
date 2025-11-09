from __future__ import annotations
import fnmatch
from pathlib import Path
from typing import List

from .constants import DEFAULT_EXCLUDES


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
    # e.g. src/utils/parser.py -> parts = ["src","utils","parser.py"] -> depth = 2
    rel = path.relative_to(root)
    dirs = len(rel.parts) - 1
    return dirs <= max_depth
