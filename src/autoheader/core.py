# src/autoheader/core.py

from __future__ import annotations
from pathlib import Path
from typing import List, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor

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


def _analyze_single_file(
    args: Tuple[Path, LanguageConfig],
    root: Path,
    excludes: List[str],
    depth: int | None,
    override: bool,
    remove: bool,
    cache: dict,
) -> Tuple[PlanItem, Tuple[str, dict] | None]:
    path, lang = args
    rel_posix = path.relative_to(root).as_posix()

    if filters.is_excluded(path, root, excludes):
        return PlanItem(path, rel_posix, "skip-excluded", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode), None

    if not filters.within_depth(path, root, depth):
        return PlanItem(path, rel_posix, "skip-excluded", reason="depth", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode), None

    try:
        stat = path.stat()
        mtime = stat.st_mtime
        file_size = stat.st_size
        if file_size > MAX_FILE_SIZE_BYTES:
            reason = f"file size ({file_size}b) exceeds limit"
            return PlanItem(path, rel_posix, "skip-excluded", reason=reason, prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode), None
    except (IOError, PermissionError) as e:
        log.warning(f"Could not stat file {path}: {e}")
        return PlanItem(path, rel_posix, "skip-excluded", reason=f"stat failed: {e}", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode), None

    if rel_posix in cache and cache[rel_posix]["mtime"] == mtime:
        return PlanItem(path, rel_posix, "skip-cached", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode), (rel_posix, cache[rel_posix])

    lines = filesystem.read_file_lines(path)
    file_hash = filesystem.get_file_hash(lines)
    cache_entry = {"mtime": mtime, "hash": file_hash}

    is_ignored = False
    for line in lines:
        if INLINE_IGNORE_COMMENT in line:
            is_ignored = True
            break
    
    if is_ignored:
        return PlanItem(path, rel_posix, "skip-excluded", reason="inline ignore", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode), (rel_posix, cache_entry)

    expected = headerlogic.header_line_for(rel_posix, lang.template)
    analysis = headerlogic.analyze_header_state(
        lines, expected, lang.prefix, lang.check_encoding, lang.analysis_mode
    )

    if remove:
        if analysis.existing_header_line is not None:
            return PlanItem(path, rel_posix, "remove", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode), (rel_posix, cache_entry)
        else:
            return PlanItem(path, rel_posix, "skip-header-exists", reason="no-header-to-remove", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode), (rel_posix, cache_entry)

    if analysis.has_correct_header:
        return PlanItem(path, rel_posix, "skip-header-exists", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode), (rel_posix, cache_entry)

    if analysis.existing_header_line is None:
        return PlanItem(path, rel_posix, "add", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode), (rel_posix, cache_entry)

    if override:
        return PlanItem(path, rel_posix, "override", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode), (rel_posix, cache_entry)
    else:
        return PlanItem(path, rel_posix, "skip-header-exists", reason="incorrect-header-no-override", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode), (rel_posix, cache_entry)


def plan_files(
    root: Path,
    *,
    depth: int | None,
    excludes: List[str],
    override: bool,
    remove: bool,
    # --- MODIFIED ---
    languages: List[LanguageConfig],
    workers: int,
) -> Tuple[List[PlanItem], dict]:
    """
    Plan all actions to be taken. This is now an orchestrator
    and does not contain any I/O logic itself.
    """
    out: List[PlanItem] = []
    use_cache = not override and not remove
    cache = filesystem.load_cache(root) if use_cache else {}
    new_cache = {}

    file_iterator = list(filesystem.find_configured_files(root, languages))

    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = track(
            executor.map(
                lambda args: _analyze_single_file(
                    args, root, excludes, depth, override, remove, cache
                ),
                file_iterator,
            ),
            description="Planning files...",
            console=ui.console,
            disable=ui.console.quiet,
            transient=True,
            total=len(file_iterator),
        )
        for plan_item, cache_info in results:
            out.append(plan_item)
            if cache_info:
                rel_posix, cache_entry = cache_info
                new_cache[rel_posix] = cache_entry

    return out, new_cache


def write_with_header(
    item: PlanItem,
    *,
    backup: bool,
    dry_run: bool,
    blank_lines_after: int,
    # --- prefix: str is no longer needed ---
) -> Tuple[str, float, str]:
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
        original_lines, expected, item.prefix, item.check_encoding, item.analysis_mode
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

    new_mtime = path.stat().st_mtime
    new_hash = filesystem.get_file_hash(new_lines)

    return item.action, new_mtime, new_hash