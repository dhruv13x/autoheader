
import pytest
from pathlib import Path
import autoheader
from autoheader import AutoHeader

def test_sdk_apply_headers(tmp_path):
    # Setup
    root = tmp_path
    src_file = root / "myscript.py"
    src_file.write_text("print('hello')\n")

    # Create a config
    config_file = root / "autoheader.toml"
    # NOTE: Using [language.python] format as expected by config.py
    config_file.write_text("""
[general]
workers = 1

[language.python]
file_globs = ["*.py"]
prefix = "# "
template = "# File: {path}"
""")

    # Use the SDK
    ah = AutoHeader(root=root)
    results = ah.apply(paths=[src_file], dry_run=False)

    # Assertions
    assert len(results) == 1
    assert results[0].path == src_file
    assert results[0].status == "add"

    content = src_file.read_text()
    assert "# File: myscript.py" in content
    assert "print('hello')" in content

def test_sdk_check_headers(tmp_path):
    # Setup
    root = tmp_path
    src_file = root / "myscript.py"
    src_file.write_text("# File: myscript.py\nprint('hello')\n")

    config_file = root / "autoheader.toml"
    config_file.write_text("""
[language.python]
file_globs = ["*.py"]
prefix = "# "
template = "# File: {path}"
""")

    ah = AutoHeader(root=root)
    results = ah.check(paths=[src_file])

    assert len(results) == 1
    assert results[0].status == "ok"

def test_sdk_remove_headers(tmp_path):
    # Setup
    root = tmp_path
    src_file = root / "myscript.py"
    src_file.write_text("# File: myscript.py\nprint('hello')\n")

    config_file = root / "autoheader.toml"
    config_file.write_text("""
[language.python]
file_globs = ["*.py"]
prefix = "# "
template = "# File: {path}"
""")

    ah = AutoHeader(root=root)
    results = ah.remove(paths=[src_file], dry_run=False)

    assert len(results) == 1
    assert results[0].status == "remove"

    content = src_file.read_text()
    assert "# File: myscript.py" not in content
