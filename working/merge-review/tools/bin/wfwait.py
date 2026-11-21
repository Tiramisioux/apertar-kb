#!/usr/bin/env python3
"""wfwait.py <max-seconds> <run-id> [<run-id> ...]
Blocks until one of the runs looks finished (no agent running and nothing written for 40 s), or the time is up.
Prints one status line per run."""
import json, os, sys, time, glob
B='/root/.claude/projects/-home-user/c92f0a57-d507-5425-af34-ea239a4bf210/subagents/workflows'
def state(w):
    order=[]; done=set()
    for line in open(os.path.join(B,w,'journal.jsonl')):
        try: j=json.loads(line)
        except Exception: continue
        if j.get('type')=='started': order.append((j.get('agentId'), j.get('label') or '?'))
        elif j.get('type')=='result': done.add(j.get('agentId'))
    age=time.time()-max(os.path.getmtime(f) for f in glob.glob(os.path.join(B,w,'*')))
    return order, done, age
def finished(w):
    o,d,age=state(w)
    return bool(o) and all(a in d for a,_ in o) and age>40
limit=float(sys.argv[1]); runs=sys.argv[2:]; t0=time.time()
while time.time()-t0<limit and not any(finished(w) for w in runs):
    time.sleep(15)
for w in runs:
    o,d,age=state(w)
    run=[l for a,l in o if a not in d]
    print(f"{w}: {'FINISHED' if finished(w) else 'running'}; {len(d)}/{len(o)} agents done; now: {', '.join(run) or '-'}; last: {o[-1][1] if o else '-'}")
print('waited', int(time.time()-t0), 's')
