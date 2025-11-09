from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import List
import logging
import importlib.metadata  # <-- NEW

# Add TimeoutError
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

from . import app
from . import ui  # <-- NEW
from .constants import DEFAULT_EXCLUDES
from .core import (
    plan_files,
    write_with_header,
)
from .models import PlanItem

# Get the root logger for our application
log = logging.getLogger("autoheader")


def get_version() -> str:  # <-- NEW FUNCTION
    """Get package version from metadata."""
    try:
        # Get version from package metadata
        return importlib.metadata.version("autoheader")
    except importlib.metadata.PackageNotFoundError:
        # Fallback for when not installed (e.g., running from source)
        return "0.1.0-dev"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="autoheader",
        description="Add a '# <relative/path.py>' header to Python files, safely and repeatably.",
    )

    p.add_argument(  # <-- NEW
        "--version",
        action="version",
        version=f"%(prog)s {get_version()}",
    )

    # Dry-run by default; allow explicit --dry-run and --no-dry-run
    g_dry = p.add_mutually_exclusive_group()
    g_dry.add_argument(  # <-- MODIFIED
        "-d", "--dry-run", dest="dry_run", action="store_true", help="Do not write changes (default)."
    )
    g_dry.add_argument(  # <-- MODIFIED
        "-nd", "--no-dry-run", dest="dry_run", action="store_false", help="Apply changes to files."
    )
    p.set_defaults(dry_run=True)

    # --- NEW FEATURE ---
    # Add mutually exclusive group for override/remove
    g_action = p.add_mutually_exclusive_group()
    g_action.add_argument(
        "--override",
        action="store_true",
        help="Rewrite existing header lines to fresh, correct ones.",
    )
    g_action.add_argument(
        "--remove", action="store_true", help="Remove all autoheader lines from files."
    )

    p.add_argument(
        "-y", "--yes", action="store_true", help="Assume yes to all confirmation prompts."
    )
    p.add_argument(
        "--depth", type=int, default=None, help="Max directory depth from root (e.g., 3)."
    )
    p.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help="Extra glob(s) to exclude (can repeat). Defaults also exclude common dangerous paths.",
    )
    p.add_argument("--backup", action="store_true", help="Create .bak backups before writing.")

    # --- NEW: Verbosity Group ---
    g_verbosity = p.add_mutually_exclusive_group()
    g_verbosity.add_argument(
        "--verbose", "-v", action="count", default=0, help="Increase verbosity. (use -vv for more)."
    )
    g_verbosity.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress informational output; only show errors."
    )
    # --- END NEW ---

    p.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Root directory (default: current working directory).",
    )
    p.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Number of parallel workers to use (default: 8).",
    )

    return p


def setup_logging(verbosity: int, quiet: bool) -> None:  # <-- MODIFIED
    """Configure logging based on verbosity."""
    if quiet:  # <-- NEW
        level = logging.ERROR
    elif verbosity >= 2:
        level = logging.DEBUG
    elif verbosity == 1:
        level = logging.INFO
    else:
        level = logging.INFO  # Default to INFO

    logging.basicConfig(
        level=level,
        format="%(message)s",
    )
    logging.getLogger("autoheader").name = "autoheader:"


def main(argv: List[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # Configure logging as the first step
    setup_logging(args.verbose, args.quiet)  # <-- MODIFIED

    root: Path = args.root.resolve()

    # Root confirmation uses the new app orchestrator
    if not app.ensure_root_or_confirm(path_to_check=root, auto_yes=args.yes):
        # Note: ui.py now handles the "Aborted" message
        return 1

    # --- NEW: Confirmation for --no-dry-run ---
    if not args.dry_run and not args.yes:
        needs_backup_warning = not args.backup
        if not ui.confirm_no_dry_run(needs_backup_warning):
            return 1
    # --- END NEW ---

    log.debug(f"Using root = {root}")
    log.debug(
        f"Run config: dry_run={args.dry_run}, override={args.override}, remove={args.remove}, backup={args.backup}"
    )
    if args.depth is not None:
        log.debug(f"Depth guard = {args.depth}")
    log.debug(f"Default excludes = {sorted(DEFAULT_EXCLUDES)}")
    if args.exclude:
        log.debug(f"Extra excludes = {args.exclude}")

    # 1. PLAN
    log.info(f"Planning changes for {root}...")
    plan = plan_files(
        root,
        depth=args.depth,
        excludes=args.exclude,
        override=args.override,
        remove=args.remove,
    )
    log.info(f"Plan complete. Found {len(plan)} files.")

    # 2. PRE-CALCULATE & FILTER
    added = 0
    overridden = 0
    skipped_exists = 0
    skipped_excluded = 0
    removed = 0
    items_to_process: List[PlanItem] = []

    for item in plan:
        if item.action in ("skip-excluded", "skip-nonpy"):
            skipped_excluded += 1
            log.debug(f"SKIP: {item.rel_posix} [excluded{item.reason or ''}]")
        elif item.action == "skip-header-exists":
            skipped_exists += 1
            log.debug(f"OK:   {item.rel_posix} [header ok {item.reason or ''}]")
        else:
            items_to_process.append(item)

    # 3. EXECUTE (Now in parallel)
    log.info(f"Applying changes to {len(items_to_process)} files using {args.workers} workers...")

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_item = {
            executor.submit(write_with_header, item, backup=args.backup, dry_run=args.dry_run): item
            for item in items_to_process
        }

        for future in as_completed(future_to_item):
            item = future_to_item[future]
            rel = item.rel_posix
            try:
                action_done = future.result(timeout=60.0)

                if action_done == "override":
                    overridden += 1
                    log.info(f"{'DRY ' if args.dry_run else ''}OVERRIDE: {rel}")
                elif action_done == "add":
                    added += 1
                    log.info(f"{'DRY ' if args.dry_run else ''}ADD:      {rel}")
                elif action_done == "remove":
                    removed += 1
                    log.info(f"{'DRY ' if args.dry_run else ''}REMOVE:   {rel}")

            except TimeoutError:
                log.error(f"Failed to process {rel}: Operation timed out after 60s")
            except Exception as e:
                log.error(f"Failed to process {rel}: {e}")

    # 4. REPORT
    log.info(
        f"\nSummary: added={added}, overridden={overridden}, removed={removed}, "
        f"skipped_ok={skipped_exists}, skipped_excluded={skipped_excluded}."
    )
    if args.dry_run:
        log.info("NOTE: this was a dry run. Use --no-dry-run to apply changes.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
