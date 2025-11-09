# tests/unit/test_config.py

import pytest
from pathlib import Path
from autoheader.config import load_config
import logging

# 'pyfakefs_config' fixture is automatically used by pytest
# when the 'fs' fixture (from pyfakefs) is an argument.

@pytest.mark.usefixtures("pyfakefs_config")
def test_load_config_valid(fs):
    """
    Tests loading a valid, fully populated autoheader.toml.
    Uses the file created in 'pyfakefs_config' fixture.
    """
    root = Path("/fake_project")
    config = load_config(root)
    
    expected_config = {
        "backup": True,
        "workers": 4,
        "override": True,
        "depth": 5,
        "markers": ["pyproject.toml", ".git"],
        "exclude": ["docs/", "*.generated.py"],
        "blank_lines_after": 2,
    }
    assert config == expected_config

@pytest.mark.usefixtures("pyfakefs_config")
def test_load_config_no_file(fs):
    """
    Tests loading config from a root with no autoheader.toml.
    Uses the '/other_project' created in the fixture.
    """
    root = Path("/other_project")
    config = load_config(root)
    assert config == {}

def test_load_config_malformed(fs, caplog):
    """
    Tests that a malformed TOML file logs a warning and returns {}.
    'caplog' is a pytest fixture to capture log output.
    """
    root = Path("/bad_toml")
    fs.create_dir(root)
    fs.create_file(root / "autoheader.toml", contents="[general]\n key = 'unterminated string")
    
    with caplog.at_level(logging.WARNING):
        config = load_config(root)
    
    assert config == {}
    assert "Could not parse autoheader.toml" in caplog.text

def test_load_config_partial(fs):
    """
    Tests that a partial config file is loaded correctly.
    """
    root = Path("/partial_config")
    fs.create_dir(root)
    fs.create_file(
        root / "autoheader.toml",
        contents="[general]\nworkers = 16\n[header]\nblank_lines_after = 0"
    )
    
    config = load_config(root)
    expected_config = {
        "workers": 16,
        "blank_lines_after": 0,
    }
    assert config == expected_config