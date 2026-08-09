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
- `.github/workflows/ci.yml` — CI: tests + linter matrix (Ubuntu + Windows,
  Python 3.9/3.11/3.12, offline HTTP-mocked suite), README drift guard, and
  the commit-message gate (AREA marker must name a logged decision).
- `start.py` — boot briefing: sibling-log health (errors + decisions, if the
  sibling repos live next door), a 2-second endpoint reachability probe, the
  command cheat-sheet, and the latest session note. Uses the canonical
  `check_logs_ai` helpers (never reimplements parsing).
- Removed the broken `start.bat` launcher (it referenced a `start.py` that
  never existed).
