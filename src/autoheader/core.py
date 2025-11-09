# src/autoheader/core.py

from __future__ import annotations
from pathlib import Path
from typing import List
import logging

# --- MODIFIED ---
from .models import PlanItem, LanguageConfig
from .constants import MAX_FILE_SIZE_BYTES, INLINE_IGNORE_COMMENT
# --- END MODIFIED ---
from . import filters
from . import headerlogic
from . import filesystem
from . import ui
from rich.progress import track


log = logging.getLogger(__name__)


def plan_files(
    root: Path,
    *,
    depth: int | None,
    excludes: List[str],
    override: bool,
    remove: bool,
    # --- MODIFIED ---
    languages: List[LanguageConfig]
) -> List[PlanItem]:
    """
    Plan all actions to be taken. This is now an orchestrator
    and does not contain any I/O logic itself.
    """
    out: List[PlanItem] = []

    # --- MODIFIED ---
    file_iterator = filesystem.find_configured_files(root, languages)

    for path, lang in track(
        file_iterator,
        description="Planning files...",
        console=ui.console,
        disable=ui.console.quiet,
        transient=True,
    ):
    # --- END MODIFIED ---
        rel_posix = path.relative_to(root).as_posix()

        if filters.is_excluded(path, root, excludes):
            # Pass lang config to PlanItem
            out.append(PlanItem(path, rel_posix, "skip-excluded", 
                                prefix=lang.prefix, 
                                check_encoding=lang.check_encoding, 
                                template=lang.template))
            continue

        if not filters.within_depth(path, root, depth):
            out.append(PlanItem(path, rel_posix, "skip-excluded", reason="depth",
                                prefix=lang.prefix, 
                                check_encoding=lang.check_encoding, 
                                template=lang.template))
            continue

        try:
            file_size = path.stat().st_size
            if file_size > MAX_FILE_SIZE_BYTES:
                reason = f"file size ({file_size}b) exceeds limit"
                out.append(PlanItem(path, rel_posix, "skip-excluded", reason=reason,
                                    prefix=lang.prefix, 
                                    check_encoding=lang.check_encoding, 
                                    template=lang.template))
                continue
        except (IOError, PermissionError) as e:
            log.warning(f"Could not stat file {path}: {e}")
            out.append(PlanItem(path, rel_posix, "skip-excluded", reason=f"stat failed: {e}",
                                prefix=lang.prefix, 
                                check_encoding=lang.check_encoding, 
                                template=lang.template))
            continue

        lines = filesystem.read_file_lines(path)

        is_ignored = False
        for line in lines:
            if INLINE_IGNORE_COMMENT in line:
                is_ignored = True
                break
        
        if is_ignored:
            out.append(PlanItem(path, rel_posix, "skip-excluded", reason="inline ignore",
                                prefix=lang.prefix, 
                                check_encoding=lang.check_encoding, 
                                template=lang.template))
            continue

        # --- MODIFIED ---
        expected = headerlogic.header_line_for(rel_posix, lang.template)
        analysis = headerlogic.analyze_header_state(
            lines, expected, lang.prefix, lang.check_encoding
        )
        # --- END MODIFIED ---

        if remove:
            if analysis.existing_header_line is not None:
                out.append(PlanItem(path, rel_posix, "remove",
                                    prefix=lang.prefix, 
                                    check_encoding=lang.check_encoding, 
                                    template=lang.template))
            else:
                out.append(
                    PlanItem(path, rel_posix, "skip-header-exists", reason="no-header-to-remove",
                             prefix=lang.prefix, 
                             check_encoding=lang.check_encoding, 
                             template=lang.template)
                )
            continue

        if analysis.has_correct_header:
            out.append(PlanItem(path, rel_posix, "skip-header-exists",
                                prefix=lang.prefix, 
                                check_encoding=lang.check_encoding, 
                                template=lang.template))
            continue

        if analysis.existing_header_line is None:
            out.append(PlanItem(path, rel_posix, "add",
                                prefix=lang.prefix, 
                                check_encoding=lang.check_encoding, 
                                template=lang.template))
            continue

        if override:
            out.append(PlanItem(path, rel_posix, "override",
                                prefix=lang.prefix, 
                                check_encoding=lang.check_encoding, 
                                template=lang.template))
        else:
            out.append(
                PlanItem(
                    path, rel_posix, "skip-header-exists", reason="incorrect-header-no-override",
                    prefix=lang.prefix, 
                    check_encoding=lang.check_encoding, 
                    template=lang.template
                )
            )

    return out


def write_with_header(
    item: PlanItem,
    *,
    backup: bool,
    dry_run: bool,
    blank_lines_after: int,
    # --- prefix: str is no longer needed ---
) -> str:
    """
    Execute the write/remove action for a single PlanItem.
    Orchestrates reading, logic, and writing.
    """
    path = item.path
    rel_posix = item.rel_posix
    
    # --- MODIFIED: Get config from the item ---
    expected = headerlogic.header_line_for(rel_posix, item.template)
    # --- END MODIFIED ---

    original_lines = filesystem.read_file_lines(path)
    original_content = "\n".join(original_lines) + "\n"

    # --- MODIFIED ---
    analysis = headerlogic.analyze_header_state(
        original_lines, expected, item.prefix, item.check_encoding
    )
    # --- END MODIFIED ---

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

    filesystem.write_file_content(
        path,
        new_text,
        original_content,
        backup=backup,
        dry_run=dry_run,
    )

    return item.action