# src/autoheader/cli.py

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import List

from .walker import ensure_root_or_confirm
from .core import (
    DEFAULT_EXCLUDES,
    plan_files,
    write_with_header,
)

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="autoheader",
        description="Add a '# <relative/path.py>' header to Python files, safely and repeatably.",
    )

    # Dry-run by default; allow explicit --dry-run and --no-dry-run
    g = p.add_mutually_exclusive_group()
    g.add_argument("--dry-run", dest="dry_run", action="store_true", help="Do not write changes (default).")
    g.add_argument("--no-dry-run", dest="dry_run", action="store_false", help="Apply changes to files.")
    p.set_defaults(dry_run=True)

    p.add_argument("-y", "--yes", action="store_true", help="Assume yes when root detection is inconclusive.")
    p.add_argument("--depth", type=int, default=None, help="Max directory depth from root (e.g., 3).")
    p.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help="Extra glob(s) to exclude (can repeat). Defaults also exclude common dangerous paths.",
    )
    p.add_argument("--override", action="store_true", help="Rewrite existing header lines to fresh, correct ones.")
    p.add_argument("--backup", action="store_true", help="Create .bak backups before writing.")
    p.add_argument("--verbose", "-v", action="count", default=0, help="Increase verbosity.")
    p.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Root directory (default: current working directory).",
    )

    return p

def main(argv: List[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # Root confirmation
    if not ensure_root_or_confirm(auto_yes=args.yes):
        print("autoheader: Aborted.")
        return 1

    root: Path = args.root.resolve()

    if args.verbose:
        print(f"autoheader: using root = {root}")
        print(f"autoheader: dry_run = {args.dry_run}, override = {args.override}, backup = {args.backup}")
        if args.depth is not None:
            print(f"autoheader: depth guard = {args.depth}")
        print(f"autoheader: default excludes = {sorted(DEFAULT_EXCLUDES)}")
        if args.exclude:
            print(f"autoheader: extra excludes = {args.exclude}")

    plan = plan_files(
        root,
        depth=args.depth,
        excludes=args.exclude,
        override=args.override,
    )

    added = overridden = skipped_exists = skipped_excluded = 0
    for item in plan:
        rel = item.rel_posix

        if item.action in ("skip-excluded", "skip-nonpy"):
            skipped_excluded += 1
            if args.verbose:
                reason = f" ({item.reason})" if item.reason else ""
                print(f"SKIP: {rel} [excluded{reason}]")
            continue

        if item.action == "skip-header-exists":
            skipped_exists += 1
            if args.verbose:
                print(f"OK:   {rel} [header ok]")
            continue

        # write
        action_done = write_with_header(
            item.path,
            root=root,
            override=(item.action == "override"),
            backup=args.backup,
            dry_run=args.dry_run,
        )
        if action_done == "override":
            overridden += 1
            print(f"{'DRY ' if args.dry_run else ''}OVERRIDE: {rel}")
        else:
            added += 1
            print(f"{'DRY ' if args.dry_run else ''}ADD:      {rel}")

    # summary
    print(
        f"\nSummary: added={added}, overridden={overridden}, "
        f"skipped_ok={skipped_exists}, skipped_excluded={skipped_excluded}."
    )
    if args.dry_run:
        print("NOTE: this was a dry run. Use --no-dry-run to apply changes.")

    return 0

if __name__ == "__main__":
    sys.exit(main())
