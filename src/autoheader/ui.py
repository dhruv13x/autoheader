# src/autoheader/ui.py

from __future__ import annotations
import logging
from rich.console import Console

log = logging.getLogger(__name__)

# This console will be reconfigured by cli.py after args are parsed
console = Console(force_terminal=True)

# --- NEW: Rich Formatting ---

EMOJI_MAP = {
    "ADD": "✅",
    "OVERRIDE": "⚠️",
    "REMOVE": "❌",
    "SKIP": "🔵",
    "SKIP_EXCLUDED": "⚫",
    "SKIP_CACHED": "⚡️",
    "ERROR": "🔥",
}

STYLE_MAP = {
    "ADD": "green",
    "OVERRIDE": "yellow",
    "REMOVE": "red",
    "SKIP": "cyan",
    "SKIP_EXCLUDED": "bright_black",
    "SKIP_CACHED": "blue",
    "ERROR": "bold red",
    "DRY_RUN": "bright_black",
}


def format_action(action_name: str, rel_path: str, no_emoji: bool, dry_run: bool) -> str:
    """Formats a single file action line with styles and emojis."""

    base_action = action_name.replace("DRY ", "")
    emoji = EMOJI_MAP.get(base_action, " ")
    prefix = f"{emoji} " if not no_emoji else ""

    style = STYLE_MAP.get(base_action, "white")
    
    # Pad the action text for alignment
    # 16 chars is wide enough for "DRY OVERRIDE"
    action_text = f"[{style}]{action_name:<16}[/{style}]"

    return f"{prefix}{action_text} {rel_path}"


def format_error(rel_path: str, err: Exception, no_emoji: bool) -> str:
    """Formats an error line."""
    emoji = EMOJI_MAP["ERROR"]
    prefix = f"{emoji} " if not no_emoji else ""

    style = STYLE_MAP["ERROR"]
    action_styled = f"[{style}]ERROR           [/{style}]"  # 16 chars
    
    return f"{prefix}{action_styled} Failed to process {rel_path}: {err}"


def format_summary(
    added: int, overridden: int, removed: int,
    skipped_ok: int, skipped_excluded: int
) -> str:
    """Formats the final summary line."""
    parts = [
        f"[{STYLE_MAP['ADD']}]added={added}[/{STYLE_MAP['ADD']}]",
        f"[{STYLE_MAP['OVERRIDE']}]overridden={overridden}[/{STYLE_MAP['OVERRIDE']}]",
        f"[{STYLE_MAP['REMOVE']}]removed={removed}[/{STYLE_MAP['REMOVE']}]",
        f"[{STYLE_MAP['SKIP']}]skipped_ok={skipped_ok}[/{STYLE_MAP['SKIP']}]",
        f"[{STYLE_MAP['SKIP_EXCLUDED']}]skipped_excluded={skipped_excluded}[/{STYLE_MAP['SKIP_EXCLUDED']}]",
    ]
    return f"\nSummary: {', '.join(parts)}."


def format_dry_run_note() -> str:
    """Formats the dry-run note."""
    return f"[{STYLE_MAP['DRY_RUN']}]NOTE: this was a dry run. Use --no-dry-run to apply changes.[/{STYLE_MAP['DRY_RUN']}]"


def confirm_continue(auto_yes: bool = False) -> bool:
    """
    Ask user whether to continue when root detection fails.
    Handles non-interactive environments.
    """
    if auto_yes:
        log.warning("Inconclusive root detection, proceeding automatically (--yes).")
        return True

    while True:
        try:
            # Use rich console for input to ensure clean prompt
            resp = (
                console.input(
                    "[yellow]autoheader: Could not confidently detect project root.\n"
                    "Are you sure you want to continue? [/yellow][white][y/N]: [/white]"
                )
                .strip()
                .lower()
            )
        except EOFError:
            # Handle non-interactive environments (e.g., CI pipelines)
            log.error("Aborted: Non-interactive environment and --yes not provided.")
            return False

        if resp in ("y", "yes"):
            return True
        if resp in ("n", "no", ""):
            log.warning("Aborted by user.")
            return False


def show_header_diff(path: str, old_header: str | None, new_header: str) -> None:
    """Displays a rich diff for header changes."""
    from rich.panel import Panel
    from rich.text import Text

    if old_header:
        title = f"Header diff for [bold]{path}[/bold]"
        content = Text.from_markup(f"- [red]{old_header}[/red]\n+ [green]{new_header}[/green]")
    else:
        title = f"Header to be added to [bold]{path}[/bold]"
        content = Text.from_markup(f"+ [green]{new_header}[/green]")

    console.print(Panel(content, title=title, border_style="dim"))


def confirm_no_dry_run(needs_backup_warning: bool) -> bool:
    """
    Ask user to confirm a --no-dry-run operation.
    Warns if --backup is not present.
    """
    prompt = (
        "[yellow]autoheader: You are about to apply changes directly to files (--no-dry-run).\n"
    )
    if needs_backup_warning:
        prompt += (
            "WARNING: For safety, running with --backup is recommended, but it is not enabled.\n"
        )

    prompt += "[/yellow][white]Are you sure you want to continue? [y/N]: [/white]"

    while True:
        try:
            resp = console.input(prompt).strip().lower()
        except EOFError:
            log.error("Aborted: Non-interactive environment and --yes not provided.")
            return False

        if resp in ("y", "yes"):
            return True
        if resp in ("n", "no", ""):
            log.warning("Aborted by user.")
            return False
