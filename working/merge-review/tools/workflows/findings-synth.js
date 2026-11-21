export const meta = {
  name: 'port-fix-list',
  description: 'Merge all verified review findings into one fix list, and all inventories into one feature list',
  phases: [
    { title: 'Cluster', detail: 'one editor per domain merges unit and sweep findings into fix items', model: 'opus' },
    { title: 'Features', detail: 'feature list per area from the inventories', model: 'sonnet' },
    { title: 'Edit', detail: 'one fix list, one feature list, the decisions for the owner', model: 'opus' },
  ],
}
const MR = '/home/user/apertar-kb/working/merge-review'
const RAW = `${MR}/raw`
const COMMON = `You are part of a merge review for Patrik's Apertar camera project. First read ${MR}/BRIEF.md (paths, vocabulary, rules) and follow it. The yardstick is ${MR}/apertar-conventions.md (how original Apertar 1.6.0 is built; cite its rule ids where one applies; if the file is missing use ${RAW}/conv-*.md).

WHERE THE REVIEW STANDS: 37 units covered every changed line of the cinemate port (inventory, review against original Apertar, skeptic), and nine whole-port sweeps ran. Everything is on disk: ${RAW}/FINDINGS.md (every finding, one line each, grouped by unit and sweep), ${RAW}/FINDINGS.json (the same with full text: port way, Apertar way, why it matters, rework), the unit reports ${RAW}/rev-<unit>.md (their "## Final findings" section is authoritative where present), the sweep reports ${RAW}/sweep-<key>.md, the inventories ${RAW}/inv-<unit>.md and ${RAW}/FEATURES.json.

ALREADY FIXED on the improvement branch (do not list as open; mention as done): the GPIO chip setting is back on the Controls page and its checks are per chip (Apertar-Core 04fe197; worktree /home/user/wt/core-work).`

const ITEM = { type: 'object', properties: {
  id: { type: 'string' }, title: { type: 'string' },
  kind: { type: 'string', enum: ['mismatch', 'removed', 'stock', 'protocol', 'new-ground', 'bug', 'board', 'security', 'slop', 'duplication', 'knob', 'commit', 'docs'] },
  severity: { type: 'string', enum: ['blocker', 'major', 'minor', 'nit'] },
  sources: { type: 'array', items: { type: 'string' }, description: 'finding ids merged into this item' },
  where: { type: 'array', items: { type: 'string' } },
  problem: { type: 'string', description: 'Two or three plain sentences: what the port does and what goes wrong or reads as foreign' },
  apertar_way: { type: 'string', description: 'How original Apertar does it, with path:line@upstream-1.6.0 or a conventions rule id; "no precedent" for new ground' },
  rework: { type: 'array', items: { type: 'string' }, description: 'Concrete steps in order: function, file, what moves or goes' },
  effort: { type: 'string', enum: ['S', 'M', 'L'] },
  risk: { type: 'string' },
  deliberate: { type: 'string', enum: ['yes', 'no', 'unknown'] },
  owner_decision: { type: 'string', description: 'Empty, or the one question the owner must answer before this can be done, with the recommendation' },
  check_here: { type: 'string', description: 'How to verify the fix on the review machine (build, host test, browser against --simulate)' },
  needs_pi: { type: 'string', description: 'What only the camera can confirm, with the command' },
  depends_on: { type: 'array', items: { type: 'string' } },
  recommendation: { type: 'string', enum: ['fix-now', 'fix-later', 'keep-and-document', 'ask-owner', 'drop'] },
}, required: ['id', 'title', 'kind', 'severity', 'sources', 'where', 'problem', 'apertar_way', 'rework', 'effort', 'deliberate', 'recommendation'] }
const DOMAIN_SCHEMA = { type: 'object', properties: { domain: { type: 'string' }, report_path: { type: 'string' }, summary: { type: 'string' },
  conforms: { type: 'array', items: { type: 'string' } }, items: { type: 'array', items: ITEM },
  dropped: { type: 'array', items: { type: 'string' }, description: 'finding ids left out, each with the reason (duplicate of X, not real, taste)' } },
  required: ['domain', 'report_path', 'summary', 'items'] }

