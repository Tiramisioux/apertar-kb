#!/usr/bin/env python3
"""Tutor helper: find a tutorial, check its code refs, run its read-only step checks, log progress.

Used by the apertar-dev skill when Patrik says "work with me on T01". Runs on the Mac and on the Pi.

  python3 tutorial.py list                        # every tutorial: id, status, note, last progress
  python3 tutorial.py show T01                    # note path, outline (sections + steps), checks, progress
  python3 tutorial.py refs T01                    # are the note's code refs still at the stated lines (Pi tree)?
  python3 tutorial.py check T01 4.1               # run step 4.1's read-only check on the Pi, PASS/FAIL
  python3 tutorial.py log T01 4.1 done "iso jumped to 800"   # append to tutorials/progress/T01.md

A tutorial is found by its ID (T01) or by a fragment of its file name ("talk-to-core").

The machine-readable part of a note is a hidden Obsidian comment block (see tutorials/README.md):

  %% tutor
  ref core src/ApertarCoreApp.cpp 9091 std::string ApertarCoreApp::handleCommand
  check 3.1 | curl -s -X POST http://127.0.0.1:8000/api/command -d '{"cmd":"ping"}' | "pong":true
  %%

  ref   <core|ui|drv> <repo path> <line> <literal anchor>      anchor = rest of the line
  check <step> | <command, run ON THE PI> | <expected regex>   read-only commands only (see SAFE)

Read-only except `log`, which appends one line to a progress file (commit it in the KB afterwards).
"""
import datetime
import re
import shlex
import subprocess
import sys
from pathlib import Path

KB = Path(__file__).resolve().parent.parent
HOME = Path.home()
ON_PI = (HOME / "ApertarCore").is_dir()
PI_HOST = "apertar"
OBSIDIAN = HOME / "local anteckningar/obsidian vaults/Patrik Obsidian/02_PROJEKT/CINEMATE/APERTAR/notes"
NOTE_DIRS = [KB / "tutorials" / "inbox"] + ([HOME / "apertar-tutorials", HOME / "apertar-tutorials" / "_archive"] if ON_PI else [OBSIDIAN, OBSIDIAN.parent / "_archive"])  # _archive: finished notes Patrik moved
PROGRESS = KB / "tutorials" / "progress"
PI_REPOS = {"core": "ApertarCore", "ui": "ApertarUI", "drv": "drivers/imx585-v4l2-driver"}

# A check runs only if it is plainly read-only. Anything else is refused, not run.
SAFE_FIRST = {"curl", "grep", "cat", "ls", "git", "systemctl", "findmnt", "stat", "test", "head",
              "tail", "wc", "pgrep", "i2cdetect", "i2cget", "gpioinfo", "v4l2-ctl", "dmesg", "id", "free", "df", "uname",
              "pinctrl", "python3", "rpicam-hello"}
SAFE_GIT = {"diff", "status", "log", "show", "rev-parse", "branch"}
SAFE_SYSTEMCTL = {"show", "status", "is-active", "cat"}
SAFE_CORE_CMDS = {"ping", "help", "get_state", "get_media_test_state", "audio_capabilities",
                  "list_sensor_modes", "list_actions", "get_controls", "controls_history", "controls_last_input"}


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)


# ---------- finding notes ----------

def learning_path():
    """ID -> (title, status) from llm/tutoring.md §5."""
    rows = {}
    text = (KB / "llm" / "tutoring.md").read_text()
    for line in text.splitlines():
        m = re.match(r"\|\s*(T\d\d)\s*\|", line)
        if m:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            rows[m.group(1)] = (cells[2], cells[-1])
    return rows


def all_notes():
    notes = []
    for d in NOTE_DIRS:
        if d.is_dir():
            notes += [p for p in sorted(d.glob("*.md")) if p.name != "README.md"]
    return notes


def find_note(key):
    notes = all_notes()
    if re.fullmatch(r"[Tt]\d\d", key):
        hits = [p for p in notes if re.search(rf"\b{key.upper()}\b", p.name)]
        if not hits:  # an older note without the ID in its name: the `fragment` in the path title
            m = re.search(r"`([^`]+)`", learning_path().get(key.upper(), ("", ""))[0])
            hits = [p for p in notes if m and m.group(1).lower() in p.name.lower()]
    else:
        hits = [p for p in notes if key.lower() in p.name.lower()]
    if not hits:
        where = ", ".join(str(d) for d in NOTE_DIRS)
        die(f"No tutorial note matches {key!r} in {where}."
            + ("\nOn the Pi, Mac-written notes arrive with deploy_to_pi.sh." if ON_PI else ""))
    if len(hits) > 1:
        die("Several notes match:\n  " + "\n  ".join(p.name for p in hits))
    return hits[0]


