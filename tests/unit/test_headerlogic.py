import datetime
import hashlib
from unittest.mock import patch, MagicMock
import pytest

from autoheader.headerlogic import (
    HeaderAnalysis,
    analyze_header_state,
    build_new_lines,
    build_removed_lines,
    header_line_for,
)

# --- header_line_for Tests ---

@pytest.mark.parametrize("year, expected_year_str", [
    (2025, "2025"),
    (2030, "2030"),
])
def test_header_line_for_simple_year(year, expected_year_str):
    # Mocking datetime.datetime to return a mocked object with 'year' attribute
    with patch("autoheader.headerlogic.datetime.datetime") as mock_dt:
        mock_now = MagicMock()
        mock_now.year = year
        mock_dt.now.return_value = mock_now

        template = "# {year}"
        result = header_line_for("test.py", template)
        assert result == f"# {expected_year_str}"


def test_header_line_for_smart_year_update():
    with patch("autoheader.headerlogic.datetime.datetime") as mock_dt:
        mock_now = MagicMock()
        mock_now.year = 2025
        mock_dt.now.return_value = mock_now

        template = "# {year}"
        existing_header = "# 2020"
        result = header_line_for("test.py", template, existing_header=existing_header)
        assert result == "# 2020-2025"


def test_header_line_for_smart_year_no_update_needed():
    with patch("autoheader.headerlogic.datetime.datetime") as mock_dt:
        mock_now = MagicMock()
        mock_now.year = 2025
        mock_dt.now.return_value = mock_now

        template = "# {year}"
        existing_header = "# 2025"
        result = header_line_for("test.py", template, existing_header=existing_header)
        assert result == "# 2025"

def test_header_line_for_no_year():
    template = "# {path}"
    result = header_line_for("test.py", template)
    assert result == "# test.py"


def test_header_line_for_hash():
    template = "# {hash}"
    content = "hello world"
    expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    result = header_line_for("test.js", template, content=content)
    assert result == f"# {expected_hash}"

# --- analyze_header_state Tests ---

@pytest.mark.parametrize("lines, expected_index", [
    (["#!/usr/bin/env python", "# -*- coding: utf-8 -*-", "import os"], 2),
    (["#!/usr/bin/env python", "import os"], 1),
    (["# -*- coding: utf-8 -*-", "import os"], 1),
    (["import os"], 0),
    ([], 0),
])
def test_analyze_header_state_shebang_and_encoding(lines, expected_index):
    analysis = analyze_header_state(lines, "", "#", check_encoding=True)
    assert analysis.insert_index == expected_index

def test_analyze_header_state_ast_mode_no_docstring():
    lines = ["import os", "print('hello')"]
    analysis = analyze_header_state(
        lines, "expected_header", "#", check_encoding=False, analysis_mode="ast"
    )
    assert analysis.insert_index == 0


def test_analyze_header_state_ast_mode():
    lines = ['"""Module docstring."""', "import os", "print('hello')"]
    analysis = analyze_header_state(
        lines, "expected_header", "#", check_encoding=False, analysis_mode="ast"
    )
    assert analysis.insert_index == 1


def test_analyze_header_state_ast_mode_with_future_import():
    lines = [
        '"""Module docstring."""',
        "from __future__ import annotations",
        "import os",
    ]
    analysis = analyze_header_state(
        lines, "expected_header", "#", check_encoding=False, analysis_mode="ast"
    )
    assert analysis.insert_index == 2


def test_analyze_header_state_ast_mode_invalid_python():
    lines = ["invalid python code"]
    analysis = analyze_header_state(
        lines, "expected_header", "#", check_encoding=False, analysis_mode="ast"
    )
    assert analysis.insert_index == 0


def test_analyze_header_state_empty_content_ast_mode():
    lines = [""]
    analysis = analyze_header_state(
        lines, "expected_header", "#", check_encoding=False, analysis_mode="ast"
    )
    assert analysis.insert_index == 0


def test_analyze_header_state_compatibility_check_no_match():
    lines = ["# different prefix", "import os"]
    analysis = analyze_header_state(lines, "# header", "+", False)
    assert not analysis.has_correct_header


def test_analyze_header_state_tampered_header():
    # This hash doesn't match the content
    lines = [
        "# hash:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "print('hello')",
    ]
    analysis = analyze_header_state(
        lines, "header", "#", check_encoding=False, check_hash=True
    )
    assert analysis.has_tampered_header


def test_analyze_header_state_hash_check_no_hash():
    lines = ["# no hash here", "print('hello')"]
    analysis = analyze_header_state(
        lines, "header", "#", check_encoding=False, check_hash=True
    )
    assert not analysis.has_tampered_header

# --- build_new_lines Tests ---

def test_build_new_lines_no_blank_lines():
    analysis = HeaderAnalysis(0, None, False)
    lines = build_new_lines([], "header", analysis, False, 0)
    assert lines == ["header"]

def test_build_new_lines_with_blank_lines():
    analysis = HeaderAnalysis(0, None, False)
    lines = build_new_lines(["code"], "header", analysis, False, 2)
    assert lines == ["header", "", "", "code"]

# --- build_removed_lines Tests ---

def test_build_removed_lines_multiline_header_with_blank():
    lines = ["# line 1", "# line 2", "", "import os"]
    analysis = HeaderAnalysis(
        insert_index=0,
        existing_header_line="# line 1\n# line 2",
        has_correct_header=False,
    )
    result = build_removed_lines(lines, analysis)
    assert result == ["import os"]


def test_build_removed_lines_no_blank_after():
    lines = ["# line 1", "import os"]
    analysis = HeaderAnalysis(
        insert_index=0, existing_header_line="# line 1", has_correct_header=False
    )
    result = build_removed_lines(lines, analysis)
    assert result == ["import os"]


def test_build_removed_lines_empty_existing_header():
    lines = ["import os"]
    analysis = HeaderAnalysis(
        insert_index=0, existing_header_line="", has_correct_header=False
    )
    result = build_removed_lines(lines, analysis)
    assert result == ["import os"]
