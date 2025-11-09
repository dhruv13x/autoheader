from __future__ import annotations
from pathlib import Path
import logging

from . import walker
from . import ui
from .models import RootDetectionResult

# Note: In a real implementation, you'd get the logger
# from the main app setup.
log = logging.getLogger(__name__)


def ensure_root_or_confirm(
    path_to_check: Path,
    auto_yes: bool = False,
) -> bool:
    """
    Orchestrates root detection and user confirmation.
    Returns True to proceed, False to abort.
    """
    result = walker.detect_project_root(path_to_check)

    if result.is_project_root:
        log.info(f"Project root confirmed ({result.match_count} markers found).")
        return True

    # Otherwise, fallback to user confirmation
    log.warning(f"Warning: only {result.match_count} project markers found.")
    return ui.confirm_continue(auto_yes=auto_yes)
