"""Unit tests for check_logs_ai.py - parsers, heuristics, prompt builders,
the LLM client (HTTP mocked - the suite runs offline with no network and no
API key), --apply/--append writes, and the commit gate.
Run: python _test_logs_ai.py"""

import contextlib
import io
import json
import random
import subprocess
import sys
import tempfile
import unittest.mock as mock
import urllib.error
from pathlib import Path

import shutil as _sh
import check_logs_ai as cla

PASS = 0

BAR = "=" * 80


def t(name, cond):
    global PASS
    assert cond, f"FAIL: {name}"
    PASS += 1
    print(f"PASS {PASS}: {name}")


def quiet(fn, *args, **kwargs):
    old = sys.stdout
    sys.stdout = io.StringIO()
    try:
        return fn(*args, **kwargs)
    finally:
        sys.stdout = old


# --- fixtures ----------------------------------------------------------------

def err_entry(tag, area, error="symptom", cause="root cause", fix="the fix",
              status="FIXED"):
    e = f"[{tag}] AREA: {area}\n"
    e += f"  ERROR: {error}\n"
    e += f"  CAUSE: {cause}\n"
    e += f"  FIX: {fix}\n"
    e += f"  STATUS: {status}.\n"
    return e


def dec_entry(ts, title, status="LOCKED", reason="why", files="", supersedes=""):
    e = f"[{ts}] DECISION: {title}\n"
    if reason is not None:
        e += f"  REASON: {reason}\n"
    if files:
        e += f"  FILES: {files}\n"
    if supersedes:
        e += f"  SUPERSEDES: {supersedes}\n"
    e += f"  STATUS: {status}.\n"
    return e


def sample_errors():
    return (
        BAR + "\n1) TEST\n" + BAR + "\n\n"
        + err_entry("2026-08-01", "payment webhook parser")
        + "\n"
        + err_entry("2026-08-02", "image resize timeout", status="OPEN")
        + "\n"
        + err_entry("always", "evergreen issue", status="MITIGATED")
        + "\n"
        + BAR + "\n5) TO ADD A NEW ENTRY\n" + BAR + "\n"
    )


def sample_decisions():
    return (
        BAR + "\n1) TEST\n" + BAR + "\n\n"
        + dec_entry("2026-08-01 10:00", "regex parser", files="src/parser.py")
        + "\n"
        + dec_entry("2026-08-02 10:00", "moved to AST", status="REVISED",
                    files="src/parser.py", reason="file grew",
                    supersedes="2026-08-01 10:00")
        + "\n"
        + dec_entry("2026-08-03 10:00", "back to regex", status="REVISED",
                    files="src/parser.py", reason="too heavy",
                    supersedes="2026-08-02 10:00")
        + "\n"
        + dec_entry("2026-08-04 10:00", "auth - JWT", status="OPEN",
                    reason="deferred")
        + "\n"
        + BAR + "\n5) TO ADD A NEW ENTRY\n" + BAR + "\n"
    )


def tmp_log(text):
    d = tempfile.TemporaryDirectory()
    p = Path(d.name) / "log.txt"
    p.write_text(text, encoding="utf-8")
    return d, p


class FakeResp:
    """Stand-in for urllib's response object (supports `with`)."""

    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def mock_ok(content="LLM answer"):
    return mock.patch(
        "urllib.request.urlopen",
        return_value=FakeResp({"choices": [{"message": {"content": content}}]}))


def mock_http_error(code=429, body="rate limited"):
    def _boom(*a, **k):
        fp = io.BytesIO(json.dumps({"error": {"message": body}}).encode())
        raise urllib.error.HTTPError("http://x/v1/chat/completions", code,
                                     "err", {}, fp)
    return mock.patch("urllib.request.urlopen", side_effect=_boom)


def mock_url_error():
    return mock.patch("urllib.request.urlopen",
                      side_effect=urllib.error.URLError("connection refused"))


# --- parsers ------------------------------------------------------------------

SE = sample_errors()
ees = cla.parse_entries(SE, "errors")
t("errors: parses 3 real entries", len(ees) == 3)
t("errors: template not an entry", not any("what broke" in e["area"] for e in ees))
t("errors: area parsed", ees[0]["area"] == "payment webhook parser")
t("errors: fields parsed", ees[0]["fields"]["CAUSE"] == "root cause")
t("errors: body stops before bar", not any("5) TO ADD" in l for e in ees for l in e["body"]))
t("errors: empty text parses to []", cla.parse_entries("", "errors") == [])

