# Tools of the merge review (saved copies)

The scripts that ran this campaign. They were written for the review container (paths under `/home/user/...`), so
they are a record and a starting point, not something to run as they are on another machine.

| Folder | Holds |
| --- | --- |
| `bin/` | The checks every fix must pass, and helpers for the reports |
| `workflows/` | The scripts that drive the worker agents (one script per kind of step) |

## bin

| Script | What it does |
| --- | --- |
| `check_core.sh <core-tree> <tag> [lc\|nolc\|both] [tests]` | The gate for Core: builds with and without libcamera (`-Wall -Wextra`, ccache), then compiles and runs the host tests in `tools/` |
| `check_ui.sh <ui-tree> <tag>` | The gate for the touch UI: Qt 6 build with the QML compiled ahead of time |
| `smoke_core.sh <apertar-core binary> <port> [outfile]` | Starts Core with `--simulate` and prints the shape of its main replies (field names and types), so two builds can be diffed |
| `finding.py <id> ...` / `--grep <regex>` / `--unit <unit>` | Prints verified review findings from `raw/FINDINGS.json` |
| `design_final.py <run> [theme]` | Prints the final commit plan a design run returned |
| `fixlog_append.py <run> <C\|U\|D5\|D2> <first-number> <worktree>` | Writes `fix-log.md` entries from the implementers' notes of one lane |
| `aggregate.py` | Collects the reviewers' results into `raw/FINDINGS.*` and `raw/FEATURES.json` |
| `check_map.js` | Checks every quoted code line of the coding map against the tree it claims to quote |
| `wfstat.py`, `wfwait.py` | Status of the running agent workflows |

## workflows

| Script | Step |
| --- | --- |
| `conventions-v2.js`, `conventions-synth.js` | How original Apertar 1.6.0 is built: eight topic studies, each challenged, then one audited page |
| `port-review-v2.js` | The unit review: inventory, review against the original, skeptic, per unit |
| `sweeps-v2.js` | The whole-port sweeps (knobs, boards, stock behaviour, protocol, state, slop, commits) |
| `hdr-gather-v2.js`, `hdr-conclude.js` | The 12-bit Clear HDR investigation |
| `coding-map-v2.js`, `map-fix.js` | Coding map: check, then apply and re-check |
| `findings-synth.js` | Fix list, feature list and owner decisions from the findings |
| `design.js` | One large rework: design, challenge, final commit plan |
| `owner-decisions-audit.js` | Every plan and fix checked against the decisions recorded in this KB |
| `implement.js` | One lane of fixes: implement, gate, review, up to two fix rounds, one commit per item |
