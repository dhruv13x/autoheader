# src/autoheader/filters.py

from __future__ import annotations
import fnmatch
from pathlib import Path
from typing import List

from .constants import DEFAULT_EXCLUDES


def is_excluded(path: Path, root: Path, extra_patterns: List[str]) -> bool:
    rel = path.relative_to(root)
    parts = rel.parts

    # --- FIX START ---
    # We need to combine default folder excludes with folder excludes
    # from extra_patterns (e.g., "docs/").
    
    all_folder_excludes = set(DEFAULT_EXCLUDES)
    glob_patterns = []
    
    for pat in extra_patterns:
        pat_clean = pat.strip('/')
        if "*" not in pat and pat_clean:
            # If it has no glob star, treat it as a folder name.
            all_folder_excludes.add(pat_clean)
        else:
            # Otherwise, treat it as a glob.
            glob_patterns.append(pat)

    # folder name exclusions
    for part in parts[:-1]:
        if part in all_folder_excludes:
            return True
    # --- FIX END ---

    # glob patterns (apply to the posix relpath)
    rel_posix = rel.as_posix()
    for pat in glob_patterns: # --- FIX --- (use the filtered list)
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
