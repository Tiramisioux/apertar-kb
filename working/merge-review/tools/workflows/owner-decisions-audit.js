export const meta = {
  name: 'owner-decisions-audit',
  description: 'Collect every decision the owner recorded in the KB, then check each rework plan and the fixes made against them',
  phases: [
    { title: 'Collect', detail: 'two readers list every recorded owner decision in the knowledge base', model: 'opus' },
    { title: 'Audit', detail: 'one auditor per plan checks each commit against the recorded decisions', model: 'opus' },
  ],
}
const MR = '/home/user/apertar-kb/working/merge-review'
const KB = '/home/user/apertar-kb'
const HEAD = `You work on the merge review of the "cinemate port" of Apertar (camera software for the Raspberry Pi). Read ${MR}/BRIEF.md first (paths, vocabulary, writing rules). You do not change code and you do not commit.

WHY THIS TASK EXISTS. Patrik (the owner and contributor) recorded many decisions in his knowledge base (${KB}) while he designed the port's features: pages like ${KB}/working/controls/decisions.md and ${KB}/working/playback/decisions.md, question tables in design documents, "answer" and "handoff" pages, the fork log. The rework plans of this review (${MR}/design/*.md) were written from the code and the review findings, WITHOUT those pages. Two conflicts were already found by chance: a plan let the browser change [run_script] paths although Patrik decided "ssh only" (controls decision Q2), and a plan deleted the automatic inversion of a button that reads pressed at start although Patrik asked for it "like Cinemate" (controls decisions, note of 2026-10-29). His words for this review: mismatches are to be re-implemented the Apertar way, but "Some [new architecture] might be needed, but these are usually carefully considered (or are they?) by me, the contributor." So: a recorded decision of his is a carefully considered choice. It stays, unless it makes a STOCK camera (original driver, original 720x720 screen, a 1.6.0 hardware file, no port keys) behave differently from Apertar 1.6.0; then the feature must become something the operator turns on, not something that is removed.`

const AREAS = [
  { key: 'a', what: `${KB}/working/controls/ (all pages: decisions.md, design-controls*.md question tables, plan-summary*.md, critique-*.md, changes-from-critique.md), ${KB}/working/playback/ (decisions.md, design-playback.md question tables and option lists), ${KB}/working/handoff-boot-config.md, ${KB}/working/dual-sensor/ (decisions and constraints that touch today's code: env switches, per-instance files), ${KB}/tutorials/ (README.md and the tutorial list: what Patrik chose to build and why), ${KB}/fork-log.md` },
  { key: 'b', what: `everything else under ${KB}: ${KB}/working/*.md (the *-answer.md, handoff-*.md, *-request.md, clearhdr-*.md, ramp-*.md, storage-answer.md, sync.md, upstream-sync.md, distribution-image.md, sensor-capabilities.md, build-deploy.md and the rest), ${KB}/working/drop-frames/, ${KB}/working/dng-chain/, ${KB}/working/ramp-ladder/, ${KB}/working/research-30fps/, ${KB}/working/compare-raw/, ${KB}/working/port-raw/, ${KB}/lessons/, ${KB}/llm/, ${KB}/architecture/, ${KB}/README.md and the top-level pages. Skip ${KB}/working/merge-review/ (this review) and ${KB}/working/controls, playback, dual-sensor, tutorials (another reader has them)` },
]
phase('Collect')
const collected = await parallel(AREAS.map(a => () => agent(`${HEAD}

YOUR TASK: COLLECT. Read ${a.what}. List every decision, requirement, standing rule or constraint that came from Patrik himself (an answer to a numbered question, "the user asked", "Patrik:", "accepted", "wish", a rule he set, a fact about his camera such as "no touch screen"). Not the designs' own defaults unless he accepted them (then say "default accepted"). Grep widely first (grep -rn -i "patrik\\|the user\\|decision\\|decided\\|accepted\\|Q[0-9]\\+ \\|wish\\|asked for\\|standing rule" <folder>), then read the pages that hold them.

WRITE ${MR}/owner-recorded-decisions-${a.key}.md: a table with one row per decision: | id (D${a.key.toUpperCase()}-n) | date | topic (controls, hardware file, inputs, playback and clip browser, WebUI, touch UI, timecode, storage and write path, pre-roll, mode ladder, Clear HDR, camera modes and limits, boot config, drivers, commits and process, the rig itself) | the decision in one plain sentence | his words, quoted | source path:line |. Under the table: "## Facts about the owner's camera" (what hardware it has and lacks, which files and switches it runs with, as far as the KB says) and "## Standing rules for work on this code" (commit format, who types, what must be asked first). Be complete rather than brief: a missed decision is the failure here. Return the count and the ten decisions most likely to collide with a rework that pulls the port back toward original Apertar.`,
  { label: `collect:${a.key}`, phase: 'Collect', model: 'opus', schema: { type: 'object', properties: { count: { type: 'integer' }, file_written: { type: 'boolean' }, likely_collisions: { type: 'array', items: { type: 'string' } }, full_text: { type: 'string' } }, required: ['count', 'likely_collisions'] } })))

