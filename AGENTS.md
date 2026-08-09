# AGENTS.md - instructions for AI coding agents

This repo is the REASONING layer of the agent-memory family. It takes the
clusters distilled from the sibling logs (`errors.txt` / `decisions.txt`),
sends them to an LLM-compatible endpoint, and drafts the root-cause lessons
the heuristics can only point at. Companion repos:
[agent-error-log](https://github.com/vartiainen1/agent-error-log) (what
broke) and
[agent-decision-log](https://github.com/vartiainen1/agent-decision-log)
(what was chosen).

## 1) Read first (in this order)

1. `README.md` - the command surface (`--lessons` / `--review` / `--notes`)
2. `rules.txt` - behavior rules (how to behave)
3. `notes.txt` - session notes and context

## 2) The discipline

- **Deterministic first, LLM second.** The heuristics select what matters;
  the model explains it. Never send a raw log - always distill first.
- **Local-first.** The default `--base-url` is Ollama
  (`http://localhost:11434/v1`). Cloud keys come from the environment
  (`OPENAI_API_KEY`), never from the repo.
- **Dry-run before you send.** `--dry-run` prints the prompt and costs
  nothing - use it to sanity-check a prompt before paying for tokens.
- **Log before fixing.** Found a bug? Record it in `notes.txt` (or the
  sibling error log) first, then fix.
- **Never commit an API key.** The repo, `.gitignore`, and CI all enforce
  this.

## 3) Committing (the AREA-marker gate)

Every commit or PR title must carry an `AREA: <text>` marker naming a
logged decision in `decisions.txt`:

    git commit -m "feat: <thing> (AREA: <logged decision>)"

The CI workflow enforces this on master with `--check-commit` — the marker
must name a decision already in `decisions.txt`. Log the decision first
(use the sibling `python check_decisions.py --decide` on the same file
format), then commit.

## 4) The compounding loop

This tool closes the agent-memory loop: failures teach rules
(agent-error-log `--lessons`), decisions teach rules (agent-decision-log
`--review`), and `agent-log-ai` turns both into *reasoned* drafts that a
human confirms into `rules.txt` — memory that explains itself.

## 5) Companion tools

| Repo | What it remembers |
|---|---|
| agent-error-log | what BROKE (reactive memory) |
| agent-decision-log | what was CHOSEN and why (proactive memory) |
| **agent-log-ai (this)** | *why* it kept happening (reasoning memory) |