def note_id(path):
    m = re.search(r"\b(T\d\d)\b", path.name)
    if m:
        return m.group(1)
    for tid, (title, _) in learning_path().items():
        frag = re.search(r"`([^`]+)`", title)
        if frag and frag.group(1).lower() in path.name.lower():
            return tid
    return None  # not a tutorial (manual, learning path)


def tutor_block(text):
    m = re.search(r"%%\s*tutor\s*\n(.*?)%%", text, re.S)
    refs, checks = [], []
    if not m:
        return refs, checks
    for raw in m.group(1).splitlines():
        line = raw.strip()
        if line.startswith("ref "):
            parts = line.split(None, 4)
            if len(parts) == 5:
                refs.append({"repo": parts[1], "path": parts[2], "line": int(parts[3]), "anchor": parts[4]})
        elif line.startswith("check "):
            body = line[len("check "):]
            fields = [f.strip() for f in body.split(" | ")]
            if len(fields) == 3:
                checks.append({"step": fields[0], "cmd": fields[1], "expect": fields[2]})
    return refs, checks


def progress_file(tid):
    return PROGRESS / f"{tid}.md"


def last_progress(tid):
    p = progress_file(tid)
    if not p.exists():
        return None
    rows = [l for l in p.read_text().splitlines() if re.match(r"\|\s*\d{4}-", l)]
    return rows[-1] if rows else None


# ---------- running on the Pi ----------

def pi_run(cmd, timeout=20):
    """Run a shell command on the Pi (locally when already there). Returns (code, output)."""
    argv = ["bash", "-c", cmd] if ON_PI else ["ssh", "-o", "ConnectTimeout=5", PI_HOST, cmd]
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr)
    except subprocess.TimeoutExpired:
        return 124, "timeout"


def pipe_stages(cmd):
    """Split on | outside quotes."""
    stages, cur, quote = [], "", None
    for ch in cmd:
        if quote:
            quote = None if ch == quote else quote
        elif ch in "'\"":
            quote = ch
        elif ch == "|":
            stages.append(cur)
            cur = ""
            continue
        cur += ch
    return stages + [cur]


def unsafe_reason(cmd):
    unquoted = re.sub(r"'[^']*'", "''", cmd)  # only single quotes are inert in a shell
    if re.search(r"[;&`]|\$\(|>|\bsudo\b|\brm\b|\btee\b", unquoted):
        return "contains ; & ` $( > sudo rm or tee outside single quotes"
    for stage in pipe_stages(cmd):
        words = shlex.split(stage)
        if not words:
            continue
        first = words[0]
        if first not in SAFE_FIRST:
            return f"{first!r} is not on the read-only list"
        if first == "git":
            sub = next((w for w in words[1:] if not w.startswith("-") and "/" not in w and w != "-C"), "")
            if sub not in SAFE_GIT:
                return f"git {sub} is not read-only"
        if first == "rpicam-hello" and "--list-cameras" not in words:
            return "rpicam-hello is allowed only with --list-cameras (anything else opens the camera)"
        if first == "systemctl":
            sub = next((w for w in words[1:] if not w.startswith("-")), "")
            if sub not in SAFE_SYSTEMCTL:
                return f"systemctl {sub} is not read-only"
        if first == "curl":
            names = re.findall(r'"cmd"\s*:\s*"([a-z_]+)"', stage)
            if any(n not in SAFE_CORE_CMDS for n in names):
                return f"Core command {names} changes state"
            if re.search(r"/api/config", stage):
                return "/api/config can write the hardware config"
        peek = len(words) == 2 and words[1].endswith(".py") and "sock_peek" in words[1]
        if first == "python3" and not (peek or words[1:3] == ["-m", "json.tool"]):
            return "python3 is allowed only as `-m json.tool` or the tutorial's own sock_peek script"
    return None


# ---------- commands ----------

def cmd_list(_):
    path = learning_path()
    notes = {note_id(p): p for p in all_notes() if note_id(p)}
    ids = sorted(set(path) | set(notes))
    print(f"{'ID':5} {'status':12} {'note':55} last progress")
    for tid in ids:
        title, status = path.get(tid, ("", "?"))
        note = notes[tid].name if tid in notes else f"(no note yet) {title}"
        lp = last_progress(tid) or ""
        print(f"{tid:5} {status:12} {note[:55]:55} {lp[:60]}")


