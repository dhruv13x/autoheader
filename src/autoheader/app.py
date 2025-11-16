# src/autoheader/app.py

from __future__ import annotations
from pathlib import Path
import logging
from typing import List

from . import walker
from . import ui
from .constants import ROOT_MARKERS  # <-- NEW

# Note: In a real implementation, you'd get the logger
# from the main app setup.
log = logging.getLogger(__name__)


def ensure_root_or_confirm(
    path_to_check: Path,
    auto_yes: bool = False,
    markers: List[str] | None = None,  # <-- MODIFIED
) -> bool:
    """
    Orchestrates root detection and user confirmation.
    Returns True to proceed, False to abort.
    """
    # Use markers from config if provided, else fall back to constants
    use_markers = markers if markers is not None else ROOT_MARKERS  # <-- NEW

    result = walker.detect_project_root(path_to_check, markers=use_markers)

    if result.is_project_root:
        log.info(f"Project root confirmed ({result.match_count} markers found).")
        return True

    # Otherwise, fallback to user confirmation
    log.warning(f"Warning: only {result.match_count} project markers found.")
    return ui.confirm_continue(auto_yes=auto_yes)
