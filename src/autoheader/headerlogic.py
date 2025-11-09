# src/autoheader/headerlogic.py

from __future__ import annotations
from dataclasses import dataclass
from typing import List

from .constants import ENCODING_RX, HEADER_PREFIX


def header_line_for(rel_posix: str) -> str:
    return f"{HEADER_PREFIX}{rel_posix}"


@dataclass
class HeaderAnalysis:
    """Result of analyzing file content for header state."""

    insert_index: int
    existing_header_line: str | None
    has_correct_header: bool


def analyze_header_state(
    lines: List[str],
    expected_header: str,
) -> HeaderAnalysis:
    """
    Pure, testable logic to find header insertion point and check existing state.
    This replaces compute_insert_index, has_correct_header, and has_any_header.
    """
    if not lines:
        return HeaderAnalysis(0, None, False)

    i = 0
    if lines[0].startswith("#!"):
        i = 1  # Insert after shebang

    # Check for encoding cookie on line 1 or 2
    if i == 0 and ENCODING_RX.match(lines[0]):
        i = 1
    elif len(lines) > i and ENCODING_RX.match(lines[i]):
        i += 1

    # At this point, `i` is the correct insertion index
    insert_index = i
    existing_header = None
    is_correct = False

    if insert_index < len(lines) and lines[insert_index].startswith(HEADER_PREFIX):
        existing_header = lines[insert_index].strip()
        # --- THE FIX ---
        # Check if the existing line *starts with* the expected header
        # This allows for comments like # src/autoheader/cli.py (Refactored)
        if existing_header.startswith(expected_header):
            is_correct = True

    return HeaderAnalysis(insert_index, existing_header, is_correct)


def build_new_lines(
    lines: List[str],
    expected_header: str,
    analysis: HeaderAnalysis,
    override: bool,
    blank_lines_after: int,  # <-- NEW
) -> List[str]:
    """
    Pure, testable logic to construct the new file content.
    This replaces the core logic of write_with_header.
    """
    new_lines = lines[:]
    insert_at = analysis.insert_index

    # Override mode: remove existing header if present
    # This logic is correct for *override*
    if override and analysis.existing_header_line is not None:
        del new_lines[insert_at]

    # Insert header
    new_lines.insert(insert_at, expected_header)

    # Insert N blank lines after it
    for i in range(blank_lines_after):
        new_lines.insert(insert_at + 1 + i, "")

    return new_lines


def build_removed_lines(
    lines: List[str],
    analysis: HeaderAnalysis,
) -> List[str]:
    """
    Pure, testable logic to construct file content with header removed.
    """
    new_lines = lines[:]
    insert_at = analysis.insert_index

    if analysis.existing_header_line is not None:
        # Remove the header line
        del new_lines[insert_at]

        # If the next line is a blank line, remove it too
        if insert_at < len(new_lines) and not new_lines[insert_at].strip():
            del new_lines[insert_at]

    return new_lines