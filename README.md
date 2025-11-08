# autoheader

**autoheader** is an enterprise-grade CLI tool for Python projects that automatically adds or refreshes file headers containing each file’s *repo-relative path*.  
This helps developers quickly identify file origins, improves navigation in large codebases, and standardizes file structure across teams.

Example of what autoheader produces:

```python
# src/utils/parser.py

from __future__ import annotations

Perfect for monorepos, multi-module architectures, enterprise Python codebases, and any project where file traceability matters.


---

✅ Features

Automatic repository root detection
Uses multiple project markers (pyproject.toml, README, .gitignore, etc.) to confirm safe execution.

Idempotent header insertion
Runs repeatedly with no duplicates. If the header already matches the file’s path, it simply skips.

Override mode (--override)
Rewrites outdated or incorrect headers when files are moved or refactored.

Dry-run by default
No accidental writes. Shows exactly what will change.

Backup support (--backup)
Creates .bak files for full rollback safety.

Depth guard (--depth)
Prevents accidental traversal of deep or unwanted paths in large repos.

Exclusion system (--exclude)
Automatically avoids dangerous directories like .git, .github, virtualenvs, build folders, etc.

Verbose reporting (--verbose)
See exactly which files were added, skipped, or overridden.

Installable via PyPI with zero configuration
Just pip install autoheader.



---

📦 Installation

Install from PyPI:

pip install autoheader

Or install from source:

pip install git+https://github.com/dhruv13x/autoheader


---

🚀 Quick Start

Run inside a Python project:

autoheader

This performs a safe dry-run and shows what would be changed.

Apply changes for real:

autoheader --no-dry-run

Override all headers (useful after moving files):

autoheader --override --no-dry-run

Create backups for safety:

autoheader --backup --no-dry-run


---

📘 Advanced Usage

✅ Specify max directory depth

autoheader --depth 3 --no-dry-run

Avoids walking deep directory trees.


---

✅ Exclude additional paths

autoheader --exclude tests --exclude build

Built-in exclusions include:

.git/

.github/

virtualenvs

build artifacts



---

✅ Force yes in CI environments

autoheader --yes --no-dry-run

Skips root detection prompts.


---

📂 Example Output

Dry-run:

DRY ADD:      src/utils/parser.py
DRY ADD:      src/models/user.py
DRY ADD:      api/routes/index.py

Summary: added=3, overridden=0, skipped_ok=14, skipped_excluded=5.
NOTE: this was a dry run. Use --no-dry-run to apply changes.

Real run:

ADD:          src/utils/parser.py
OVERRIDE:     src/core/config.py
SKIP (ok):    src/api/__init__.py

Summary: added=1, overridden=1, skipped_ok=22, skipped_excluded=5.


---

🛡 Safety & Guarantees

autoheader is built with enterprise safety in mind:

Never touches files without your permission

Never rewrites headers unless explicitly told

Never runs destructive operations

Clearly separates real execution from dry-run

Designed for CI/CD environments

OIDC-secure PyPI publishing



---

🔧 Development

Install in editable mode:

git clone https://github.com/dhruv13x/autoheader
cd autoheader
pip install -e .[dev]

Run tests:

pytest

Run linter & formatter:

ruff check .
black .


---

🤝 Contributing

Pull requests are welcome.
If proposing large changes, open an issue first to discuss design and approach.


---

🐛 Reporting Issues

Please open issues here:
https://github.com/dhruv13x/autoheader/issues

Include:

What command you ran

Error output

Your Python version

OS / environment information



---

📜 License

MIT © dhruv13x


---

⭐ Support the Project

If this tool helped you, consider giving the repo a star:

https://github.com/dhruv13x/autoheader

Stars help visibility and future development!

---