const PLANS = [
  { key: 'hardware-inputs', extra: 'A lane has already made commits 1, 2 and 3 of this plan (git -C /home/user/wt/lane-core3 log --oneline 56e135c..HEAD): judge them too. Commit 2 is already known to contradict Q2.' },
  { key: 'command-plane', extra: 'A lane is implementing commits 1, 2, 3, 4, 5, 8, 10 and 16 of this plan now (git -C /home/user/wt/lane-hdr log --oneline 56e135c..HEAD).' },
  { key: 'touch-ui', extra: 'A lane is implementing commits 1, 2, 3, 5, 7, 8, 11, 12, 13, 14, 15, 18, 21 and 23 of this plan now (git -C /home/user/wt/lane-ui1 log --oneline ac1fc28..HEAD); the Core commits 6, 9 and 10 are in /home/user/wt/lane-hdr. Mind that the owner has no touch screen: say for each commit how he can look at the result (HDMI and a mouse, or not at all).' },
  { key: 'camera-modes', extra: 'A lane is implementing commits 1, 2, 3, 4, 5, 8 and 9 now (git -C /home/user/wt/lane-core4 log --oneline 56e135c..HEAD). Commits 6, 7, 10, 11, 12 are held.' },
  { key: 'boot-config-helpers', extra: 'Not started.' },
  { key: 'storage-settings', extra: 'Not started. The lead plans one change to this plan: old hardware-file keys are taken over only while camera_settings.conf has no such key (read-only, no edit of the operator\'s file). Say whether a recorded decision speaks for or against that, and for or against removing the environment twins (the KB shows them used in test campaigns and in the dual-sensor design).' },
  { key: 'preroll', extra: 'Not started.' },
  { key: 'webui-state', extra: 'Not started. The Clip Browser, the Viewer and the Controls page were designed with the owner question by question (playback and controls decisions): check every header, button, dialog, list, icon and rename this plan changes against what he chose.' },
  { key: 'fixes-made', extra: `This audit is not of a plan but of the fixes already on the improvement branches: read ${MR}/fix-log.md (entries C1 to C14, U1 to U3, D2-1) and the commits (git -C /home/user/wt/core-work log --format='%h %s' 01f170c..HEAD ; git -C /home/user/wt/ui-work log --format='%h %s' 7ea9afc..HEAD), and ${MR}/owner-decisions.md (the review's open questions to the owner: say which of them a recorded decision already answers).` },
]
phase('Audit')
async function audit(p) {
  const target = p.key === 'fixes-made' ? `the fixes already made` : `the plan ${MR}/design/${p.key}.md (read it whole: target, commit plan, For the owner, What stays as new ground)`
  return agent(`${HEAD}

The recorded decisions were collected into ${MR}/owner-recorded-decisions-a.md and ${MR}/owner-recorded-decisions-b.md. Read both whole. Where a row matters for your plan, open its source page and read the surrounding text (the reason he gave is often there), and search the KB yourself for more on your theme (the collectors may have missed something: grep -rn -i '<keyword>' ${KB} --include=*.md | grep -v merge-review).

YOUR TASK: AUDIT ${target} against the owner's recorded decisions. ${p.extra}
For every commit (or fix): does it remove, reverse or change something Patrik decided or asked for? Does it rely on something his camera lacks (no touch screen, no IMU, a CM5 with a CFexpress hat and an HDMI monitor)? Would it break a script, a tutorial or a test campaign of his that the KB holds (${KB}/working/tools, ${KB}/working/drop-frames, ${KB}/tutorials)? For each conflict, design the smallest variant that keeps his decision AND leaves a stock camera behaving as Apertar 1.6.0 (usually: the behaviour becomes a setting that is off or at the 1.6.0 value by default; say which key or command, with the upstream precedent for its shape). Check the code where the variant depends on it (port tree with fixes: /home/user/wt/core-work, /home/user/wt/ui-work; original: /home/user/wt/core-upstream, /home/user/wt/ui-upstream).

${p.key === 'fixes-made' ? `WRITE ${MR}/design/decisions-audit-fixes-made.md` : `APPEND to ${MR}/design/${p.key}.md a section "## Checked against the owner's recorded decisions"`}: a table | commit | touches decision (id, his words) | verdict: fine / conflict / needs his answer | what changes in the commit |, then "Decisions this plan must keep" (a short list an implementer reads before starting), then "Open questions a recorded decision already answers" (question, the decision id, the answer). Return the structured summary.`,
    { label: `audit:${p.key}`, phase: 'Audit', model: 'opus', schema: { type: 'object', properties: {
      conflicts: { type: 'array', items: { type: 'object', properties: { commit: { type: 'string' }, decision: { type: 'string' }, problem: { type: 'string' }, variant: { type: 'string' }, already_committed: { type: 'boolean' } }, required: ['commit', 'decision', 'problem', 'variant'] } },
      fine: { type: 'integer' }, must_keep: { type: 'array', items: { type: 'string' } }, answered_questions: { type: 'array', items: { type: 'string' } }, summary: { type: 'string' } }, required: ['conflicts', 'summary'] } })
}
// two lanes, depth-first
const half = Math.ceil(PLANS.length / 2)
const lanes = [PLANS.slice(0, half), PLANS.slice(half)]
const out = await parallel(lanes.map(l => async () => { const r = []; for (const p of l) r.push({ key: p.key, audit: await audit(p) }); return r }))
return { collected, audits: out.flat() }
