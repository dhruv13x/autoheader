from pathlib import Path
from unittest.mock import MagicMock, patch, ANY
import pytest
import logging
from autoheader.planner import (
    _analyze_single_file,
    plan_files,
    _get_language_for_file
)
from autoheader.models import PlanItem, LanguageConfig, RuntimeContext
from autoheader.constants import MAX_FILE_SIZE_BYTES

@pytest.fixture
def lang_config():
    return LanguageConfig(
        name="python",
        file_globs=["*.py"],
        template="",
        prefix="#",
        check_encoding=False,
        analysis_mode="auto",
    )

@pytest.fixture
def runtime_context():
    return RuntimeContext(
        root=Path("."),
        check_hash=False,
        remove=False,
        override=False,
        depth=None,
        excludes=[],
        timeout=10,
    )

@pytest.fixture
def mock_path():
    path = MagicMock(spec=Path)
    path.name = "test.py"
    path.relative_to.return_value.as_posix.return_value = "test.py"
    stat_mock = MagicMock()
    stat_mock.st_mtime = 12345
    stat_mock.st_size = 100
    path.stat.return_value = stat_mock
    path.match.side_effect = lambda glob: path.name.endswith(glob.strip("*"))
    return path

def test_analyze_single_file_inline_ignore(mock_path, lang_config, runtime_context):
    with patch("autoheader.planner.filesystem.read_file_lines", return_value=["# autoheader: ignore", "import os"]), \
         patch("autoheader.planner.filesystem.get_file_hash", return_value="some_hash"):
        result, _ = _analyze_single_file((mock_path, lang_config, runtime_context), {})
        assert result.action == "skip-excluded"
        assert result.reason == "inline ignore"

def test_get_language_for_file_no_match(lang_config):
    path = Path("test.txt")
    languages = [lang_config]
    assert _get_language_for_file(path, languages) is None

def test_analyze_single_file_stat_error(mock_path, lang_config, runtime_context):
    mock_path.stat.side_effect = IOError("Permission denied")

    result, _ = _analyze_single_file((mock_path, lang_config, runtime_context), {})
    assert result.action == "skip-excluded"
    assert "stat failed" in result.reason

def test_analyze_single_file_too_large(mock_path, lang_config, runtime_context):
    mock_path.stat.return_value.st_size = MAX_FILE_SIZE_BYTES + 1

    result, _ = _analyze_single_file((mock_path, lang_config, runtime_context), {})
    assert result.action == "skip-excluded"
    assert "exceeds limit" in result.reason

def test_analyze_single_file_hash_failed(mock_path, lang_config, runtime_context):
    with patch("autoheader.planner.filesystem.get_file_hash", return_value=None):
        result, _ = _analyze_single_file((mock_path, lang_config, runtime_context), {})
        assert result.action == "skip-excluded"
        assert result.reason == "hash failed"

def test_analyze_single_file_empty_file(mock_path, lang_config, runtime_context):
    with patch("autoheader.planner.filesystem.read_file_lines", return_value=[]), \
         patch("autoheader.planner.filesystem.get_file_hash", return_value="some_hash"):
        result, _ = _analyze_single_file((mock_path, lang_config, runtime_context), {})
        assert result.action == "skip-empty"

def test_analyze_single_file_remove_header(mock_path, lang_config, runtime_context):
    runtime_context.remove = True

    analysis_result = MagicMock()
    analysis_result.existing_header_line = "# My Header"
    analysis_result.has_correct_header = False
    analysis_result.has_tampered_header = False

    with patch("autoheader.planner.filesystem.read_file_lines", return_value=["# My Header", "import os"]), \
         patch("autoheader.planner.filesystem.get_file_hash", return_value="some_hash"), \
         patch("autoheader.planner.headerlogic.analyze_header_state", return_value=analysis_result):
        result, _ = _analyze_single_file((mock_path, lang_config, runtime_context), {})
        assert result.action == "remove"

def test_analyze_single_file_remove_no_header(mock_path, lang_config, runtime_context):
    runtime_context.remove = True

    analysis_result = MagicMock()
    analysis_result.existing_header_line = None
    analysis_result.has_correct_header = False
    analysis_result.has_tampered_header = False

    with patch("autoheader.planner.filesystem.read_file_lines", return_value=["import os"]), \
         patch("autoheader.planner.filesystem.get_file_hash", return_value="some_hash"), \
         patch("autoheader.planner.headerlogic.analyze_header_state", return_value=analysis_result):
        result, _ = _analyze_single_file((mock_path, lang_config, runtime_context), {})
        assert result.action == "skip-header-exists"
        assert result.reason == "no-header-to-remove"

def test_analyze_single_file_incorrect_header_no_override(mock_path, lang_config, runtime_context):
    runtime_context.override = False

    analysis_result = MagicMock()
    analysis_result.existing_header_line = "# Old Header"
    analysis_result.has_correct_header = False
    analysis_result.has_tampered_header = False

    with patch("autoheader.planner.filesystem.read_file_lines", return_value=["# Old Header", "import os"]), \
         patch("autoheader.planner.filesystem.get_file_hash", return_value="some_hash"), \
         patch("autoheader.planner.headerlogic.analyze_header_state", return_value=analysis_result):
        result, _ = _analyze_single_file((mock_path, lang_config, runtime_context), {})
        assert result.action == "skip-header-exists"
        assert result.reason == "incorrect-header-no-override"

def test_plan_files_no_language_configured(caplog, lang_config, runtime_context, mock_path):
    # Setup mock path to not match the language config (which expects .py)
    mock_path.name = "test.txt"
    mock_path.match.side_effect = lambda glob: False

    files = [mock_path]
    languages = [lang_config]

    with patch("autoheader.planner.filesystem.load_cache", return_value={}), \
         caplog.at_level(logging.WARNING):
        generator, count = plan_files(runtime_context, files, languages, workers=1)
        results = list(generator)
        assert not results
        assert count == 0
        assert "No language configuration found for file" in caplog.text

def test_analyze_single_file_cached(mock_path, lang_config, runtime_context):
    cache = {"test.py": {"mtime": 12345, "hash": "some_hash"}}

    result, _ = _analyze_single_file((mock_path, lang_config, runtime_context), cache)
    assert result.action == "skip-header-exists"
    assert result.reason == "cached"

def test_plan_files_no_files_provided(runtime_context, lang_config):
    languages = [lang_config]

    with patch("autoheader.planner.filesystem.load_cache", return_value={}), \
         patch("autoheader.planner.filesystem.find_configured_files", return_value=[]) as mock_find:
        generator, count = plan_files(runtime_context, None, languages, workers=1)
        list(generator) # Consume
        mock_find.assert_called_once_with(runtime_context.root, languages)
