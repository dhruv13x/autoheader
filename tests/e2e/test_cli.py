# tests/e2e/test_cli.py

from pathlib import Path
from unittest import mock
import logging

from autoheader.cli import main

# 'populated_project' fixture is from conftest.py
# 'capsys' fixture is from pytest, for capturing stdout/stderr
# 'caplog' fixture is from pytest, for capturing logs

# --- Helper Function ---

def read_file_lines(path: Path) -> list[str]:
    """Helper to read file lines for assertions."""
    return path.read_text().splitlines()

# -------------------------

def test_cli_check_mode(populated_project: Path, capsys):
    """
    Tests 'autoheader --check'
    1. Fails with exit code 1 on a dirty project.
    2. Passes with exit code 0 on a clean project.
    """
    root = populated_project
    
    # --- 1. Test failure on dirty project ---
    # The fixture has dirty/incorrect files
    exit_code = main(["--check", "--root", str(root)])
    
    assert exit_code == 1
    
    # Check that it printed the error message
    captured = capsys.readouterr()
    assert "autoheader: The following files require header changes:" in captured.out
    assert "src/dirty_file.py" in captured.out
    
    # --- 2. Clean the project first ---
    # Run with --no-dry-run and --override to fix all files
    exit_code_clean = main([
        "--no-dry-run",
        "--yes",
        "--override",
        "--root",
        str(root)
    ])
    assert exit_code_clean == 0
    
    # --- 3. Test success on clean project ---
    # Now that it's clean, --check should pass
    exit_code_pass = main(["--check", "--root", str(root)])
    
    captured_pass = capsys.readouterr()
    assert exit_code_pass == 0
    assert "✅ autoheader: All headers are correct." in captured_pass.out


def test_cli_apply_changes(populated_project: Path):
    """
    Tests 'autoheader --no-dry-run --yes'
    Asserts files are modified on disk.
    """
    root = populated_project
    dirty_file = root / "src/dirty_file.py"
    incorrect_file = root / "src/incorrect_file.py"
    
    # Get original content
    incorrect_original_content = incorrect_file.read_text()
    
    # Run the app
    exit_code = main(["--no-dry-run", "--yes", "--root", str(root)])
    assert exit_code == 0
    
    # --- Assert 'dirty_file.py' was ADDED ---
    dirty_lines = read_file_lines(dirty_file)
    assert dirty_lines[2] == "# src/dirty_file.py"
    assert dirty_lines[3] == "" # Blank line
    
    # --- Assert 'incorrect_file.py' was SKIPPED ---
    # (because --override was not used)
    incorrect_new_content = incorrect_file.read_text()
    assert incorrect_new_content == incorrect_original_content


def test_cli_override_remove_flags(populated_project: Path):
    """
    Tests the --override and --remove flags.
    """
    root = populated_project
    incorrect_file = root / "src/incorrect_file.py"
    clean_file = root / "src/clean_file.py"
    
    # --- 1. Test --override ---
    exit_code_override = main([
        "--no-dry-run",
        "--yes",
        "--override",
        "--root",
        str(root)
    ])
    assert exit_code_override == 0
    
    # Assert 'incorrect_file.py' was OVERRIDDEN
    incorrect_lines = read_file_lines(incorrect_file)
    assert incorrect_lines[0] == "# src/incorrect_file.py"
    
    # --- 2. Test --remove ---
    # Now all files (clean, dirty, incorrect) have headers.
    # Let's remove them.
    exit_code_remove = main([
        "--no-dry-run",
        "--yes",
        "--remove",
        "--root",
        str(root)
    ])
    assert exit_code_remove == 0
    
    # Assert 'clean_file.py' header was REMOVED
    clean_lines = read_file_lines(clean_file)
    assert clean_lines[0] == 'print("hello")' # Header is gone


def test_cli_config_file(populated_project: Path):
    """
    Tests that settings from 'autoheader.toml' are loaded and respected.
    """
    root = populated_project
    dirty_file = root / "src/dirty_file.py"
    incorrect_file = root / "src/incorrect_file.py"
    
    # Create a config file in the project root
    config_content = """
[general]
override = true  # Test bool flag

[header]
blank_lines_after = 2  # Test int value
"""
    (root / "autoheader.toml").write_text(config_content)
    
    # Run *without* CLI flags -- they should come from the TOML
    exit_code = main(["--no-dry-run", "--yes", "--root", str(root)])
    assert exit_code == 0
    
    # --- Assert 'incorrect_file.py' was OVERRIDDEN (from toml) ---
    incorrect_lines = read_file_lines(incorrect_file)
    assert incorrect_lines[0] == "# src/incorrect_file.py"
    
    # --- Assert 'dirty_file.py' has 2 BLANK LINES (from toml) ---
    dirty_lines = read_file_lines(dirty_file)
    assert dirty_lines[2] == "# src/dirty_file.py"
    assert dirty_lines[3] == "" # Blank line 1
    assert dirty_lines[4] == "" # Blank line 2
    assert dirty_lines[5] == "" # Original blank line


def test_cli_root_detection_prompt_abort(tmp_path: Path, monkeypatch, caplog):
    """
    Tests that running in an "unsafe" directory (no markers)
    triggers the confirmation prompt, which we mock to 'no'.
    This implicitly tests app.ensure_root_or_confirm.
    """
    # Patch 'ui.confirm_continue' to simulate a user pressing 'n'
    mock_confirm = mock.Mock(return_value=False)
    
    monkeypatch.setattr("autoheader.ui.confirm_continue", mock_confirm)
    
    # Run from an empty temp dir (not a project root)
    with caplog.at_level(logging.WARNING):
        exit_code = main(["--root", str(tmp_path)])
    
    assert exit_code == 1 # Should abort
    # Check that it was called, and auto_yes was False
    mock_confirm.assert_called_once_with(auto_yes=False)
    
    # --- FIX ---
    # The "Aborted by user." log message is *inside* the mocked function,
    # so it will never appear. We just check for the log from app.py.
    assert "Warning: only 0 project markers found." in caplog.text
    # --- END FIX ---


def test_cli_root_detection_prompt_yes_flag(tmp_path: Path, monkeypatch, caplog):
    """
    Tests that '--yes' skips the confirmation prompt when in an
    "unsafe" directory.
    """
    mock_confirm = mock.Mock(return_value=True) # Mock return value
    
    monkeypatch.setattr("autoheader.ui.confirm_continue", mock_confirm)
    
    # Run with --yes
    with caplog.at_level(logging.WARNING):
        exit_code = main(["--yes", "--root", str(tmp_path)])
    
    assert exit_code == 0 # Should proceed (and find 0 files)
    
    # The 'auto_yes=True' flag is passed to the mock
    mock_confirm.assert_called_once_with(auto_yes=True)
    
    # --- FIX ---
    # The "Inconclusive root detection..." log message is *inside* the
    # mocked function. We check for the log from app.py instead.
    assert "Warning: only 0 project markers found." in caplog.text
    # --- END FIX ---
