# src/autoheader/models.py

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List


# --- ADD THIS ---
@dataclass
class LanguageConfig:
    """Configuration for a single language."""
    name: str
    file_globs: List[str]
    prefix: str
    check_encoding: bool  # Is this Python-like (shebang, encoding)?
    template: str  # The template for the header line
    analysis_mode: str = "line"


@dataclass
class PlanItem:
    path: Path
    rel_posix: str
    action: str  # "skip-excluded" | "skip-header-exists" | "add" | "override" | "remove" | "skip-cached"
    
    # --- ADD THESE ---
    # Config needed by the execution (write) phase
    prefix: str
    check_encoding: bool
    template: str
    analysis_mode: str
    # --- END ADD ---

    reason: str = ""


@dataclass
class RootDetectionResult:
    """Result of a project root check."""

    is_project_root: bool
    match_count: int
    path: Path


@dataclass
class RuntimeContext:
    """Configuration flags encapsulated for less argument bloat."""

    root: Path
    excludes: List[str]
    depth: int | None
    override: bool
    remove: bool
    check_hash: bool
    timeout: float