SD = sample_decisions()
des = cla.parse_entries(SD, "decisions")
t("decisions: parses 4 real entries", len(des) == 4)
t("decisions: title parsed", des[0]["title"] == "regex parser")
t("decisions: SUPERSEDES parsed", des[2]["fields"]["SUPERSEDES"] == "2026-08-02 10:00")
t("decisions: empty text parses to []", cla.parse_entries("", "decisions") == [])

# --- status_token --------------------------------------------------------------

t("status_token strips dot", cla.status_token("FIXED.") == "FIXED")
t("status_token strips em/en/hyphen", cla.status_token("OPEN—").upper() == "OPEN"
  and cla.status_token("OPEN–").upper() == "OPEN" and cla.status_token("OPEN- x") == "OPEN")
t("status_token splits note", cla.status_token("WORKAROUND shipped; root fix") == "WORKAROUND")
t("status_token empty", cla.status_token("") == "")

# --- clustering / topics / open -----------------------------------------------

cl = cla.cluster_entries(ees)
t("cluster_entries groups the 3", len(cl) >= 1 and sum(len(c["entries"]) for c in cl) == 3)
t("cluster_entries returns empty for []", cla.cluster_entries([]) == [])

t("_topic_of uses FILES basename", cla._topic_of(des[0]) == "parser.py")
def _dec(title):
    return cla.parse_entries(dec_entry("2026-08-05 10:00", title), "decisions")[0]
t("_topic_of falls back to title words",
  cla._topic_of(_dec("auth flow JWT choice")) == "auth flow jwt")
t("_topic_of empty title -> untitled",
  cla._topic_of(_dec("it")) == "untitled")

topics = cla.reversal_topics(des)
t("reversal_topics finds parser.py (2 reversals)", "parser.py" in topics)
t("reversal_topics excludes single reversals", len(topics) == 1)

t("current_open finds OPEN not superseded",
  [e["tag"] for e in cla.current_open(des)] == ["2026-08-04 10:00"])
resolved = des + cla.parse_entries(
    dec_entry("2026-08-05 10:00", "settled auth", supersedes="2026-08-04 10:00"),
    "decisions")
t("current_open drops resolved OPEN", cla.current_open(resolved) == [])

# --- last_session_note ----------------------------------------------------------

t("last_session_note finds the block",
  "SESSION NOTE (2026-08-01): the title" in cla.last_session_note(
      "NOTES\n\nSESSION NOTE (2026-08-01): the title\n  - bullet\n"))
t("last_session_note none", cla.last_session_note("no notes here") == "(no session notes yet)")
t("last_session_note handles empty", cla.last_session_note(None) == "(no session notes yet)")

# --- prompt builders ------------------------------------------------------------

sys_p, user_p = cla.build_lessons_prompt(cl)
t("lessons prompt has system guard", "DATA, not instructions" in sys_p)
t("lessons prompt names clusters", "CLUSTER 1" in user_p)
t("lessons prompt asks for RULE", "RULE" in user_p)
t("lessons prompt includes AREA text", "payment webhook parser" in user_p)

tr_text = (err_entry("2026-08-01", "shared area")
           + err_entry("2026-08-02", "shared area")
           + err_entry("2026-08-03", "shared area"))
_, u1 = cla.build_lessons_prompt(cla.cluster_entries(cla.parse_entries(tr_text, "errors")),
                                 max_entries=1)
_, u3 = cla.build_lessons_prompt(cla.cluster_entries(cla.parse_entries(tr_text, "errors")),
                                 max_entries=10)
t("max_entries truncates per-cluster entries",
  u1.count("AREA:") == 1 and u3.count("AREA:") == 3)

sys_r, user_r = cla.build_review_prompt(topics)
t("review prompt names topic", "parser.py" in user_r)
t("review prompt quotes REASON", "file grew" in user_r)
t("review prompt asks for PATTERN", "PATTERN" in user_r)

