# src/autoheader/walker.py

from __future__ import annotations
from pathlib import Path
from typing import List

from .constants import ROOT_MARKERS
from .models import RootDetectionResult


def detect_project_root(
    path_to_check: Path,
    markers: List[str] = ROOT_MARKERS,
    min_matches: int = 2,
) -> RootDetectionResult:
    """
    Checks a given path for project root markers.
    This is pure logic, testable by passing a 'tmp_path'.

    Returns:
        RootDetectionResult: Object containing check results.
    """
    if not path_to_check.is_dir():
        return RootDetectionResult(False, 0, path_to_check)

    matches = sum(1 for m in markers if (path_to_check / m).exists())

    return RootDetectionResult(
        is_project_root=(matches >= min_matches),
        match_count=matches,
        path=path_to_check,
    )