const DOMAINS = [
  { key: 'core-app', prefix: 'APP', title: 'Core app, command plane, state, build', units: ['App-1', 'App-2', 'App-3', 'App-4', 'App-5', 'Build-scripts-docs'], sweeps: 'protocol-security, state-consistency, knobs, stock-behaviour' },
  { key: 'hardware', prefix: 'HW', title: 'Hardware inputs, Controls, hardware file, Boot Config', units: ['HW-config-text-store', 'HW-controls-model', 'HW-input-classes', 'Boot-config', 'WCP-09'], sweeps: 'protocol-security, stock-behaviour, board-support, knobs' },
  { key: 'camera', prefix: 'CAM', title: 'Camera controller, sensor modes, drivers', units: ['CC-1', 'CC-4', 'CC-5', 'Camera-headers', 'Driver-imx585', 'Driver-imx283'], sweeps: 'board-support, stock-behaviour, state-consistency, knobs' },
  { key: 'recording', prefix: 'REC', title: 'Recording pipeline, encoders, audio, media, playback', units: ['CC-2', 'CC-3', 'CC-6', 'Encoders-audio', 'Media-fault-tune', 'Media-buffer-split', 'Playback'], sweeps: 'board-support, stock-behaviour, protocol-security, knobs' },
  { key: 'webui', prefix: 'WEB', title: 'WebUI page', units: ['WCP-01', 'WCP-02', 'WCP-03', 'WCP-04', 'WCP-05', 'WCP-06', 'WCP-07', 'WCP-08', 'WCP-10'], sweeps: 'stock-behaviour, state-consistency, protocol-security' },
  { key: 'touch-ui', prefix: 'UI', title: 'Touch UI: bridges and QML', units: ['UI-bridges', 'UI-control-bridge', 'UI-settings-qml', 'UI-camera-qml'], sweeps: 'stock-behaviour, state-consistency, board-support, protocol-security, commits-ui-drivers' },
  { key: 'text-history', prefix: 'TXT', title: 'Comments, UI text, README, commit series', units: [], sweeps: 'slop, commits-core-1, commits-core-2, commits-ui-drivers, knobs (documentation side)' },
]

phase('Cluster')
const clusters = (await parallel(DOMAINS.map(d => () =>
  agent(`${COMMON}\n\nYOU ARE THE EDITOR for the domain "${d.title}". Your units: ${d.units.length ? d.units.join(', ') : '(none: you work from the sweeps)'}. Also take, from these sweeps, every finding that lies in your domain's files or subject: ${d.sweeps}. Another editor owns each other domain; when a sweep finding clearly belongs elsewhere leave it.\n\nRead your units' and sweeps' findings in full (FINDINGS.json, and the reports for context). Then build the list of FIX ITEMS for your domain:\n- Merge findings that are the same problem seen from two places into one item (list all source ids). Merge findings that one change would fix.\n- Re-check anything that looks doubtful or that two reports contradict: open the code (port: /home/user/Apertar-Core and /home/user/Apertar-UI at cinemate-port; original: the *-upstream worktrees). Drop what is not real, with the reason.\n- For each item decide the kind. mismatch = the port did it its own way where original Apertar has a pattern. removed = something original Apertar offers went missing or was narrowed. stock = a stock camera would behave differently after the merge with nothing configured. new-ground = no upstream precedent (say whether the shape is the least foreign one). Then bug, board (Raspberry Pi model), protocol, security, slop, duplication, knob, commit, docs.\n- Write the rework as steps a careful engineer can follow in the ORIGINAL code's style: which function in which file, what moves where, what is deleted, which upstream pattern is copied (name it with path:line). No new layers. If the honest answer is "this is new architecture and should stay", say keep-and-document and what the original developer must be told.\n- Where the choice is the owner's (keep a new architecture or rework it; keep a changed default or restore the original), put ONE question in owner_decision with your recommendation and what each answer costs.\n- Severity: blocker = the original developer would refuse the merge, or original behaviour breaks; major = clearly foreign or risky; minor; nit.\n- recommendation: fix-now (milestone 1: design conformance, removed behaviour, stock behaviour, protocol; and any bug that loses footage or settings), fix-later, keep-and-document, ask-owner, drop.\nIds: "${d.prefix}-<n>", most severe first. Also list what in this domain conforms well to original Apertar (for the handoff).\nWrite the full list to ${MR}/fix-list-${d.key}.md (one section per item: title line, a small table of kind / severity / effort / deliberate / recommendation / sources, then problem, Apertar way, rework steps, owner decision, check here, needs the Pi), then return it.`,
    { label: `cluster:${d.key}`, phase: 'Cluster', schema: DOMAIN_SCHEMA, model: 'opus' }).then(r => r ? { ...r, key: d.key, prefix: d.prefix } : null)
))).filter(Boolean)
log(`clusters: ${clusters.length}/${DOMAINS.length}, ${clusters.reduce((n, c) => n + c.items.length, 0)} fix items`)

