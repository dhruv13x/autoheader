import pytest
from pathlib import Path

# The 'tmp_path' and 'fs' fixtures are provided by pytest and pyfakefs respectively.

@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """
    Creates a basic, temporary project root directory with common
    root markers. Useful as a base for integration tests.
    """
    # Create root markers for detection
    (tmp_path / ".git").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test-project'\n")
    (tmp_path / "README.md").write_text("# Test Project\n")
    return tmp_path


@pytest.fixture
def populated_project(project_root: Path) -> Path:
    """
    Builds on 'project_root' to create a realistic project structure
    with various file states for testing core logic.
    """
    src_dir = project_root / "src"
    src_dir.mkdir()

    # --- Test Cases ---

    # 1. File that is already correct
    (src_dir / "clean_file.py").write_text(
        """# src/clean_file.py\n
print("hello")
"""
    )

    # 2. File that needs a header (tests shebang/encoding skip)
    (src_dir / "dirty_file.py").write_text(
        """#!/usr/bin/env python
# -*- coding: utf-8 -*-
\n
print("needs header")
"""
    )

    # 3. File with an incorrect (stale) header
    (src_dir / "incorrect_file.py").write_text(
        """# src/wrong_path.py\n
print("wrong header")
"""
    )

    # 4. File that is excluded by default (in .venv)
    venv_dir = project_root / ".venv" / "lib"
    venv_dir.mkdir(parents=True)
    (venv_dir / "some_lib.py").write_text("print('excluded')")

    # 5. File that is too deep (for depth check)
    deep_dir = src_dir / "a" / "b" / "c" / "d" / "e"
    deep_dir.mkdir(parents=True)
    (deep_dir / "deep_file.py").write_text("print('too deep')")

    return project_root


@pytest.fixture
def pyfakefs_config(fs): # 'fs' is the pyfakefs fixture
    """
    Sets up a fake filesystem with a mock autoheader.toml
    for unit testing config.py and walker.py.
    """
    # Create root markers for walker.py
    fs.create_file("/fake_project/pyproject.toml")
    fs.create_file("/fake_project/README.md")
    
    # Create a mock config file for config.py
    config_content = """
[general]
backup = true
workers = 4
override = true

[detection]
depth = 5
markers = ["pyproject.toml", ".git"]

[exclude]
paths = [
    "docs/",
    "*.generated.py"
]

[header]
blank_lines_after = 2
"""
    fs.create_file("/fake_project/autoheader.toml", contents=config_content)
    
    # Create another project directory without a config
    fs.create_dir("/other_project")
    fs.create_file("/other_project/pyproject.toml") # Mark as root
    
    return fs # Return the configured filesystem object