# Changelog

All notable changes to this project are documented here. The version at the
top of this file is the single source of truth - releases are cut from it by
`.github/workflows/release.yml`.

## [Unreleased]

### Added

- Project scaffold: README, AGENTS.md, LICENSE, community files
  (CONTRIBUTING, SECURITY, CODE_OF_CONDUCT), issue/PR templates, and the
  release workflow.
- Repository created on GitHub (vartiainen1/agent-log-ai).
- `check_logs_ai.py` — the LLM reasoning layer: `--lessons` (error-log
  root-cause drafts), `--review` (decision-log reversal analysis),
  `--notes` (session-note drafts), `--check` (endpoint ping), `--dry-run`
  (prompt preview, sends nothing), and `--check-commit` (CI gate). Stdlib
  only (urllib), local-first (Ollama default), prompt-injection guard.
- `_test_logs_ai.py` — 82 offline tests (HTTP mocked, no network, no key).
- `_check_readme_count.py` — README test-count drift guard.
