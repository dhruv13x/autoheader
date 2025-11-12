# tests/unit/test_headerlogic.py

import pytest
from autoheader.headerlogic import (
    analyze_header_state,
    build_new_lines,
    build_removed_lines,
    header_line_for,
    HeaderAnalysis,
)
# --- ADD THIS ---
from autoheader.constants import HEADER_PREFIX
import datetime
from unittest.mock import patch

# --- Fixtures for common inputs ---

# --- MODIFIED: Define test constants for new args ---
TEST_REL_PATH = "src/main.py"
TEST_PREFIX = HEADER_PREFIX  # Default Python prefix
TEST_TEMPLATE = f"{TEST_PREFIX}{{path}}"
TEST_CHECK_ENCODING = True  # We are testing Python logic here

EXPECTED_HEADER = header_line_for(TEST_REL_PATH, TEST_TEMPLATE)  # # src/main.py
# --- END MODIFIED ---

LINES_SHEBANG = ["#!/usr/bin/env python"]
LINES_ENCODING = ["# -*- coding: utf-8 -*-"]
LINES_CODE = ["import os", "", "print('hello')"]
LINES_CORRECT_HEADER = [EXPECTED_HEADER, "", *LINES_CODE]
LINES_INCORRECT_HEADER = ["# src/old.py", "", *LINES_CODE]


def test_header_line_for():
    """Tests the header_line_for function with all template variables."""
    template = "Copyright (c) {year} {filename} | {path}"
    with patch("autoheader.headerlogic.datetime") as mock_datetime:
        mock_datetime.datetime.now.return_value = datetime.datetime(2025, 1, 1)
        result = header_line_for("src/utils/parser.py", template)
        assert result == "Copyright (c) 2025 parser.py | src/utils/parser.py"


# --- Phase 1: test_analyze_header_state ---

@pytest.mark.parametrize(
    "lines_in, expected_analysis",
    [
        # 1. Empty file
        ([], HeaderAnalysis(0, None, False)),

        # 2. Shebang only
        (LINES_SHEBANG, HeaderAnalysis(1, None, False)),

        # 3. Encoding only
        (LINES_ENCODING, HeaderAnalysis(1, None, False)),

        # 4. Shebang + encoding
        ([*LINES_SHEBANG, *LINES_ENCODING], HeaderAnalysis(2, None, False)),

        # 5. No header (just code)
        (LINES_CODE, HeaderAnalysis(0, None, False)),

        # 6. Correct header
        (LINES_CORRECT_HEADER, HeaderAnalysis(0, EXPECTED_HEADER, True)),

        # 7. Incorrect header
        (
            LINES_INCORRECT_HEADER,
            HeaderAnalysis(0, "# src/old.py", False),
        ),

        # 8. 'startswith' fix (header with extra commentary)
        (
            [f"{EXPECTED_HEADER} (Refactored)", "", *LINES_CODE],
            HeaderAnalysis(0, f"{EXPECTED_HEADER} (Refactored)", True),
        ),

        # 9. Shebang + correct header
        (
            [*LINES_SHEBANG, *LINES_CORRECT_HEADER],
            HeaderAnalysis(1, EXPECTED_HEADER, True),
        ),
    ],
    ids=[
        "empty_file",
        "shebang_only",
        "encoding_only",
        "shebang_and_encoding",
        "no_header_code_only",
        "correct_header",
        "incorrect_header",
        "correct_header_with_comment",
        "shebang_with_correct_header",
    ],
)
def test_analyze_header_state(lines_in, expected_analysis):
    """
    Tests analyze_header_state against various file content scenarios.
    """
    # --- MODIFIED: Pass new required arguments ---
    analysis = analyze_header_state(
        lines_in, EXPECTED_HEADER, TEST_PREFIX, TEST_CHECK_ENCODING
    )
    # --- END MODIFIED ---
    assert analysis == expected_analysis


