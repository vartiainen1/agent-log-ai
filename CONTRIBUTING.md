# Contributing

Thanks for considering a contribution to **agent-log-ai**. It is a small,
deliberate project - every file earns its place.

## Principles

- **Zero dependencies, stdlib only.** The only external call is the LLM
  endpoint via `urllib.request`. Nothing may be added to `requirements`.
- **Windows + Unix.** Every script runs on both; CI proves it.
- **Local-first.** Defaults must never require a cloud key; the cloud path is
  explicit (`--base-url` + `OPENAI_API_KEY`).
- **Tests are offline.** The HTTP layer is mocked, so the suite runs
  deterministically with no network and no key.

## Workflow

1. **Decide before you code.** This is an agent-memory tool - dogfood it:
   log the decision in `decisions.txt` (same format as the sibling
   agent-decision-log) before changing behavior.
2. **Log before fixing.** If you find a bug, record it in `notes.txt` (or the
   sibling error log) first, then fix.
3. **Tests.** Add or update `_test_logs_ai.py` for any behavior change.
   Run `python _test_logs_ai.py` - all tests must pass.
4. **Validate.** `python check_logs_ai.py` must exit 0 on the repo's own log.
5. **Changelog.** Add a bullet under `## [Unreleased]` in CHANGELOG.md.
6. **Branch + PR.** Create a branch, open a pull request, keep the diff
   focused. PRs are squash-merged with the `(AREA: <logged decision>)`
   marker in the title (the log-before-fix discipline).
7. **Release.** The maintainer bumps `[Unreleased]` to a version; the
   release workflow tags it and drafts the GitHub Release.

## Code of conduct

Be kind and constructive. The Contributor Covenant
([CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)) applies to all spaces.
