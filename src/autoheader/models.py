from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PlanItem:
    path: Path
    rel_posix: str
    action: str  # "skip-excluded" | "skip-header-exists" | "add" | "override" | "remove"
    reason: str = ""


@dataclass
class RootDetectionResult:
    """Result of a project root check."""

    is_project_root: bool
    match_count: int
    path: Path
