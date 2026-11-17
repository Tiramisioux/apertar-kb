#!/usr/bin/env python3
"""wfstat.py [run-id ...]   one line per workflow run: + finished agent, ~ running agent (default: runs written to in the last 7 min)"""
import json, os, sys, time, glob
B='/root/.claude/projects/-home-user/c92f0a57-d507-5425-af34-ea239a4bf210/subagents/workflows'
runs=sys.argv[1:] or [os.path.basename(p) for p in glob.glob(B+'/wf_*') if time.time()-max([os.path.getmtime(f) for f in glob.glob(p+'/*')] or [0])<420]
for w in sorted(runs, key=lambda r: os.path.getmtime(os.path.join(B,r))):
    order=[]; done=set()
    for line in open(os.path.join(B,w,'journal.jsonl')):
        try: j=json.loads(line)
        except Exception: continue
        if j.get('type')=='started': order.append((j.get('agentId'), j.get('label')))
        elif j.get('type')=='result': done.add(j.get('agentId'))
    age=int(time.time()-max(os.path.getmtime(f) for f in glob.glob(os.path.join(B,w,'*'))))
    print(f"{w} last write {age}s ago: "+' '.join(('+' if a in done else '~')+str(l) for a,l in order))
