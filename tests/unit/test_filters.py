# tests/unit/test_filters.py

import pytest
from pathlib import Path
from autoheader.filters import is_excluded, within_depth

# Fixture for a mock root
@pytest.fixture
def root() -> Path:
    # Use a generic Path object; filesystem access isn't needed
    return Path("/fake_project")


# --- test_is_excluded ---

@pytest.mark.parametrize(
    "path_str, extra_patterns, expected",
    [
        # Default excludes (folders)
        (".venv/lib/python3.11/site-packages/rich/console.py", [], True),
        ("__pycache__/some.pyc", [], True),
        (".git/hooks/pre-commit", [], True),
        ("src/autoheader/core.py", [], False),  # Not excluded
        
        # Extra patterns (globs)
        ("docs/conf.py", ["docs/"], True),
        ("src/api/v1.generated.py", ["*.generated.py"], True),
        ("src/api/v1.py", ["*.generated.py"], False), # Not matching
        ("README.md", ["docs/"], False), # Not matching
    ],
    ids=[
        "default-venv",
        "default-pycache",
        "default-git",
        "not-excluded",
        "extra-docs-folder",
        "extra-generated-glob",
        "not-matching-glob",
        "not-matching-extra",
    ]
)
def test_is_excluded(root: Path, path_str: str, extra_patterns: list[str], expected: bool):
    """
    Tests that default and extra exclusion patterns are correctly applied.
    """
    path = root / path_str
    assert is_excluded(path, root, extra_patterns) == expected


# --- test_within_depth ---

@pytest.mark.parametrize(
    "path_str, max_depth, expected",
    [
        ("src/autoheader/core.py", None, True), # depth=2, max=None
        ("src/autoheader/core.py", 3, True),  # depth=2, max=3
        ("src/autoheader/core.py", 2, True),  # depth=2, max=2 (equal)
        ("src/autoheader/core.py", 1, False), # depth=2, max=1
        ("README.md", 0, True),                # depth=0, max=0
        ("README.md", None, True),             # depth=0, max=None
        ("src/a/b/c/d/e/f.py", 3, False),      # depth=6, max=3
    ],
    ids=[
        "depth-ok-none",
        "depth-ok-greater",
        "depth-ok-equal",
        "depth-fail-less",
        "depth-root-ok",
        "depth-root-none",
        "depth-fail-deep",
    ]
)
def test_within_depth(root: Path, path_str: str, max_depth: int | None, expected: bool):
    """
    Tests that the max_depth logic is correctly applied.
    """
    path = root / path_str
    assert within_depth(path, root, max_depth) == expected