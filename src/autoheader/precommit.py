# src/autoheader/precommit.py

from __future__ import annotations
import logging
from pathlib import Path
from . import ui

try:
    import yaml
except ImportError:
    ui.console.print("[red]PyYAML not found.[/red]")
    ui.console.print("Please install with: [bold]pip install autoheader[precommit][/bold]")
    raise

log = logging.getLogger(__name__)

# This hook uses `language: system` to run the `autoheader`
# command available in the user's environment.
LOCAL_AUTOHEADER_HOOK = {
    "id": "autoheader",
    "name": "autoheader file header checker",
    "entry": "autoheader --check",
    "language": "system",
    "types": ["python"],
    "pass_filenames": True,
}


def install_precommit_config(root: Path):
    """
    Finds or creates .pre-commit-config.yaml and adds the
    autoheader hook to it.
    """
    config_path = root / ".pre-commit-config.yaml"

    if not config_path.exists():
        ui.console.print(f"[green]Creating {config_path}...[/green]")
        # Create a config with a 'local' repo
        cfg = {"repos": [{"repo": "local", "hooks": [LOCAL_AUTOHEADER_HOOK]}]}
        try:
            with config_path.open("w", encoding="utf-8") as f:
                yaml.safe_dump(cfg, f)
            ui.console.print("[green]✅ autoheader hook installed.[/green]")
            ui.console.print("\n[bold]Run 'pre-commit install' to activate the hook.[/bold]")
        except Exception as e:
            ui.console.print(f"[red]Failed to write {config_path}: {e}[/red]")
        return

    ui.console.print(f"[cyan]Found existing {config_path}...[/cyan]")
    try:
        with config_path.open("r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    except Exception as e:
        ui.console.print(f"[red]Failed to parse {config_path}: {e}[/red]")
        return

    repos = cfg.setdefault("repos", [])

    # Check if a 'local' repo already exists
    local_repo = None
    for repo in repos:
        if repo.get("repo") == "local":
            local_repo = repo
            break

    if local_repo:
        # Local repo exists, check hooks
        hooks = local_repo.setdefault("hooks", [])
        for hook in hooks:
            if hook.get("id") == "autoheader":
                ui.console.print(
                    "[yellow]autoheader hook already installed in 'local' repo. Skipping.[/yellow]"
                )
                return

        # Not found, add to existing 'local' repo
        ui.console.print("Adding autoheader to existing 'local' repo...")
        hooks.append(LOCAL_AUTOHEADER_HOOK)

    else:
        # No 'local' repo, add a new one
        ui.console.print("Adding new 'local' repo for autoheader...")
        repos.append({"repo": "local", "hooks": [LOCAL_AUTOHEADER_HOOK]})

    try:
        with config_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(cfg, f)
        ui.console.print("[green]✅ autoheader hook added to .pre-commit-config.yaml.[/green]")
        ui.console.print("\n[bold]Run 'pre-commit install' to activate the hook.[/bold]")
    except Exception as e:
        ui.console.print(f"[red]Failed to write to {config_path}: {e}[/red]")
