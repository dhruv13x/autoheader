# src/autoheader/constants.py

from __future__ import annotations
import re

HEADER_PREFIX = "# "  # exact header line prefix
# PEP 263 encoding-cookie regex
ENCODING_RX = re.compile(r"^[ \t]*#.*coding[:=][ \t]*([-\w.]+)")

DEFAULT_EXCLUDES = {
    ".git",
    ".github",
    ".svn",
    ".hg",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    "node_modules",
}

ROOT_MARKERS = [
    ".gitignore",
    "README.md",
    "README.rst",
    "pyproject.toml",
]

# NEW: Add a file size limit to prevent resource exhaustion (10MB)
MAX_FILE_SIZE_BYTES = 10_000_000

# NEW: Config file name
CONFIG_FILE_NAME = "autoheader.toml"

# --- ADD THIS ---
# NEW: Inline ignore comment
INLINE_IGNORE_COMMENT = "autoheader: ignore"