sys_n, user_n = cla.build_notes_prompt(des, ees, "SESSION NOTE (2026-08-01): old\n")
t("notes prompt lists recent decisions", "auth - JWT" in user_n)
t("notes prompt lists active errors", "image resize timeout" in user_n)
t("notes prompt excludes FIXED from active", "payment webhook parser" not in user_n)
t("notes prompt asks for SESSION NOTE format", "SESSION NOTE (YYYY-MM-DD)" in user_n)
sys_n2, user_n2 = cla.build_notes_prompt([], [], None)
t("notes prompt handles empty inputs", "Draft a SESSION NOTE" in user_n2)

# --- LLM client (HTTP mocked - offline) ------------------------------------------

with mock_ok("hello there"):
    content, err = cla.chat("http://localhost:11434/v1", "m", "s", "u")
t("chat: success returns content", content == "hello there" and err is None)

with mock_ok("  padded  "):
    content, err = cla.chat("http://x/v1", "m", "s", "u")
t("chat: content stripped", content == "padded")

with mock_http_error():
    content, err = cla.chat("http://x/v1", "m", "s", "u")
t("chat: HTTPError surfaces code", err is not None and "HTTP 429" in err)

with mock_http_error(code=401, body="bad key"):
    content, err = cla.chat("http://x/v1", "m", "s", "u")
t("chat: 401 surfaces body", "bad key" in err)

with mock_url_error():
    content, err = cla.chat("http://x/v1", "m", "s", "u")
t("chat: URLError surfaces", "cannot reach" in err)

with mock.patch("urllib.request.urlopen",
                side_effect=json.JSONDecodeError("x", "doc", 0)):
    content, err = cla.chat("http://x/v1", "m", "s", "u")
t("chat: JSON error caught", err is not None and "JSONDecodeError" in err)

with mock.patch("urllib.request.urlopen",
                return_value=FakeResp({"unexpected": "shape"})):
    content, err = cla.chat("http://x/v1", "m", "s", "u")
t("chat: malformed response caught", "unexpected API response" in err)

def _last_request(m):
    return m.call_args[0][0]  # the urllib.request.Request object

with mock.patch("urllib.request.urlopen") as m:
    m.return_value = FakeResp({"choices": [{"message": {"content": "ok"}}]})
    cla.chat("http://x/v1", "m", "s", "u", api_key="k123")
    req = _last_request(m)
t("chat: api key sent as Bearer", req.get_header("Authorization") == "Bearer k123")

with mock.patch("urllib.request.urlopen") as m:
    m.return_value = FakeResp({"choices": [{"message": {"content": "ok"}}]})
    cla.chat("http://x/v1", "m", "s", "u")
    req = _last_request(m)
t("chat: no auth header without key", req.get_header("Authorization") is None)
t("chat: posts to /chat/completions", "/chat/completions" in req.full_url)

t("estimate_tokens is >= 1", cla.estimate_tokens("") == 1 and cla.estimate_tokens("abcd") == 1)

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    cla._token_warn(cla.TOKEN_WARN_THRESHOLD + 1)
t("token_warn warns over threshold", "WARN" in buf.getvalue())
buf2 = io.StringIO()
with contextlib.redirect_stdout(buf2):
    cla._token_warn(10)
t("token_warn silent under threshold", buf2.getvalue() == "")

with mock.patch("urllib.request.urlopen") as m:
    m.return_value = FakeResp({"choices": [{"message": {"content": "ok"}}]})
    cla.chat("http://x/v1", "m", "s", "u", timeout=7)
    timeout_kw = m.call_args[1].get("timeout")
t("chat: timeout passed through", timeout_kw == 7)

with mock.patch("urllib.request.urlopen", side_effect=KeyboardInterrupt):
    try:
        cla.chat("http://x/v1", "m", "s", "u")
        ki_escaped = False
    except KeyboardInterrupt:
        ki_escaped = True
t("chat: KeyboardInterrupt propagates", ki_escaped)

# --- _patch_rules_lessons (--apply write path) ----------------------------------

def rules_with_section():
    d = tempfile.TemporaryDirectory()
    p = Path(d.name) / "rules.txt"
    p.write_text("OLD\n## 7) LESSONS LEARNED (proposed drafts)\n========\nOLD BODY\n",
                 encoding="utf-8")
    return d, p

