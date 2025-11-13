# tests/integration/test_filesystem.py

import pytest
from pathlib import Path
import os
import stat
import logging
from unittest import mock  # <-- Import mock
import builtins # <-- ADDED

# --- MODIFIED IMPORTS ---
from autoheader.filesystem import (
    read_file_lines,
    write_file_content,
    find_configured_files,
    load_gitignore_patterns,
    get_file_hash,
    save_cache,
)
from autoheader.models import LanguageConfig  # <-- Added
# --- END MODIFIED IMPORTS ---


# --- test_read_file_lines ---

def test_read_file_lines_valid(tmp_path: Path):
    """Tests reading a valid UTF-8 file."""
    p = tmp_path / "test.py"
    p.write_text("line 1\nline 2")

    lines = read_file_lines(p)
    assert lines == ["line 1", "line 2"]


def test_read_file_lines_nonexistent(tmp_path: Path, caplog):
    """Tests reading a non-existent file."""
    p = tmp_path / "nonexistent.py"

    with caplog.at_level(logging.WARNING):
        lines = read_file_lines(p)

    assert lines == []
    assert f"Failed to read {p}" in caplog.text
    assert "No such file or directory" in caplog.text


def test_read_file_lines_permission_error(tmp_path: Path, caplog, monkeypatch):
    """Tests reading a file with a PermissionError."""
    p = tmp_path / "protected.py"
    p.write_text("secret")

    # Mock path.open to raise PermissionError
    def mock_open(*args, **kwargs):
        raise PermissionError("Permission denied")

    monkeypatch.setattr(Path, "open", mock_open)

    with caplog.at_level(logging.WARNING):
        lines = read_file_lines(p)

    assert lines == []
    assert f"Failed to read {p}" in caplog.text
    assert "Permission denied" in caplog.text


# --- NEW: Test generic exception in read_file_lines ---
def test_read_file_lines_generic_exception(tmp_path: Path, caplog, monkeypatch):
    """Tests the generic except block in read_file_lines."""
    p = tmp_path / "test.py"
    p.write_text("content")

    # --- FIX ---
    # 1. This is the 'f' object *inside* the 'with' block
    mock_file_object = mock.Mock()
    mock_file_object.read.side_effect = ValueError("Unexpected error")

    # 2. This is the context manager returned by open()
    #    Use MagicMock to create __enter__ and __exit__
    mock_context_manager = mock.MagicMock()
    # --- END FIX ---
    mock_context_manager.__enter__.return_value = mock_file_object
    mock_context_manager.__exit__.return_value = None  # Must return None

    # 3. Mock path.open to return the context manager
    monkeypatch.setattr(Path, "open", lambda *args, **kwargs: mock_context_manager)

    with caplog.at_level(logging.ERROR):
        lines = read_file_lines(p)

    assert lines == []
    assert "An unexpected error occurred" in caplog.text
    assert "Unexpected error" in caplog.text  # This should now pass


# --- test_write_file_content ---

def test_write_file_content_basic(tmp_path: Path):
    """Asserts file content is correctly written."""
    p = tmp_path / "test.py"
    p.write_text("original")

    write_file_content(p, "new", "original", backup=False, dry_run=False)

    assert p.read_text() == "new"


def test_write_file_content_backup(tmp_path: Path):
    """Asserts --backup creates a .bak file."""
    p = tmp_path / "test.py"
    p.write_text("original")
    bak_path = p.with_suffix(".py.bak")

    assert not bak_path.exists()

    write_file_content(p, "new", "original", backup=True, dry_run=False)

    assert p.read_text() == "new"
    assert bak_path.exists()
    assert bak_path.read_text() == "original"


def test_write_file_content_dry_run(tmp_path: Path):
    """Asserts --dry-run does not write the file."""
    p = tmp_path / "test.py"
    p.write_text("original")
    bak_path = p.with_suffix(".py.bak")

    write_file_content(p, "new", "original", backup=True, dry_run=True)

    assert p.read_text() == "original"
    assert not bak_path.exists()


def test_write_file_content_preserves_permissions(tmp_path: Path):
    """Asserts file permissions are preserved on write."""
    p = tmp_path / "test.py"
    p.write_text("original")

    # Set executable permissions (0o755)
    executable_mode = stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
    os.chmod(p, executable_mode)

    original_mode = p.stat().st_mode
    assert (original_mode & executable_mode) == executable_mode

    write_file_content(p, "new", "original", backup=False, dry_run=False)

    new_mode = p.stat().st_mode
    assert new_mode == original_mode


# --- NEW: Test failure paths for write_file_content ---

def test_write_file_content_stat_fails(tmp_path: Path, monkeypatch, caplog):
    """Tests failure when getting original permissions (stat)."""
    p = tmp_path / "test.py"

    def mock_stat(*args, **kwargs):
        raise PermissionError("Cannot stat")

    monkeypatch.setattr(Path, "stat", mock_stat)

    with pytest.raises(PermissionError, match="Cannot stat"), caplog.at_level(logging.ERROR):
        write_file_content(p, "new", "original", backup=False, dry_run=False)

    assert "Failed to read permissions" in caplog.text


def test_write_file_content_backup_fails(tmp_path: Path, monkeypatch, caplog):
    """Tests failure when writing the .bak file."""
    p = tmp_path / "test.py"
    p.write_text("original")

    def mock_write_text(*args, **kwargs):
        # Let the *first* write (the backup) fail
        raise IOError("Disk full")

    monkeypatch.setattr(Path, "write_text", mock_write_text)

    with pytest.raises(IOError, match="Disk full"), caplog.at_level(logging.ERROR):
        write_file_content(p, "new", "original", backup=True, dry_run=False)

    assert "Failed to create backup" in caplog.text
    # Ensure original file is untouched
    assert p.read_text() == "original"


