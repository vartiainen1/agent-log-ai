## What & why

<!-- What does this change do, and why? One or two sentences. -->

- [ ] Linked issue (if any): #

## Agent-memory discipline (dogfooding)

This repo is the reasoning layer over the sibling logs - the change itself
should follow the rules:

- [ ] I logged the decision in `decisions.txt` before changing behavior (or
      the change is a trivial fix already covered by an existing decision)
- [ ] `python _test_logs_ai.py` passes (all tests green, offline - HTTP mocked)
- [ ] `python check_logs_ai.py` exits 0 on the repo's own log
- [ ] CHANGELOG.md has a bullet under `## [Unreleased]`
- [ ] Added/updated tests for any behavior change

## Checklist

- [ ] Zero new dependencies (stdlib only)
- [ ] No API keys committed (env var only)
- [ ] Runs on Windows and Unix (CI proves it)
