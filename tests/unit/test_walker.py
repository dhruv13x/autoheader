# tests/unit/test_walker.py

import pytest
from pathlib import Path
from autoheader.walker import detect_project_root
from autoheader.models import RootDetectionResult

# 'pyfakefs_config' fixture is automatically used by pytest
# when the 'fs' fixture (from pyfakefs) is an argument.

@pytest.mark.usefixtures("pyfakefs_config")
def test_detect_project_root_success(fs):
    """
    Tests detection in a dir with 2+ markers.
    Fixture 'pyfakefs_config' creates 2 markers in /fake_project.
    """
    path = Path("/fake_project")
    result = detect_project_root(path)
    
    assert result.is_project_root is True
    assert result.match_count == 2
    assert result.path == path

@pytest.mark.usefixtures("pyfakefs_config")
def test_detect_project_root_failure(fs):
    """
    Tests detection in a dir with < 2 markers.
    '/other_project' was created with 1 marker by the fixture.
    """
    path = Path("/other_project")
    result = detect_project_root(path, min_matches=2)  # default
    
    assert result.is_project_root is False
    assert result.match_count == 1
    assert result.path == path

@pytest.mark.usefixtures("pyfakefs_config")
def test_detect_project_root_not_a_directory(fs):
    """
    Tests detection on a path that is not a directory.
    """
    path = Path("/fake_project/pyproject.toml")  # This is a file
    result = detect_project_root(path)
    
    assert result.is_project_root is False
    assert result.match_count == 0
    assert result.path == path