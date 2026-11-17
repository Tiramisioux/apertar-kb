#!/usr/bin/env python3
"""Collect every agent result from the workflow journals into compact files under the KB's merge-review folder.

  aggregate.py            writes raw/_results.json (label -> newest result) and prints a status table
  aggregate.py hdr        also writes hdr12/DIGEST.md from the G* readers
  aggregate.py findings   also writes raw/FINDINGS.json and raw/FINDINGS.md (verified findings per unit and sweep)
                          and raw/FEATURES.json (features per unit from the inventories)
"""
import glob, json, os, sys

WF = '/root/.claude/projects/-home-user/c92f0a57-d507-5425-af34-ea239a4bf210/subagents/workflows'
MR = '/home/user/apertar-kb/working/merge-review'

def load():
    newest = {}   # label -> (mtime order index, result)
    for i, d in enumerate(sorted(glob.glob(WF + '/wf_*'), key=os.path.getmtime)):
        labels = {}
        try:
            lines = open(d + '/journal.jsonl').read().splitlines()
        except OSError:
            continue
        for n, line in enumerate(lines):
            try:
                j = json.loads(line)
            except ValueError:
                continue
            if j.get('type') == 'started':
                labels[j['agentId']] = j.get('label')
            elif j.get('type') == 'result' and j.get('result') is not None:
                label = labels.get(j['agentId'])
                if label:
                    newest[label] = ((i, n), j['result'], os.path.basename(d))
    return newest

def main():
    res = load()
    what = sys.argv[1] if len(sys.argv) > 1 else ''
    json.dump({k: v[1] for k, v in res.items()}, open(MR + '/raw/_results.json', 'w'))
    kinds = {}
    for label in sorted(res):
        kinds.setdefault(label.split(':')[0] if ':' in label else label.split('-')[0], []).append(label)
    for kind, labels in sorted(kinds.items()):
        print(f'{kind:10s} {len(labels):3d}  ' + ' '.join(l.split(":", 1)[-1] for l in labels)[:400])

    if what == 'hdr':
        out = ['# Digest of the nine 12-bit Clear HDR reader reports', '',
               'Built from the readers\' structured results. Full notes: the G*.md files beside this one.', '']
        for label in sorted(l for l in res if l.startswith('G') and '-' in l and l[1].isdigit()):
            g = res[label][1]
            out += [f'## {label} ({g.get("report_path", "")})', '', g.get('summary', ''), '']
            for f in g.get('findings', []):
                out.append(f'- **{f.get("id")}** ({f.get("status")}, could cause it: {f.get("could_cause_strange_output")}) {f.get("claim")}')
                out.append(f'  - symptom: {f.get("symptom")}')
                ev = f.get('evidence') or []
                if ev: out.append('  - evidence: ' + ' | '.join(ev[:4]))
                if f.get('settle_with'): out.append(f'  - settle with: {f.get("settle_with")}')
            if g.get('open_questions'):
                out += ['', 'Open: ' + ' ; '.join(g['open_questions'])]
            out.append('')
        open(MR + '/hdr12/DIGEST.md', 'w').write('\n'.join(out))
        print('wrote hdr12/DIGEST.md', len(out), 'lines')

    if what == 'findings':
        units, sweeps, feats = {}, {}, {}
        sweep_keys = {'knobs', 'board-support', 'stock-behaviour', 'protocol-security', 'state-consistency', 'slop',
                      'commits-core-1', 'commits-core-2', 'commits-ui-drivers'}
        for label, (_, r, wf) in res.items():
            kind, _, key = label.partition(':')
            if kind == 'inv':
                feats[key] = {'report': r.get('report_path'), 'summary': r.get('summary'), 'features': r.get('features', []),
                              'upstream_code_changed': r.get('upstream_code_changed', []), 'new_abstractions': r.get('new_abstractions', []),
                              'removed_or_narrowed': r.get('removed_or_narrowed', []), 'board_assumptions': r.get('board_assumptions', [])}
            elif kind in ('rev', 'verify') and key not in sweep_keys and not (key[:1] == 'H' and key[1:].isdigit()):
                cur = units.get(key)
                if kind == 'verify' or cur is None:
                    units[key] = {'verified': kind == 'verify', 'report': r.get('report_path'), 'summary': r.get('summary'),
                                  'conforms': r.get('conforms', []), 'abstraction_verdicts': r.get('abstraction_verdicts', []),
                                  'findings': r.get('findings', [])}
            elif kind in ('sweep', 'verify') and key in sweep_keys:
                cur = sweeps.get(key)
                if kind == 'verify' or cur is None:
                    sweeps[key] = {'verified': kind == 'verify', 'report': r.get('report_path'), 'summary': r.get('summary') or (cur or {}).get('summary'),
                                   'findings': r.get('findings', [])}
        json.dump({'units': units, 'sweeps': sweeps}, open(MR + '/raw/FINDINGS.json', 'w'), indent=1)
        json.dump(feats, open(MR + '/raw/FEATURES.json', 'w'), indent=1)
        rows = ['# All review findings, one line each', '',
                'Built from the agents\' structured results (after the skeptic where it ran). Full text: the report named per group.', '']
        total = 0
        sev_order = {'blocker': 0, 'major': 1, 'minor': 2, 'nit': 3}
        for name, group in (('Unit', units), ('Sweep', sweeps)):
            for key in sorted(group):
                g = group[key]
                rows += [f'## {name} {key} ({"verified" if g["verified"] else "NOT verified"}; {g.get("report")})', '',
                         '| id | sev | category | effort | deliberate | title | where |', '| --- | --- | --- | --- | --- | --- | --- |']
                for f in sorted(g['findings'], key=lambda f: sev_order.get(f.get('severity'), 9)):
                    total += 1
                    where = '; '.join((f.get('where') or [])[:2]).replace('|', '/')
                    rows.append(f'| {f.get("id")} | {f.get("severity")} | {f.get("category")} | {f.get("effort", "")} | {f.get("deliberate", "")} | {str(f.get("title", "")).replace("|", "/")} | {where} |')
                rows.append('')
        open(MR + '/raw/FINDINGS.md', 'w').write('\n'.join(rows))
        nsev = {}
        for g in list(units.values()) + list(sweeps.values()):
            for f in g['findings']:
                nsev[f.get('severity')] = nsev.get(f.get('severity'), 0) + 1
        print(f'units {len(units)} ({sum(1 for u in units.values() if u["verified"])} verified), sweeps {len(sweeps)}, inventories {len(feats)}, findings {total}: {nsev}')

if __name__ == '__main__':
    main()
