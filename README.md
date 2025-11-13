<div align="center">
  <img src="https://raw.githubusercontent.com/dhruv13x/autoheader/main/autoheader_logo.png" alt="autoheader logo" width="200"/>
</div>

<div align="center">

<!-- Package Info -->
[![PyPI version](https://img.shields.io/pypi/v/autoheader.svg)](https://pypi.org/project/autoheader/)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
![Wheel](https://img.shields.io/pypi/wheel/autoheader.svg)
[![Release](https://img.shields.io/badge/release-PyPI-blue)](https://pypi.org/project/autoheader/)

<!-- Build & Quality -->
[![Build status](https://github.com/dhruv13x/autoheader/actions/workflows/publish.yml/badge.svg)](https://github.com/dhruv13x/autoheader/actions/workflows/publish.yml)
[![Codecov](https://codecov.io/gh/dhruv13x/autoheader/graph/badge.svg)](https://codecov.io/gh/dhruv13x/autoheader)
[![Test Coverage](https://img.shields.io/badge/coverage-90%25%2B-brightgreen.svg)](https://github.com/dhruv13x/autoheader/actions/workflows/test.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/badge/linting-ruff-yellow.svg)](https://github.com/astral-sh/ruff)
![Security](https://img.shields.io/badge/security-CodeQL-blue.svg)

<!-- Usage -->
![Downloads](https://img.shields.io/pypi/dm/autoheader.svg)
![OS](https://img.shields.io/badge/os-Linux%20%7C%20macOS%20%7C%20Windows-blue.svg)
![Languages](https://img.shields.io/badge/languages-Python%20%7C%20JavaScript%20%7C%20TypeScript-green.svg)
[![Python Versions](https://img.shields.io/pypi/pyversions/autoheader.svg)](https://pypi.org/project/autoheader/)

<!-- License -->
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

<!-- Docs -->
[![Docs](https://img.shields.io/badge/docs-latest-brightgreen.svg)](https://your-docs-link)

</div>


# autoheader

**autoheader** is an enterprise-grade CLI tool for **source code projects** that automatically adds or refreshes file headers containing each file's *repo-relative path*.  
This helps developers quickly identify file origins, improves navigation in large codebases, and standardizes file structure across teams.

Example of what `autoheader` produces:

```python
# src/utils/parser.py

from __future__ import annotations
...
```

```javascript
// src/api/client.js

import { fetch } from 'node-fetch';
...
```

Perfect for monorepos, multi-module architectures, enterprise codebases, and any project where file traceability matters.

## ✅ Features

* 🌐 **Polyglot Support:** Manages headers for Python, JavaScript, Go, CSS, and any other language via a simple TOML configuration.
* ⚡ **Rich UX:** Beautiful, modern output with emojis, progress bars, and a formatted help screen (powered by Rich).
* 👁️ **Visual Diffs:** See exactly what will change with side-by-side diffs during dry-runs.
* 🧠 **Smart Copyright:** Automatically updates year ranges (e.g., 2020-2025) in existing headers instead of overwriting them.
* 🚀 **Performance:** Supports passing specific files for blazing fast execution in pre-commit hooks.
* ⚙️ **Smart Setup:** Get started in seconds with `autoheader --init` to generate a default configuration file.
* 📂 **Team Configuration:** Centralize settings for your whole team using `autoheader.toml` or a remote config URL.
* 🛡️ **Pre-commit Integration:** Automatically enforce headers on every commit with `autoheader --check`.
* 🤖 **Auto-Installer:** Get started in seconds with `autoheader --install-precommit`.
* **Smart Filtering:**
  * **.gitignore Aware:** Automatically respects all patterns in your project's `.gitignore` file.
  * **Inline Ignores:** Skip any file by adding `autoheader: ignore` anywhere in its content.
  * **Robust Excludes:** Includes a depth guard (`--depth`) and a robust exclusion system (`--exclude`).
* **Idempotent & Safe:** Runs repeatedly with no duplicates. Dry-run by default.
* **Flexible Modes:** Supports `--override` (for refactoring), `--remove` (for cleanup), and `--backup` (for safety).
* **CI-Friendly:** Full support for `--yes` and `--quiet` flags for non-interactive environments.
* **Automatic Root Detection:** Uses project markers (`pyproject.toml`, `README.md`, `.gitignore`) to confirm safe execution.

## 📦 Installation

Install from PyPI:

```bash
pip install "autoheader[precommit]"
```

* The `[precommit]` extra installs `pyyaml`, which is required for the `autoheader --install-precommit` command.
* `rich-argparse` is now a direct dependency and will be installed automatically.

Or install the latest version directly from source:

```bash
pip install git+https://github.com/dhruv13x/autoheader
```

## 🚀 Quick Start

### Step 1. Initialize (Recommended)

Run `autoheader --init` to create a default `autoheader.toml` file in your project.

```bash
autoheader --init
```

> ✅ Created default config at /path/to/project/autoheader.toml.
> 
> This file is pre-configured for Python files and lists all default settings.

### Step 2. Run a Dry-Run

Run `autoheader` for a safe, colorful dry-run. If headers need changing, you will see a visual diff:

```bash
autoheader
```

### Step 3. Apply Changes

To apply changes to your files for real, use `--no-dry-run`:

```bash
autoheader --no-dry-run
```

## 🛡️ Pre-commit & CI Mode

`autoheader` is built for modern CI/CD and pre-commit workflows.

### 1. `autoheader --check`

The `--check` flag runs `autoheader` in a dry-run mode. If any files need headers added, removed, or overridden, it will print the files and exit with code 1, **failing your CI or pre-commit hook**.

This is the engine that enforces header consistency.

### 2. `autoheader --install-precommit`

This is the easiest way to get started. It automatically finds your `.pre-commit-config.yaml` (or creates one) and adds `autoheader` as a local hook.

**Requires pyyaml:** You must run `pip install "autoheader[precommit]"` first.

```bash
# 1. Install with pre-commit support
pip install "autoheader[precommit]"

# 2. Add autoheader to your .pre-commit-config.yaml
autoheader --install-precommit

# 3. Activate the hook
pre-commit install
```

Now, `autoheader --check` will run automatically on every commit.

### 3. Manual Pre-commit Config

You can also add `autoheader` as a remote hook. For a multi-language project, we recommend specifying `types_or` to run on all configured file types.

Add this to your `.pre-commit-config.yaml`:

```yaml
- repo: https://github.com/dhruv13x/autoheader
  rev: v4.1.0  # <-- Use the latest version
  hooks:
    - id: autoheader
      name: autoheader file header checker
      # Run on any file type you have configured in autoheader.toml
      types_or: [python, javascript]
```

## 📂 Enterprise Configuration (`autoheader.toml`)

For teams, you can stop passing CLI flags and standardize settings in an `autoheader.toml` file at your project's root.

**Precedence:** CLI arguments > `autoheader.toml` settings > Application defaults.

Run `autoheader --init` to generate a file pre-filled with the defaults, which looks like this:

```toml
# autoheader configuration file
# Generated by `autoheader --init`
# For more info, see: https://github.com/dhruv13x/autoheader

[general]
# Run in simulation mode. (Default: true)
# To apply changes, run `autoheader --no-dry-run` or set:
# dry_run = false

# Create .bak files before modifying. (Default: false)
backup = false

# Number of parallel workers. (Default: 8)
workers = 8

# auto-confirm all prompts (e.g., for CI). (Default: false)
# yes = false

[detection]
# Max directory depth to scan. (Default: no limit)
# depth = 10

# Files that mark the project root.
markers = [
    ".gitignore",
    "README.md",
    "README.rst",
    "pyproject.toml",
]

[exclude]
# Extra paths/globs to exclude.
# The built-in defaults are included below for convenience.
# Note: .gitignore patterns are also automatically included.
paths = [
    ".git",
    ".github",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".svn",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "env",
    "node_modules",
    "venv",
]

# This legacy section is used for the global `blank_lines_after` setting.
[header]
blank_lines_after = 1

# --- Language-Specific Configuration ---
# autoheader v2.0+ uses language blocks.
# The default config for Python is shown below.
# You can add more, e.g., [language.javascript], [language.go], etc.

[language.python]
# Globs to identify files for this language
file_globs = [
    "*.py",
    "*.pyi",
]

# The comment prefix to use
prefix = "# "

# The template for the header line. {path} is the placeholder.
template = "# {path}"

# Whether to check for shebangs/encoding (Python-specific)
check_encoding = true
```

### Example: Adding JavaScript Support

To add support for JavaScript, simply add another language block:

```toml
[language.javascript]
file_globs = ["*.js", "*.jsx", "*.ts"]
prefix = "// "
template = "// {path}"
check_encoding = false  # No shebangs to worry about
```

## 📘 Advanced Usage

### Run on Specific Files

You can pass specific file paths to `autoheader` to only process those files. This is extremely fast for CI/CD pipelines that only want to check changed files.

```bash
autoheader src/main.py src/utils.py --no-dry-run
```

### Ignore Specific Files

To exclude a single file without adding it to `autoheader.toml` or `.gitignore`, add a magic comment anywhere in the file's content:

```python
# autoheader: ignore
```

`autoheader` will see this and skip the file.

### Specify Max Directory Depth

Avoids walking deep directory trees.

```bash
autoheader --depth 3 --no-dry-run
```

### Exclude Additional Paths

`autoheader` automatically excludes paths in `.gitignore` and `[exclude].paths` in your TOML file. You can add more one-time excludes:

```bash
autoheader --exclude tests --exclude "api/generated/"
```

### Force Yes in CI Environments

Skips all interactive prompts (e.g., root detection, no-dry-run warning).

```bash
autoheader --yes --no-dry-run
```

### Disable Rich Output

For CI logs that don't support color or emojis:

```bash
autoheader --no-color --no-emoji
```

## 📂 Example Output

`autoheader` provides clear, aligned, and color-coded output.

```text
Project root confirmed (3 markers found).
Planning changes for /path/to/my-project...
[progress bar]
Plan complete. Found 42 files.
Applying changes to 5 files using 8 workers...
✅ ADD              src/autoheader/app.py
⚠️ OVERRIDE         src/autoheader/cli.py
│  Header diff for src/autoheader/cli.py
│  - # old_header
│  + # src/autoheader/cli.py
❌ REMOVE           src/autoheader/old_util.py
🔵 SKIP             src/autoheader/models.py
⚫ SKIP_EXCLUDED    .venv/lib/python3.11/site-packages/rich/console.py
🔥 ERROR            Failed to process src/autoheader/locked_file.py: [Errno 13] Permission denied

Summary: added=1, overridden=1, removed=1, skipped_ok=34, skipped_excluded=5.
NOTE: this was a dry run. Use --no-dry-run to apply changes.

✨ Done in 0.42s.
```

## 🛡 Safety & Guarantees

`autoheader` is built with enterprise safety in mind:

* Dry-run by default.
* Never touches files without your explicit `--no-dry-run`.
* **.gitignore Aware:** Automatically respects your project's `.gitignore` rules.
* **Root Detection:** Confirms it's running in a project root before starting.
* **Interactive Prompts:** Prompts for confirmation before making changes (unless `--yes` is used).
* **Safe by Default:** Warns you if you run without `--backup`.
* **Resource Safe:** Includes a file size limit to avoid parsing huge files.
* **Safe Traversal:** Skips symlinks to prevent unexpected behavior.
* **Preserves Permissions:** Keeps original file permissions on write.

## 🔧 Development

Install in editable mode with all dev and pre-commit dependencies:

```bash
git clone https://github.com/dhruv13x/autoheader
cd autoheader
pip install -e ".[dev,precommit]"
```

Run tests:

```bash
pytest
```

Run linter & formatter:

```bash
ruff check .
black .
```

## 🤝 Contributing

Pull requests are welcome.  
If proposing large changes, open an issue first to discuss design and approach.

## 🐛 Reporting Issues

Please open issues here:  
https://github.com/dhruv13x/autoheader/issues

Include:
* What command you ran
* Error output
* Your Python version
* OS / environment information

## 📜 License

MIT © dhruv13x

## ⭐ Support the Project

If this tool helped you, consider giving the repo a star:  
https://github.com/dhruv13x/autoheader

Stars help visibility and future development!