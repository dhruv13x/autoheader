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

</div>

# autoheader

### The enterprise-grade standard for adding, refreshing, and managing repo-relative file headers.

**autoheader** automatically manages file headers containing *repo-relative paths* for source code projects. Whether you are working in a massive monorepo or a small microservice, it ensures every file is traceable, standardizing your codebase and improving developer navigation.

> "Where is this file located?" — **Never ask this again.**

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.8+**
- Basic understanding of your project structure (e.g., where `pyproject.toml` or `.git` lives).

### Installation
Install instantly via pip:

```bash
pip install "autoheader[precommit]"
```
> **Note:** The `[precommit]` extra is recommended for full feature support (like hook installation).

### Usage Example
Scan your project and verify what needs to change (Dry Run):

```bash
# 1. Initialize a default config
autoheader --init

# 2. Preview changes (Safe by default)
autoheader
```

Apply the changes:

```bash
autoheader --no-dry-run
```

**What it does:**
It transforms this:
```python
import os
def main(): pass
```
Into this:
```python
# src/utils/main.py

import os
def main(): pass
```

---

## ✨ Key Features

*   **🌐 Polyglot Support**: **God Level**. Manages headers for Python, JavaScript, Go, CSS, and *any* other language via a simple TOML configuration.
*   **🛡️ Pre-commit Integration**: **God Level**. Automatically enforce headers on every commit with `autoheader --check` or the built-in hook installer.
*   **⚙️ Smart Setup**: **God Level**. Get started in seconds with `autoheader --init` to generate a battle-tested default configuration.
*   **🧩 LSP Support**: **God Level**. Includes a Language Server (`autoheader --lsp`) for real-time diagnostics directly in your IDE.
*   **⚡ Rich UX**: Beautiful, modern output with emojis, progress bars, and visual diffs (powered by Rich).
*   **🧠 Smart Copyright**: Automatically updates year ranges (e.g., 2020-2025) in existing headers instead of overwriting them.
*   **🚀 Performance**: Supports passing specific files, parallel execution, and caching for blazing fast speed in CI pipelines.
*   **📂 Team Configuration**: Centralize settings using `autoheader.toml` or a remote config URL (`--config-url`) to keep your team aligned.
*   **💻 Official SDK**: Import `autoheader` in your own Python scripts (`from autoheader import AutoHeader`) for custom integrations.
*   **🤖 Auto-Installer**: Setup hooks instantly with `autoheader --install-precommit` or `autoheader --install-git-hook`.
*   **📜 Native SPDX Support**: Easily use standard licenses (e.g., MIT, Apache-2.0) by setting `license_spdx` in your config.
*   **Smart Filtering**: `.gitignore` aware, inline ignores (`autoheader: ignore`), and robust depth/exclusion controls.
*   **Safety First**: Dry-run by default, backups supported (`--backup`), and idempotent (runs repeatedly without duplicates).

---

## ⚙️ Configuration & Advanced Usage

### 1. The `autoheader.toml` File
The primary way to configure `autoheader` is via the `autoheader.toml` file. Generate one with `autoheader --init`.

```toml
[general]
workers = 8
backup = false

[language.python]
file_globs = ["*.py"]
prefix = "# "
template = "# {path}\n#\n{license}"
license_spdx = "MIT"
```

### 2. CLI Arguments & API
All configuration can be overridden via CLI arguments.

| Argument | Description | Default |
| :--- | :--- | :--- |
| **Main Actions** | | |
| `files` | Specific files to process (space separated). Scans root if empty. | (all) |
| `-d`, `--dry-run` | Do not write changes. | `True` |
| `-nd`, `--no-dry-run` | Apply changes to files. | `False` |
| `--override` | Force rewrite of existing headers. | `False` |
| `--remove` | Remove all autoheader lines from files. | `False` |
| **CI / Pre-commit** | | |
| `--check` | Exit code 1 if changes are needed (for CI). | `False` |
| `--check-hash` | Verify integrity via content hash. | `False` |
| `--install-precommit` | Install as a `repo: local` pre-commit hook. | `False` |
| `--install-git-hook` | Install raw `.git/hooks/pre-commit` script. | `False` |
| `--init` | Create default `autoheader.toml`. | `False` |
| `--lsp` | Start LSP server. | `False` |
| **Configuration** | | |
| `-y`, `--yes` | Auto-confirm all prompts. | `False` |
| `--backup` | Create `.bak` files before writing. | `False` |
| `--root` | Specify project root directory. | `cwd` |
| `--workers` | Number of parallel workers. | `8` |
| `--timeout` | File processing timeout (seconds). | `60.0` |
| `--config-url` | Fetch config from a remote URL. | `None` |
| `--clear-cache` | Clear internal cache. | `False` |
| **Filtering** | | |
| `--depth` | Max directory scan depth. | `None` |
| `--exclude` | Extra globs to exclude (repeatable). | `[]` |
| `--markers` | Project root markers. | `['.gitignore', ...]` |
| **Header Customization** | | |
| `--blank-lines-after` | Blank lines after header. | `1` |
| **Output** | | |
| `-v`, `--verbose` | Increase verbosity. | `0` |
| `-q`, `--quiet` | Suppress info output. | `False` |
| `--no-color` | Disable colors. | `False` |
| `--no-emoji` | Disable emojis. | `False` |
| `--format` | Output format (`default`, `sarif`). | `default` |

### 3. Environment Variables
While `autoheader` primarily uses `autoheader.toml`, standard environment variables like `NO_COLOR=1` are respected.

### 4. Inline Ignores
To skip a specific file without complex config, simply add this comment anywhere in the file:
```python
# autoheader: ignore
```

---

## 🏗️ Architecture

`autoheader` is designed for modularity and speed.

```text
src/autoheader/
├── cli.py         # Entry Point: Parses args, handles modes (check, lsp, init)
├── core.py        # Brain: Plans changes, diffs files, orchestrates execution
├── config.py      # Config: Loads TOML (local/remote), merges defaults
├── walker.py      # Eyes: Scans filesystem, respects .gitignore, finds root
├── headerlogic.py # Logic: Parses headers, detects SPDX, handles comments
├── ui.py          # Face: Renders Rich output, diffs, and progress bars
└── lsp.py         # Server: Implements Language Server Protocol
```

**Core Flow:**
1.  **Initialize**: `cli.py` starts, determines project root via `walker.py`.
2.  **Configuration**: `config.py` loads `autoheader.toml` and merges CLI args.
3.  **Discovery**: `walker.py` scans files, filtering by excluded globs and `.gitignore`.
4.  **Planning**: `core.py` analyzes each file to create a `PlanItem` (Add, Override, Skip).
5.  **Execution**: A `ThreadPoolExecutor` runs in parallel to apply changes (write files) safely.

---

## 🗺️ Roadmap

We are actively building the future of code standardization.

*   ✅ **v9.0**: Native LSP Support, Pre-commit auto-installer, Rich CLI.
*   🔜 **v10.0**:
    *   **Native Git Hook Installer**: Zero-dependency hook installation.
    *   **Enhanced SPDX**: Automatic license text generation from SPDX IDs.
    *   **IDE Extensions**: Official VS Code / JetBrains plugins (wrapping the LSP).

Check `ROADMAP.md` for the full list.

---

## 🤝 Contributing & License

**Contributions are welcome!**
1.  Fork the repository.
2.  Clone: `git clone ...`
3.  Install dev deps: `pip install -e ".[dev,precommit]"`
4.  Run tests: `pytest`

**License**: MIT © dhruv13x
