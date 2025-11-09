# src/autoheader/filesystem.py

from __future__ import annotations
from pathlib import Path
from typing import List, Iterable
import logging

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


def find_python_files(root: Path) -> Iterable[Path]:
    """Yields all .py files from the root, skipping symlinks."""
    for path in root.rglob("*.py"):
        if path.is_symlink():
            log.debug(f"Skipping symlink: {path}")
            continue
        if not path.is_dir():
            yield path
