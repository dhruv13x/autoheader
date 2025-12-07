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
![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)

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
- Basic understanding of your project structure.

### Installation
```bash
pip install "autoheader[precommit]"
```

### Run
```bash
# Initialize and dry-run
autoheader --init && autoheader
```

### Demo
```python
# Copy-paste this into any file to see autoheader in action!
# src/main.py (autoheader will add this line)

import sys
print("Hello World")
```

---

## ✨ Features

### Core
*   **🌐 Polyglot Support**: Manages headers for Python, JavaScript, Go, CSS, and *any* other language via a simple TOML configuration.
*   **⚙️ Smart Setup**: Get started in seconds with `autoheader --init` to generate a battle-tested default configuration.
*   **🧩 LSP Support**: Includes a Language Server (`autoheader --lsp`) for real-time diagnostics directly in your IDE.
*   **⚡ Rich UX**: Beautiful, modern output with emojis, progress bars, and visual diffs (powered by Rich).
*   **🧠 Smart Copyright**: Automatically updates year ranges (e.g., 2020-2025) in existing headers instead of overwriting them.
*   **💻 Official SDK**: Import `autoheader` in your own Python scripts (`from autoheader import AutoHeader`) for custom integrations.
*   **📂 Team Configuration**: Centralize settings using `autoheader.toml` or a remote config URL (`--config-url`) to keep your team aligned.
*   **📜 Native SPDX Support**: Easily use standard licenses (e.g., MIT, Apache-2.0) by setting `license_spdx` in your config.

### Performance
*   **🚀 Parallel Execution**: Supports passing specific files, parallel execution, and caching for blazing fast speed in CI pipelines.
*   **Smart Filtering**: `.gitignore` aware, inline ignores (`autoheader: ignore`), and robust depth/exclusion controls.

### Security
*   **🛡️ Pre-commit Integration**: Automatically enforce headers on every commit with `autoheader --check` or the built-in hook installer.
*   **🤖 GitHub Action**: Use the official action `uses: dhruv13x/autoheader@v1` to check headers in your CI/CD pipelines.
*   **🤖 Auto-Installer**: Setup hooks instantly with `autoheader --install-precommit` or `autoheader --install-git-hook`.
*   **🔍 SARIF Support**: Output results in SARIF format (`--format sarif`) for integration with GitHub Security and other scanning tools.

---

## 🛠️ Configuration

### Environment Variables
| Variable | Description | Default | Required |
| :--- | :--- | :--- | :--- |
| `NO_COLOR` | Disable colored output if set. | `None` | No |
| `AUTOHEADER_CONFIG` | Path to configuration file. | `autoheader.toml` | No |

### CLI Arguments
| Argument | Description | Default |
| :--- | :--- | :--- |
| **Main Actions** | | |
| `files` | Specific files to process (space separated). Scans root if empty. | (all) |
| `-d`, `--dry-run` | Preview changes without writing. | `True` |
| `-nd`, `--no-dry-run` | Apply changes to disk. | `False` |
| `--override` | Force rewrite of existing headers. | `False` |
| `--remove` | Remove all autoheader lines from files. | `False` |
| **CI / Integration** | | |
| `--check` | Exit 1 if changes needed. | `False` |
| `--check-hash` | Verify content integrity. | `False` |
| `--install-precommit` | Install `pre-commit` hook. | `False` |
| `--install-git-hook` | Install native `.git/hooks`. | `False` |
| `--init` | Generate default config. | `False` |
| `--lsp` | Start Language Server. | `False` |
| **Configuration** | | |
| `--config-url` | Remote config URL. | `None` |
| `--root` | Project root path. | `cwd` |
| `--workers` | Parallel workers. | `8` |
| `--timeout` | File processing timeout (s). | `60.0` |
| `--clear-cache` | Reset internal cache. | `False` |
| **Filtering** | | |
| `--depth` | Max directory scan depth. | `None` |
| `--exclude` | Glob patterns to skip. | `[]` |
| `--markers` | Project root markers. | `['.gitignore', ...]` |
| **Header Customization** | | |
| `--blank-lines-after` | Blank lines after header. | `1` |
| **Output** | | |
| `--format` | `default` or `sarif`. | `default` |
| `-v`, `--verbose` | Increase verbosity. | `0` |
| `-q`, `--quiet` | Suppress info output. | `False` |
| `--no-color` | Disable colors. | `False` |
| `--no-emoji` | Disable emojis. | `False` |