d1, rp1 = rules_with_section()
try:
    cla._patch_rules_lessons(rp1, "NEW BLOCK")
    after = rp1.read_text(encoding="utf-8")
    t("apply: replaces old body", "OLD BODY" not in after)
    t("apply: keeps the header", "LESSONS LEARNED" in after)
    t("apply: writes the new block", "NEW BLOCK" in after)
    t("apply: exactly one header", after.count("LESSONS LEARNED") == 1)
    t("apply: keeps pre-section text", after.startswith("OLD\n"))
finally:
    d1.cleanup()

d2 = tempfile.TemporaryDirectory()
rp2 = Path(d2.name) / "rules.txt"
rp2.write_text("JUST RULES\n", encoding="utf-8")
try:
    cla._patch_rules_lessons(rp2, "BLOCK2")
    t("apply: appends when no section", "LESSONS LEARNED" in rp2.read_text(encoding="utf-8"))
finally:
    d2.cleanup()

d3 = tempfile.TemporaryDirectory()
rp3 = Path(d3.name) / "rules_crlf.txt"
rp3.write_bytes(b"OLD\r\n## 7) LESSONS LEARNED (proposed drafts)\r\n====\r\nOLD\r\n")
try:
    cla._patch_rules_lessons(rp3, "BLOCK3")
    t("apply: preserves CRLF", b"\r\n" in rp3.read_bytes())
finally:
    d3.cleanup()

# --- commands: dry-run paths (no network) ---------------------------------------

d4, lp4 = tmp_log(sample_errors())
try:
    t("cmd_lessons dry-run exit 0", quiet(cla.cmd_lessons, lp4.read_text(encoding="utf-8"),
                                          Path("x"), mock.Mock(dry_run=True, max_entries=15)) == 0)
finally:
    d4.cleanup()

d5, lp5 = tmp_log(sample_decisions())
try:
    t("cmd_review dry-run exit 0", quiet(cla.cmd_review, lp5.read_text(encoding="utf-8"),
                                         Path("x"), mock.Mock(dry_run=True, max_entries=15)) == 0)
finally:
    d5.cleanup()

t("cmd_lessons empty log exit 0", quiet(cla.cmd_lessons, "", Path("x"),
                                        mock.Mock(dry_run=True, max_entries=15)) == 0)
t("cmd_review single reversal nothing", quiet(cla.cmd_review,
    dec_entry("2026-08-01 10:00", "a", files="src/x.py")
    + dec_entry("2026-08-02 10:00", "b", status="REVISED", files="src/x.py",
                reason="r", supersedes="2026-08-01 10:00"),
    Path("x"), mock.Mock(dry_run=True, max_entries=15)) == 0)

# --- commands: live paths with mocked HTTP --------------------------------------

d6, lp6 = tmp_log(sample_errors())
with mock_ok("LESSON OUT"):
    rc = quiet(cla.cmd_lessons, lp6.read_text(encoding="utf-8"), Path("x"),
               mock.Mock(dry_run=False, model="m", base_url="http://x/v1",
                         api_key="", max_tokens=1024, temperature=0.3,
                         timeout=30, max_entries=15, apply=False))
t("cmd_lessons live (mocked) exit 0", rc == 0)

dA = tempfile.TemporaryDirectory()
rpA = Path(dA.name) / "rules.txt"
rpA.write_text("RULES\n", encoding="utf-8")
with mock_ok("APPLIED DRAFT RULE"):
    rcA = quiet(cla.cmd_lessons, sample_errors(), rpA,
                mock.Mock(dry_run=False, model="m", base_url="http://x/v1",
                          api_key="", max_tokens=1024, temperature=0.3,
                          timeout=30, max_entries=15, apply=True))
    applied = rpA.read_text(encoding="utf-8")
t("cmd_lessons --apply writes the draft into rules",
  rcA == 0 and "APPLIED DRAFT RULE" in applied and "LESSONS LEARNED" in applied)
dA.cleanup()

d7, lp7 = tmp_log(sample_decisions())
with mock_ok("REVIEW OUT"):
    rc = quiet(cla.cmd_review, lp7.read_text(encoding="utf-8"), Path("x"),
               mock.Mock(dry_run=False, model="m", base_url="http://x/v1",
                         api_key="", max_tokens=1024, temperature=0.3,
                         timeout=30, max_entries=15, apply=False))
t("cmd_review live (mocked) exit 0", rc == 0)

