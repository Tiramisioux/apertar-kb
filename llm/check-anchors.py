#!/usr/bin/env python3
"""Check that every grep anchor in the llm/ maps still matches the Apertar source.

Reads the markdown tables in llm/*.md whose header has a column named "Anchor" or "Grep anchor",
takes the first `backticked` string of that cell and counts literal hits across the three repos.
An anchor is OK when at least one file contains it exactly once (anchors are unique per file).

  python3 check-anchors.py            # report BROKEN (0 hits) and MULTI (no file has exactly 1 hit) anchors
  python3 check-anchors.py --all      # also list the OK ones

Run after an upstream merge. A BROKEN anchor means the chapter moved or was rewritten: re-grep it
and fix the row. MULTI is often expected (the row says so, e.g. "3 hits, one per input class").
Works on the Mac (~/Documents/Apertar/<Mac names>) and on the Pi (~/ApertarCore, ~/ApertarUI,
~/drivers/imx585-v4l2-driver). Read-only: it never edits a file.
"""
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("APERTAR_LOCAL_ROOT", Path.home() / "Documents" / "Apertar"))
REPOS = ["Apertar-Core", "Apertar-UI", "imx585-v4l2-driver"]
if not (ROOT / REPOS[0]).is_dir() and (Path.home() / "ApertarCore").is_dir():  # on the Pi
    ROOT = Path.home()
    REPOS = ["ApertarCore", "ApertarUI", "drivers/imx585-v4l2-driver"]
SKIP_DIRS = {".git", "build", "mesa-minimal", "third_party", "node_modules"}
EXTS = {".cpp", ".hpp", ".h", ".c", ".qml", ".js", ".sh", ".txt", ".dts", ".conf", ".qrc"}


def load_sources():
    texts = {}
    for repo in REPOS:
        base = ROOT / repo
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for name in filenames:
                path = Path(dirpath) / name
                if path.suffix in EXTS or name == "CMakeLists.txt":
                    try:
                        texts[str(path.relative_to(ROOT))] = path.read_text(errors="replace")
                    except OSError:
                        pass
    return texts


def split_row(line):
    cells = re.split(r"(?<!\\)\|", line.strip().strip("|"))
    return [c.strip().replace("\\|", "|") for c in cells]


def anchors_in(md_path):
    col = None
    for lineno, line in enumerate(md_path.read_text().splitlines(), 1):
        if not line.lstrip().startswith("|"):
            col = None
            continue
        cells = split_row(line)
        if col is None:
            lowered = [c.lower() for c in cells]
            for name in ("grep anchor", "anchor"):
                if name in lowered:
                    col = lowered.index(name)
                    break
            continue
        if col >= len(cells) or set(cells[0]) <= set("-: "):
            continue
        m = re.search(r"`([^`]+)`", cells[col])
        if m and not re.search(r"<[A-Za-z]+>", m.group(1)):  # <name> = a pattern, not a literal
            yield lineno, m.group(1), cells[col]


def main():
    show_all = "--all" in sys.argv
    sources = load_sources()
    broken = multi = ok = 0
    for md in sorted(HERE.glob("*.md")):
        for lineno, anchor, cell in anchors_in(md):
            hits = [f for f, t in sources.items() if anchor in t]
            count = sum(sources[f].count(anchor) for f in hits)
            where = f"{md.name}:{lineno}"
            if count == 0:
                broken += 1
                print(f"BROKEN {where}  {anchor!r}")
            elif not any(sources[f].count(anchor) == 1 for f in hits) and "hit" not in cell:
                multi += 1
                print(f"MULTI  {where}  {anchor!r}  {count} hits in {', '.join(hits[:3])}")
            else:
                ok += 1
                if show_all:
                    print(f"OK     {where}  {anchor!r}  {hits[0]}")
    print(f"\n{ok} ok, {multi} multi, {broken} broken (sources: {len(sources)} files under {ROOT})")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
