# agent-log-ai

An LLM that reads your agent's error and decision logs and drafts the
root-cause lessons your keyword heuristics can't.

The third member of the agent-memory family. Where
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

## Why

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
  v0.1.0 — `--timeout N` controls how long a single call waits.

## Companion tools

| Repo | What it remembers | How it works |
|---|---|---|
| [agent-error-log](https://github.com/vartiainen1/agent-error-log) | what BROKE | text log + linter + git gate |
| [agent-decision-log](https://github.com/vartiainen1/agent-decision-log) | what was CHOSEN and why | append-only decisions + currency chain |
| **agent-log-ai (this)** | *why* it kept happening | heuristics select → LLM reasons |

## FAQ

**Do I need an API key?** No — local-first. With Ollama running
(`ollama serve`), the default base-url works with no key. A key is only
needed for cloud endpoints.

**Does this replace `--lessons` / `--review`?** No — it uses them. This tool
is the reasoning layer on top of the existing heuristics.

**Is my log sent somewhere?** Only to the endpoint you point at. Local by
default; cloud only if you pass `--base-url https://...` and a key.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md). Run `python _test_logs_ai.py` —
all tests are offline (the HTTP layer is mocked; the suite runs green with
no network and no API key) — (93, 100% pass expected).
`python check_logs_ai.py` must exit 0 on the repo's own log. README test
counts are enforced by a drift-guard CI job, so keep them in sync.