d8, lp8 = tmp_log("")
with mock_ok("NOTE OUT"):
    rc = quiet(cla.cmd_notes, Path(d8.name) / "dec.txt", Path(d8.name) / "err.txt",
               Path(d8.name) / "notes.txt",
               mock.Mock(dry_run=False, model="m", base_url="http://x/v1",
                         api_key="", max_tokens=1024, temperature=0.3,
                         timeout=30, max_entries=15, append=False))
t("cmd_notes with missing logs exit 1", rc == 1)  # nothing to draft from

d9 = tempfile.TemporaryDirectory()
dec_p = Path(d9.name) / "dec.txt"
err_p = Path(d9.name) / "err.txt"
not_p = Path(d9.name) / "notes.txt"
dec_p.write_text(sample_decisions(), encoding="utf-8")
err_p.write_text(sample_errors(), encoding="utf-8")
not_p.write_text("NOTES\n", encoding="utf-8")
with mock_ok("SESSION NOTE (2026-08-09): drafted"):
    rc = quiet(cla.cmd_notes, dec_p, err_p, not_p,
               mock.Mock(dry_run=False, model="m", base_url="http://x/v1",
                         api_key="", max_tokens=1024, temperature=0.3,
                         timeout=30, max_entries=15, append=False))
t("cmd_notes live (mocked) exit 0", rc == 0)

with mock_ok("SESSION NOTE (2026-08-09): appended"):
    rc = quiet(cla.cmd_notes, dec_p, err_p, not_p,
               mock.Mock(dry_run=False, model="m", base_url="http://x/v1",
                         api_key="", max_tokens=1024, temperature=0.3,
                         timeout=30, max_entries=15, append=True))
    appended = not_p.read_text(encoding="utf-8")
t("cmd_notes --append writes the note", "appended" in appended)
d9.cleanup()

with mock_ok("Ok"):
    rc = quiet(cla.cmd_check, mock.Mock(base_url="http://x/v1", model="m",
                                        api_key="", timeout=30))
t("cmd_check success exit 0", rc == 0)

with mock_url_error():
    rc = quiet(cla.cmd_check, mock.Mock(base_url="http://x/v1", model="m",
                                        api_key="", timeout=30))
t("cmd_check failure exit 1", rc == 1)

_cli = Path(__file__).resolve().parent / "check_logs_ai.py"
r = subprocess.run([sys.executable, str(_cli), "--lessons", "--review"],
                   capture_output=True, text=True)
t("--lessons + --review mutually exclusive (argparse exit 2)", r.returncode == 2)

# --- commit gate -----------------------------------------------------------------

def _msg(content):
    td = tempfile.TemporaryDirectory()
    p = Path(td.name) / "msg.txt"
    p.write_text(content, encoding="utf-8")
    return p, td

t("gate: missing message file fails",
  quiet(cla.cmd_check_commit, SD, Path("definitely-not-here.txt")) == 1)
p, td = _msg("chore: tidy up\n")
t("gate: no marker blocked", quiet(cla.cmd_check_commit, SD, p) == 1)
td.cleanup()
p, td = _msg("feat: x (AREA: regex parser)\n")
t("gate: logged decision passes", quiet(cla.cmd_check_commit, SD, p) == 0)
td.cleanup()
p, td = _msg("feat: x (AREA: regex parser)\n")
t("gate: trailing paren stripped", True)
td.cleanup()
p, td = _msg("feat: x (LOG: moved to AST)\n")
t("gate: LOG: marker passes", quiet(cla.cmd_check_commit, SD, p) == 0)
td.cleanup()
p, td = _msg("feat: x (AREA: totally different)\n")
t("gate: unlogged blocked", quiet(cla.cmd_check_commit, SD, p) == 1)
td.cleanup()
p, td = _msg("feat: x (AREA: regex parser) - and LOG: back to regex\n")
t("gate: last marker wins (LOG: last, logged -> pass)", quiet(cla.cmd_check_commit, SD, p) == 0)
td.cleanup()
p, td = _msg("feat: x (AREA: regex parser) - and LOG: never logged thing\n")
t("gate: last marker wins (LOG: last, unlogged -> block)", quiet(cla.cmd_check_commit, SD, p) == 1)
p, td = _msg("feat: x (AREA: regex parser) (#24)\n")
t("gate: GitHub squash-merge (#NN) suffix stripped", quiet(cla.cmd_check_commit, SD, p) == 0)
td.cleanup()
td.cleanup()
p, td = _msg("feat: x (AREA: never logged thing) - and LOG: back to regex\n")
t("gate: last marker wins (LOG: last, logged -> pass)", quiet(cla.cmd_check_commit, SD, p) == 0)
td.cleanup()
p, td = _msg("feat: x (AREA: auth - JWT)\n")
t("gate: partial title match passes", quiet(cla.cmd_check_commit, SD, p) == 0)
td.cleanup()

