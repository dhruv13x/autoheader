# src/autoheader/headerlogic.py

from __future__ import annotations
from dataclasses import dataclass
from typing import List
import datetime
from pathlib import Path
import ast

from .constants import ENCODING_RX


# --- MODIFIED ---
import hashlib


def header_line_for(
    rel_posix: str,
    template: str,
    content: str | None = None,
    existing_header: str | None = None,
    license_spdx: str | None = None,
    license_owner: str | None = None,
) -> str:
    """Creates the header line from a template, with smart year updating."""
    import re
    from . import licenses

    current_year = datetime.datetime.now().year
    year_to_insert = str(current_year)

    if existing_header and "{year}" in template:
        match = re.search(r"\b(\d{4})\b", existing_header)
        if match:
            existing_year = int(match.group(1))
            if existing_year < current_year:
                year_to_insert = f"{existing_year}-{current_year}"

    # Handle hash replacement before other formatting to avoid KeyErrors
    if "{hash}" in template and content is not None:
        file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        template = template.replace("{hash}", file_hash)

    # Handle license replacement
    license_text = ""
    if license_spdx:
        text = licenses.get_license_text(license_spdx)
        if text:
             # Basic substitution of year in the license text itself
             # SPDX licenses often use {year} or similar which might conflict with f-string.
             # Our licenses in licenses.py use {year} and {owner}.
             # We should format the license text first.
             # TODO: where to get owner? maybe from config? For now use a placeholder or empty.
             # Actually, if the user config has `license = {text = "MIT © dhruv13x"}` in pyproject.toml
             # we might want to use that.
             # For now, let's just expose the raw license text or format it with available data.

             # If the license text has {year}, we format it.
             # If it has {owner}, we need that info.
             # Let's assume for now we just pass the text and let the outer format handle it if it was embedded?
             # No, if {license} is in the template, we need to return the formatted license text.

             # Simple approach: Format license text with year.
             owner_str = license_owner if license_owner else "<Owner>"
             # --- FIX: Ensure owner_str is correctly passed ---
             # Some license texts might use {owner} placeholder, others might not.
             # We should try to format with both year and owner.
             try:
                # Replace explicitly known keys first to avoid formatting errors with curly braces in license text
                # (some licenses might contain { or } which break .format())
                # Note: We replace <year> and <owner> too as some templates use that convention.
                # And we replace [year] and [fullname] etc.

                # Standard autoheader placeholders from licenses.py
                license_text = text.replace("{year}", year_to_insert).replace("{owner}", owner_str)

                # Common SPDX placeholders
                license_text = license_text.replace("<year>", year_to_insert).replace("<owner>", owner_str)
                license_text = license_text.replace("[year]", year_to_insert).replace("[fullname]", owner_str)

                # Also try .format for simple cases where {} are used
                # But catch errors if the license has other braces
                try:
                    license_text = license_text.format(year=year_to_insert, owner=owner_str)
                except (IndexError, KeyError, ValueError):
                    pass
             except Exception:
                 # Fallback
                license_text = text

    return template.format(
        path=rel_posix,
        filename=Path(rel_posix).name,
        year=year_to_insert,
        license=license_text
    )


@dataclass
class HeaderAnalysis:
    """Result of analyzing file content for header state."""

    insert_index: int
    existing_header_line: str | None
    has_correct_header: bool
    has_tampered_header: bool = False


# --- MODIFIED ---
def analyze_header_state(
    lines: List[str],
    expected_header: str,
    prefix: str,
    check_encoding: bool,  # <-- ADD THIS
    analysis_mode: str = "line",
    check_hash: bool = False,
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

    expected_header_lines = expected_header.splitlines()
    num_expected_lines = len(expected_header_lines)

    # Check if the whole block matches
    is_correct = (
        lines[insert_index : insert_index + num_expected_lines] == expected_header_lines
    )

    if not is_correct and insert_index < len(lines) and lines[insert_index].startswith(prefix):
        if lines[insert_index].strip().startswith(expected_header_lines[0]):
            is_correct = True

    if insert_index < len(lines) and lines[insert_index].startswith(prefix):
        # For single-line compatibility, we still store the first line.
        existing_header = lines[insert_index].strip()

        if check_hash and "hash:" in existing_header:
            import re
            match = re.search(r"hash:([a-f0-9]{64})", existing_header)
            if match:
                existing_hash = match.group(1)
                content_without_header = "\n".join(lines[insert_index + 1 :])
                current_hash = hashlib.sha256(
                    content_without_header.encode("utf-8")
                ).hexdigest()
                if existing_hash != current_hash:
                    return HeaderAnalysis(insert_index, existing_header, False, has_tampered_header=True)


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
    expected_header_lines = expected_header.splitlines()

    if override and analysis.existing_header_line is not None:
        del new_lines[insert_at]

    # Insert header lines
    for i, line in enumerate(expected_header_lines):
        new_lines.insert(insert_at + i, line)

    # Insert N blank lines after it
    for i in range(blank_lines_after):
        new_lines.insert(insert_at + len(expected_header_lines) + i, "")

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
        # We need to determine how many lines the old header occupied.
        num_existing_lines = 0
        if analysis.existing_header_line:
            num_existing_lines = len(analysis.existing_header_line.splitlines())
        del new_lines[insert_at : insert_at + num_existing_lines]

        # If the next line is a blank line, remove it too
        if insert_at < len(new_lines) and not new_lines[insert_at].strip():
            del new_lines[insert_at]

    return new_lines
