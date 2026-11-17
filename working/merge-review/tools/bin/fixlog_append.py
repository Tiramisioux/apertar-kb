#!/usr/bin/env python3
"""Append fix-log entries for the commits an implementation lane produced.

  fixlog_append.py <workflow-run-dir-name> <repo-letter C|U|D5|D2> <first-number> <worktree-with-the-commits>

Reads the implementers' structured results (the newest result per item id) from the run's journal and writes one
entry per commit, in commit order, to the KB fix log. Prints the next free number.
"""
import json, subprocess, sys

WF = '/root/.claude/projects/-home-user/c92f0a57-d507-5425-af34-ea239a4bf210/subagents/workflows/'
LOG = '/home/user/apertar-kb/working/merge-review/fix-log.md'
REPO = {'C': 'Apertar-Core', 'U': 'Apertar-UI', 'D5': 'imx585-v4l2-driver', 'D2': 'imx283-v4l2-driver'}

def main():
    run, letter, n, wt = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    labels, results, reviews = {}, {}, {}
    for line in open(WF + run + '/journal.jsonl'):
        j = json.loads(line)
        if j.get('type') == 'started':
            labels[j['agentId']] = j.get('label', '')
        elif j.get('type') == 'result' and isinstance(j.get('result'), dict):
            label = labels.get(j['agentId'], '')
            r = j['result']
            if label.startswith(('impl:', 'fix:')) and r.get('status') == 'done' and r.get('sha'):
                results[r['id']] = r
            elif label.startswith('review:'):
                reviews[r.get('id', label[7:].split('#')[0])] = r
    # commit order as on the branch
    order = subprocess.run(['git', '-C', wt, 'log', '--reverse', '--format=%H %s', '-n', '60'], capture_output=True, text=True).stdout.splitlines()
    pos = {}
    for i, line in enumerate(order):
        pos[line.split(' ', 1)[0]] = (i, line.split(' ', 1)[1])
    def find(sha, subject=''):
        for full, v in pos.items():
            if full.startswith(sha[:7]):
                return full, v
        # a cherry-picked commit has a new sha: match the subject (its first 45 characters)
        for full, v in pos.items():
            if subject and v[1][:45] == subject[:45]:
                return full, v
        return None, (10 ** 6, '')
    items = []
    for fid, r in results.items():
        full, (i, subject) = find(r['sha'], r.get('subject', ''))
        if full:
            items.append((i, full, subject, fid, r))
        else:
            print('not on the branch, skipped:', fid, r['sha'])
    items.sort()
    out = []
    for i, full, subject, fid, r in items:
        rv = reviews.get(fid, {})
        out += ['', '---', '', f'## {letter}{n}. {subject}', '',
                f'{REPO[letter]} `{full[:7]}`. Finding: {fid}. Reviewed by a second agent: {rv.get("verdict", "not reviewed")}.', '']
        def part(title, key):
            v = r.get(key)
            if not v:
                return
            if isinstance(v, list):
                out.extend([f'**{title}**', ''] + [f'- {x}' for x in v] + [''])
            else:
                out.extend([f'**{title}** {v}' if '\n' not in v else f'**{title}**\n\n{v}', ''])
        part('What was there.', 'log_was')
        part('Why it is a problem.', 'log_why')
        part('How to spot it.', 'log_spot')
        part('Options.', 'log_options')
        part('Chosen, and why.', 'log_chosen')
        if r.get('log_after'):
            out.extend(['**After.**', '', '```', r['log_after'].strip('\n'), '```', ''])
        part('Checked.', 'log_checked')
        part('Rule.', 'log_rule')
        if rv.get('notes') and rv.get('verdict') == 'accept' and len(rv['notes']) < 0:
            out += [f'Reviewer: {rv["notes"]}', '']
        n += 1
    open(LOG, 'a').write('\n'.join(out) + '\n')
    print('appended', len(items), 'entries; next number', n)

if __name__ == '__main__':
    main()
