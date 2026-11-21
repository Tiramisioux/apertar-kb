#!/usr/bin/env python3
"""finding.py <id> [<id> ...]      print findings in full
   finding.py --grep <regex>      one line per finding whose id, title, where or detail matches
   finding.py --unit <unit>       one line per finding of a unit or sweep"""
import json, re, sys
D = json.load(open('/home/user/apertar-kb/working/merge-review/raw/FINDINGS.json'))
rows = []
for grp in ('units', 'sweeps'):
    for u, v in D[grp].items():
        for f in v.get('findings', []):
            rows.append((u, f))
def line(u, f):
    return f"{f.get('severity','?'):8} {f.get('category','?'):28} {str(f.get('effort','')):3} {f['id']:34} {f['title']}"
def full(u, f):
    out = [f"===== {f['id']} | {f.get('severity')} | {f.get('category')} | effort {f.get('effort')} | deliberate: {f.get('deliberate')} | unit {u}"]
    for k in ('title', 'where', 'detail', 'port_way', 'apertar_way', 'why_it_matters', 'fix', 'rework', 'rework_risk', 'deliberate_evidence'):
        if f.get(k):
            out.append(f"-- {k}: " + (f[k] if isinstance(f[k], str) else json.dumps(f[k])))
    return "\n".join(out)
a = sys.argv[1:]
if not a:
    print(__doc__); sys.exit(0)
if a[0] == '--grep':
    rx = re.compile(a[1], re.I)
    for u, f in rows:
        if rx.search(json.dumps(f)):
            print(line(u, f))
elif a[0] == '--unit':
    for u, f in rows:
        if u == a[1] or f['id'].startswith(a[1]):
            print(line(u, f))
else:
    idx = {f['id']: (u, f) for u, f in rows}
    for i in a:
        print(full(*idx[i]) if i in idx else f"no finding {i}")
