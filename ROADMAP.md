---

# 🚀 autoheader: Public Roadmap

This document outlines the planned evolution for `autoheader`. The v2.0 release successfully refactored the tool into a language-agnostic engine with a robust, test-covered core.

The strategic goal is to evolve `autoheader` from a *best-in-class linter* into an *enterprise-grade governance platform* with a focus on **Performance**, **Integration**, and **Security**.

---

## v3.0.0: The "Performance & Enterprise Integration" Release

**🎯 Primary Goal:** To make `autoheader` instantaneously fast on subsequent runs and to add the most-requested enterprise feature: fully customizable legal/copyright headers.

### ⚡ 1. Blazing Fast Caching

* **The "Why":** On large repos (10,000+ files), the planning phase is still the bottleneck. `plan_files` must `stat()` and `read()` every file, every time. This is slow in CI. A cache will make subsequent runs (where only 1-2 files changed) near-instant.
* **Implementation Plan:**
    1.  A new file, `.autoheader_cache`, will be created in the project root.
    2.  This file will store a JSON map: `{"src/main.py": {"mtime": 123456.789, "hash": "sha256-..."}}`.
    3.  In `plan_files`, *before* reading the file:
        * `stat()` the file.
        * Check `path` and `mtime` against the cache.
        * If `mtime` matches, add a `PlanItem(action="skip-cached")` and `continue`. This skips the file read entirely.
        * If `mtime` *differs* (or the file is not in the cache), proceed with the full read and analysis.
    4.  In `write_with_header`, after a successful write (for `add`, `override`, or `remove`), the new `mtime` and content hash must be updated in the cache.

### 💨 2. Parallel Planning Phase

* **The "Why":** The current `plan_files` loop is single-threaded. While the file *writing* is parallelized, the *planning* (all the `stat`, `read`, and `analyze` calls) is not. For a first run on a large repo, this is the main bottleneck.
* **Implementation Plan:**
    1.  Refactor `plan_files`. It will still use `filesystem.find_configured_files` to get the list of `(path, lang)` tuples.
    2.  It will then create a new internal function, e.g., `_analyze_single_file(path, lang)`.
    3.  A `ThreadPoolExecutor` will be used to map `_analyze_single_file` across the entire list of paths.
    4.  This `_analyze_single_file` function will contain all the logic currently in the `plan_files` `for` loop (exclusion checks, `stat`, `read`, `analyze_header_state`).
    5.  The main thread will simply collect the `PlanItem` objects returned by the workers.

### ⚖️ 3. Fully Customizable Header Templates

* **The "Why":** This is the number one enterprise feature. Most companies have a required legal/copyright line (e.g., `Copyright (C) 2025 MyCorp | {path}`). The v2.0 engine already supports this via the `template` key, but it needs to be expanded.
* **Implementation Plan:**
    1.  Update `headerlogic.py`'s `header_line_for` function. It currently only formats `{path}`.
    2.  It will be expanded to support a richer set of variables:
        * `{path}`: The full relative path (e.g., `src/utils/parser.py`).
        * `{filename}`: The file's name (e.g., `parser.py`).
        * `{year}`: The current year (e.g., `2025`).
    3.  Support multi-line templates (e.g., from a TOML multi-line string) to allow for full license block management.
    4.  The `analyze_header_state` logic (which checks `startswith(prefix)`) is already robust enough to handle this.

### 🧠 4. AST-Based Insertion (Python)

* **The "Why":** The current regex-based logic for shebangs and encoding (`ENCODING_RX`) is robust, but not foolproof. It can be confused by complex docstrings. Using Python's `ast` module is the *only* 100% correct way to find the insertion point.
* **Implementation Plan:**
    1.  In `headerlogic.py`, `analyze_header_state` will be modified.
    2.  If `check_encoding` is `True` for a language, it will first attempt to `ast.parse(content)`.
    3.  It will walk the `ast` tree and find the line number of the *last* "future import" (`from __future__ import ...`) or module-level docstring.
    4.  The `insert_index` will be set to the line *after* this node.
    5.  If `ast.parse` fails (e.g., invalid syntax), it will fall back to the current regex-based method.

---

## v4.0.0: The "Security & Fleet Management" Release

**🎯 Primary Goal:** To evolve `autoheader` from an integration tool into a core component of an organization's security and compliance strategy.

### 🛡️ 1. Security: File Tamper & Drift Detection

* **The "Why":** This transforms `autoheader` from a linter into a lightweight File Integrity Monitoring (FIM) tool. It provides a guarantee that a file's content *has not changed* since the header was last applied.
* **Implementation Plan:**
    1.  Add a new `{hash}` variable to the templating engine.
    2.  `header_line_for` will, if `{hash}` is in the template, calculate a `sha256` hash of the file's content *minus* the header line itself.
    3.  A new CLI flag, `--check-hash`, will be added.
    4.  When `--check-hash` is used, `analyze_header_state` will:
        * Parse the `[hash: sha256-...]` from the existing header.
        * Calculate the hash of the *current* file content.
        * If the hashes do not match, it will return a new state (e.g., `has_tampered_header=True`), which `plan_files` will turn into an `override` action with the reason "hash mismatch". This will fail `--check` mode.

### 📊 2. Auditability: SARIF Reporting

* **The "Why":** This is the gold standard for CI/CD integration. It allows GitHub, GitLab, and other security dashboards to natively ingest `autoheader`'s output and display it as code quality or security violations directly in the pull request.
* **Implementation Plan:**
    1.  Add a new CLI flag: `--format sarif`.
    2.  If set, `autoheader` will *not* print its usual summary.
    3.  In `cli.py`'s `main` function, after the `plan` is generated, it will iterate through all `PlanItem`s that are *not* `skip-cached` or `skip-header-exists`.
    4.  Each of these items (`add`, `remove`, `override`) will be formatted as a "result" object in a SARIF v2.1.0 JSON blob.
    5.  The final JSON will be printed to stdout, for redirection (e.g., `autoheader --check --format sarif > autoheader-report.sarif`).

### 🌐 3. Fleet Management: Remote Configuration

* **The "Why":** For an organization with 500+ repositories, managing 500+ individual `autoheader.toml` files is not feasible. This feature allows a central SRE or Developer Experience (DevEx) team to enforce a single, canonical configuration for the entire fleet.
* **Implementation Plan:**
    1.  Add a new CLI flag: `--config-url <url>`.
    2.  In `config.py`'s `load_config_data` function, it will check for this flag.
    3.  If present, it will download the content from the URL (e.g., using `urllib.request`) and parse it with `tomllib`, bypassing the local file check.
    4.  The rest of the config loading (`load_general_config`, `load_language_configs`) will proceed as normal.

### 📜 4. Full Scope: Copyright & License Management

* **The "Why":** This is the tool's "final form." It evolves from managing a single-line header to managing and enforcing complex, multi-line copyright and license blocks at the top of every file.
* **Implementation Plan:**
    1.  This is primarily an extension of the v3.0 "Custom Header Templates" feature.
    2.  The `template` key in `autoheader.toml` will officially support TOML multi-line strings.
    3.  `headerlogic.py`'s `analyze_header_state` will be updated to handle multi-line `prefix` and `template` checks, ensuring the *entire block* is present and correct.
    4.  This allows `autoheader` to become a complete, auditable solution for ensuring legal and IP compliance across all source code.

---

## How to Contribute

We build in the open. This roadmap is a living document. If you have a feature request or want to contribute to one of these goals, please **[open an issue on GitHub](https://github.com/dhruv13x/autoheader/issues)** to discuss the design and implementation.

We welcome all pull requests that align with these strategic goals.

---
