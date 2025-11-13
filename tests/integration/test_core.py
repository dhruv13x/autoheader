# tests/integration/test_core.py

import pytest
from pathlib import Path

from autoheader.core import plan_files, write_with_header
from autoheader.models import PlanItem, RuntimeContext
# --- ADD THESE IMPORTS ---
from autoheader.models import LanguageConfig
from autoheader.constants import HEADER_PREFIX

# --- ADD DEFAULT LANGUAGE CONFIG FOR TESTS ---
# Most tests assume the default Python behavior
DEFAULT_TEMPLATE = f"{HEADER_PREFIX}{{path}}"
PY_LANG = LanguageConfig(
    name="python",
    file_globs=["*.py"],
    prefix=HEADER_PREFIX,
    check_encoding=True,
    template=DEFAULT_TEMPLATE,
)
DEFAULT_LANGUAGES = [PY_LANG]


# The 'populated_project' fixture is defined in tests/conftest.py
# and automatically used by pytest.

def test_plan_files(populated_project: Path):
    """
    Tests the main plan_files orchestrator using the 'populated_project' fixture.
    """
    root = populated_project

    # Run the plan
    context = RuntimeContext(
        root=root,
        excludes=[],
        depth=None,
        override=False,
        remove=False,
        check_hash=False,
        timeout=60.0,
    )
    plan, _ = plan_files(context, languages=DEFAULT_LANGUAGES, workers=1)
    # --- END MODIFIED ---

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
    context_override = RuntimeContext(
        root=root, excludes=[], depth=None, override=True, remove=False, check_hash=False, timeout=60.0
    )
    plan_override, _ = plan_files(context_override, languages=DEFAULT_LANGUAGES, workers=1)
    plan_map = {item.rel_posix: item.action for item in plan_override}
    assert plan_map["src/incorrect_file.py"] == "override"

    # --- Test --remove ---
    context_remove = RuntimeContext(
        root=root, excludes=[], depth=None, override=False, remove=True, check_hash=False, timeout=60.0
    )
    plan_remove, _ = plan_files(context_remove, languages=DEFAULT_LANGUAGES, workers=1)
    plan_map = {item.rel_posix: item.action for item in plan_remove}
    assert plan_map["src/clean_file.py"] == "remove"
    assert plan_map["src/dirty_file.py"] == "skip-header-exists"

    # --- Test --depth ---
    context_depth = RuntimeContext(
        root=root, excludes=[], depth=3, override=False, remove=False, check_hash=False, timeout=60.0
    )
    plan_depth, _ = plan_files(context_depth, languages=DEFAULT_LANGUAGES, workers=1)
    # --- END MODIFIED ---
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
    # --- MODIFIED: Add language config to PlanItem ---
    item_add = PlanItem(
        path=root / "src/dirty_file.py",
        rel_posix="src/dirty_file.py",
        action="add",
        prefix=PY_LANG.prefix,
        check_encoding=PY_LANG.check_encoding,
        template=PY_LANG.template,
        analysis_mode=PY_LANG.analysis_mode,
    )
    # --- END MODIFIED ---
    
    # --- MODIFIED: Remove prefix argument ---
    action, _, _ = write_with_header(
        item_add, backup=False, dry_run=False, blank_lines_after=1
    )
    # --- END MODIFIED ---
    assert action == "add"

    # Check file content
    lines = (root / "src/dirty_file.py").read_text().splitlines()
    assert lines[0] == "#!/usr/bin/env python"
    assert lines[1] == "# -*- coding: utf-8 -*-"
    assert lines[2] == "# src/dirty_file.py"  # Header added
    assert lines[3] == ""  # Blank line added
    assert lines[4] == ""  # Original blank line

    # --- 2. Test "override" action ---
    # --- MODIFIED: Add language config to PlanItem ---
    item_override = PlanItem(
        path=root / "src/incorrect_file.py",
        rel_posix="src/incorrect_file.py",
        action="override",
        prefix=PY_LANG.prefix,
        check_encoding=PY_LANG.check_encoding,
        template=PY_LANG.template,
        analysis_mode=PY_LANG.analysis_mode,
    )
    # --- END MODIFIED ---
    
    # --- MODIFIED: Remove prefix argument ---
    action, _, _ = write_with_header(
        item_override, backup=False, dry_run=False, blank_lines_after=1
    )
    # --- END MODIFIED ---
    assert action == "override"

    # Check file content
    lines = (root / "src/incorrect_file.py").read_text().splitlines()
    assert lines[0] == "# src/incorrect_file.py"  # Header overridden
    assert lines[1] == ""  # Blank line added
    assert lines[2] == ""  # Original blank line

    # --- 3. Test "remove" action ---
    # --- MODIFIED: Add language config to PlanItem ---
    item_remove = PlanItem(
        path=root / "src/clean_file.py",
        rel_posix="src/clean_file.py",
        action="remove",
        prefix=PY_LANG.prefix,
        check_encoding=PY_LANG.check_encoding,
        template=PY_LANG.template,
        analysis_mode=PY_LANG.analysis_mode,
    )
    # --- END MODIFIED ---
    
    # --- MODIFIED: Remove prefix argument ---
    action, _, _ = write_with_header(
        item_remove, backup=False, dry_run=False, blank_lines_after=1
    )
    # --- END MODIFIED ---
    assert action == "remove"

    # Check file content
    lines = (root / "src/clean_file.py").read_text().splitlines()
    # Header and blank line should be gone
    assert lines[0] == 'print("hello")'