# agent-log-ai

An LLM that reads your agent's error and decision logs and drafts the
root-cause lessons your keyword heuristics can't.

The reasoning layer of the agent-memory family. Where
[agent-error-log](https://github.com/vartiainen1/agent-error-log) records
what BROKE (reactive memory) and
[agent-decision-log](https://github.com/vartiainen1/agent-decision-log)
records what was CHOSEN (proactive memory), this repo adds the REASONING
layer: it sends the distilled clusters and reversal chains to an
LLM-compatible endpoint and drafts the *why* — the root-cause lesson that
keyword frequency and reversal counting can only point at.

[![CI](https://github.com/vartiainen1/agent-log-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/vartiainen1/agent-log-ai/actions/workflows/ci.yml)
[![checks on master](https://img.shields.io/github/checks-status/vartiainen1/agent-log-ai/master)](https://github.com/vartiainen1/agent-log-ai/actions)
[![release](https://img.shields.io/github/v/release/vartiainen1/agent-log-ai)](https://github.com/vartiainen1/agent-log-ai/releases)
[![license](https://img.shields.io/github/license/vartiainen1/agent-log-ai)](https://github.com/vartiainen1/agent-log-ai/blob/master/LICENSE)
[![python](https://img.shields.io/badge/python-3.9%20%7C%203.11%20%7C%203.12-3776AB)](https://github.com/vartiainen1/agent-log-ai/actions)
[![dependencies-0](https://img.shields.io/badge/dependencies-0-brightgreen)](https://github.com/vartiainen1/agent-log-ai)
[![Visitors](https://visitor-badge.laobi.icu/badge?page_id=vartiainen1.agent-log-ai&left_text=Visitors&right_color=2F80ED)](https://github.com/vartiainen1/agent-log-ai)
[![companion-error](https://img.shields.io/badge/companion-agent--error--log-2ea44f)](https://github.com/vartiainen1/agent-error-log)
[![companion-decision](https://img.shields.io/badge/companion-agent--decision--log-2ea44f)](https://github.com/vartiainen1/agent-decision-log)
[![companion-diff-gate](https://img.shields.io/badge/companion-agent--diff--gate-2ea44f)](https://github.com/vartiainen1/agent-diff-gate)

## Why this exists

The two sibling tools turn an agent's history into *mechanical* memory:
`--lessons` groups failures by shared keywords, `--review` counts reversals
by topic. Both are deliberately heuristic — deterministic, testable, free.
But the *reasoning* is left to you: *why* did this cluster keep failing?
*why* did you flip-flop between regex and AST every time the file grew past
200 lines?

That gap is exactly what an LLM is good at. `agent-log-ai` keeps the
heuristics (they select what matters) and hands the explanation to a model —
so your memory stops being a list of symptoms and starts being a list of
causes.

## Quick start

```bash
# 1. Point it at a log and draft lessons for the biggest failure cluster
python check_logs_ai.py --lessons --log errors.txt --dry-run   # see the prompt first, costs nothing

# 2. Send it (local-first: no key needed for Ollama/vLLM)
python check_logs_ai.py --lessons --log errors.txt

# 3. Cloud option: any OpenAI-compatible endpoint
OPENAI_API_KEY=sk-... python check_logs_ai.py --lessons --log errors.txt --base-url https://api.openai.com/v1 --model gpt-4o
```

## Commands

| Command | Reads | Writes | Notes |
|---|---|---|---|
| `--lessons` | `errors.txt` | root-cause lesson drafts (→ `rules.txt` §7 with `--apply`) | Heuristics pick the top clusters; the LLM explains each cluster's real root cause and proposes the rule |
| `--review` | `decisions.txt` | reversal analysis (→ `rules.txt` §7 with `--apply`) | Reversal chains with their REASONs; the LLM infers the deeper pattern |
| `--notes` | logs + `notes.txt` | a SESSION NOTE draft (append with `--append`) | The loop drafts its own closing memory |
| `--check` | — | API connectivity health check | Tiny ping — no real prompt |
| `--dry-run` | — | prints the exact prompt, sends nothing | Free preview |
| `--init [DIR]` | — | scaffolds `errors.txt` / `decisions.txt` / `rules.txt` / `notes.txt` | One-command adoption — never overwrites existing files; runs the offline self-test |

## Design

- **Stdlib only, zero install.** The LLM call is `urllib.request` →
  `POST {base}/chat/completions`. No pip packages, same as the siblings.
- **Local-first, provider-agnostic.** Default `--base-url` is
  `http://localhost:11434/v1` (Ollama); vLLM and any OpenAI-compatible
  server work with `--base-url`. The cloud path
  (`https://api.openai.com/v1`) uses `OPENAI_API_KEY` from the environment —
  never committed.
- **Heuristics point, LLM reasons.** The sibling clustering/reversal logic
  selects *what* matters; the model explains *why*. Deterministic
  pre-processing keeps the prompt small, cheap, and testable.
- **Graceful failure.** No key and no local server → a clear message, a
  `--dry-run` suggestion, and a pointer to the sibling heuristics. Never
  crashes, never blocks work.
- **Cost guard.** `--max-entries N`, line truncation, and a cheap token
  estimate (chars/4 — approximate by design) that warns before any send.
- **Retry manually.** Local models load on the first request; if a call
  times out, run it again (later calls are warm). No automatic backoff in
  v0.5.0 — `--timeout N` controls how long a single call waits.

## FAQ

**Do I need an API key?** No — local-first. With Ollama running
(`ollama serve`), the default base-url works with no key. A key is only
needed for cloud endpoints.

**Does this replace `--lessons` / `--review`?** No — it uses them. This tool
is the reasoning layer on top of the existing heuristics.

**Is my log sent somewhere?** Only to the endpoint you point at. Local by
default; cloud only if you pass `--base-url https://...` and a key.
**I copied the tool to a scratch folder — will it read my real logs?** No —
the `--errors` / `--decisions` / `--notes-file` defaults resolve relative to
the script location (`HERE`), so a scratch copy reads next to itself. Point at
your real logs from anywhere with those flags.
**Does it handle unicode (café, em-dash) on Windows?** Yes — `stdin` is
reconfigured to UTF-8 like `stdout`, so piped unicode prompts are handled
without double-encoding.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md). Run `python _test_logs_ai.py` —
all tests are offline (the HTTP layer is mocked; the suite runs green with
no network and no API key) — (110, 100% pass expected).
`python check_logs_ai.py` must exit 0 on the repo's own log. README test
counts and family structure are enforced by drift-guard CI jobs, so keep them in sync.

## Security

- The tool sends log excerpts only to the endpoint you point at — local by
  default. **Never put credentials or secrets in your logs**; keep the repo
  private if in doubt.
- API keys come from the environment (`OPENAI_API_KEY` or `--api-key`),
  never from files or the log.
- To report a vulnerability, use the private advisory path in
  [`SECURITY.md`](SECURITY.md) — never a public issue.

## Companion tools

The agent-memory family — same shape, same lifecycle verbs, four layers:

| Repo | What it remembers | How it works |
|---|---|---|
| [agent-error-log](https://github.com/vartiainen1/agent-error-log) | what BROKE | text log + linter + git gate |
| [agent-decision-log](https://github.com/vartiainen1/agent-decision-log) | what was CHOSEN and why | append-only decisions + currency chain |
| **agent-log-ai (this)** | *why* it kept happening | heuristics select → LLM reasons |
| [agent-diff-gate](https://github.com/vartiainen1/agent-diff-gate) | what must never be COMMITTED | pre-commit diff scan + gate |

## Installing with pip (optional)

The single-file adoption story is unchanged - copy `check_logs_ai.py` into
your project and you are done. The tool is *also* pip-installable with zero
runtime dependencies:

```sh
pip install agent-log-ai1        # the PyPI name — PyPI's name-similarity
                                 # guard rejected the plain "agent-log-ai"
log-ai --help                    # console script is unchanged
```

- The package version is derived from the git tag (setuptools-scm), which the
  release workflow creates from CHANGELOG.md - there is no version to drift.
- Run from the installed package, default paths (`decisions.txt`, `errors.txt`,
  `rules.txt`, `notes.txt`) resolve against your current directory; an in-place
  copy keeps resolving against the file's folder.
- `--init` works identically from an installed copy (built-in templates).


## Dogfood ledger

This repo is reviewed by its own family gate — **agent-diff-gate**, a
pre-commit diff analyzer that flags risky patterns in added code. The
ledger below is the gate's output over this repo's entire history
(initial commit → `HEAD`), recorded so the tool's claims are backed by
its own findings.

The gate numbers its rules R1–R14 (`python check_diff.py --list-rules`
prints the full list). The classes that appear in this repo's history:

- **R2** — silent failure: an exception swallowed without a trace
- **R4** — duplicate logic: near-identical lines added in the same diff
- **R6** — hardcoded URL: a non-placeholder URL in added code
- **R10** — overly broad exception handler (a catch-all `except` clause)

| | |
|---|---|
| Commits scanned | 34 (~2,400 diff lines) |
| Findings | **79** — 1 HIGH · 59 MEDIUM · 19 LOW |
| Classes | R4 ×58 (MEDIUM) · R6 ×19 (LOW) · R2 ×1 (HIGH) · R10 ×1 (MEDIUM) |
| Suppressed | **none** — every finding is fixed, tracked in `decisions.txt`, or documented here |

- **R4 (MEDIUM, dominant)** — the documented test-fixture duplication
  class; this repo's scan is dominated by it.
- **R6 (LOW)** — URL literals in docs and fixtures (the explicit-contract
  behavior).
- **R2 (HIGH)** — a best-effort test-teardown swallow, deliberate by intent.
- **R10 (MEDIUM)** — a broad exception handler, tracked in this repo's log.

Reproduce from this repo:

```sh
git diff $(git rev-list --max-parents=0 HEAD) HEAD \
  | python <path-to>/agent-diff-gate/check_diff.py --stdin --json
```

## License

MIT - see [LICENSE](LICENSE).
