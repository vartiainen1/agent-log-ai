# Changelog

All notable changes to this project are documented here. The version at the
top of this file is the single source of truth - releases are cut from it by
`.github/workflows/release.yml`.

## [0.2.0] - 2026-08-10

### Fixed
- L10: `load()` no longer crashes on a locked/unreadable log file (graceful `OSError` fallback; regression tests added).

## [0.1.0] - 2026-08-09

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
- `--init [DIR]` — one-command adoption: scaffolds `errors.txt`,
  `decisions.txt`, `rules.txt` (with the §7 LESSONS header), and `notes.txt`
  from built-in templates; never overwrites existing files; runs the offline
  self-test suite when present.
- The reasoning commands are now mutually exclusive (`--lessons` / `--review` /
  `--notes` / `--check` / `--check-commit` / `--init`) — previously two could
  be passed and one silently won.
- `chat()` now explicitly re-raises `KeyboardInterrupt` — Ctrl-C always
  escapes and is never folded into an error string.
- `_test_logs_ai.py` — 93 tests (+11): `_token_warn` threshold, `--timeout`
  pass-through, `KeyboardInterrupt` propagation, `--max-entries` truncation,
  `--apply` through the command path, mutual exclusion, and four `--init`
  cases (scaffold, no-overwrite, self-test run, failing self-test fails
  adoption).
