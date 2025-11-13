# tests/e2e/test_cli_args.py

from pathlib import Path
from subprocess import run

def test_cli_explicit_files(populated_project: Path):
    """
    Tests that passing specific files to the CLI processes only those files.
    """
    root = populated_project

    # We expect dirty_file.py to be processed, but clean_file.py to be ignored
    # because it wasn't passed as an argument.
    result = run(
        ["autoheader", "--no-dry-run", "--yes", "src/dirty_file.py"],
        cwd=root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

    # Check that dirty_file.py was modified
    dirty_content = (root / "src/dirty_file.py").read_text()
    assert "# src/dirty_file.py" in dirty_content

    # Check that clean_file.py was NOT modified (i.e., header was not removed)
    clean_content = (root / "src/clean_file.py").read_text()
    assert "# src/clean_file.py" in clean_content