phase('Features')
const AREAS = [
  { key: 'camera-modes', title: 'Camera, sensors and modes', units: 'CC-1, CC-4, CC-5, CC-6, Camera-headers, Driver-imx585, Driver-imx283' },
  { key: 'recording-media', title: 'Recording, files, audio, media and playback', units: 'CC-2, CC-3, Encoders-audio, Media-fault-tune, Media-buffer-split, Playback, App-1, App-3' },
  { key: 'controls-system', title: 'Controls, hardware, system and configuration', units: 'App-2, App-4, App-5, HW-config-text-store, HW-controls-model, HW-input-classes, Boot-config, Build-scripts-docs' },
  { key: 'webui', title: 'WebUI', units: 'WCP-01 to WCP-10' },
  { key: 'touch-ui', title: 'Touch UI and HDMI monitor', units: 'UI-bridges, UI-control-bridge, UI-settings-qml, UI-camera-qml' },
]
const FEAT_SCHEMA = { type: 'object', properties: { area: { type: 'string' }, report_path: { type: 'string' }, features: { type: 'array', items: { type: 'object', properties: {
  name: { type: 'string' }, operator_gets: { type: 'string' }, how_to_use: { type: 'string' },
  commands: { type: 'array', items: { type: 'string' } }, state_fields: { type: 'array', items: { type: 'string' } }, config: { type: 'array', items: { type: 'string' } }, env: { type: 'array', items: { type: 'string' } },
  touches_upstream: { type: 'string', description: 'Which original functions or files it extends, replaces or sits beside' },
  relation: { type: 'string', enum: ['extends-in-place', 'beside-upstream', 'replaces-upstream', 'new-area'] },
  default_state: { type: 'string', description: 'on or off by default; what a stock camera sees' },
  needs: { type: 'string', description: 'Driver, helper, package or file it depends on' },
  tested: { type: 'string' }, commits: { type: 'array', items: { type: 'string' } }, means_for_development: { type: 'string' } },
  required: ['name', 'operator_gets', 'touches_upstream', 'relation', 'default_state'] } } }, required: ['area', 'report_path', 'features'] }
