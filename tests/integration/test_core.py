# tests/integration/test_core.py

import pytest
from pathlib import Path

from autoheader.core import plan_files, write_with_header
from autoheader.models import PlanItem

# The 'populated_project' fixture is defined in tests/conftest.py
# and automatically used by pytest.

def test_plan_files(populated_project: Path):
    """
    Tests the main plan_files orchestrator using the 'populated_project' fixture.
    """
    root = populated_project
    
    # Run the plan
    plan = plan_files(
        root,
        depth=None,
        excludes=[],
        override=False,
        remove=False,
    )
    
    # Convert to a dict for easy lookup
    plan_map = {item.rel_posix: item.action for item in plan}
    
    # 1. 'src/clean_file.py' should be skipped (header exists)
    assert plan_map["src/clean_file.py"] == "skip-header-exists"
    
    # 2. 'src/dirty_file.py' should be marked for 'add'
    assert plan_map["src/dirty_file.py"] == "add"
    
    # 3. 'src/incorrect_file.py' should be skipped (no --override)
    assert plan_map["src/incorrect_file.py"] == "skip-header-exists"
    
    # 4. '.venv/lib/some_lib.py' should be excluded
    assert plan_map[".venv/lib/some_lib.py"] == "skip-excluded"
    
    # 5. 'src/a/b/c/d/e/deep_file.py' should be marked for 'add'
    assert plan_map["src/a/b/c/d/e/deep_file.py"] == "add"

def test_plan_files_with_flags(populated_project: Path):
    """
    Tests the --override, --remove, and --depth flags.
    """
    root = populated_project
    
    # --- Test --override ---
    plan_override = plan_files(
        root, depth=None, excludes=[], override=True, remove=False
    )
    plan_map = {item.rel_posix: item.action for item in plan_override}
    # 'src/incorrect_file.py' should now be 'override'
    assert plan_map["src/incorrect_file.py"] == "override"
    
    # --- Test --remove ---
    plan_remove = plan_files(
        root, depth=None, excludes=[], override=False, remove=True
    )
    plan_map = {item.rel_posix: item.action for item in plan_remove}
    # 'src/clean_file.py' (which has a header) should be 'remove'
    assert plan_map["src/clean_file.py"] == "remove"
    # 'src/dirty_file.py' (no header) should be skipped
    assert plan_map["src/dirty_file.py"] == "skip-header-exists"

    # --- Test --depth ---
    plan_depth = plan_files(
        root, depth=3, excludes=[], override=False, remove=False
    )
    plan_map = {item.rel_posix: item.action for item in plan_depth}
    # 'src/a/b/c/d/e/deep_file.py' (depth 5) should be excluded
    assert plan_map["src/a/b/c/d/e/deep_file.py"] == "skip-excluded"
    # 'src/dirty_file.py' (depth 1) should still be 'add'
    assert plan_map["src/dirty_file.py"] == "add"


def test_write_with_header_actions(populated_project: Path):
    """
    Tests the write_with_header function to ensure it correctly
    modifies files on disk.
    """
    root = populated_project
    
    # --- 1. Test "add" action ---
    item_add = PlanItem(
        path=root / "src/dirty_file.py",
        rel_posix="src/dirty_file.py",
        action="add"
    )
    result = write_with_header(
        item_add, backup=False, dry_run=False, blank_lines_after=1
    )
    assert result == "add"
    
    # Check file content
    lines = (root / "src/dirty_file.py").read_text().splitlines()
    assert lines[0] == "#!/usr/bin/env python"
    assert lines[1] == "# -*- coding: utf-8 -*-"
    assert lines[2] == "# src/dirty_file.py" # Header added
    assert lines[3] == ""                    # Blank line added
    assert lines[4] == ""                    # Original blank line

    # --- 2. Test "override" action ---
    item_override = PlanItem(
        path=root / "src/incorrect_file.py",
        rel_posix="src/incorrect_file.py",
        action="override"
    )
    result = write_with_header(
        item_override, backup=False, dry_run=False, blank_lines_after=1
    )
    assert result == "override"
    
    # Check file content
    lines = (root / "src/incorrect_file.py").read_text().splitlines()
    assert lines[0] == "# src/incorrect_file.py" # Header overridden
    assert lines[1] == ""                        # Blank line added
    assert lines[2] == ""                        # Original blank line
    
    # --- 3. Test "remove" action ---
    item_remove = PlanItem(
        path=root / "src/clean_file.py",
        rel_posix="src/clean_file.py",
        action="remove"
    )
    result = write_with_header(
        item_remove, backup=False, dry_run=False, blank_lines_after=1
    )
    assert result == "remove"
    
    # Check file content
    lines = (root / "src/clean_file.py").read_text().splitlines()
    # Header and blank line should be gone
    assert lines[0] == 'print("hello")'