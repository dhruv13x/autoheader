
from unittest.mock import patch
import pytest
from autoheader.ui import (
    format_action,
    format_error,
    format_summary,
    format_dry_run_note,
    confirm_continue,
    confirm_no_dry_run,
    show_header_diff,
)


@pytest.mark.parametrize(
    "action_name, rel_path, no_emoji, dry_run, expected",
    [
        ("ADD", "src/main.py", False, False, "✅ [green]ADD             [/green] src/main.py"),
        ("OVERRIDE", "src/main.py", False, False, "⚠️ [yellow]OVERRIDE        [/yellow] src/main.py"),
        ("REMOVE", "src/main.py", False, False, "❌ [red]REMOVE          [/red] src/main.py"),
        ("SKIP", "src/main.py", False, False, "🔵 [cyan]SKIP            [/cyan] src/main.py"),
        ("SKIP_EXCLUDED", "src/main.py", False, False, "⚫ [bright_black]SKIP_EXCLUDED   [/bright_black] src/main.py"),
        ("DRY ADD", "src/main.py", False, True, "✅ [green]DRY ADD         [/green] src/main.py"),
        ("ADD", "src/main.py", True, False, "[green]ADD             [/green] src/main.py"),
    ],
)
def test_format_action(action_name, rel_path, no_emoji, dry_run, expected):
    result = format_action(action_name, rel_path, no_emoji, dry_run)
    assert result == expected


def test_format_error():
    result = format_error("src/main.py", Exception("Test error"), False)
    assert result == "🔥 [bold red]ERROR           [/bold red] Failed to process src/main.py: Test error"


def test_format_summary():
    result = format_summary(1, 2, 3, 4, 5)
    assert "added=1" in result
    assert "overridden=2" in result
    assert "removed=3" in result
    assert "skipped_ok=4" in result
    assert "skipped_excluded=5" in result


def test_format_dry_run_note():
    result = format_dry_run_note()
    assert "this was a dry run" in result


def test_confirm_continue_auto_yes():
    assert confirm_continue(auto_yes=True) is True


@pytest.mark.parametrize(
    "user_input, expected_return, log_level, log_message",
    [
        ("y", True, None, None),
        ("yes", True, None, None),
        ("n", False, "warning", "Aborted by user."),
        ("no", False, "warning", "Aborted by user."),
        ("", False, "warning", "Aborted by user."),
        (EOFError, False, "error", "Aborted: Non-interactive environment and --yes not provided."),
    ],
)
def test_confirm_continue_interactive(user_input, expected_return, log_level, log_message):
    with patch("autoheader.ui.console.input", side_effect=user_input if isinstance(user_input, type) else [user_input]), \
         patch("autoheader.ui.log") as mock_log:
        assert confirm_continue(auto_yes=False) == expected_return
        if log_level == "warning":
            mock_log.warning.assert_called_once_with(log_message)
        elif log_level == "error":
            mock_log.error.assert_called_once_with(log_message)


@pytest.mark.parametrize(
    "user_input, expected_return, log_level, log_message",
    [
        ("y", True, None, None),
        ("yes", True, None, None),
        ("n", False, "warning", "Aborted by user."),
        ("no", False, "warning", "Aborted by user."),
        ("", False, "warning", "Aborted by user."),
        (EOFError, False, "error", "Aborted: Non-interactive environment and --yes not provided."),
    ],
)
def test_confirm_no_dry_run_interactive(user_input, expected_return, log_level, log_message):
    with patch("autoheader.ui.console.input", side_effect=user_input if isinstance(user_input, type) else [user_input]), \
         patch("autoheader.ui.log") as mock_log:
        assert confirm_no_dry_run(needs_backup_warning=False) is expected_return
        if log_level == "warning":
            mock_log.warning.assert_called_once_with(log_message)
        elif log_level == "error":
            mock_log.error.assert_called_once_with(log_message)


@pytest.mark.parametrize(
    "needs_warning, expected_text_in_prompt",
    [
        (True, "WARNING: For safety"),
        (False, None),
    ],
)
def test_confirm_no_dry_run_backup_warning_text(needs_warning, expected_text_in_prompt):
    with patch("autoheader.ui.console.input", return_value="y") as mock_input:
        confirm_no_dry_run(needs_backup_warning=needs_warning)
        prompt = mock_input.call_args[0][0]
        if expected_text_in_prompt:
            assert expected_text_in_prompt in prompt
        else:
            assert "WARNING" not in prompt


def test_show_header_diff_with_old_header():
    with patch("autoheader.ui.console.print") as mock_print:
        show_header_diff("src/main.py", "old header", "new header")
        mock_print.assert_called_once()


def test_show_header_diff_no_old_header():
    with patch("autoheader.ui.console.print") as mock_print:
        show_header_diff("src/main.py", None, "new header")
        mock_print.assert_called_once()
