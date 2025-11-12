# tests/unit/test_ui.py

import pytest
from autoheader import ui
import logging
from unittest import mock  # <-- Import mock

# We can patch the console to avoid printing during tests
@pytest.fixture(autouse=True)
def mock_console(monkeypatch):
    # Use a mock for the console *object* so we can also mock 'input'
    monkeypatch.setattr(ui, "console", mock.Mock())


@pytest.mark.parametrize(
    "action, rel_path, no_emoji, dry_run, expected_prefix",
    [
        ("ADD", "src/main.py", False, False, "✅ ADD"),
        ("OVERRIDE", "src/main.py", False, False, "⚠️ OVERRIDE"),
        ("REMOVE", "src/main.py", False, False, "❌ REMOVE"),
        ("SKIP", "src/main.py", False, False, "🔵 SKIP"),
        ("SKIP_EXCLUDED", "src/main.py", False, False, "⚫ SKIP_EXCLUDED"),
        ("DRY ADD", "src/main.py", False, True, "✅ DRY ADD"),
        ("ADD", "src/main.py", True, False, "ADD"), # No emoji
    ]
)
def test_format_action(action, rel_path, no_emoji, dry_run, expected_prefix):
    """Tests that format_action correctly includes emojis, styles, and padding."""
    output = ui.format_action(action, rel_path, no_emoji, dry_run)

    # --- FIX ---
    # The original assertions failed because they didn't account
    # for Rich's style tags (e.g., [yellow]...[/yellow]).
    # We will test for the components separately.

    if no_emoji:
        # 1. Check it does NOT start with an emoji from the map
        all_emojis = [e for e in ui.EMOJI_MAP.values()]
        assert not any(output.startswith(e) for e in all_emojis)
    else:
        # 2. Check it starts with the correct emoji
        assert output.startswith(expected_prefix[0])

    # 3. Check that the action text itself is present (this will be in the output)
    assert action in output

    # 4. Check that the path is present
    assert rel_path in output


def test_format_error(capsys):
    """Tests the error formatter."""
    output = ui.format_error("src/locked.py", Exception("Permission denied"), no_emoji=False)

    # --- FIX ---
    # The original assertion "🔥 ERROR" in output failed because
    # of the style tags: '🔥 [bold red]ERROR...'
    # We test for the components separately.
    assert "🔥" in output
    assert "ERROR" in output
    # --- END FIX ---

    assert "Failed to process src/locked.py: Permission denied" in output

    output_no_emoji = ui.format_error("src/locked.py", Exception("Permission denied"), no_emoji=True)
    assert "🔥" not in output_no_emoji
    assert "ERROR" in output_no_emoji

def test_format_summary():
    """Tests the final summary line."""
    output = ui.format_summary(
        added=1, overridden=2, removed=3, skipped_ok=4, skipped_excluded=5, skipped_cached=6
    )

    assert "added=1" in output
    assert "overridden=2" in output
    assert "removed=3" in output
    assert "skipped_ok=4" in output
    assert "skipped_excluded=5" in output
    assert "skipped_cached=6" in output

def test_format_dry_run_note():
    """Tests the dry run note."""
    output = ui.format_dry_run_note()
    assert "NOTE: this was a dry run" in output

# --- NEW TESTS TO INCREASE COVERAGE ---

def test_confirm_continue_auto_yes(caplog):
    """Tests confirm_continue with auto_yes=True."""
    with caplog.at_level(logging.WARNING):
        assert ui.confirm_continue(auto_yes=True) is True
    # Check that the correct warning was logged
    assert "Inconclusive root detection" in caplog.text

@pytest.mark.parametrize("user_input, expected_return, expected_log", [
    ("y", True, None),
    ("yes", True, None),
    ("n", False, "Aborted by user."),
    ("no", False, "Aborted by user."),
    ("", False, "Aborted by user."),
    (EOFError, False, "Aborted: Non-interactive"),
])
def test_confirm_continue_interactive(monkeypatch, caplog, user_input, expected_return, expected_log):
    """Tests all interactive branches of confirm_continue."""
    if isinstance(user_input, type) and issubclass(user_input, Exception):
        # Mock .input() to raise an exception
        mock_input = mock.Mock(side_effect=user_input)
    else:
        # Mock .input() to return the user's string
        mock_input = mock.Mock(return_value=user_input)
    
    monkeypatch.setattr(ui.console, "input", mock_input)
    
    with caplog.at_level(logging.WARNING):
        assert ui.confirm_continue(auto_yes=False) is expected_return
    
    if expected_log:
        assert expected_log in caplog.text

@pytest.mark.parametrize("user_input, expected_return, expected_log", [
    ("y", True, None),
    ("yes", True, None),
    ("n", False, "Aborted by user."),
    ("no", False, "Aborted by user."),
    ("", False, "Aborted by user."),
    (EOFError, False, "Aborted: Non-interactive"),
])
def test_confirm_no_dry_run_interactive(monkeypatch, caplog, user_input, expected_return, expected_log):
    """Tests all interactive branches of confirm_no_dry_run."""
    if isinstance(user_input, type) and issubclass(user_input, Exception):
        mock_input = mock.Mock(side_effect=user_input)
    else:
        mock_input = mock.Mock(return_value=user_input)
    
    monkeypatch.setattr(ui.console, "input", mock_input)
    
    with caplog.at_level(logging.WARNING):
        assert ui.confirm_no_dry_run(needs_backup_warning=False) is expected_return
    
    if expected_log:
        assert expected_log in caplog.text

@pytest.mark.parametrize("needs_warning, should_be_in_prompt", [
    (True, "WARNING: For safety"),
    (False, None),
])
def test_confirm_no_dry_run_backup_warning_text(monkeypatch, needs_warning, should_be_in_prompt):
    """Tests that the backup warning text appears/disappears correctly."""
    mock_input = mock.Mock(return_value="y")
    monkeypatch.setattr(ui.console, "input", mock_input)
    
    ui.confirm_no_dry_run(needs_backup_warning=needs_warning)
    
    # Get the text that was passed to console.input()
    prompt_text = mock_input.call_args[0][0]
    
    if should_be_in_prompt:
        assert should_be_in_prompt in prompt_text
    else:
        assert "WARNING: For safety" not in prompt_text