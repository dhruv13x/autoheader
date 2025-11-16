# src/autoheader/filesystem.py

from __future__ import annotations
from pathlib import Path
from typing import List, Iterable, Tuple
import logging
import json
import hashlib

# --- ADD THIS ---
from .models import LanguageConfig

# Use logging instead of print
log = logging.getLogger(__name__)


def read_file_lines(path: Path) -> List[str]:
    """
    Safely reads file lines.
    (File size check is now done in core.plan_files before calling this)
    """
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            return f.read().splitlines(keepends=False)
    # Use specific, expected exceptions
    except (IOError, PermissionError, UnicodeDecodeError) as e:
        log.warning(f"Failed to read {path}: {e}")
        return []
    except Exception as e:
        log.error(f"An unexpected error occurred while reading {path}: {e}")
        return []


def write_file_content(
    path: Path,
    new_content: str,
    original_content: str,
    backup: bool,
    dry_run: bool,
) -> None:
    """
    Safely writes new content to a file, with backup logic.
    Preserves original file permissions.
    """
    if dry_run:
        return

    try:
        # 1. Get original permissions
        original_mode = path.stat().st_mode
    except (IOError, PermissionError) as e:
        log.error(f"Failed to read permissions for {path}: {e}")
        # Re-raise to be caught by the thread pool
        raise

    # Optional backup
    if backup:
        bak = path.with_suffix(path.suffix + ".bak")
        try:
            bak.write_text(original_content, encoding="utf-8")
            # 2. Copy permissions to backup file
            bak.chmod(original_mode)
        except (IOError, PermissionError) as e:
            log.error(f"Failed to create backup {bak}: {e}")
            # Re-raise to be caught by the thread pool
            raise

    # Write result
    try:
        path.write_text(new_content, encoding="utf-8")
        # 3. Restore original permissions
        path.chmod(original_mode)
    except (IOError, PermissionError) as e:
        log.error(f"Failed to write file {path}: {e}")
        # Re-raise to be caught by the thread pool
        raise


def load_gitignore_patterns(root: Path) -> List[str]:
    """
    Loads and parses .gitignore patterns from the project root.
    - Ignores comments (#)
    - Ignores blank lines
    - Strips whitespace
    """
    gitignore_path = root / ".gitignore"
    if not gitignore_path.is_file():
        log.debug("No .gitignore found, skipping.")
        return []

    patterns: List[str] = []
    try:
        with gitignore_path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                patterns.append(line)
        log.debug(f"Loaded {len(patterns)} patterns from .gitignore.")
        return patterns
    except (IOError, PermissionError) as e:
        log.warning(f"Could not read {gitignore_path}: {e}")
        return []


def get_file_hash(path: Path) -> str:
    """Calculates the SHA256 hash of a file by reading in chunks."""
    sha256 = hashlib.sha256()
    try:
        with path.open("rb") as f:
            while True:
                data = f.read(65536)  # 64KB chunks
                if not data:
                    break
                sha256.update(data)
    except (IOError, PermissionError) as e:
        log.warning(f"Failed to hash {path}: {e}")
        return ""
    return sha256.hexdigest()


def load_cache(root: Path) -> dict:
    """Loads the cache file from the project root."""
    cache_path = root / ".autoheader_cache"
    if not cache_path.is_file():
        return {}
    try:
        with cache_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        log.warning(f"Could not load cache file: {e}")
        return {}


def save_cache(root: Path, cache: dict):
    """Saves the cache to the project root."""
    cache_path = root / ".autoheader_cache"
    try:
        with cache_path.open("w", encoding="utf-8") as f:
            json.dump(cache, f)
    except IOError as e:
        log.warning(f"Could not save cache file: {e}")


# --- REPLACE find_python_files WITH THIS ---
def find_configured_files(
    root: Path, languages: List[LanguageConfig]
) -> Iterable[Tuple[Path, LanguageConfig]]:
    """
    Yields all files matching language globs from the root,
    associating each path with its LanguageConfig.
    """
    seen_paths: set[Path] = set()
    for lang in languages:
        for glob in lang.file_globs:
            log.debug(f"Scanning for glob: {glob} (lang: {lang.name})")
            for path in root.rglob(glob):
                if path in seen_paths:
                    continue  # Handled by a higher-priority language
                
                seen_paths.add(path)

                if path.is_symlink():
                    log.debug(f"Skipping symlink: {path}")
                    continue
                if not path.is_file():
                    continue
                
                yield path, lang
