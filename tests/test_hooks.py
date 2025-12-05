
import os
import stat
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from autoheader import hooks

def test_install_native_hook_no_git_dir(tmp_path, capsys):
    """Test installing hook when .git directory is missing."""
    # Run install_native_hook
    hooks.install_native_hook(tmp_path)

    # Check output
    captured = capsys.readouterr()
    # It should probably print an error or warning
    # We'll assert on the behavior we implement
    # For now, let's assume it checks for .git and returns/prints
    assert ".git directory not found" in captured.out or ".git directory not found" in captured.err

def test_install_native_hook_success(tmp_path, capsys):
    """Test successful installation of the hook."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir()

    # Run install_native_hook
    hooks.install_native_hook(tmp_path)

    hook_path = hooks_dir / "pre-commit"
    assert hook_path.exists()

    content = hook_path.read_text()
    assert "#!/bin/sh" in content
    assert "autoheader --check" in content

    # Check permissions (executable)
    # On Windows this might be tricky, but on Linux/Mac:
    if os.name == 'posix':
        st = os.stat(hook_path)
        assert bool(st.st_mode & stat.S_IXUSR)

    captured = capsys.readouterr()
    assert "Native git hook installed" in captured.out

def test_install_native_hook_already_exists(tmp_path, capsys):
    """Test behavior when hook already exists."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir()

    hook_path = hooks_dir / "pre-commit"
    hook_path.write_text("#!/bin/sh\necho existing hook")

    # Run install_native_hook
    hooks.install_native_hook(tmp_path)

    # Content should NOT change
    content = hook_path.read_text()
    assert "echo existing hook" in content
    assert "autoheader --check" not in content

    captured = capsys.readouterr()
    assert "Hook already exists" in captured.out
