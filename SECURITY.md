# Security Policy

## Reporting a vulnerability

Please do **not** open a public issue for a security vulnerability. Instead,
report it privately to the maintainer via GitHub's security advisory feature:
**Security → Report a vulnerability** on this repository.

You should receive a response within 7 days. If the issue is confirmed, a fix
and (if warranted) a security release will be prepared before the details are
made public.

## Scope

This project is stdlib-only tooling with one deliberate external surface:
it sends distilled log excerpts to an LLM endpoint you point it at. The
realistic risks:

- **API key exposure** - `OPENAI_API_KEY` is read from the environment,
  never from the repo. Never commit a key; `.gitignore` guards it.
- **Data egress** - the tool is local-first (default `--base-url` is
  `http://localhost:11434/v1`). Nothing leaves your machine unless you pass
  a cloud `--base-url`. Prompts are distilled clusters, not raw logs.
- **Prompt injection** - log text is untrusted input that ends up inside a
  prompt. The system prompt instructs the model to treat log content as
  data, not instructions.
- **Log spoofing** - a tool that reasons over text cannot verify the *truth*
  of what is logged. The linter checks format, not honesty; that is true of
  any documentation system.

## Supported versions

Security fixes land in the latest release and are backported on request.
