# autoheader: Implementation Roadmap

This document tracks the recommended order of implementation for the major features outlined in the public roadmap.

## v3.0.0: Performance & Enterprise Integration

1.  **Blazing Fast Caching:** Implement a caching mechanism based on file modification times and content hashes to make subsequent runs near-instant.
2.  **Parallel Planning Phase:** Parallelize the file analysis phase to speed up initial runs on large repositories.
3.  **Fully Customizable Header Templates:** Expand the templating engine to support more variables (`{filename}`, `{year}`) and multi-line templates for legal/copyright headers.
4.  **AST-Based Insertion (Python):** Use Python's `ast` module for more robust header insertion in Python files.

## v4.0.0: Security & Fleet Management

5.  **Security: File Tamper & Drift Detection:** Introduce file integrity monitoring by checking a content hash stored in the header.
6.  **Auditability: SARIF Reporting:** Add support for SARIF output for seamless integration with CI/CD security dashboards.
7.  **Fleet Management: Remote Configuration:** Allow for centralized configuration management by fetching the configuration from a URL.
8.  **Full Scope: Copyright & License Management:** Evolve the tool to manage and enforce full multi-line copyright and license blocks.
