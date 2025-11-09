from __future__ import annotations
from pathlib import Path
from typing import List
import logging

from .models import PlanItem
from .constants import MAX_FILE_SIZE_BYTES  # Import new constant
from . import filters
from . import headerlogic
from . import filesystem

log = logging.getLogger(__name__)


def plan_files(
    root: Path,
    *,
    depth: int | None,
    excludes: List[str],
    override: bool,
    remove: bool,  # <-- NEW
) -> List[PlanItem]:
    """
    Plan all actions to be taken. This is now an orchestrator
    and does not contain any I/O logic itself.
    """
    out: List[PlanItem] = []

    for path in filesystem.find_python_files(root):
        rel_posix = path.relative_to(root).as_posix()

        if filters.is_excluded(path, root, excludes):
            out.append(PlanItem(path, rel_posix, "skip-excluded"))
            continue

        if not filters.within_depth(path, root, depth):
            out.append(PlanItem(path, rel_posix, "skip-excluded", reason="depth"))
            continue

        # NEW: File Size Check
        try:
            file_size = path.stat().st_size
            if file_size > MAX_FILE_SIZE_BYTES:
                reason = f"file size ({file_size}b) exceeds limit"
                out.append(PlanItem(path, rel_posix, "skip-excluded", reason=reason))
                continue
        except (IOError, PermissionError) as e:
            log.warning(f"Could not stat file {path}: {e}")
            out.append(PlanItem(path, rel_posix, "skip-excluded", reason=f"stat failed: {e}"))
            continue

        # Read lines (this is now safe, as we've size-checked)
        lines = filesystem.read_file_lines(path)

        expected = headerlogic.header_line_for(rel_posix)
        analysis = headerlogic.analyze_header_state(lines, expected)

        # --- NEW LOGIC ---
        # Handle "remove" action first, as it takes precedence
        if remove:
            if analysis.existing_header_line is not None:
                out.append(PlanItem(path, rel_posix, "remove"))
            else:
                out.append(
                    PlanItem(path, rel_posix, "skip-header-exists", reason="no-header-to-remove")
                )
            continue

        # --- EXISTING LOGIC (from bug fix) ---
        if analysis.has_correct_header:
            # Case 1: Header is correct. Skip.
            out.append(PlanItem(path, rel_posix, "skip-header-exists"))
            continue

        if analysis.existing_header_line is None:
            # Case 2: No header exists. Add one.
            out.append(PlanItem(path, rel_posix, "add"))
            continue

        # Case 3: Header exists, but it's incorrect.
        if override:
            # Action: Override it.
            out.append(PlanItem(path, rel_posix, "override"))
        else:
            # Action: Skip it. We don't override unless asked.
            # This prevents the duplication bug.
            out.append(
                PlanItem(
                    path, rel_posix, "skip-header-exists", reason="incorrect-header-no-override"
                )
            )

    return out


def write_with_header(
    item: PlanItem,
    *,  # Force keyword arguments for flags
    backup: bool,
    dry_run: bool,
) -> str:
    """
    Execute the write/remove action for a single PlanItem.
    Orchestrates reading, logic, and writing.
    """
    path = item.path
    rel_posix = item.rel_posix
    expected = headerlogic.header_line_for(rel_posix)

    original_lines = filesystem.read_file_lines(path)
    original_content = "\n".join(original_lines) + "\n"

    analysis = headerlogic.analyze_header_state(original_lines, expected)

    # --- UPDATED LOGIC ---
    if item.action == "remove":
        new_lines = headerlogic.build_removed_lines(
            original_lines,
            analysis,
        )
    else:  # "add" or "override"
        new_lines = headerlogic.build_new_lines(
            original_lines,
            expected,
            analysis,
            override=(item.action == "override"),
        )

    # Rebuild file text
    new_text = "\n".join(new_lines) + "\n"

    # This call will now re-raise exceptions if it fails
    filesystem.write_file_content(
        path,
        new_text,
        original_content,
        backup=backup,
        dry_run=dry_run,
    )

    return item.action