def cmd_show(args):
    note = find_note(args[0])
    text = note.read_text()
    tid = note_id(note) or note.stem
    refs, checks = tutor_block(text)
    status = re.search(r"^Status:.*$", text, re.M)
    print(f"{tid}  {note}")
    print(status.group(0) if status else "Status: (no status line)")
    print("\nOutline (line: heading / step):")
    for i, line in enumerate(text.splitlines(), 1):
        if re.match(r"^#{2,3} ", line) or re.match(r"^\*\*\d+\.\d+ ", line):
            print(f"  {i:4}: {line[:100]}")
    print(f"\n{len(refs)} refs, {len(checks)} checks")
    for c in checks:
        print(f"  check {c['step']:5} expect /{c['expect']}/   {c['cmd'][:80]}")
    p = progress_file(tid)
    print(f"\nProgress ({p.relative_to(KB)}):")
    if p.exists():
        rows = [l for l in p.read_text().splitlines() if re.match(r"\|\s*\d{4}-", l)]
        for r in rows[-8:]:
            print("  " + r)
    else:
        print("  not started")


def cmd_refs(args):
    note = find_note(args[0])
    refs, _ = tutor_block(note.read_text())
    if not refs:
        die("No `ref` lines in the tutor block.")
    bad = 0
    for r in refs:
        repo = PI_REPOS.get(r["repo"])
        if not repo:
            print(f"BAD    unknown repo {r['repo']!r}")
            bad += 1
            continue
        target = f"~/{repo}/{r['path']}"
        code, out = pi_run(f"grep -nF -- {shlex.quote(r['anchor'])} {target}")
        lines = [int(l.split(":", 1)[0]) for l in out.splitlines() if re.match(r"\d+:", l)]
        if not lines:
            print(f"MISSING {r['repo']}/{r['path']}:{r['line']}  {r['anchor']!r}")
            bad += 1
        elif len(lines) > 1:
            print(f"MULTI  {r['repo']}/{r['path']}:{r['line']}  {r['anchor']!r} at {lines}")
            bad += 1
        elif lines[0] != r["line"]:
            print(f"MOVED  {r['repo']}/{r['path']}:{r['line']} -> {lines[0]}  {r['anchor']!r}")
            bad += 1
        else:
            print(f"OK     {r['repo']}/{r['path']}:{r['line']}")
    print(f"\n{len(refs) - bad} ok, {bad} to fix (checked on the Pi tree)")
    return 1 if bad else 0


def cmd_check(args):
    if len(args) < 2:
        die("usage: tutorial.py check <id> <step>")
    note = find_note(args[0])
    _, checks = tutor_block(note.read_text())
    mine = [c for c in checks if c["step"] == args[1]]
    if not mine:
        die(f"No check for step {args[1]}. Steps with checks: {', '.join(c['step'] for c in checks)}")
    failed = 0
    for c in mine:
        reason = unsafe_reason(c["cmd"])
        if reason:
            print(f"REFUSED step {c['step']}: {reason}\n  {c['cmd']}")
            failed += 1
            continue
        code, out = pi_run(c["cmd"])
        ok = re.search(c["expect"], out) is not None
        failed += 0 if ok else 1
        print(f"{'PASS' if ok else 'FAIL'} step {c['step']}  expect /{c['expect']}/  (exit {code})")
        print("  $ " + c["cmd"])
        key = re.match(r'"(\w+)":', c["expect"])
        actual = re.search(rf'"{key.group(1)}":("[^"]*"|[^,}}]*)', out) if key else None
        if actual:
            print(f"  actual: {actual.group(0)}")
        else:
            snippet = out.strip().replace("\n", "\n  ")
            print("  " + (snippet[:300] + (" …" if len(snippet) > 300 else "")))
    return 1 if failed else 0


def cmd_log(args):
    if len(args) < 3:
        die("usage: tutorial.py log <id> <step> <event> [note…]\n"
            "events: started, done, hint1..hint4, stuck, skipped, finished, confirmed")
    note = find_note(args[0])
    tid = note_id(note) or note.stem
    step, event, text = args[1], args[2], " ".join(args[3:]).replace("|", "/")
    PROGRESS.mkdir(parents=True, exist_ok=True)
    p = progress_file(tid)
    if not p.exists():
        p.write_text(f"# {tid} progress\n\nNote: `{note.name}`. Written by `tutorial.py log`; "
                     "newest at the bottom.\n\n| When | Where | Step | Event | Note |\n| --- | --- | --- | --- | --- |\n")
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with p.open("a") as f:
        f.write(f"| {now} | {'pi' if ON_PI else 'mac'} | {step} | {event} | {text} |\n")
    rel = p.relative_to(KB)
    print(f"logged to {rel}. Commit: git -C {KB} add {rel} && git -C {KB} commit -m 'kb: {tid} progress'")


COMMANDS = {"list": cmd_list, "show": cmd_show, "refs": cmd_refs, "check": cmd_check, "log": cmd_log}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(2)
    if sys.argv[1] != "list" and len(sys.argv) < 3:
        die(f"usage: tutorial.py {sys.argv[1]} <id|name fragment> …")
    sys.exit(COMMANDS[sys.argv[1]](sys.argv[2:]) or 0)