# --- Phase 2: test_build_new_lines ---

def test_build_new_lines_add_action():
    """
    Test 'add' action: no existing header, override=False.
    """
    lines_in = [*LINES_SHEBANG, *LINES_ENCODING, "", *LINES_CODE]
    # Expect insertion at index 2, after shebang and encoding
    analysis = HeaderAnalysis(insert_index=2, existing_header_line=None, has_correct_header=False)

    new_lines = build_new_lines(
        lines_in,
        EXPECTED_HEADER,
        analysis,
        override=False,
        blank_lines_after=1,
    )

    expected_lines = [
        "#!/usr/bin/env python",
        "# -*- coding: utf-8 -*-",
        EXPECTED_HEADER,  # Added
        "",  # Added blank line
        "",  # Original blank line
        "import os",
        "",
        "print('hello')",
    ]
    assert new_lines == expected_lines


def test_build_new_lines_override_action():
    """
    Test 'override' action: existing header, override=True.
    """
    lines_in = [*LINES_SHEBANG, "# src/old.py", "", *LINES_CODE]
    # Expect insertion at index 1, after shebang
    analysis = HeaderAnalysis(
        insert_index=1, existing_header_line="# src/old.py", has_correct_header=False
    )

    new_lines = build_new_lines(
        lines_in,
        EXPECTED_HEADER,
        analysis,
        override=True,
        blank_lines_after=1,
    )

    expected_lines = [
        "#!/usr/bin/env python",
        EXPECTED_HEADER,  # Overridden
        "",  # Added blank line
        "",  # Original blank line
        "import os",
        "",
        "print('hello')",
    ]
    assert new_lines == expected_lines


@pytest.mark.parametrize("blank_lines_count", [0, 1, 2])
def test_build_new_lines_blank_lines_after(blank_lines_count):
    """
    Test with blank_lines_after=0, 1, and 2.
    """
    lines_in = LINES_CODE
    analysis = HeaderAnalysis(insert_index=0, existing_header_line=None, has_correct_header=False)

    new_lines = build_new_lines(
        lines_in,
        EXPECTED_HEADER,
        analysis,
        override=False,
        blank_lines_after=blank_lines_count,
    )

    # Check that the header is at index 0
    assert new_lines[0] == EXPECTED_HEADER

    # Check that the correct number of blank lines follow
    for i in range(blank_lines_count):
        assert new_lines[i + 1] == ""

    # Check that the original code follows the blank lines
    assert new_lines[blank_lines_count + 1] == "import os"


# --- Phase 3: test_build_removed_lines ---

def test_build_removed_lines_with_blank():
    """
    Test removal of an existing header AND the following blank line.
    """
    lines_in = [EXPECTED_HEADER, "", *LINES_CODE]
    analysis = HeaderAnalysis(insert_index=0, existing_header_line=EXPECTED_HEADER, has_correct_header=True)

    new_lines = build_removed_lines(lines_in, analysis)

    # Both header (index 0) and blank line (index 1) should be gone.
    # The new list should start with the original code.
    assert new_lines == LINES_CODE


def test_build_removed_lines_no_blank():
    """
    Test removal of an existing header NOT followed by a blank line.
    """
    lines_in = [EXPECTED_HEADER, *LINES_CODE]  # No blank line
    analysis = HeaderAnalysis(insert_index=0, existing_header_line=EXPECTED_HEADER, has_correct_header=True)

    new_lines = build_removed_lines(lines_in, analysis)

    # Only the header (index 0) should be gone.
    assert new_lines == LINES_CODE


def test_build_removed_lines_idempotent():
    """
    Test that it is idempotent (does nothing) if no header exists.
    """
    lines_in = LINES_CODE
    analysis = HeaderAnalysis(insert_index=0, existing_header_line=None, has_correct_header=False)

    new_lines = build_removed_lines(lines_in, analysis)

    # List should be unchanged
    assert new_lines == LINES_CODE