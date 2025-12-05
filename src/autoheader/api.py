from __future__ import annotations
from pathlib import Path
from typing import List, Literal, NamedTuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import config
from . import filesystem
from . import planner
from . import core
from .models import RuntimeContext, PlanItem, LanguageConfig
from .constants import ROOT_MARKERS

@dataclass
class HeaderResult:
    path: Path
    status: str  # "added", "overridden", "removed", "skipped-...", "error"
    mtime: float | None = None
    hash: str | None = None
    error: str | None = None
    diff: tuple[str, str, str] | None = None # rel_path, old, new


class AutoHeader:
    """
    Official Python SDK for autoheader.

    Usage:
        ah = AutoHeader(root=".")
        results = ah.apply(paths=["src/"])
    """
    def __init__(self, root: str | Path = ".", config_url: str | None = None, timeout: float = 60.0):
        self.root = Path(root).resolve()
        self.timeout = timeout

        # Load configuration
        toml_data, _ = config.load_config_data(self.root, config_url, timeout)
        self.general_config = config.load_general_config(toml_data)
        self.languages = config.load_language_configs(toml_data, self.general_config)

        # Override general config with provided args if needed,
        # but for now we just stick to what's in TOML + defaults.

        # Load excludes
        gitignore_excludes = filesystem.load_gitignore_patterns(self.root)
        self.excludes = list(self.general_config.get("exclude", [])) + gitignore_excludes

    def _execute(
        self,
        paths: List[str | Path] | None,
        mode: Literal["apply", "remove", "check"],
        dry_run: bool = False,
        override: bool = False,
        workers: int | None = None
    ) -> List[HeaderResult]:

        if paths:
            files_to_process = [Path(p).resolve() for p in paths]
        else:
            files_to_process = None # Will trigger auto-discovery

        workers = workers or self.general_config.get("workers", 8)

        # Determine context flags based on mode
        remove = (mode == "remove")
        check_mode = (mode == "check")

        # For "apply", we might be in override mode
        is_override = override and mode == "apply"

        context = RuntimeContext(
            root=self.root,
            excludes=self.excludes,
            depth=None, # TODO: Expose depth in init or methods?
            override=is_override,
            remove=remove,
            check_hash=False, # TODO: Expose check_hash
            timeout=self.timeout,
        )

        plan_generator, _ = planner.plan_files(
            context,
            files=files_to_process,
            languages=self.languages,
            workers=workers,
        )

        # Collect plan items
        # Note: planner returns (PlanItem, cache_info)
        plan_items: List[PlanItem] = []
        new_cache = {}

        for item, cache_info in plan_generator:
            if cache_info:
                rel, entry = cache_info
                new_cache[rel] = entry
            plan_items.append(item)

        results: List[HeaderResult] = []

        # If check mode, we just analyze the plan
        if check_mode:
            for item in plan_items:
                status = "ok"
                if item.action in ("add", "override", "remove"):
                    status = "fail"
                elif item.action.startswith("skip-"):
                    status = "ok" # skipped means no change needed usually, or ignored

                # If the action is add/override/remove, it means the file is NOT compliant
                # So for check mode:
                # add -> fail (needs header)
                # override -> fail (wrong header)
                # remove -> fail (has header but shouldn't)

                # However, PlanItem.action tells us what *needs to be done*.
                # If action is 'skip-header-exists', status is OK.

                res_status = "ok"
                if item.action in ("add", "override", "remove"):
                    res_status = "fail"

                results.append(HeaderResult(
                    path=item.path,
                    status=res_status
                ))
            return results

        # Execute write/remove
        # Filter items to process
        to_process = [
            item for item in plan_items
            if item.action not in ("skip-excluded", "skip-header-exists")
        ]

        # Also add skipped items to results for completeness?
        # The user might want to know what happened to all files.
        for item in plan_items:
            if item.action in ("skip-excluded", "skip-header-exists"):
                 results.append(HeaderResult(path=item.path, status=item.action))

        if not to_process:
            return results

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_item = {
                executor.submit(
                    core.write_with_header,
                    item,
                    backup=False, # TODO: Expose backup
                    dry_run=dry_run,
                    blank_lines_after=self.general_config.get("blank_lines_after", 1),
                ): item
                for item in to_process
            }

            for future in as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    action_done, new_mtime, new_hash, diff_info = future.result(timeout=self.timeout)
                    if not dry_run:
                        # Update cache for this file
                        rel = item.rel_posix
                        new_cache[rel] = {"mtime": new_mtime, "hash": new_hash}

                    results.append(HeaderResult(
                        path=item.path,
                        status=action_done,
                        mtime=new_mtime,
                        hash=new_hash,
                        diff=diff_info
                    ))
                except Exception as e:
                    results.append(HeaderResult(
                        path=item.path,
                        status="error",
                        error=str(e)
                    ))

        if not dry_run:
            filesystem.save_cache(self.root, new_cache)

        return results

    def apply(self, paths: List[str | Path] | None = None, dry_run: bool = False, override: bool = False) -> List[HeaderResult]:
        """
        Apply headers to files.
        """
        return self._execute(paths, mode="apply", dry_run=dry_run, override=override)

    def remove(self, paths: List[str | Path] | None = None, dry_run: bool = False) -> List[HeaderResult]:
        """
        Remove headers from files.
        """
        return self._execute(paths, mode="remove", dry_run=dry_run)

    def check(self, paths: List[str | Path] | None = None) -> List[HeaderResult]:
        """
        Check if files have correct headers.
        Returns list of results with status="ok" or "fail".
        """
        return self._execute(paths, mode="check")
