
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import logging
from autoheader.core import (
    write_with_header,
)
# Update imports to point to planner
from autoheader.planner import plan_files, _analyze_single_file, _get_language_for_file
from autoheader.models import PlanItem, LanguageConfig, RuntimeContext
from autoheader.constants import MAX_FILE_SIZE_BYTES

def create_lang_config():
    return LanguageConfig(
        name="python",
        file_globs=["*.py"],
        template="",
        prefix="#",
        check_encoding=False,
        analysis_mode="auto",
    )

def create_runtime_context(**kwargs):
    defaults = {
        "root": Path("."),
        "check_hash": False,
        "remove": False,
        "override": False,
        "depth": None,
        "excludes": [],
        "timeout": 10,
    }
    defaults.update(kwargs)
    return RuntimeContext(**defaults)

def create_mock_path(name="test.py", size=100, mtime=12345):
    mock_path = MagicMock(spec=Path)
    mock_path.name = name
    mock_path.relative_to.return_value.as_posix.return_value = name
    stat_mock = MagicMock()
    stat_mock.st_mtime = mtime
    stat_mock.st_size = size
    mock_path.stat.return_value = stat_mock
    mock_path.match.side_effect = lambda glob: name.endswith(glob.strip("*"))
    return mock_path

# ... existing analyze_single_file tests ...

def test_plan_files_no_language_configured(caplog):
    context = create_runtime_context()
    files = [create_mock_path(name="test.txt")]
    languages = [create_lang_config()]

    with patch("autoheader.planner.filesystem.load_cache", return_value={}), \
         caplog.at_level(logging.WARNING):
        generator, count = plan_files(context, files, languages, workers=1)
        results = list(generator)
        assert not results
        assert count == 0
        assert "No language configuration found for file" in caplog.text

def test_analyze_single_file_cached():
    mock_path = create_mock_path(mtime=12345)
    lang = create_lang_config()
    context = create_runtime_context()
    cache = {"test.py": {"mtime": 12345, "hash": "some_hash"}}

    result, _ = _analyze_single_file((mock_path, lang, context), cache)
    assert result.action == "skip-header-exists"
    assert result.reason == "cached"

def test_plan_files_no_files_provided():
    context = create_runtime_context()
    languages = [create_lang_config()]

    with patch("autoheader.planner.filesystem.load_cache", return_value={}), \
         patch("autoheader.planner.filesystem.find_configured_files", return_value=[]) as mock_find:
        generator, count = plan_files(context, None, languages, workers=1)
        list(generator) # Consume
        mock_find.assert_called_once_with(context.root, languages)

def test_write_with_header_remove():
    item = PlanItem(
        path=create_mock_path(),
        rel_posix="test.py",
        action="remove",
        prefix="#",
        check_encoding=False,
        template="",
        analysis_mode="auto",
    )

    with patch("autoheader.core.filesystem.read_file_lines", return_value=["# My Header", "import os"]), \
         patch("autoheader.core.filesystem.write_file_content") as mock_write, \
         patch("autoheader.core.headerlogic.build_removed_lines", return_value=["import os"]), \
         patch("autoheader.core.filesystem.get_file_hash", return_value="new_hash"):
        write_with_header(item, backup=False, dry_run=False, blank_lines_after=1)
        mock_write.assert_called_once()
        assert "# My Header" not in mock_write.call_args[0][1]

def test_write_with_header_dry_run():
    item = PlanItem(
        path=create_mock_path(),
        rel_posix="test.py",
        action="add",
        prefix="#",
        check_encoding=False,
        template="",
        analysis_mode="auto",
    )

    with patch("autoheader.core.filesystem.read_file_lines", return_value=["import os"]), \
         patch("autoheader.core.filesystem.get_file_hash", return_value="new_hash"):
        _, _, _, diff_info = write_with_header(item, backup=False, dry_run=True, blank_lines_after=1)
        assert diff_info is not None

def test_write_with_header_add():
    item = PlanItem(
        path=create_mock_path(),
        rel_posix="test.py",
        action="add",
        prefix="#",
        check_encoding=False,
        template="",
        analysis_mode="auto",
    )

    with patch("autoheader.core.filesystem.read_file_lines", return_value=["import os"]), \
         patch("autoheader.core.filesystem.write_file_content") as mock_write, \
         patch("autoheader.core.headerlogic.build_new_lines", return_value=["# New Header", "import os"]), \
         patch("autoheader.core.filesystem.get_file_hash", return_value="new_hash"):
        write_with_header(item, backup=False, dry_run=False, blank_lines_after=1)
        mock_write.assert_called_once()
        assert "# New Header" in mock_write.call_args[0][1]
