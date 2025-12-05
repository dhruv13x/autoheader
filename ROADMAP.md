# 🚀 autoheader: Public Roadmap

This document outlines the visionary, integration-oriented plan for `autoheader`. We categorize features from **"Core Essentials"** to **"God Level"** ambition.

---

## Phase 1: Foundation (Q1)
**Focus**: Core functionality, stability, security, and basic usage.

- [x] Core header insertion/removal logic
- [x] Configuration via `autoheader.toml`
- [x] Polyglot support via language blocks
- [x] `.gitignore` integration
- [x] Pre-commit integration (`--check`)
- [x] Dry-run mode (`--dry-run`)
- [x] Caching for performance
- [x] Parallel file processing
- [x] Smart copyright year updating
- [x] Inline ignores (`autoheader: ignore`)
- [x] Native Git Hook Installer

---

## Phase 2: The Standard (Q2)
**Focus**: Feature parity with top competitors, user experience improvements, and robust error handling.

- [x] Visual Diffs for dry-runs
- [x] Rich CLI output (progress bars, colors)
- [x] SARIF reporting (`--format sarif`)
- [x] Remote configuration (`--config-url`)
- [x] File tamper detection (`{hash}`)
- [x] Native SPDX License Support

---

## Phase 3: The Ecosystem (Q3)
**Focus**: Webhooks, API exposure, 3rd party plugins, SDK generation, and extensibility.

- [x] LSP (Language Server) Integration
- [ ] GitHub Action for automated header checks
- [ ] VSCode Extension for real-time header management
- [ ] Pre-commit.ci support (automated config)
- [ ] Integration with linters (e.g., Ruff, ESLint) as a plugin

---

## Phase 4: The Vision (Q4)
**Focus**: **"Futuristic"** features, AI integration, advanced automation, and industry-disrupting capabilities.

- [ ] AI-powered header generation (e.g., suggesting license based on dependencies)
- [ ] Automated code provenance tracking (e.g., linking headers to Jira tickets or Git commits)
- [ ] Security-focused headers (e.g., embedding vulnerability scan results)
- [ ] Blockchain-based file integrity verification

---

## The Sandbox (OUT OF THE BOX / OPTIONAL)
**Focus**: Wild, creative, experimental ideas that set the project apart.

- [ ] Gamification of header compliance (e.g., team leaderboards)
- [ ] ASCII art headers
- [ ] "Header history" command to show how a file's header has evolved

---

## How to Contribute

If you have a feature request or want to contribute, please **[open an issue on GitHub](https://github.com/dhruv13x/autoheader/issues)** to discuss the design and implementation. We welcome all pull requests!

