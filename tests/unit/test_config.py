# tests/unit/test_config.py

from pathlib import Path
# --- MODIFIED IMPORTS ---
from autoheader.config import (
    load_config_data,
    load_general_config,
    load_language_configs,
)
from autoheader.constants import HEADER_PREFIX
# --- END MODIFIED IMPORTS ---
import logging

# This TOML content is used by multiple tests
VALID_TOML_CONTENT = """
[general]
backup = true
workers = 4
override = true

[detection]
depth = 5
markers = ["pyproject.toml", ".git"]

[exclude]
paths = ["docs/", "*.generated.py"]

[header]
blank_lines_after = 2
"""

# --- MODIFIED: Refactored tests for new functions ---

def test_load_general_config_valid(fs):
    """
    Tests loading a valid, fully populated autoheader.toml.
    """
    root = Path("/fake_project")
    fs.create_dir(root)
    fs.create_file(root / "autoheader.toml", contents=VALID_TOML_CONTENT)
    
    toml_data, _ = load_config_data(root, config_url=None, timeout=10.0)
    config = load_general_config(toml_data)

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


def test_load_general_config_no_file(fs):
    """
    Tests loading config from a root with no autoheader.toml.
    """
    root = Path("/other_project")
    fs.create_dir(root)
    
    toml_data, _ = load_config_data(root, config_url=None, timeout=10.0)
    config = load_general_config(toml_data)
    assert config == {}


def test_load_config_data_malformed(fs, caplog):
    """
    Tests that a malformed TOML file logs a warning and returns {}.
    'caplog' is a pytest fixture to capture log output.
    """
    root = Path("/bad_toml")
    fs.create_dir(root)
    fs.create_file(root / "autoheader.toml", contents="[general]\n key = 'unterminated string")

    with caplog.at_level(logging.WARNING):
        toml_data, _ = load_config_data(root, config_url=None, timeout=10.0)
        config = load_general_config(toml_data)

    assert toml_data == {}
    assert config == {}
    assert "Could not parse autoheader.toml" in caplog.text


def test_load_general_config_partial(fs):
    """
    Tests that a partial config file is loaded correctly.
    """
    root = Path("/partial_config")
    fs.create_dir(root)
    fs.create_file(
        root / "autoheader.toml",
        contents="[general]\nworkers = 16\n[header]\nblank_lines_after = 0"
    )

    toml_data, _ = load_config_data(root, config_url=None, timeout=10.0)
    config = load_general_config(toml_data)
    
    expected_config = {
        "workers": 16,
        "blank_lines_after": 0,
    }
    assert config == expected_config

# --- ADDED NEW TESTS for load_language_configs ---

def test_load_language_configs_default(fs):
    """Tests that the default Python config is returned when no [language] section exists."""
    toml_data = {}
    general_config = {}
    
    languages = load_language_configs(toml_data, general_config)
    
    assert len(languages) == 1
    py_lang = languages[0]
    assert py_lang.name == "python"
    assert py_lang.file_globs == ["*.py", "*.pyi"]
    assert py_lang.prefix == HEADER_PREFIX
    assert py_lang.check_encoding is True
    assert py_lang.template == f"{HEADER_PREFIX}{{path}}"

def test_load_language_configs_legacy_prefix(fs):
    """Tests that the default config respects the old [header].prefix."""
    toml_data = {"header": {"prefix": "// "}}
    general_config = {"_legacy_prefix": "// "}

    languages = load_language_configs(toml_data, general_config)

    assert len(languages) == 1
    py_lang = languages[0]
    assert py_lang.name == "python"
    assert py_lang.prefix == "// "
    assert py_lang.template == "// {path}"

def test_load_language_configs_custom(fs):
    """Tests loading a custom [language.*] configuration."""
    custom_toml = """
    [language.javascript]
    file_globs = ["*.js", "*.ts"]
    prefix = "// "
    check_encoding = false
    template = "// HEADER: {path}"
    
    [language.css]
    file_globs = ["*.css"]
    prefix = "/* "
    template = "/* {path} */"
    """
    root = Path("/custom_lang")
    fs.create_dir(root)
    fs.create_file(root / "autoheader.toml", contents=custom_toml)
    
    toml_data, _ = load_config_data(root, config_url=None, timeout=10.0)
    general_config = load_general_config(toml_data)
    languages = load_language_configs(toml_data, general_config)
    
    assert len(languages) == 2
    
    js_lang = languages[0]
    assert js_lang.name == "javascript"
    assert js_lang.file_globs == ["*.js", "*.ts"]
    assert js_lang.prefix == "// "
    assert js_lang.check_encoding is False
    assert js_lang.template == "// HEADER: {path}"
    
    css_lang = languages[1]
    assert css_lang.name == "css"
    assert css_lang.file_globs == ["*.css"]
    assert css_lang.prefix == "/* "
    assert css_lang.check_encoding is False  # Test default
    assert css_lang.template == "/* {path} */"

def test_load_language_configs_missing_keys(fs, caplog):
    """Tests that a misconfigured language block is skipped."""
    custom_toml = """
    [language.bad]
    # 'prefix' and 'file_globs' are missing
    """
    root = Path("/bad_lang")
    fs.create_dir(root)
    fs.create_file(root / "autoheader.toml", contents=custom_toml)
    
    toml_data, _ = load_config_data(root, config_url=None, timeout=10.0)
    general_config = load_general_config(toml_data)
    
    with caplog.at_level(logging.WARNING):
        languages = load_language_configs(toml_data, general_config)
    
    # It logs a warning and falls back to the default Python config
    # --- THIS IS THE FIX ---
    assert "missing required key: 'prefix'" in caplog.text
    # --- END FIX ---
    assert len(languages) == 1
    assert languages[0].name == "python"