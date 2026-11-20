#!/usr/bin/env python3
"""shape_subset.py <base smoke file> <new smoke file>
Every reply field in the base (for example the 1.6.0 smoke output) must exist in the new one with the same type.
Prints each missing or retyped field; exit 1 if any. Lists (e.g. "3 x int") compare by element type only."""
import json, re, sys
def load(p):
    out, title, buf = {}, None, []
    for line in open(p):
        if line.startswith('== '):
            if title is not None: out[title] = ''.join(buf)
            title = re.sub(r' -> .*', '', line[3:].strip()); buf = []
        else:
            buf.append(line)
    if title is not None: out[title] = ''.join(buf)
    res = {}
    for t, b in out.items():
        try: res[t] = json.loads(b)
        except ValueError: res[t] = None
    return res
def walk(a, b, path, bad):
    if isinstance(a, dict):
        if not isinstance(b, dict):
            bad.append(f'{path}: was object, now {type(b).__name__}'); return
        for k, v in a.items():
            if k not in b: bad.append(f'{path}.{k}: missing')
            else: walk(v, b[k], f'{path}.{k}', bad)
    elif isinstance(a, list):
        ea = a[0].split(' x ')[-1] if a and isinstance(a[0], str) else None
        eb = b[0].split(' x ')[-1] if isinstance(b, list) and b and isinstance(b[0], str) else None
        if not isinstance(b, list): bad.append(f'{path}: was list, now {b!r}')
        elif ea not in (None, 'empty') and eb not in (None, 'empty') and ea != eb: bad.append(f'{path}: list of {ea}, now of {eb}')
    else:
        if a != b and not (a in ('int', 'float') and b in ('int', 'float')): bad.append(f'{path}: {a} -> {b}')
base, new = load(sys.argv[1]), load(sys.argv[2])
bad = []
for t, a in base.items():
    if a is None: continue
    if t not in new: bad.append(f'{t}: reply missing'); continue
    if isinstance(a, dict) and a.get('ok') == 'bool' and 'error' in a and len(a) <= 3: continue   # base refused it too
    walk(a, new[t], t, bad)
print('\n'.join(bad) if bad else 'every base field present with the same type')
sys.exit(1 if bad else 0)