### The `autoheader.toml` File
The primary way to configure `autoheader` is via the `autoheader.toml` file. Generate one with `autoheader --init`.

```toml
[general]
workers = 8
backup = false
exclude = ["tests/fixtures/*"]

[language.python]
file_globs = ["*.py"]
prefix = "# "
template = "# {path}\n#\n{license}"
license_spdx = "MIT"
```

### Python SDK
You can use `autoheader` directly in your Python scripts.

```python
from autoheader import AutoHeader

ah = AutoHeader(root=".")

# Apply headers to all files
results = ah.apply(dry_run=False)

# Check compliance
check_results = ah.check(["src/main.py"])
```

---

## 🏗️ Architecture

`autoheader` follows a strict Separation of Concerns.

```text
src/autoheader/
├── cli.py         # Entry Point: UI, args parsing, mode selection
├── api.py         # The SDK: Official public API wrapper
├── core.py        # Execution: File writing, diffing, safety checks
├── planner.py     # The Brain: Pure business logic, decision making (PlanItem)
├── config.py      # Config: TOML loading, merging, validation
├── walker.py      # Discovery: File scanning, gitignore processing
├── headerlogic.py # Parsing: Header detection, SPDX handling
├── ui.py          # The Face: Rich output, visual diffs
├── lsp.py         # Language Server: Real-time IDE integration
└── hooks.py       # Integration: Native git hook installer
```

**Flow:**
1.  **Input**: User runs CLI or SDK, providing target files and flags.
2.  **Discovery**: `walker.py` scans the file system, respecting `.gitignore` and `exclude` rules.
3.  **Planning**: `planner.py` evaluates each file in parallel against the configuration to determine the necessary action (Add, Override, Skip).
4.  **Execution**: `core.py` applies the plan, modifying files safely with optional backups.
5.  **Output**: `ui.py` renders the results to the console (or SARIF) with rich feedback.

---

## 🐞 Troubleshooting

| Issue | Solution |
| :--- | :--- |
| **"Header not updating"** | Check if file is excluded in `.gitignore` or via `exclude` in `autoheader.toml`. |
| **"Permission denied"** | Ensure you have write permissions to the files. Run with `sudo` only if necessary. |
| **"LSP not working"** | Ensure `autoheader[lsp]` is installed. Restart your IDE language server. |
| **"Config not found"** | Run `autoheader --init` to create `autoheader.toml`. |
| **"Wrong path in header"** | Check your root directory setting (`--root`). |

**Debug Mode**:
Run with `autoheader -vv` to see detailed debug logs, including file scanning decisions and configuration loading.

---

## 🤝 Contributing

**Contributions are welcome!**

Please refer to our contribution guidelines below (full `CONTRIBUTING.md` coming soon).

1.  Fork the repository.
2.  Clone your fork: `git clone ...`
3.  Install dev dependencies: `pip install -e ".[dev,precommit]"`
4.  Run tests: `pytest`
5.  Linting: `ruff check .`

---

## 🗺️ Roadmap

We are actively building the future of code standardization.

*   ✅ **v9.0**: Native LSP Support, Pre-commit auto-installer, Rich CLI, Official SDK, GitHub Action.
*   ✅ **v10.0 (Pre-release)**: Native Git Hook Installer, SARIF reporting, Remote Configuration.

Check `ROADMAP.md` for the full list of future goals like Semantic License Analysis.

---

**License**: MIT © dhruv13x