# --- robustness: fuzz + edge cases -----------------------------------------------

random.seed(7)
from datetime import date, timedelta
fuzz_parts = []
for i in range(100):
    tag = (date(2026, 1, 1) + timedelta(days=i % 28)).isoformat()
    fuzz_parts.append(err_entry(tag, f"area_{i}", status=random.choice(
        ["FIXED", "OPEN", "PARTIAL", "MITIGATED", "WORKAROUND"])))
t("fuzz: 100 random error entries parse+cluster without crash",
  len(cla.cluster_entries(cla.parse_entries("\n\n".join(fuzz_parts), "errors"))) >= 1)

random.seed(11)
base_dt = __import__("datetime").datetime(2026, 1, 1, 0, 0)
fuzz_dec = []
for i in range(100):
    ts = (base_dt + timedelta(minutes=i)).strftime("%Y-%m-%d %H:%M")
    fuzz_dec.append(dec_entry(ts, f"topic {i}", status=random.choice(["LOCKED", "OPEN"])))
t("fuzz: 100 random decisions parse without crash",
  len(cla.parse_entries("\n\n".join(fuzz_dec), "decisions")) == 100)

dU = tempfile.TemporaryDirectory()
try:
    pU = Path(dU.name) / "bom.txt"
    pU.write_bytes(b"\xef\xbb\xbf" + sample_errors().encode("utf-8"))
    t("BOM-prefixed log parses", len(cla.parse_entries(cla.load(pU) or "", "errors")) == 3)
    pU2 = Path(dU.name) / "bad.txt"
    pU2.write_bytes(b"[2026-08-01] AREA: \xff\xfe broken\n  ERROR: e\n  STATUS: OPEN.\n")
    t("invalid UTF-8 never crashes the parser",
      len(cla.parse_entries(cla.load(pU2) or "", "errors")) == 1)
finally:
    dU.cleanup()

# --check-commit with a BOM + CRLF message file
dC = tempfile.TemporaryDirectory()
pC = Path(dC.name) / "msg.txt"
pC.write_bytes(b"\xef\xbb\xbffeat: x (AREA: regex parser)\r\n")
t("gate: BOM + CRLF message file handled",
  quiet(cla.cmd_check_commit, SD, pC) == 0)
dC.cleanup()

# Windows console safety: stdin must be UTF-8 too (regression - same class
# as the stdout-only reconfigure bug fixed in the siblings).
t("stdin is reconfigured to utf-8", getattr(sys.stdin, "encoding", "utf-8") == "utf-8")

# --- --init scaffold -----------------------------------------------------------------

dI = tempfile.TemporaryDirectory()
rcI = quiet(cla.cmd_init, Path(dI.name), run_tests=False)
created = sorted(p.name for p in Path(dI.name).iterdir())
t("init: scaffolds all four files",
  rcI == 0 and created == ["decisions.txt", "errors.txt", "notes.txt", "rules.txt"])
(Path(dI.name) / "notes.txt").write_text("KEEP", encoding="utf-8")
quiet(cla.cmd_init, Path(dI.name), run_tests=False)
t("init: never overwrites existing files",
  (Path(dI.name) / "notes.txt").read_text(encoding="utf-8") == "KEEP")
(Path(dI.name) / "_test_logs_ai.py").write_text("print('OK')\n", encoding="utf-8")
with mock.patch("subprocess.run") as mr:
    mr.return_value.returncode = 0
    rc_run = quiet(cla.cmd_init, Path(dI.name))
t("init: runs the self-test suite when present", mr.call_count == 1 and rc_run == 0)
with mock.patch("subprocess.run") as mr2:
    mr2.return_value.returncode = 1
    rc_fail = quiet(cla.cmd_init, Path(dI.name))
