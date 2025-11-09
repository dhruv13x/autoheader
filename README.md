# autoheader

**autoheader** is an enterprise-grade CLI tool for Python projects that automatically adds or refreshes file headers containing each file’s *repo-relative path*.
This helps developers quickly identify file origins, improves navigation in large codebases, and standardizes file structure across teams.

Example of what `autoheader` produces:

```python
# src/utils/parser.py

from __future__ import annotations
...
```

Perfect for monorepos, multi-module architectures, enterprise Python codebases, and any project where file traceability matters.

---

## ✅ Features

* **⚡ Rich & Colorful Output:** Beautiful, modern output with emojis and industry-standard colors (powered by Rich).
* **📂 Team Configuration:** Centralize settings for your whole team using `autoheader.toml`.
* **🛡️ Pre-commit Integration:** Automatically enforce headers on every commit with `autoheader --check`.
* **🤖 Auto-Installer:** Get started in seconds with `autoheader --install-precommit`.
* **Automatic Root Detection:** Uses project markers (`pyproject.toml`, `README.md`, `.gitignore`) to confirm safe execution.
* **Idempotent & Safe:** Runs repeatedly with no duplicates. **Dry-run by default.**
* **Flexible Modes:** Supports `--override` (for refactoring), `--remove` (for cleanup), and `--backup` (for safety).
* **Smart Filtering:** Includes a depth guard (`--depth`) and a robust exclusion system (`--exclude`).
* **CI-Friendly:** Full support for `--yes` and `--quiet` flags for non-interactive environments.

---

## 📦 Installation

Install from PyPI:

```bash
pip install autoheader
```

To include support for the `autoheader --install-precommit` command, install the `precommit` extras:

```bash
pip install "autoheader[precommit]"
```

Or install the latest version directly from source:

```bash
pip install git+https://github.com/dhruv13x/autoheader
```

---

## 🚀 Quick Start

Run inside a Python project for a safe, colorful dry-run:

```bash
autoheader
```


To apply changes for real:

```bash
autoheader --no-dry-run
```

To override all existing headers (e.g., after moving files):

```bash
autoheader --override --no-dry-run
```

To remove all headers:

```bash
autoheader --remove --no-dry-run
```

---

## 🛡️ Pre-commit & CI Mode

`autoheader` is built for modern CI/CD and pre-commit workflows.

### 1. `autoheader --check`

The `--check` flag runs `autoheader` in a dry-run mode. If any files need headers added, removed, or overridden, it will print the files and exit with code 1, **failing your CI or pre-commit hook.**

This is the engine that enforces header consistency.

### 2. `autoheader --install-precommit`

This is the easiest way to get started. It automatically finds your `.pre-commit-config.yaml` (or creates one) and adds `autoheader` as a local hook.

**Requires `pyyaml`:** You must run `pip install "autoheader[precommit]"` first.

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

You can also add `autoheader` as a remote hook. Add this to your `.pre-commit-config.yaml`:

```yaml
- repo: https://github.com/dhruv13x/autoheader
  rev: v0.1.0 # <-- Use the latest tag
  hooks:
    - id: autoheader
      name: autoheader file header checker
```

---

## 📂 Enterprise Configuration (`autoheader.toml`)

For teams, you can stop passing CLI flags and standardize settings in an `autoheader.toml` file at your project's root.

**Precedence:** CLI arguments > `autoheader.toml` settings > Application defaults.

Just create `autoheader.toml` in your project root:

```toml
# Example autoheader.toml

[general]
# dry_run = true   # Default is true, but can be set
backup = false
workers = 8
# override = false
# remove = false

[detection]
# Max directory depth to scan
depth = 10
# Files that mark the project root
markers = ["pyproject.toml", "README.md", ".gitignore"]

[exclude]
# Extra paths/globs to exclude (in addition to defaults)
paths = [
    "docs/",
    "tests/fixtures/",
    "*.generated.py",
]

[header]
# Number of blank lines to add after the header
blank_lines_after = 1
```

---

## 📘 Advanced Usage

### Specify Max Directory Depth

Avoids walking deep directory trees.

```bash
autoheader --depth 3 --no-dry-run
```

### Exclude Additional Paths

`autoheader` already excludes common paths like `.git`, `.venv`, `__pycache__`, and `build/`. You can add more:

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

---

## 📂 Example Output

`autoheader` provides clear, aligned, and color-coded output.

```bash
$ autoheader
Planning changes for /path/to/my-project...
Plan complete. Found 42 files.
Applying changes to 5 files using 8 workers...
✅ ADD              src/autoheader/app.py
⚠️ OVERRIDE         src/autoheader/cli.py
❌ REMOVE           src/autoheader/old_util.py
🔵 SKIP             src/autoheader/models.py
⚫ SKIP_EXCLUDED    .venv/lib/python3.11/site-packages/rich/console.py
🔥 ERROR            Failed to process src/autoheader/locked_file.py: [Errno 13] Permission denied

Summary: added=1, overridden=1, removed=1, skipped_ok=34, skipped_excluded=5.
NOTE: this was a dry run. Use --no-dry-run to apply changes.
```

---

## 🛡 Safety & Guarantees

`autoheader` is built with enterprise safety in mind:

* **Dry-run by default.**
* Never touches files without your explicit `--no-dry-run`.
* Prompts for confirmation before making changes (unless `--yes` is used).
* Warns you if you run without `--backup`.
* Includes a file size limit to avoid parsing huge files.
* Skips symlinks to prevent unexpected behavior.
* Preserves original file permissions on write.
* Designed for CI/CD environments.
* Uses OIDC-secure PyPI publishing.

---

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

---

## 🤝 Contributing

Pull requests are welcome.
If proposing large changes, open an issue first to discuss design and approach.

---

## 🐛 Reporting Issues

Please open issues here:
[https://github.com/dhruv13x/autoheader/issues](https://github.com/dhruv13x/autoheader/issues)

Include:

* What command you ran
* Error output
* Your Python version
* OS / environment information

---

## 📜 License

MIT © dhruv13x

---

## ⭐ Support the Project

If this tool helped you, consider giving the repo a star:

[https://github.com/dhruv13x/autoheader](https://github.com/dhruv13x/autoheader)

Stars help visibility and future development!