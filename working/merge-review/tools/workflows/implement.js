export const meta = {
  name: 'port-fix-lane',
  description: 'Implement one lane of fix items on the improvement branch: implement, gate, review, one commit per item',
  phases: [
    { title: 'Implement', detail: 'one fix item at a time in the lane worktree, in the original code\'s style', model: 'opus' },
    { title: 'Review', detail: 'a second agent reads the commit against the item and the conventions', model: 'opus' },
  ],
}
const MR = '/home/user/apertar-kb/working/merge-review'
// args: { lane: 'cam', repo: 'core'|'ui', worktree: '/home/user/wt/lane-cam', items: [{ id, domain_file, title }], notes: '' }
const lane = args.lane, repo = args.repo, wt = args.worktree
const isCore = repo === 'core'
const gate = isCore
  ? `/home/user/build/bin/check_core.sh ${wt} lane-${lane} both tests   (prints PASS/FAIL lines; builds with and without libcamera with -Wall -Wextra and runs the host tests; uses ccache, so only changed files recompile)`
  : `/home/user/build/bin/check_ui.sh ${wt} lane-${lane}   (prints PASS/FAIL; builds the Qt UI with QML compiled ahead of time)`
const upstream = isCore ? '/home/user/wt/core-upstream' : '/home/user/wt/ui-upstream'
const COMMON = `You are implementing fixes for Patrik's Apertar camera project. First read ${MR}/BRIEF.md (paths, vocabulary, rules) and ${MR}/apertar-conventions.md (how ORIGINAL Apertar 1.6.0 is built: the yardstick; cite its rule ids). The cinemate port is being made mergeable into Apertar main: where the port did something its own way, the code is reworked to follow the original developer's patterns. Minimal, local changes in the style of the surrounding ORIGINAL code. No new layers, no new files unless the item says so, no drive-by clean-ups, no reformatting.

YOUR WORKSPACE (differs from the BRIEF's read-only rule: here you DO edit, in this worktree only): ${wt} , a git worktree of the ${isCore ? 'Apertar-Core' : 'Apertar-UI'} improvement line (branch lane/${lane}). Original code for comparison: ${upstream}. Never touch /home/user/Apertar-Core, /home/user/Apertar-UI or any other worktree. Never push. Never change git config. No git stash, no rebase, no reset --hard, no checkout of other branches.

THE GATE, run it before every commit: ${gate}
A commit goes in only when the gate prints no FAIL line. New warnings in a file you touched count as failures: fix them.
${isCore ? `The WebUI can be tried for real: ${wt} builds to /home/user/build/lane-${lane}-lc/apertar-core ; start it with  HOME=/home/user/build/sim timeout 120 /home/user/build/lane-${lane}-lc/apertar-core --simulate --socket /home/user/build/sim/${lane}.sock --media /home/user/build/sim/media --web-bind 127.0.0.1 --web-port <a free port 8100-8199> &  and drive the page with Playwright (node, require('playwright'), chromium.launch(), page.goto(url, { waitUntil: 'domcontentloaded' })) or curl -s -X POST http://127.0.0.1:<port>/api/command -d '{"cmd":"get_state"}'. Do that for any change to the WebUI page or to a socket command or state field. Kill the process when done. This machine has no camera, no GPIO chips and no /media/RAW.` : `Nothing can be run on a screen here; say so under Tested.`}