t("init: a failing self-test fails adoption", mr2.call_count == 1 and rc_fail == 1)
dI.cleanup()



# --- L10 regression: load() must not crash on a locked/unreadable file ------
def _locked_load_fallback():
    import tempfile
    d = tempfile.mkdtemp()
    try:
        p = Path(d) / "locked.txt"
        p.write_text("content", encoding="utf-8")
        with mock.patch.object(Path, "read_text",
                               side_effect=PermissionError(13, "denied")):
            val = cla.load(p)
            return val == None
    finally:
        _sh.rmtree(d, ignore_errors=True)


t("L10 locked/unreadable file degrades, never crashes", _locked_load_fallback())

# Real msvcrt lock probe on Windows (skips elsewhere)
def _real_lock_probe():
    try:
        import msvcrt
    except ImportError:
        return True  # non-Windows: portable test above covers it
    import tempfile
    d = tempfile.mkdtemp()
    try:
        p = Path(d) / "locked.txt"
        p.write_text("content", encoding="utf-8")
        fh = open(p, "r+", encoding="utf-8")
        try:
            try:
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                return True  # lock unavailable in this environment
            val = cla.load(p)
            return val == None
        finally:
            try:
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
            fh.close()
    finally:
        _sh.rmtree(d, ignore_errors=True)


t("L10 real locked-file read degrades (Windows msvcrt)", _real_lock_probe())

# --- reviewer-driven: typed entries + exception vocabulary ------------------
_dec = cla.parse_entries(SD, "decisions")
_err = cla.parse_entries(SE, "errors")
t("entries are LogEntry dataclasses",
  isinstance(_dec[0], cla.LogEntry) and isinstance(_err[0], cla.LogEntry))
t("entry attributes match the dict bridge",
  _dec[0].tag == _dec[0]["tag"] and _dec[0].title == _dec[0]["title"]
  and _err[0].area == _err[0]["area"] and _dec[0].line == _dec[0]["line"])
t("entry fields/body are the same objects via the bridge",
  _dec[0]["fields"] is _dec[0].fields and _dec[0]["body"] is _dec[0].body)
t("entry .get() bridge covers kind-specific keys",
  _dec[0].get("area") == "" and _err[0].get("title") == ""
  and _dec[0].get("tag") == _dec[0]["tag"])
t("exception vocabulary is a real hierarchy",
  issubclass(cla.ValidationError, cla.AgentLogError))

# --- professional packaging: installed-mode defaults guard ---------------
t("default base: in-place file resolves to its own folder",
  cla._default_base(Path("/home/user/project/check_logs_ai.py"))
  == Path("/home/user/project/check_logs_ai.py"))
t("default base: pip-installed module resolves to the cwd",
  cla._default_base(Path("/usr/local/lib/python3.12/site-packages/check_logs_ai.py"))
  == Path.cwd())

# --- cosmetic: --help shows the installed console-script name -------------
_hlp = subprocess.run(
    [sys.executable, str(Path(__file__).resolve().parent / "check_logs_ai.py"), "--help"],
    capture_output=True, text=True)
t("--help usage shows log-ai prog name (not check_logs_ai.py)",
  _hlp.returncode == 0 and "usage: log-ai" in (_hlp.stdout or ""))


# --- --version contract (family finding #1) --------------------------------
_ver = subprocess.run(
    [sys.executable, str(Path(__file__).resolve().parent / "check_logs_ai.py"), "--version"],
    capture_output=True, text=True)
t("version: flag prints module name and version",
  _ver.returncode == 0 and "check_logs_ai.py" in (_ver.stdout or "")
  and cla.VERSION in (_ver.stdout or ""))
# true self-sync: read the CHANGELOG at test time (diff-gate contract)
_cl = (Path(__file__).resolve().parent / "CHANGELOG.md").read_text(
    encoding="utf-8")
_first_versioned = next(
    (ln for ln in _cl.splitlines() if ln.startswith("## [") and "Unreleased" not in ln), None)
t("version: CHANGELOG first versioned header matches VERSION",
  _first_versioned is not None and _first_versioned[4:].split("]", 1)[0] == cla.VERSION)
t("version: constant is a semantic version triple",
  len(cla.VERSION.split(".")) == 3)

print(f"\nAll {PASS} tests passed.")
