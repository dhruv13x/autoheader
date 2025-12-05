# 🚀 autoheader: Public Roadmap

This document outlines the visionary, integration-oriented plan for `autoheader`. We categorize features from **"Core Essentials"** to **"God Level"** ambition.

---

## Phase 1: Foundation (Q1 2024 - Completed)
**Focus**: Core functionality, stability, security, and basic usage.
**Instruction**: Prioritize items that are partially built or standard for this type of tool.

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

## Phase 2: The Standard (Q2 2024 - Completed)
**Focus**: Feature parity with top competitors, user experience improvements, and robust error handling.

- [x] Visual Diffs for dry-runs
- [x] Rich CLI output (progress bars, colors, emojis)
- [x] SARIF reporting (`--format sarif`)
- [x] Remote configuration (`--config-url`)
- [x] File tamper detection (`{hash}`)
- [x] Native SPDX License Support

---

## Phase 3: The Ecosystem (Q3 2024 - Integration)
**Focus**: Webhooks, API exposure, 3rd party plugins, SDK generation, and extensibility.

- [x] LSP (Language Server) Integration
- [ ] **Official SDK Mode**: First-class Python API for other tools to import `autoheader` logic.
- [ ] **GitHub Action**: Official action for automated header checks and PR comments.
- [ ] **VSCode Extension**: Wrapper around the LSP for real-time header management and "Quick Fix" actions.
- [ ] **Pre-commit.ci support**: Zero-config integration.
- [ ] **Linter Plugins**: Integrations for Ruff or ESLint.
- [ ] **Header Telemetry**: Optional reporting to a central server for enterprise audit logs.

---

## Phase 4: The Vision (Q4 2024 / 2025 - GOD LEVEL)
**Focus**: **"Futuristic"** features, AI integration, advanced automation, and industry-disrupting capabilities.

- [ ] **Semantic License Analysis**: Use local LLMs to verify if file content (imports, logic) matches the header's license (e.g., detecting GPL code in an MIT file).
- [ ] **Automated Code Provenance**: Link headers to Jira tickets or specific Git commits automatically (`Source: <url>`).
- [ ] **Security-Focused Headers**: Embed signed vulnerability scan timestamps or SBOM references in the header.
- [ ] **Blockchain Integrity**: Anchor file hashes to a public ledger for immutable proof of authorship.
- [ ] **Context-Aware Headers**: AI-generated summaries of the file's purpose embedded in the header.
- [ ] **Watcher Mode**: "Self-healing" headers that update instantly when a file is moved or renamed.

---

## The Sandbox (OUT OF THE BOX / OPTIONAL)
**Focus**: Wild, creative, experimental ideas that set the project apart.

- [ ] **Gamification**: Leaderboards for "Most Compliant Team" or "Oldest Header".
- [ ] **ASCII Art Headers**: Support for figlet-style project logos in file headers.
- [ ] **Header History**: `autoheader history <file>` command to visualize how a header has evolved over time.
- [ ] **Steganographic Signatures**: Hide cryptographic signatures in header whitespace for invisible verification.
- [ ] **"Ghost" Headers**: Store headers in file system extended attributes (xattrs) instead of file content (for pristine source files).

---

## How to Contribute

If you have a feature request or want to contribute, please **[open an issue on GitHub](https://github.com/dhruv13x/autoheader/issues)** to discuss the design and implementation. We welcome all pull requests!
