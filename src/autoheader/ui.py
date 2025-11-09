from __future__ import annotations
import logging

log = logging.getLogger(__name__)


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
            resp = (
                input(
                    "autoheader: Could not confidently detect project root.\n"
                    "Are you sure you want to continue? [y/N]: "
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


# --- NEW FUNCTION ---
def confirm_no_dry_run(needs_backup_warning: bool) -> bool:
    """
    Ask user to confirm a --no-dry-run operation.
    Warns if --backup is not present.
    """
    prompt = (
        "autoheader: You are about to apply changes directly to files (--no-dry-run).\n"
    )
    if needs_backup_warning:
        prompt += (
            "WARNING: For safety, running with --backup is recommended, but it is not enabled.\n"
        )

    prompt += "Are you sure you want to continue? [y/N]: "

    while True:
        try:
            resp = input(prompt).strip().lower()
        except EOFError:
            log.error("Aborted: Non-interactive environment and --yes not provided.")
            return False

        if resp in ("y", "yes"):
            return True
        if resp in ("n", "no", ""):
            log.warning("Aborted by user.")
            return False
# --- END NEW FUNCTION ---
