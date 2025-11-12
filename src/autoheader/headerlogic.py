# src/autoheader/headerlogic.py

from __future__ import annotations
from dataclasses import dataclass
from typing import List
import datetime
from pathlib import Path
import ast

from .constants import ENCODING_RX


# --- MODIFIED ---
def header_line_for(rel_posix: str, template: str) -> str:
    """Creates the header line from a template."""
    return template.format(
        path=rel_posix,
        filename=Path(rel_posix).name,
        year=datetime.datetime.now().year,
    )


@dataclass
class HeaderAnalysis:
    """Result of analyzing file content for header state."""

    insert_index: int
    existing_header_line: str | None
    has_correct_header: bool


# --- MODIFIED ---
def analyze_header_state(
    lines: List[str],
    expected_header: str,
    prefix: str,
    check_encoding: bool,  # <-- ADD THIS
    analysis_mode: str = "line",
) -> HeaderAnalysis:
    """
    Pure, testable logic to find header insertion point and check existing state.
    This replaces compute_insert_index, has_correct_header, and has_any_header.
    """
    if not lines:
        return HeaderAnalysis(0, None, False)

    i = 0
    # --- MAKE PYTHON-SPECIFIC LOGIC CONDITIONAL ---
    if check_encoding and lines[0].startswith("#!"):
        i = 1  # Insert after shebang

    # Check for encoding cookie on line 1 or 2
    if check_encoding:
        if i == 0 and ENCODING_RX.match(lines[0]):
            i = 1
        elif len(lines) > i and ENCODING_RX.match(lines[i]):
            i += 1
    # --- END CONDITIONAL BLOCK ---
    if analysis_mode == "ast":
        # Special handling for Python AST analysis
        # We still respect shebang/encoding, but then use AST to find the true
        # start of the code, ignoring the module-level docstring.
        try:
            # Join lines starting from `i` (after shebang/encoding)
            content_to_parse = "\n".join(lines[i:])
            if not content_to_parse.strip():
                return HeaderAnalysis(i, None, False)

            tree = ast.parse(content_to_parse)
            relative_insert_index = 0

            for node in tree.body:
                is_docstring = (
                    isinstance(node, ast.Expr)
                    and isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, str)
                )
                is_future_import = (
                    isinstance(node, ast.ImportFrom) and node.module == "__future__"
                )

                if is_docstring or is_future_import:
                    if node.end_lineno is not None:
                        relative_insert_index = node.end_lineno
                else:
                    break
            i += relative_insert_index

        except (SyntaxError, IndexError, ValueError):
            # If the file isn't valid Python, fall back to the simple line-based
            # analysis. `i` will still be at the correct shebang/encoding offset.
            pass

    # At this point, `i` is the correct insertion index
    insert_index = i
    existing_header = None
    is_correct = False

    if insert_index < len(lines) and lines[insert_index].startswith(prefix):
        existing_header = lines[insert_index].strip()
        
        if existing_header.startswith(expected_header):
            is_correct = True

    return HeaderAnalysis(insert_index, existing_header, is_correct)


def build_new_lines(
    lines: List[str],
    expected_header: str,
    analysis: HeaderAnalysis,
    override: bool,
    blank_lines_after: int,
) -> List[str]:
    """
    Pure, testable logic to construct the new file content.
    This replaces the core logic of write_with_header.
    """
    new_lines = lines[:]
    insert_at = analysis.insert_index

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