# 🚀 autoheader: Public Roadmap

This document outlines the evolution of `autoheader`. We build in the open.

---

## 🔮 Future Roadmap (v5.0+)

The goal for the next major epoch is **Standardization & Ecosystem**.

### 📜 1. Native SPDX License Support
* **Goal:** Instead of writing custom templates, users can simply set `license = "MIT"` or `license = "Apache-2.0"`.
* **Plan:** Integrate SPDX license database to automatically generate legally compliant header blocks.

### 🔌 2. Native Git Hook Installer
* **Goal:** Remove the dependency on the `pre-commit` python framework for simple use cases.
* **Plan:** Add `autoheader --install-git-hook` to write a lightweight shell script directly into `.git/hooks/pre-commit`.

### 🧠 3. LSP (Language Server) Integration
* **Goal:** Highlight missing headers directly in VS Code / PyCharm as you type.
* **Plan:** Expose an LSP interface or a JSON-RPC mode for editor plugins.

---

## ✅ Completed Milestones

### v4.1.0: The "UX & Speed" Release (Completed 2025-11)
* ✅ **Explicit File Arguments:** Drastically sped up pre-commit hooks by allowing specific file paths (`autoheader file1.py`).
* ✅ **Visual Diffs:** Added rich, side-by-side diffs for dry-runs to show exactly what will change.
* ✅ **Smart Copyright:** Implemented logic to update year ranges (e.g., `2020-2025`) rather than overwriting old years.

### v4.0.0: The "Security & Fleet" Release (Completed 2025-11)
* ✅ **File Tamper Detection:** Added content hashing (`{hash}`) to headers to detect unauthorized file modifications.
* ✅ **SARIF Reporting:** Added `--format sarif` for native integration with GitHub Security & SonarQube.
* ✅ **Remote Configuration:** Added `--config-url` to support fetching central config from a URL (Fleet Management).
* ✅ **Full License Blocks:** Refactored engine to support complex, multi-line copyright headers.

### v3.0.0: The "Performance" Release (Completed 2025-11)
* ✅ **Blazing Fast Caching:** Implemented `mtime` + `sha256` caching to make re-runs near instant.
* ✅ **Parallel Planning:** Multithreaded the file analysis phase.
* ✅ **Custom Templates:** Added fully dynamic variables (`{filename}`, `{year}`, `{path}`).
* ✅ **AST-Based Insertion:** Switched to Python AST parsing for robust header insertion that respects docstrings and shebangs.

---

## How to Contribute

If you have a feature request or want to contribute to the v5.0 goals, please **[open an issue on GitHub](https://github.com/dhruv13x/autoheader/issues)** to discuss the design and implementation.

We welcome all pull requests!