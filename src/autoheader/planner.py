from __future__ import annotations
from pathlib import Path
from typing import List, Tuple, Iterator
import logging
from concurrent.futures import ThreadPoolExecutor

from .models import PlanItem, LanguageConfig, RuntimeContext
from .constants import MAX_FILE_SIZE_BYTES, INLINE_IGNORE_COMMENT
from . import filters
from . import headerlogic
from . import filesystem

log = logging.getLogger(__name__)

def _analyze_single_file(
    args: Tuple[Path, LanguageConfig, RuntimeContext],
    cache: dict,
) -> Tuple[PlanItem, Tuple[str, dict] | None]:
    """
    Analyzes a single file and determines the required action (add/remove/override/skip).
    Pure business logic.
    """
    path, lang, context = args
    rel_posix = path.relative_to(context.root).as_posix()

    if filters.is_excluded(path, context.root, context.excludes):
        return PlanItem(path, rel_posix, "skip-excluded", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode, license_spdx=lang.license_spdx), None

    if not filters.within_depth(path, context.root, context.depth):
        return PlanItem(path, rel_posix, "skip-excluded", reason="depth", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode, license_spdx=lang.license_spdx), None

    try:
        stat = path.stat()
        mtime = stat.st_mtime
        file_size = stat.st_size
        if file_size > MAX_FILE_SIZE_BYTES:
            reason = f"file size ({file_size}b) exceeds limit"
            return PlanItem(path, rel_posix, "skip-excluded", reason=reason, prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode, license_spdx=lang.license_spdx), None
    except (IOError, PermissionError) as e:
        log.warning(f"Could not stat file {path}: {e}")
        return PlanItem(path, rel_posix, "skip-excluded", reason=f"stat failed: {e}", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode, license_spdx=lang.license_spdx), None

    if rel_posix in cache and cache[rel_posix]["mtime"] == mtime:
        return PlanItem(path, rel_posix, "skip-header-exists", reason="cached", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode, license_spdx=lang.license_spdx), (rel_posix, cache[rel_posix])

    file_hash = filesystem.get_file_hash(path)
    if not file_hash:  # Hashing failed
        return PlanItem(path, rel_posix, "skip-excluded", reason="hash failed", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode, license_spdx=lang.license_spdx), None

    cache_entry = {"mtime": mtime, "hash": file_hash}
    lines = filesystem.read_file_lines(path)

    if not lines:
        return PlanItem(path, rel_posix, "skip-empty", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode, license_spdx=lang.license_spdx), (rel_posix, cache_entry)

    is_ignored = False
    for line in lines:
        if INLINE_IGNORE_COMMENT in line:
            is_ignored = True
            break

    if is_ignored:
        return PlanItem(path, rel_posix, "skip-excluded", reason="inline ignore", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode, license_spdx=lang.license_spdx), (rel_posix, cache_entry)

    content = "\n".join(lines)
    # First, get a preliminary analysis to find the existing header
    prelim_analysis = headerlogic.analyze_header_state(
        lines, "", lang.prefix, lang.check_encoding, lang.analysis_mode, context.check_hash
    )

    expected = headerlogic.header_line_for(
        rel_posix,
        lang.template,
        content,
        prelim_analysis.existing_header_line,
        license_spdx=lang.license_spdx,
        license_owner=lang.license_owner,
    )
    analysis = headerlogic.analyze_header_state(
        lines, expected, lang.prefix, lang.check_encoding, lang.analysis_mode, context.check_hash
    )

    if analysis.has_tampered_header:
        return PlanItem(path, rel_posix, "override", reason="hash mismatch", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode, license_spdx=lang.license_spdx), (rel_posix, cache_entry)

    if context.remove:
        if analysis.existing_header_line is not None:
            return PlanItem(path, rel_posix, "remove", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode, license_spdx=lang.license_spdx), (rel_posix, cache_entry)
        else:
            return PlanItem(path, rel_posix, "skip-header-exists", reason="no-header-to-remove", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode, license_spdx=lang.license_spdx), (rel_posix, cache_entry)

    if analysis.has_correct_header:
        return PlanItem(path, rel_posix, "skip-header-exists", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode, license_spdx=lang.license_spdx), (rel_posix, cache_entry)

    if analysis.existing_header_line is None:
        return PlanItem(path, rel_posix, "add", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode, license_spdx=lang.license_spdx, license_owner=lang.license_owner), (rel_posix, cache_entry)

    if context.override:
        return PlanItem(path, rel_posix, "override", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode, license_spdx=lang.license_spdx, license_owner=lang.license_owner), (rel_posix, cache_entry)
    else:
        return PlanItem(path, rel_posix, "skip-header-exists", reason="incorrect-header-no-override", prefix=lang.prefix, check_encoding=lang.check_encoding, template=lang.template, analysis_mode=lang.analysis_mode, license_spdx=lang.license_spdx, license_owner=lang.license_owner), (rel_posix, cache_entry)


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
) -> Tuple[Iterator[Tuple[PlanItem, dict | None]], int]:
    """
    Plan all actions to be taken. Returns an iterator of (PlanItem, cache_info).
    Does NOT handle UI/Progress.
    Returns: (iterator, total_files)
    """
    use_cache = not context.override and not context.remove
    cache = filesystem.load_cache(context.root) if use_cache else {}

    file_iterator_data = []
    if files:
        for path in files:
            lang = _get_language_for_file(path, languages)
            if lang:
                file_iterator_data.append((path, lang, context))
            else:
                log.warning(f"No language configuration found for file: {path}")
    else:
        file_iterator_data = [
            (path, lang, context)
            for path, lang in filesystem.find_configured_files(context.root, languages)
        ]

    total_files = len(file_iterator_data)

    # We return a generator so the caller can wrap it in progress bar
    def generator():
        with ThreadPoolExecutor(max_workers=workers) as executor:
            # map returns an iterator
            results = executor.map(
                lambda args: _analyze_single_file(args, cache),
                file_iterator_data,
            )
            for result in results:
                yield result

    return generator(), total_files