const featureLists = (await parallel(AREAS.map(a => () =>
  agent(`${COMMON}\n\nYOU BUILD THE FEATURE LIST for the area "${a.title}" from the inventories of these units: ${a.units} (${RAW}/inv-<unit>.md, and ${RAW}/FEATURES.json). A feature is something the camera operator or an integrator can now do or see that original Apertar 1.6.0 could not. Merge the same feature seen from several units into one entry (the Core part, the WebUI part and the touch part of one feature are ONE feature; if its main home is another area, leave it to that area and say so in one line at the end of your report). For each: a plain name, what the operator gets (one sentence an intermediate user understands), how it is used (button, page, command, config key), the socket commands / HTTP routes, state fields, config keys and env vars it added, which ORIGINAL functions and files it touches and in what relation (extends them in place, sits beside them, replaces them, or is a new area), whether it is on by default and what a stock camera sees, what it needs (driver branch, root helper, package, tuning file), what the commit messages and /home/user/apertar-kb/fork-log.md say was tested and where (Pi, desk, not at all), the port commits (short shas), and one sentence on what it means for further development (what a developer must know before touching it). Verify names of commands and keys by grep in the port checkout; do not copy an inventory blindly. Write ${MR}/feature-list-${a.key}.md (a table plus one short section per feature), then return it.`,
    { label: `features:${a.key}`, phase: 'Features', schema: FEAT_SCHEMA, model: 'sonnet' }).then(r => r ? { ...r, key: a.key } : null)
))).filter(Boolean)
log(`feature lists: ${featureLists.length}/${AREAS.length}, ${featureLists.reduce((n, c) => n + c.features.length, 0)} features`)

phase('Edit')
const index = clusters.map(c => `## ${c.domain} (${c.report_path})\n${c.summary}\n` + c.items.map(i => `- ${i.id} [${i.kind}, ${i.severity}, ${i.effort}, ${i.recommendation}${i.owner_decision ? ', OWNER' : ''}] ${i.title}`).join('\n')).join('\n\n')
const master = await agent(`${COMMON}\n\nYOU ARE THE CHIEF EDITOR. Seven domain editors merged the review's findings into fix items (files ${MR}/fix-list-<domain>.md). Index:\n\n${index}\n\nWrite three files.\n\n1. ${MR}/fix-list.md: THE fix list for Patrik. Start with the verdict in five lines: is cinemate-port ready to merge into Apertar main (no, and what stands in the way, in numbers). Then one table per milestone, most severe first, columns: id, kind, severity, effort, title, state (all "open", or "done <sha>" for the GPIO chip item), where to read more (the domain file). Milestones: 1 = compatibility with the original Apertar design (mismatch, removed, stock, protocol, and security holes a maintainer would refuse); 2 = bugs and Raspberry Pi model compatibility; 3 = text (comments, UI strings, README, knobs to drop); 4 = commit series. Keep the domain editors' ids. Where two domains describe the same item, keep one and point the other at it. Then "Order of work": the sequence that avoids doing things twice (what must come before what), as a numbered list. Then "What conforms": ten lines on what the port does the Apertar way. Under 400 lines; the detail stays in the domain files.\n\n2. ${MR}/owner-decisions.md: every question only the owner can answer (items with an owner decision, plus any you see across domains: keep or rework each big new architecture, keep or restore each changed default, trailers in commits, which driver branch ships). One table: question, options with the cost of each, recommendation, which fix items wait on it. Put first the ones that block the most work.\n\n3. ${MR}/feature-list.md: one page from the five area lists (${MR}/feature-list-<area>.md): a table of ALL features (name, what the operator gets, relation to the original code, on by default?, tested where), grouped by area, de-duplicated across areas, then a count. Under 250 lines; detail stays in the area files.\n\nRead the domain and area files as needed. Use the knowledge base's style: short sentences, tables, plain ASCII punctuation, no filler. Return the summary.`,
  { label: 'fix-list', phase: 'Edit', model: 'opus', schema: { type: 'object', properties: { verdict: { type: 'string' }, counts: { type: 'string' }, milestone1: { type: 'array', items: { type: 'string' } }, owner_questions: { type: 'array', items: { type: 'string' } }, features: { type: 'integer' }, files: { type: 'array', items: { type: 'string' } } }, required: ['verdict', 'counts'] } })
return { master, clusters: clusters.map(c => ({ domain: c.domain, report: c.report_path, items: c.items.map(i => ({ id: i.id, title: i.title, kind: i.kind, severity: i.severity, effort: i.effort, recommendation: i.recommendation, owner_decision: i.owner_decision || '', deliberate: i.deliberate })) })), features: featureLists.map(f => ({ area: f.area, report: f.report_path, n: f.features.length })) }
