"""start.py - Agent session bootstrap: reasoning-layer boot briefing.

agent-log-ai is the REASONING layer of the agent-memory family. It keeps no
memory of its own (the siblings do that), so unlike the sibling start.py
files it has no "what's still open" recall to print. Instead it orients a
fresh session:

    python start.py

Prints, from the folder holding this script:
  0. a health check of the sibling logs (if they live next door),
  1. whether the local LLM endpoint (Ollama by default) is reachable,
  2. the command cheat-sheet,
  3. the latest session note from the notes file.

Delegates parsing to check_logs_ai (the canonical tool) so this file can
never drift from the entry formats the tool validates.

Stdlib only. Makes one optional, 2-second socket probe - never a model call.
"""

import socket
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path

try:
    import check_logs_ai  # canonical tool: parses and validates the logs
except ImportError:
    check_logs_ai = None

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# --- CONFIG ------------------------------------------------------------
# agent-log-ai's own files (notes) live next to this script; the sibling
# logs are expected one folder up (../agent-error-log, ../agent-decision-log)
# but their absence is not fatal - every command accepts --log explicitly.
HERE = Path(__file__).resolve().parent
NOTES_FILE = "notes.txt"
RULES_FILE = "rules.txt"
SIBLING_LOGS = {
    "errors": HERE.parent / "agent-error-log" / "errors.txt",
    "decisions": HERE.parent / "agent-decision-log" / "decisions.txt",
}
# ----------------------------------------------------------------------

BAR = "=" * 80
SUB = "-" * 80


def _endpoint_reachable(base_url, timeout=2):
    """True if the LLM endpoint host:port accepts a TCP connection."""
    try:
        parts = urllib.parse.urlsplit(base_url)
        with socket.create_connection((parts.hostname, parts.port or 80),
                                      timeout=timeout):
            return True
    except OSError:
        return False


def _sibling_health(kind, path):
    """One-line health report for a sibling log, graceful when absent."""
    name = "agent-error-log" if kind == "errors" else "agent-decision-log"
    if not path.exists():
        return f"  (not found: {path.parent.name}/{path.name} - pass --log when using the tool)"
    if check_logs_ai is None:
        return f"  ok {name}: {path.name} present (check_logs_ai.py not found - count skipped)"
    text = check_logs_ai.load(path)
    if not text:
        return f"  ok {name}: {path.name} present, empty"
    entries = check_logs_ai.parse_entries(text, kind)
    if kind == "errors":
        active = [e for e in entries
                  if check_logs_ai.status_token(e["fields"].get("STATUS", "")).upper()
                  not in ("FIXED", "")]
        extra = f", {len(active)} still open" if active else ""
    else:
        active = check_logs_ai.current_open(entries)
        extra = f", {len(active)} OPEN" if active else ""
    return f"  ok {name}: {len(entries)} entries{extra} ({path.name})"


def main():
    notes = None
    if HERE.joinpath(NOTES_FILE).exists():
        notes = (HERE / NOTES_FILE).read_text(encoding="utf-8", errors="replace")

    print(BAR)
    print("AGENT-LOG-AI - REASONING MEMORY BOOT BRIEFING")
    print(f"when       : {datetime.now():%Y-%m-%d %H:%M}")
    print(f"workspace  : {HERE}")
    print(BAR)

    print(f"\n{SUB}")
    print("STEP 0 - SIBLING LOG HEALTH (what --lessons / --review will read):")
    for kind, path in SIBLING_LOGS.items():
        print(_sibling_health(kind, path))

    print(f"\n{SUB}")
    print("STEP 1 - LLM ENDPOINT (local-first by default):")
    base = check_logs_ai.DEFAULT_BASE_URL if check_logs_ai else "http://localhost:11434/v1"
    if _endpoint_reachable(base):
        print(f"  ok {base} is reachable - live reasoning available.")
    else:
        print(f"  (offline: {base} not reachable - fine, --dry-run and the")
        print("   full offline test suite work without it)")

    print(f"\n{SUB}")
    print("COMMANDS (run 'python check_logs_ai.py -h' for the full list):")
    print("  --lessons --log errors.txt    distill root causes + rules from the error log")
    print("  --review  --log decisions.txt find reversal patterns + rule drafts")
    print("  --notes                       draft a SESSION NOTE from both logs + notes")
    print("  --check                       tiny connectivity ping to the LLM endpoint")
    print("  --dry-run                     print the exact prompt, send nothing")
    print("  --apply / --append            write the LLM draft into rules.txt / notes.txt")
    print("  --check-commit msg.txt        CI gate: message must name a logged decision")
    print("  --init [DIR]                  scaffold errors/decisions/rules/notes (never overwrites)")

    print(f"\n{SUB}")
    print(f"LATEST SESSION NOTE (from {NOTES_FILE}):")
    if notes is None:
        print(f"  (missing file: {HERE / NOTES_FILE})")
    else:
        latest = (check_logs_ai.last_session_note(notes)
                  if check_logs_ai else "(check_logs_ai.py not found)")
        for line in latest.splitlines():
            print(f"  {line}")

    print(f"\n{SUB}")
    print(f"Tips: read {RULES_FILE} first; always --dry-run before spending tokens;")
    print("the model never sees instructions inside the logs (injection guard).")
    print("Log new decisions in ../agent-decision-log and errors in")
    print("../agent-error-log - the siblings own the memory, this tool reasons over it.")
    print(BAR)


if __name__ == "__main__":
    main()
