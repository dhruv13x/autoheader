
import datetime
import hashlib
from unittest.mock import patch

from autoheader.headerlogic import (
    HeaderAnalysis,
    analyze_header_state,
    build_new_lines,
    build_removed_lines,
    header_line_for,
)


@patch("autoheader.headerlogic.datetime")
def test_header_line_for_simple_year(mock_dt):
    mock_dt.datetime.now.return_value = datetime.datetime(2025, 1, 1)
    template = "# {year}"
    result = header_line_for("test.py", template)
    assert result == "# 2025"


@patch("autoheader.headerlogic.datetime")
def test_header_line_for_smart_year_update(mock_dt):
    mock_dt.datetime.now.return_value = datetime.datetime(2025, 1, 1)
    template = "# {year}"
    existing_header = "# 2020"
    result = header_line_for("test.py", template, existing_header=existing_header)
    assert result == "# 2020-2025"


@patch("autoheader.headerlogic.datetime")
def test_header_line_for_smart_year_no_update_needed(mock_dt):
    mock_dt.datetime.now.return_value = datetime.datetime(2025, 1, 1)
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


def test_analyze_header_state_shebang_and_encoding():
    lines = ["#!/usr/bin/env python", "# -*- coding: utf-8 -*-", "import os"]
    analysis = analyze_header_state(lines, "", "#", check_encoding=True)
    assert analysis.insert_index == 2


def test_analyze_header_state_encoding_no_shebang():
    lines = ["# -*- coding: utf-8 -*-", "import os"]
    analysis = analyze_header_state(lines, "", "#", check_encoding=True)
    assert analysis.insert_index == 1


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


def test_build_new_lines_no_blank_lines():
    analysis = HeaderAnalysis(0, None, False)
    lines = build_new_lines([], "header", analysis, False, 0)
    assert lines == ["header"]


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
