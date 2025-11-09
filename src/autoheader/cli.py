# src/autoheader/cli.py

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import List
import logging
import importlib.metadata

# Add TimeoutError
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

from . import app
from . import ui
from . import config
from .constants import DEFAULT_EXCLUDES, ROOT_MARKERS
from .core import (
    plan_files,
    write_with_header,
)
from .models import PlanItem

# Get the root logger for our application
log = logging.getLogger("autoheader")


def get_version() -> str:
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

    p.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {get_version()}",
    )

    # Dry-run by default; allow explicit --dry-run and --no-dry-run
    g_dry = p.add_mutually_exclusive_group()
    g_dry.add_argument(
        "-d", "--dry-run", dest="dry_run", action="store_true", help="Do not write changes (default)."
    )
    g_dry.add_argument(
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
    
    # --- NEW: Check/Install Group ---
    g_ci = p.add_mutually_exclusive_group()
    g_ci.add_argument(
        "--check",
        action="store_true",
        help="Exit with code 1 if any file needs header changes (for pre-commit/CI).",
    )
    g_ci.add_argument(
        "--install-precommit",
        action="store_true",
        help="Install autoheader as a 'repo: local' pre-commit hook.",
    )
    # --- END NEW ---

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

    # --- NEW: Output Styling Group ---
    g_output = p.add_argument_group("Output Styling")
    g_output.add_argument("--no-color", action="store_true", help="Disable colored output.")
    g_output.add_argument("--no-emoji", action="store_true", help="Disable emoji prefixes.")
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

    # --- NEW: Config-driven args ---
    p.add_argument(
        "--blank-lines-after",
        type=int,
        help="Number of blank lines to add after the header.",
    )
    p.add_argument(
        "--markers",
        action="append",
        help="Project root markers (overrides TOML and defaults).",
    )
    # --- END NEW ---

    return p


def setup_logging(verbosity: int, quiet: bool) -> None:
    """Configure logging based on verbosity."""
    if quiet:
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
    parser = build_parser()

    # --- NEW: Config Loading ---
    # 1. First pass: just to find the --root
    temp_args, remaining_argv = parser.parse_known_args(argv)
    root: Path = temp_args.root.resolve()

    # 2. Set defaults from constants *before* TOML
    parser.set_defaults(
        markers=ROOT_MARKERS,
        exclude=[],
        blank_lines_after=1
    )

    # 3. Load config from TOML
    toml_config = config.load_config(root)

    # 4. Set TOML values as new defaults (will be overridden by CLI)
    parser.set_defaults(**toml_config)

    # 5. Final parse: CLI args override TOML, which overrode constants
    args = parser.parse_args(argv)
    # --- END NEW ---

    # --- BUG FIX: Configure Rich Console ---
    ui.console.no_color = args.no_color
    ui.console.quiet = args.quiet
    # --- END BUG FIX ---

    # Configure logging as the first step
    setup_logging(args.verbose, args.quiet)

    # --- NEW: Handle pre-commit installation ---
    if args.install_precommit:
        try:
            from . import precommit
            precommit.install_precommit_config(root)
            return 0
        except ImportError:
            # Error is already printed by precommit.py
            return 1
        except Exception as e:
            ui.console.print(f"[red]Failed to install pre-commit hook: {e}[/red]")
            return 1
    # --- END NEW ---

    # Root confirmation uses the new app orchestrator
    if not app.ensure_root_or_confirm(
        path_to_check=root,
        auto_yes=args.yes,
        markers=args.markers
    ):
        return 1

    # --- NEW: Confirmation for --no-dry-run (skip in check mode) ---
    if not args.dry_run and not args.yes and not args.check:
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

    # Combine default, TOML, and CLI excludes
    all_excludes = list(DEFAULT_EXCLUDES) + args.exclude
    log.debug(f"Default excludes = {sorted(DEFAULT_EXCLUDES)}")
    if args.exclude:
        log.debug(f"Extra excludes (from TOML/CLI) = {args.exclude}")
    log.debug(f"Final full exclude list = {all_excludes}")
    log.debug(f"Root markers = {args.markers}")
    log.debug(f"Blank lines after header = {args.blank_lines_after}")

    # 1. PLAN
    log.info(f"Planning changes for {root}...")
    plan = plan_files(
        root,
        depth=args.depth,
        excludes=all_excludes,
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
        if item.action == "skip-excluded":
            skipped_excluded += 1
            log.debug(f"SKIP (excluded): {item.rel_posix} [reason: {item.reason or 'default'}]")
        elif item.action == "skip-header-exists":
            skipped_exists += 1
            log.debug(f"SKIP (ok):   {item.rel_posix} [reason: {item.reason or 'header ok'}]")
        else:
            items_to_process.append(item)

    # --- NEW: Check Mode ---
    if args.check:
        if items_to_process:
            ui.console.print("[red]autoheader: The following files require header changes:[/red]")
            for item in items_to_process:
                 ui.console.print(f"- [yellow]{item.rel_posix}[/yellow] (Action: {item.action})")
            ui.console.print("\n[bold]Run 'autoheader --no-dry-run' to fix.[/bold]")
            return 1  # Exit with error
        
        ui.console.print("[green]✅ autoheader: All headers are correct.[/green]")
        return 0  # Exit with success
    # --- END NEW ---

    # 3. EXECUTE (Now in parallel)
    log.info(f"Applying changes to {len(items_to_process)} files using {args.workers} workers...")

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_item = {
            executor.submit(
                write_with_header,
                item,
                backup=args.backup,
                dry_run=args.dry_run,
                blank_lines_after=args.blank_lines_after,
            ): item
            for item in items_to_process
        }

        for future in as_completed(future_to_item):
            item = future_to_item[future]
            rel = item.rel_posix
            try:
                # --- MODIFIED: Use Rich Output ---
                action_done = future.result(timeout=60.0)

                if action_done == "override":
                    overridden += 1
                elif action_done == "add":
                    added += 1
                elif action_done == "remove":
                    removed += 1
                
                prefix = "DRY " if args.dry_run else ""
                action_name = f"{prefix}{action_done.upper()}"
                ui.console.print(ui.format_action(action_name, rel, args.no_emoji, args.dry_run))

            except TimeoutError as e:
                ui.console.print(ui.format_error(rel, e, args.no_emoji))
            except Exception as e:
                ui.console.print(ui.format_error(rel, e, args.no_emoji))
            # --- END MODIFIED ---

    # 4. REPORT
    # --- MODIFIED: Use Rich Output ---
    ui.console.print(
        ui.format_summary(added, overridden, removed, skipped_exists, skipped_excluded)
    )
    if args.dry_run:
        ui.console.print(ui.format_dry_run_note())
    # --- END MODIFIED ---

    return 0


if __name__ == "__main__":
    sys.exit(main())