def test_write_file_content_write_fails(tmp_path: Path, monkeypatch, caplog):
    """Tests failure when writing the final file."""
    p = tmp_path / "test.py"
    p.write_text("original")

    # Mock write_text to fail on the *second* call (the main write)
    mock_writer = mock.Mock(side_effect=[None, IOError("Permission denied")])
    monkeypatch.setattr(Path, "write_text", mock_writer)

    # --- FIX ---
    # We must also mock chmod, because the mock_writer doesn't
    # create the .bak file, so bak.chmod would fail first.
    mock_chmod = mock.Mock()
    monkeypatch.setattr(Path, "chmod", mock_chmod)
    # --- END FIX ---

    with pytest.raises(IOError, match="Permission denied"), caplog.at_level(logging.ERROR):
        write_file_content(p, "new", "original", backup=True, dry_run=False)

    assert "Failed to write file" in caplog.text

    # We can check that the mocks were called as expected
    assert mock_writer.call_count == 2  # 1 for backup, 1 for main file

    # original_mode (from stat) + bak.chmod
    assert mock_chmod.call_count == 1  # Only the bak.chmod is called


# --- ADD THIS NEW TEST ---
def test_load_gitignore_patterns(tmp_path: Path, caplog):
    """Tests that .gitignore is parsed correctly."""
    gitignore = tmp_path / ".gitignore"
    content = """
    # This is a comment
    *.log
    
    /build/
    dist
    
    !important.log
    """
    gitignore.write_text(content)

    # --- THIS IS THE FIX ---
    with caplog.at_level(logging.DEBUG):
        patterns = load_gitignore_patterns(tmp_path)
        assert patterns == ["*.log", "/build/", "dist", "!important.log"]
        assert "Loaded 4 patterns" in caplog.text

        # Test no file
        gitignore.unlink()
        patterns = load_gitignore_patterns(tmp_path)
        assert patterns == []
        assert "No .gitignore found" in caplog.text
    # --- END FIX ---


# --- MODIFIED: test_find_python_files -> test_find_configured_files ---

def test_find_configured_files(tmp_path: Path):
    """
    Tests that only valid, non-symlinked files are found
    based on the multi-language config.
    """
    # Define test languages
    lang_py = LanguageConfig("py", ["*.py", "*.pyi"], "#", True, "# {path}")
    lang_js = LanguageConfig("js", ["*.js"], "//", False, "// {path}")
    languages = [lang_py, lang_js]

    # Create files
    py_file_1 = tmp_path / "script.py"
    py_file_1.write_text("")

    py_file_2 = tmp_path / "src" / "main.py"
    (tmp_path / "src").mkdir()
    py_file_2.write_text("")
    
    js_file = tmp_path / "src" / "app.js"
    js_file.write_text("")

    # Create files to be ignored
    txt_file = tmp_path / "README.txt"
    txt_file.write_text("")

    dir_with_py_suffix = tmp_path / "fake.py"  # A directory
    dir_with_py_suffix.mkdir()
    
    dir_with_js_suffix = tmp_path / "fake.js" # A directory
    dir_with_js_suffix.mkdir()

    # Create a symlink (to be ignored)
    symlink_file = tmp_path / "linked.py"
    try:
        os.symlink(py_file_1, symlink_file)
        symlink_created = True
    except (builtins.OSError, NotImplementedError): # <--- MODIFIED LINE
        # Symlinks may fail on some systems (e.g., Windows without admin)
        symlink_created = False
        print("Skipping symlink test; could not create symlink.")

    # --- Run the test ---
    found_files = list(find_configured_files(tmp_path, languages))
    
    # --- Check the results ---
    found_map = {path: lang for path, lang in found_files}
    
    assert len(found_map) == 3
    
    # Check Python files
    assert py_file_1 in found_map
    assert found_map[py_file_1] == lang_py
    assert py_file_2 in found_map
    assert found_map[py_file_2] == lang_py
    
    # Check JavaScript file
    assert js_file in found_map
    assert found_map[js_file] == lang_js

    # Check ignored files
    assert txt_file not in found_map
    assert dir_with_py_suffix not in found_map
    assert dir_with_js_suffix not in found_map
    if symlink_created:
        assert symlink_file not in found_map


def test_get_file_hash_large_file(fs):
    """Tests that get_file_hash correctly hashes a large file."""
    large_file_path = Path("/large_file.bin")
    # Create a 10MB file
    large_content = b"a" * (10 * 1024 * 1024)
    fs.create_file(large_file_path, contents=large_content)

    # Calculate expected hash
    import hashlib
    expected_hash = hashlib.sha256(large_content).hexdigest()

    # Calculate hash using the function
    actual_hash = get_file_hash(large_file_path)

    assert actual_hash == expected_hash


def test_save_cache_error(fs, caplog):
    """Tests that an error during cache saving is logged."""
    root = Path("/fake_project")
    fs.create_dir(root)
    cache_path = root / ".autoheader_cache"

    # Make the directory read-only to cause a permission error
    fs.chmod(root, 0o555)

    with caplog.at_level(logging.WARNING):
        save_cache(root, {"key": "value"})

    assert f"Could not save cache file: [Errno 13] " in caplog.text

def test_get_file_hash_error(fs, caplog):
    """Tests that an error during hashing is logged and returns an empty string."""
    p = Path("/unreadable.txt")
    fs.create_file(p)
    fs.chmod(p, 0o000) # no permissions

    with caplog.at_level(logging.WARNING):
        result = get_file_hash(p)

    assert result == ""
    assert f"Failed to hash {p}" in caplog.text
