export const meta = {
  name: 'rework-design',
  description: 'Design the Apertar-way rework of one or two mismatch themes: design, challenge, final plan',
  phases: [
    { title: 'Design', detail: 'read the mechanism and the upstream precedent, write the plan', model: 'opus' },
    { title: 'Challenge', detail: 'a second reader attacks the plan against the code', model: 'opus' },
    { title: 'Final', detail: 'the plan is revised and returned as a commit list', model: 'opus' },
  ],
}
const MR = '/home/user/apertar-kb/working/merge-review'
const themes = (args && args.themes) || []
const ALL = (args && args.all_themes) || ''

const COMMON = t => `You work on the merge review of the "cinemate port" of Apertar (camera software for the Raspberry Pi). Read ${MR}/BRIEF.md first and follow it (paths, vocabulary, the writing rules). In this task you do NOT change code and you do not commit. You only write the one page named below.

THE THEME: ${t.title}
THE QUESTION TO ANSWER: ${t.question}

THE FINDINGS behind it (each was verified by a reviewer and a skeptic): ${t.ids.join(', ')}.
Print them in full: python3 /home/user/build/bin/finding.py <id> [<id> ...]
Find the smaller ones on the same mechanism and take them along: python3 /home/user/build/bin/finding.py --grep '<regex>'   (one line each; --unit <unit> lists one unit). Unit reports: ${MR}/raw/rev-<unit>.md, section "## Final findings" (units for this theme: ${t.units.join(', ')}). Sweeps: ${MR}/raw/sweep-<key>.md.

THE YARDSTICK: ${MR}/apertar-conventions.md: the original developer's rules (CMD-, CAM-, WEB-, HW-, UIC-, QML-, PLT-, STY-) and recipes R1 to R14, with evidence. Read the parts that govern this theme.

THE CODE
- Original Apertar 1.6.0 (the measuring stick): /home/user/wt/core-upstream and /home/user/wt/ui-upstream.
- The port with the fixes made so far (design against THIS tree): /home/user/wt/core-work and /home/user/wt/ui-work. "git -C /home/user/wt/core-work log --oneline 01f170c..HEAD" lists fixes already made (do not plan them again). More small fixes are being made in parallel on other branches: the pre-roll default (now off), the Lossy DNG page-cache drop, the preview TDN strip limited to raw formats, test_input refusing script actions, three 12-bit Clear HDR defects. Treat those as done.
- Drivers: /home/user/imx585-v4l2-driver, /home/user/imx283-v4l2-driver (baselines in BRIEF.md).
- Finished fixes are logged, with reasoning, in ${MR}/fix-log.md. It shows the style of fix that is wanted.

THE OWNER'S WORDS: "instead of just informing about architectural changes, I would need you to fully try to implement any mismatches in an apertar type way, instead of enforcing new architecture into Apertar. Some might be needed, but these are usually carefully considered (or are they?) by me, the contributor." And: "from my tests on my CM5 raspberry pi everything worked. But we would need to make sure all changes are compatible with other Pi models as well."

OTHER THEMES designed at the same time by other people (name a dependency when you have one, do not design their part): ${ALL}`

const RULES = `WHAT THE DESIGN MUST HOLD TO
1. Read the mechanism in the port code yourself, end to end, before you design: who writes each value, who reads it, on which thread, under which lock, what is saved in which file, what the WebUI and the touch UI show. Do not design from the findings' wording.
2. For each thing the port does differently, find how original 1.6.0 solves the same kind of problem (the precedent: file:line in the upstream trees) and give the port's feature that shape. Where upstream has no precedent at all, say so plainly: that is new ground. New ground is kept as small and as plain as the nearest upstream pattern allows, and goes on the owner's list.
3. The features stay and the rig keeps working: the owner's camera (CM5, IMX585, CFexpress hat, HDMI monitor) must be able to behave as it does today, by settings. A stock camera (original driver, original 720x720 screen, no keys the port invented in any file) must behave as 1.6.0 does until the operator turns a port feature on.
4. Files on existing cameras keep working. A key that moves to another file or section is still read from the old place; say how the old key is taken over and when it is written to the new place, the way upstream takes over old values when it loads a file.
5. The plan is a series of small commits. After each commit the tree builds with and without libcamera, the host tests in tools/ pass, and every field original 1.6.0 publishes in its replies is still there with the same type. One idea per commit. Subject in the port's style: "area: what the code does now" (for example "core: the automatic storage pre-roll is off by default"). Order them so the camera works after each one.
6. Prefer moving and deleting over adding. No new class, file, registry, helper layer or config system unless you name the upstream precedent for it. Estimate for each commit the lines removed and added.
7. Each commit must be small enough for one programmer to do in one sitting and for a reviewer to read in ten minutes. Split anything larger. If a step cannot be made safe without the camera, say what exactly is unsafe and give the smallest safe version.
8. What can be checked in this container: both builds, the 17 host tests, "apertar-core --simulate" serving the WebUI on a port (curl the JSON, drive the page with headless Chromium), the touch UI build. What needs the Pi: say the exact command or operator step and what to look for.`

