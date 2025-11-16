# src/autoheader/core.py

from __future__ import annotations
from pathlib import Path
from typing import List, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor

# --- MODIFIED ---
from .models import PlanItem, LanguageConfig, RuntimeContext
from .constants import MAX_FILE_SIZE_BYTES, INLINE_IGNORE_COMMENT
# --- END MODIFIED ---
from . import filters
from . import headerlogic
from . import filesystem
from . import ui
from rich.progress import track


log = logging.getLogger(__name__)


def _analyze_single_file(
    args: Tuple[Path, LanguageConfig, RuntimeContext],
    cache: dict,
) -> Tuple[PlanItem, Tuple[str, dict] | None]:
    path, lang, context = args
    rel_posix = path.relative_to(context.root).as_posix()

    if filters.is_excluded(path, context.root, context.excludes):
        return PlanItem(path, rel_posix, "skip-excluded", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode), None

    if not filters.within_depth(path, context.root, context.depth):
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
        return PlanItem(path, rel_posix, "skip-header-exists", reason="cached", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode), (rel_posix, cache[rel_posix])

    file_hash = filesystem.get_file_hash(path)
    if not file_hash:  # Hashing failed
        return PlanItem(path, rel_posix, "skip-excluded", reason="hash failed", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode), None

    cache_entry = {"mtime": mtime, "hash": file_hash}
    lines = filesystem.read_file_lines(path)

    if not lines:
        return PlanItem(path, rel_posix, "skip-empty", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode), (rel_posix, cache_entry)

    is_ignored = False
    for line in lines:
        if INLINE_IGNORE_COMMENT in line:
            is_ignored = True
            break
    
    if is_ignored:
        return PlanItem(path, rel_posix, "skip-excluded", reason="inline ignore", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode), (rel_posix, cache_entry)

    content = "\n".join(lines)
    # First, get a preliminary analysis to find the existing header
    prelim_analysis = headerlogic.analyze_header_state(
        lines, "", lang.prefix, lang.check_encoding, lang.analysis_mode, context.check_hash
    )
    expected = headerlogic.header_line_for(
        rel_posix, lang.template, content, prelim_analysis.existing_header_line
    )
    analysis = headerlogic.analyze_header_state(
        lines, expected, lang.prefix, lang.check_encoding, lang.analysis_mode, context.check_hash
    )

    if analysis.has_tampered_header:
        return PlanItem(path, rel_posix, "override", reason="hash mismatch", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode), (rel_posix, cache_entry)

    if context.remove:
        if analysis.existing_header_line is not None:
            return PlanItem(path, rel_posix, "remove", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode), (rel_posix, cache_entry)
        else:
            return PlanItem(path, rel_posix, "skip-header-exists", reason="no-header-to-remove", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode), (rel_posix, cache_entry)

    if analysis.has_correct_header:
        return PlanItem(path, rel_posix, "skip-header-exists", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode), (rel_posix, cache_entry)

    if analysis.existing_header_line is None:
        return PlanItem(path, rel_posix, "add", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode), (rel_posix, cache_entry)

    if context.override:
        return PlanItem(path, rel_posix, "override", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode), (rel_posix, cache_entry)
    else:
        return PlanItem(path, rel_posix, "skip-header-exists", reason="incorrect-header-no-override", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode), (rel_posix, cache_entry)


def _get_language_for_file(path: Path, languages: List[LanguageConfig]) -> LanguageConfig | None:
    """Finds the first language config that matches the file path."""
    for lang in languages:
        for glob in lang.file_globs:
            if path.match(glob):
                return lang
    return None

def plan_files(
    context: RuntimeContext,
    files: List[Path] | None,
    languages: List[LanguageConfig],
    workers: int,
) -> Tuple[List[PlanItem], dict]:
    """
    Plan all actions to be taken. This is now an orchestrator
    and does not contain any I/O logic itself.
    """
    out: List[PlanItem] = []
    use_cache = not context.override and not context.remove
    cache = filesystem.load_cache(context.root) if use_cache else {}
    new_cache = {}

    if files:
        file_iterator = []
        for path in files:
            lang = _get_language_for_file(path, languages)
            if lang:
                file_iterator.append((path, lang, context))
            else:
                log.warning(f"No language configuration found for file: {path}")
    else:
        file_iterator = [
            (path, lang, context)
            for path, lang in filesystem.find_configured_files(context.root, languages)
        ]

    with ThreadPoolExecutor(max_workers=workers) as executor:
        # We need to pass the cache dict to each call, but executor.map only iterates
        # over the primary iterator. A lambda can capture the cache.
        results = track(
            executor.map(
                lambda args: _analyze_single_file(args, cache),
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
    
    original_lines = filesystem.read_file_lines(path)
    analysis = headerlogic.analyze_header_state(
        original_lines, "", item.prefix, item.check_encoding, item.analysis_mode
    )
    expected = headerlogic.header_line_for(
        rel_posix, item.template, existing_header=analysis.existing_header_line
    )
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

    if dry_run and item.action in ("add", "override"):
        ui.show_header_diff(rel_posix, analysis.existing_header_line, expected)

    filesystem.write_file_content(
        path,
        new_text,
        original_content,
        backup=backup,
        dry_run=dry_run,
    )

    new_mtime = path.stat().st_mtime
    new_hash = filesystem.get_file_hash(path)

    return item.action, new_mtime, new_hash
