#!/usr/bin/env python3
"""design_final.py <run-id> [key]   print the final plan(s) a design workflow returned"""
import json, sys
B='/root/.claude/projects/-home-user/c92f0a57-d507-5425-af34-ea239a4bf210/subagents/workflows/'
labels={}
want=sys.argv[2] if len(sys.argv)>2 else None
for line in open(B+sys.argv[1]+'/journal.jsonl'):
    j=json.loads(line)
    if j.get('type')=='started': labels[j['agentId']]=j.get('label')
    if j.get('type')=='result' and labels.get(j['agentId'],'').startswith('final:'):
        key=labels[j['agentId']][6:]
        if want and key!=want: continue
        r=j['result']
        print('#'*8, key, '| file_written:', r.get('file_written'), '| commits:', len(r.get('commits') or []))
        print('SUMMARY:', r.get('summary','')[:3000])
        for c in r.get('commits') or []:
            print(f"\n[{c.get('n')}] ({c.get('repo')}) {c.get('subject')}   -{c.get('removes')} +{c.get('adds')}  deps: {c.get('depends_on','')}")
            print('    what:', (c.get('what') or '')[:520])
            if c.get('risk'): print('    risk:', c['risk'][:260])
            if c.get('check_pi'): print('    pi:', c['check_pi'][:200])
        print('\nNEW GROUND:'); [print('  -', x[:300]) for x in r.get('new_ground') or []]
        print('\nOWNER:'); [print('  ?', (d.get('question') or '')[:260], '\n     ->', (d.get('recommendation') or '')[:260]) for d in r.get('owner_decisions') or []]
        print('\nRISKS:'); [print('  !', x[:300]) for x in r.get('risks') or []]
        print('\nNOT COVERED:'); [print('  x', x[:200]) for x in r.get('not_covered') or []]