COMMIT MESSAGE, house format: subject "<area>: <what changed, in plain words>" (areas as the original code and the port use them: core, camera, rec, cdng, mlv, audio, media, hw, web, ui, qml, scripts, build, docs; lower case, no trailing dot, at most about 72 characters, no tutorial or ticket numbers). Body: "Why:" (what was wrong, how original Apertar does it), "What:" (what the code does now), "Tested:" (what you ran here; what still needs the camera, with the command). Plain ASCII. End the message with exactly these two trailer lines:
Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01NEFc1w7Y8dcyiV489BiwMr
Commit with: git -C ${wt} add -A && git -C ${wt} commit -q -F <message file>   (write the message to a file under /home/user/build/sim/ first).
${args.notes || ''}`

const IMPL_SCHEMA = { type: 'object', properties: {
  id: { type: 'string' }, status: { type: 'string', enum: ['done', 'skipped', 'blocked'] },
  sha: { type: 'string' }, subject: { type: 'string' }, files: { type: 'array', items: { type: 'string' } },
  summary: { type: 'string', description: 'What changed, three sentences' },
  reason: { type: 'string', description: 'For skipped or blocked: why, and what is needed' },
  gate: { type: 'string', description: 'The gate lines as printed' },
  log_was: { type: 'string', description: 'Fix-log part: what the port did, with path:line@cinemate-port and at most 8 lines of the old code' },
  log_why: { type: 'string', description: 'Why it is a problem and how original Apertar does it (path:line@upstream-1.6.0 or a conventions rule id)' },
  log_spot: { type: 'string', description: 'How to spot this kind of problem: a grep, a question, a smell' },
  log_options: { type: 'array', items: { type: 'string' }, description: 'The ways it could be fixed, one line each with its cost' },
  log_chosen: { type: 'string', description: 'Which option and the reasoning; what was given up' },
  log_after: { type: 'string', description: 'At most 8 lines of the new code' },
  log_checked: { type: 'string', description: 'What was run here and what still needs the camera, with the command' },
  log_rule: { type: 'string', description: 'The one-line rule to take away' },
}, required: ['id', 'status', 'summary'] }
const REVIEW_SCHEMA = { type: 'object', properties: { id: { type: 'string' }, verdict: { type: 'string', enum: ['accept', 'fix-needed', 'reject'] },
  issues: { type: 'array', items: { type: 'string' } }, notes: { type: 'string' } }, required: ['id', 'verdict', 'issues'] }

const out = []
for (const item of args.items) {
  const brief = `FIX ITEM ${item.id}: ${item.title}\nThe full item (problem, Apertar way, rework steps, how to check) is the section "${item.id}" of ${MR}/${item.domain_file}. Read it, and the findings it lists as sources (in ${MR}/raw/rev-*.md or sweep-*.md, sections "Final findings") where you need more.${item.extra ? '\nNOTE FROM THE LEAD: ' + item.extra : ''}`
  let impl = await agent(`${COMMON}\n\n${brief}\n\nDo this ONE item and nothing else. Steps: (1) read the item and open the code on both sides (port worktree and original); confirm the problem is as described at the current tip (earlier items of this lane may have changed the lines). If the item turns out wrong, already fixed, or needs a decision only the owner can make, do not force it: return status skipped or blocked with the reason, and leave the tree clean (git -C ${wt} status --short must be empty). (2) Make the change the way the item's rework says, adapted to what the code needs; follow the surrounding original code's style exactly (indentation, naming, error strings as full sentences, log prefixes). (3) Run the gate. (4) Commit (one commit). (5) Return the result with the fix-log parts filled in, written for an intermediate coder (knows C++, cameras and git; newer to this code base and to Qt/QML): short sentences, the C++ or Qt idea named in a line where the fix leans on one.`,
    { label: `impl:${item.id}`, phase: 'Implement', schema: IMPL_SCHEMA, model: 'opus' })
  if (!impl) { log(`${item.id}: implementer failed`); out.push({ id: item.id, status: 'failed' }); continue }
  if (impl.status !== 'done' || !impl.sha) { log(`${item.id}: ${impl.status} (${(impl.reason || '').slice(0, 140)})`); out.push(impl); continue }
  let review = null
  for (let round = 0; round < 2; ++round) {
    review = await agent(`${COMMON}\n\nYOU ARE THE REVIEWER of one commit, not its author. ${brief}\n\nThe commit: git -C ${wt} show ${impl.sha} (read the whole diff, and the files around it). Judge: (1) Does it do what the item asks, completely, and nothing else (no unrelated edits, no reformatting, no new abstractions)? (2) Is it correct: follow every changed path, look for broken callers (grep), changed behaviour the item did not ask for, a default that differs from original Apertar 1.6.0, state fields or keys left half renamed, threads and locks. (3) Does it read like the surrounding original code (compare with ${upstream})? (4) Is the commit message true, in the house format, with both trailer lines? (5) Run the gate yourself. Verdict accept only if you would merge it as is. For fix-needed list each issue with file:line and what to do; do not fix anything yourself and leave the tree as it is.`,
      { label: `review:${item.id}${round ? '#2' : ''}`, phase: 'Review', schema: REVIEW_SCHEMA, model: 'opus' })
    if (!review || review.verdict !== 'fix-needed') break
    const fix = await agent(`${COMMON}\n\n${brief}\n\nYour commit ${impl.sha} for this item was reviewed and needs fixes:\n${review.issues.map((x, i) => `${i + 1}. ${x}`).join('\n')}\n\nCheck each point against the code; fix what is right (say so where the reviewer is wrong). Keep it ONE commit: make the changes, run the gate, then git -C ${wt} add -A && git -C ${wt} commit -q --amend -F <message file> (update the message if needed, keep the trailers). Return the result again in full with the new sha.`,
      { label: `fix:${item.id}`, phase: 'Implement', schema: IMPL_SCHEMA, model: 'opus' })
    if (fix && fix.sha) impl = fix
    else break
  }
  out.push({ ...impl, review: review ? { verdict: review.verdict, issues: review.issues, notes: review.notes || '' } : null })
  log(`${item.id}: ${impl.status} ${impl.sha || ''} review ${review ? review.verdict : 'none'}`)
}
return out
