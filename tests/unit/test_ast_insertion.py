# tests/unit/test_ast_insertion.py

import pytest
from autoheader.headerlogic import (
    analyze_header_state,
)
from autoheader.constants import HEADER_PREFIX

TEST_REL_PATH = "src/main.py"
TEST_PREFIX = HEADER_PREFIX
TEST_TEMPLATE = f"{TEST_PREFIX}{{path}}"
TEST_CHECK_ENCODING = True

EXPECTED_HEADER = f"{TEST_PREFIX}{TEST_REL_PATH}"

# Scenarios for AST analysis
LINES_DOCSTRING = ['"""Module docstring."""', "import os"]
LINES_CODE_ONLY = ["import os"]
LINES_SHEBANG_DOCSTRING = ["#!/usr/bin/env python", '"""Module docstring."""', "import os"]
LINES_SHEBANG_ENCODING_DOCSTRING = ["#!/usr/bin/env python", "# -*- coding: utf-8 -*-", '"""Module docstring."""', "import os"]
LINES_FUTURE_IMPORT = ["from __future__ import annotations", "import os"]
LINES_EMPTY = []

@pytest.mark.parametrize(
    "lines_in, expected_insert_index",
    [
        (LINES_DOCSTRING, 1),
        (LINES_CODE_ONLY, 0),
        (LINES_SHEBANG_DOCSTRING, 2),
        (LINES_SHEBANG_ENCODING_DOCSTRING, 3),
        (LINES_FUTURE_IMPORT, 1),
        (LINES_EMPTY, 0),
    ],
    ids=[
        "with_docstring",
        "code_only",
        "shebang_with_docstring",
        "shebang_encoding_with_docstring",
        "future_import",
        "empty_file",
    ],
)
def test_analyze_header_state_ast_mode(lines_in, expected_insert_index):
    """
    Tests analyze_header_state with analysis_mode='ast'.
    """
    analysis = analyze_header_state(
        lines_in, EXPECTED_HEADER, TEST_PREFIX, TEST_CHECK_ENCODING, analysis_mode="ast"
    )
    assert analysis.insert_index == expected_insert_index