const DESIGN = t => `${COMMON(t)}

${RULES}

WRITE ${MR}/design/${t.key}.md with exactly these sections:
"# ${t.title}: design" then one line: which tree and commit you read.
"## In short": ten lines at most: what is wrong today, what it becomes, how many commits.
"## How it works in the port today": the mechanism, as a table (value or path | who writes | who reads | thread and lock | file it is saved in | shown where), each row with file:line.
"## How original Apertar does this kind of thing": the precedents, file:line in the upstream trees, two or three lines each.
"## The target": where each value lives, who owns it, which command sets it, how it reaches the state replies and both UIs. A before/after table.
"## Commit plan": numbered commits. For each: subject line; repo; files and functions touched; what moves, what is deleted, what is added; lines removed and added (estimate); how to check it here; what only a Pi can show; what it depends on.
"## What stays as new ground": features with no upstream precedent, the shape they keep, and why that shape.
"## For the owner": decisions only the owner can make. Each: the question, the options, your recommendation and what it costs.
"## Risks and what was not determined".
"## Findings covered": finding id -> commit number, or "not covered" with the reason.
Write for an intermediate programmer who knows the camera but not every corner of this code: say what a mechanism does before you name it. Then return the summary asked for.`

const CHALLENGE = t => `${COMMON(t)}

A designer has written ${MR}/design/${t.key}.md: a plan to rework this theme the Apertar way. YOU ARE THE CHALLENGER. Your job is to find what is wrong with the plan before anyone implements it. Check it against the code, not against its own words.

${RULES}

ATTACK IT ON THESE POINTS
a. Precedent: open every upstream file:line the design cites. Does original Apertar really do it that way? Is there a closer precedent the designer missed? Is something called "the Apertar way" that original Apertar never does?
b. The mechanism: re-read the port code for each row of "How it works today". What reader, writer, thread, lock, file or UI did the design miss? (grep for every name it moves or deletes: who else uses it, in Core, the WebUI string, the touch UI, the scripts, the tests.)
c. Behaviour: for each commit, what does the rig lose or see change? What does a stock camera see change? Does an existing apertar-hardware.conf, camera_settings.conf or UI.conf still load and mean the same?
d. Order and size: does the tree build and work after every commit? Which commit is too big for one sitting? Which two commits are really one idea? Which commit adds more than it removes without a named precedent?
e. Simpler: is there a smaller change that reaches the same Apertar shape? Is anything in the plan itself a new abstraction?
f. The owner's list: is a decision hidden inside a commit that the owner should make? Is something on the owner's list that the code already settles?
g. What could not be checked without the camera, and is the Pi check named for it precise enough to run?

APPEND to ${MR}/design/${t.key}.md a section "## Challenge": a table (point | what the design says | what the code says, file:line | what must change), then "Verdict": which commits stand, which change, which are dropped, which are missing. Do not rewrite the designer's sections. Then return the summary asked for.`

const FINAL = (t, ch) => `${COMMON(t)}

${MR}/design/${t.key}.md holds a design for this theme and, at its end, a "## Challenge" by a second reader. YOU WRITE THE FINAL PLAN. For every row of the challenge: check the code yourself and decide (the challenger is right, partly right, or wrong: say which and why, file:line). Then rewrite the page so that it is the one plan to implement: same sections as before, corrected; the "## Challenge" section is replaced by a short "## What the challenge changed" table (point | decision | why). Keep it honest: where neither of you could determine something without the camera, it stays in "Risks and what was not determined" with the Pi check.

${RULES}

The challenger's own summary of the outcome: ${ch && ch.verdict ? ch.verdict : '(not returned; read the section in the file)'}

When the page is rewritten, return the plan in the structured form asked for: the commit list must match the page exactly (same numbers, same subjects). If you cannot write the file, put the whole page text in full_text.`

const D_SCHEMA = { type: 'object', properties: { file_written: { type: 'boolean' }, commits: { type: 'integer' }, summary: { type: 'string' } }, required: ['summary'] }
const C_SCHEMA = { type: 'object', properties: { verdict: { type: 'string' }, stands: { type: 'integer' }, changes: { type: 'integer' }, dropped: { type: 'integer' }, missing: { type: 'integer' } }, required: ['verdict'] }
const F_SCHEMA = {
  type: 'object',
  properties: {
    file_written: { type: 'boolean' },
    summary: { type: 'string' },
    commits: { type: 'array', items: { type: 'object', properties: {
      n: { type: 'integer' }, subject: { type: 'string' }, repo: { type: 'string' }, files: { type: 'string' },
      what: { type: 'string' }, removes: { type: 'integer' }, adds: { type: 'integer' },
      check_here: { type: 'string' }, check_pi: { type: 'string' }, depends_on: { type: 'string' }, risk: { type: 'string' },
    }, required: ['n', 'subject', 'repo', 'what'] } },
    new_ground: { type: 'array', items: { type: 'string' } },
    owner_decisions: { type: 'array', items: { type: 'object', properties: { question: { type: 'string' }, options: { type: 'string' }, recommendation: { type: 'string' } }, required: ['question', 'recommendation'] } },
    risks: { type: 'array', items: { type: 'string' } },
    not_covered: { type: 'array', items: { type: 'string' } },
    full_text: { type: 'string' },
  },
  required: ['summary', 'commits'],
}

async function lane(t) {
  const d = await agent(DESIGN(t), { label: `design:${t.key}`, phase: 'Design', model: 'opus', schema: D_SCHEMA })
  const c = await agent(CHALLENGE(t), { label: `challenge:${t.key}`, phase: 'Challenge', model: 'opus', schema: C_SCHEMA })
  const f = await agent(FINAL(t, c), { label: `final:${t.key}`, phase: 'Final', model: 'opus', schema: F_SCHEMA })
  return { key: t.key, design: d, challenge: c, final: f }
}
const out = await parallel(themes.map(t => () => lane(t)))
return out
