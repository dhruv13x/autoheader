# src/autoheader/cli.py


import argparse
from pathlib import Path
import sys
from typing import List
import logging
import importlib.metadata
import time

# --- ADD THIS ---
try:
    from rich_argparse import RichHelpFormatter
except ImportError:
    # Fallback for environments where rich-argparse isn't installed
    RichHelpFormatter = argparse.HelpFormatter  # type: ignore
# --- END ADD ---

# Add TimeoutError
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

from . import app
from . import ui
from .banner import print_logo
from . import config
# --- MODIFIED ---
from .constants import (
    DEFAULT_EXCLUDES,
    ROOT_MARKERS,
    CONFIG_FILE_NAME,  # <-- ADD THIS
)
from .core import (
    plan_files,
    write_with_header,
)
# --- ADD THIS IMPORT ---
from . import filesystem
from .models import PlanItem, RuntimeContext

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
        description="Add a repo-relative path header to source files, safely and repeatably.",
        # --- ADD THIS LINE ---
        formatter_class=RichHelpFormatter,
    )

    p.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {get_version()}",
    )

    p.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="Specific files to process. If not provided, scans the root directory.",
    )

    # --- REORGANIZED FOR CLEANER HELP PANELS ---

    # --- Main Actions ---
    g_action = p.add_argument_group("Main Actions")
    g_dry = g_action.add_mutually_exclusive_group()
    g_dry.add_argument(
        "-d", "--dry-run", dest="dry_run", action="store_true", help="Do not write changes (default)."
    )
    g_dry.add_argument(
        "-nd", "--no-dry-run", dest="dry_run", action="store_false", help="Apply changes to files."
    )
    
    g_mode = g_action.add_mutually_exclusive_group()
    g_mode.add_argument(
        "--override",
        action="store_true",
        help="Rewrite existing header lines to fresh, correct ones.",
    )
    g_mode.add_argument(
        "--remove", action="store_true", help="Remove all autoheader lines from files."
    )

    # --- CI & Pre-commit ---
    g_ci = p.add_argument_group("CI / Pre-commit / Init")
    g_ci.add_argument(
        "--check-hash",
        action="store_true",
        help="Verify file integrity by checking content hash in headers.",
    )
    g_ci_mode = g_ci.add_mutually_exclusive_group()
    g_ci_mode.add_argument(
        "--check",
        action="store_true",
        help="Exit with code 1 if any file needs header changes (for pre-commit/CI).",
    )
    g_ci_mode.add_argument(
        "--install-precommit",
        action="store_true",
        help="Install autoheader as a 'repo: local' pre-commit hook.",
    )
    # --- ADD THIS ---
    g_ci_mode.add_argument(
        "--init",
        action="store_true",
        help="Create a default 'autoheader.toml' in the current directory.",
    )
    # --- END ADD ---

    # --- General Behavior ---
    g_config = p.add_argument_group("General Behavior")
    g_config.add_argument(
        "-y", "--yes", action="store_true", help="Assume yes to all confirmation prompts."
    )
    g_config.add_argument("--backup", action="store_true", help="Create .bak backups before writing.")
    g_config.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Root directory (default: current working directory).",
    )
    g_config.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Number of parallel workers to use (default: 8).",
    )
    # --- ADD THIS ---
    g_config.add_argument(
        "--timeout",
        type=float,
        help="Timeout in seconds for processing a single file. (Config: [general] timeout)",
    )
    g_config.add_argument("--config-url", type=str, help="URL to fetch remote configuration from.")
    g_config.add_argument("--clear-cache", action="store_true", help="Clear the cache before running.")
    # --- END ADD ---

    # --- Filtering & Discovery ---
    g_filter = p.add_argument_group("Filtering & Discovery")
    g_filter.add_argument(
        "--depth", type=int, default=None, help="Max directory depth from root (e.g., 3)."
    )
    g_filter.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help="Extra glob(s) to exclude (can repeat). Defaults also exclude common dangerous paths.",
    )
    g_filter.add_argument(
        "--markers",
        action="append",
        help="Project root markers (overrides TOML and defaults).",
    )

    # --- Header Customization (from TOML) ---
    g_header = p.add_argument_group("Header Customization (via autoheader.toml)")
    g_header.add_argument(
        "--blank-lines-after",
        type=int,
        help="Number of blank lines to add after the header. (Config: [header] blank_lines_after)",
    )
    
    # --- Output Styling ---
    g_output = p.add_argument_group("Output Styling")
    g_verbosity = g_output.add_mutually_exclusive_group()
    g_verbosity.add_argument(
        "--verbose", "-v", action="count", default=0, help="Increase verbosity. (use -vv for more)."
    )
    g_verbosity.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress informational output; only show errors."
    )
    g_output.add_argument("--no-color", action="store_true", help="Disable colored output.")
    g_output.add_argument("--no-emoji", action="store_true", help="Disable emoji prefixes.")
    g_output.add_argument(
        "--format",
        type=str,
        choices=["default", "sarif"],
        default="default",
        help="Output format.",
    )
    
    # --- END REORGANIZATION ---

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
    start_time = time.monotonic()
    print_logo() # Print logo unconditionally at the start
    parser = build_parser()

    # --- MODIFIED: Config Loading ---
    temp_args, remaining_argv = parser.parse_known_args(argv)
    root: Path = temp_args.root.resolve()

    parser.set_defaults(
        markers=ROOT_MARKERS,
        exclude=[],
        blank_lines_after=1,
        timeout=60.0,  # <-- ADD DEFAULT HERE
        # prefix=HEADER_PREFIX  <-- REMOVED
    )

    # Load all TOML data once
    toml_data, toml_path = config.load_config_data(
        root, temp_args.config_url, temp_args.timeout
    )

    # Load general settings
    general_config = config.load_general_config(toml_data)
    parser.set_defaults(**general_config)

    # Final parse
    args = parser.parse_args(argv)
    # --- END MODIFIED ---

    # --- BUG FIX: Configure Rich Console ---
    ui.console.no_color = args.no_color
    ui.console.quiet = args.quiet
    # --- END BUG FIX ---

    # Configure logging as the first step
    setup_logging(args.verbose, args.quiet)

    # --- ADD THIS BLOCK ---
    # Handle --init flag
    if args.init:
        config_path = root / CONFIG_FILE_NAME
        if config_path.exists():
            ui.console.print(f"[red]Error: [bold]{CONFIG_FILE_NAME}[/bold] already exists in this directory.[/red]")
            return 1
        
        try:
            config_content = config.generate_default_config()
            config_path.write_text(config_content, encoding="utf-8")
            # --- THIS IS THE FIX ---
            ui.console.print(f"[green]✅ Created default config at [bold]{config_path}[/bold].[/green]")
            # --- END FIX ---
            return 0
        except Exception as e:
            ui.console.print(f"[red]Failed to create config file: {e}[/red]")
            return 1
    # --- END ADD ---

    # --- NEW: Handle pre-commit installation ---
    if args.install_precommit:
        try:
            from . import precommit
            precommit.install_precommit_config(root)
            return 0
        except (ImportError, AttributeError) as e:
            ui.console.print(f"[red]Failed to install pre-commit hook: {e}[/red]")
            return 1
        except Exception as e:
            ui.console.print(f"[red]Failed to install pre-commit hook: {e}[/red]")
            return 1
    # --- END NEW ---

    # --- ADD THIS BLOCK ---
    if args.clear_cache:
        cache_path = root / ".autoheader_cache"
        if cache_path.exists():
            cache_path.unlink()
            ui.console.print("[bold]Cache cleared.[/bold]")
    # --- END ADD ---

    # Load language configs (MOVED after --init check)
    languages = config.load_language_configs(toml_data, general_config)

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

    # --- MODIFIED BLOCK ---
    # Load .gitignore patterns
    gitignore_excludes = filesystem.load_gitignore_patterns(root)

    # Combine default, TOML, and CLI excludes
    all_excludes = list(DEFAULT_EXCLUDES) + gitignore_excludes + args.exclude
    log.debug(f"Default excludes = {sorted(DEFAULT_EXCLUDES)}")
    if gitignore_excludes:
        log.debug(f"Loaded excludes from .gitignore = {gitignore_excludes}")
    if args.exclude:
        log.debug(f"Extra excludes (from TOML/CLI) = {args.exclude}")
    log.debug(f"Final full exclude list = {all_excludes}")
    # --- END MODIFIED BLOCK ---
    
    log.debug(f"Root markers = {args.markers}")
    log.debug(f"Blank lines after header = {args.blank_lines_after}")
    log.debug(f"Processing timeout = {args.timeout}s")  # <-- ADD LOGGING
    # log.debug(f"Header prefix = {args.prefix}") # <-- REMOVED

    # 1. PLAN
    with ui.console.status("Initializing project context..."):
        context = RuntimeContext(
            root=root,
            excludes=all_excludes,
            depth=args.depth,
            override=args.override,
            remove=args.remove,
            check_hash=args.check_hash,
            timeout=args.timeout,
        )
        plan, new_cache = plan_files(
            context,
            files=[file.resolve() for file in args.files],
            languages=languages,
            workers=args.workers,
        )
    log.info(f"Plan complete. Found {len(plan)} files.")

    # 2. PRE-CALCULATE & FILTER
    added = 0
    overridden = 0
    skipped_exists = 0
    skipped_excluded = 0
    skipped_cached = 0
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
        
        # --- MODIFIED ---
        duration = time.monotonic() - start_time
        ui.console.print(f"[green]✅ autoheader: All headers are correct.[/green] (checked in {duration:.2f}s)")
        # --- END MODIFIED ---
        return 0  # Exit with success
    # --- END NEW ---

    if args.format == "sarif":
        from . import sarif
        report = sarif.generate_sarif_report(items_to_process, str(root))
        print(report)
        return 1 if items_to_process else 0

    # 3. EXECUTE (Now in parallel)
    log.info(f"Applying changes to {len(items_to_process)} files using {args.workers} workers...")

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_item = {
            # --- MODIFIED: Removed prefix, as it's in the PlanItem ---
            executor.submit(
                write_with_header,
                item,
                backup=args.backup,
                dry_run=args.dry_run,
                blank_lines_after=args.blank_lines_after,
            ): item
            for item in items_to_process
        }
        # --- END MODIFIED ---

        for future in as_completed(future_to_item):
            item = future_to_item[future]
            rel = item.rel_posix
            try:
                # --- MODIFIED: Use Rich Output and configurable timeout ---
                action_done, new_mtime, new_hash = future.result(timeout=args.timeout)
                new_cache[rel] = {"mtime": new_mtime, "hash": new_hash}

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

    if not args.dry_run:
        filesystem.save_cache(root, new_cache)

    # 4. REPORT
    # --- MODIFIED: Use Rich Output ---
    ui.console.print(
        ui.format_summary(added, overridden, removed, skipped_exists, skipped_excluded)
    )
    if args.dry_run:
        ui.console.print(ui.format_dry_run_note())
    # --- END MODIFIED ---

    # --- ADD THIS ---
    duration = time.monotonic() - start_time
    if not args.quiet:
        ui.console.print(f"\n✨ Done in {duration:.2f}s.")
    # --- END ADD ---

    return 0


if __name__ == "__main__":
    sys.exit(main())
