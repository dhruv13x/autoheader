# src/autoheader/core.py

from __future__ import annotations
from typing import Tuple

# --- MODIFIED ---
from .models import PlanItem
# --- END MODIFIED ---
from . import headerlogic
from . import filesystem

# We keep this for backward compatibility if other modules import it,
# but point them to planner.
from .planner import plan_files, _analyze_single_file # noqa

def write_with_header(
    item: PlanItem,
    *,
    backup: bool,
    dry_run: bool,
    blank_lines_after: int,
) -> Tuple[str, float, str, Tuple[str, str, str] | None]:
    """
    Execute the write/remove action for a single PlanItem.
    Orchestrates reading, logic, and writing.

    Returns:
        (action, new_mtime, new_hash, diff_info)
        diff_info is None if no diff, else (rel_posix, existing_header, expected_header)
    """
    path = item.path
    rel_posix = item.rel_posix
    
    original_lines = filesystem.read_file_lines(path)

    # Need to calculate expected header first
    analysis_prelim = headerlogic.analyze_header_state(
        original_lines, "", item.prefix, item.check_encoding, item.analysis_mode
    )

    expected = headerlogic.header_line_for(
        rel_posix,
        item.template,
        content="\n".join(original_lines),
        existing_header=analysis_prelim.existing_header_line,
        license_spdx=item.license_spdx,
        license_owner=item.license_owner,
    )
    original_content = "\n".join(original_lines) + "\n"

    # Now analyze with expected header
    analysis = headerlogic.analyze_header_state(
        original_lines, expected, item.prefix, item.check_encoding, item.analysis_mode
    )

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
            blank_lines_after=blank_lines_after,
        )

    new_text = "\n".join(new_lines) + "\n"

    diff_info = None
    if dry_run and item.action in ("add", "override"):
        diff_info = (rel_posix, analysis.existing_header_line, expected)

    filesystem.write_file_content(
        path,
        new_text,
        original_content,
        backup=backup,
        dry_run=dry_run,
    )

    new_mtime = path.stat().st_mtime
    new_hash = filesystem.get_file_hash(path)

    return item.action, new_mtime, new_hash, diff_info
