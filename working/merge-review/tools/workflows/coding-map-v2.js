export const meta = {
  name: 'coding-map-verify',
  description: 'Verify every box, arrow, code line, flow and recipe of the Apertar coding map against upstream 1.6.0 and cinemate-port',
  phases: [
    { title: 'Check', detail: 'six checkers, each owns one slice of index.html' },
    { title: 'Recheck', detail: 'a second agent re-derives each reported discrepancy from the code' },
  ],
}

const OUT = '/home/user/apertar-kb/working/merge-review/coding-map'
const COMMON = `You are checking Patrik's "Apertar coding map" for errors. First read /home/user/apertar-kb/working/merge-review/BRIEF.md (paths, vocabulary, rules) and follow it.

THE MAP: /home/user/apertar-coding-map/index.html (one self-contained page, about 940 lines; README.md beside it). It teaches where code lives in Apertar: boxes (const N, around lines 293-351), arrows (const E, 352-419), per-box fork data (const FORKDATA, line 420, one long line), repository links (GH, UP, 421-422), guided flows (const TOURS, 424-431), worked examples "Where your change goes" (const RECIPES, about 662-831), the official/fork switch (const SRC and setMode, about 911-935), static text in the HTML (lines 200-262) and the footer. Read the slice you own completely, and enough of the script to understand how a field is shown (function render, around 539-560; val() and isFork(), 433-434).

TWO MODES. "official" = Apertar-Studio main = the *-upstream worktrees (/home/user/wt/core-upstream, /home/user/wt/ui-upstream, tag upstream-1.6.0). "fork" = branch cinemate-port (/home/user/Apertar-Core at 01f170c, /home/user/Apertar-UI at 7ea9afc). A field is shown in fork mode as written; in official mode an "up:{...}" override replaces it where present (see val()). "fork:true" marks an item as fork-only or fork-changed. So: every "code" string, path, function name, line of a diff, command name, JSON field and statement in "what"/"note"/"tip" text must be TRUE for the fork as written, and TRUE for upstream after applying the up-override (or, with no override, true for both).

HOW TO CHECK a code line: grep -nF for the literal (or its distinctive part) in the file the item names, in the right tree for each mode. A line that does not occur, occurs in another file, or occurs but does not do what the text says, is a discrepancy. Paths in the map are as on the camera: "~/ApertarUI/" = the UI repo root, "~/ApertarCore/" = the Core repo root. Check that the described mechanism is right too (who calls whom, which thread, socket vs function call, which file a setting is stored in), using the code, not memory. The KB's hop-by-hop traces (/home/user/apertar-kb/llm/flows.md, against upstream-1.6.0) are a second opinion, not proof.

REPORT every discrepancy with: the item id and field, the mode it is wrong in (official, fork, both), what the map says (quoted), what the code says (path:line@ref, quoted), and the exact corrected text for that field (a replacement string that keeps the map's short, friendly, one-real-line-of-code style). Do not report style opinions. Do not report that the fork has grown (new features are handled later), except where the map's existing statement became FALSE on the fork. If your whole slice is correct, say so and list what you checked. Do not edit index.html. Write your notes to the file named in your assignment.`

const SCHEMA = {
  type: 'object',
  properties: {
    slice: { type: 'string' },
    report_path: { type: 'string' },
    items_checked: { type: 'integer' },
    discrepancies: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          item: { type: 'string', description: 'e.g. N.BRIDGE.code, E.c3.what, RECIPES.r2.steps[3].diff, FORKDATA.QML.count, README line' },
          mode: { type: 'string', enum: ['official', 'fork', 'both'] },
          map_says: { type: 'string' },
          code_says: { type: 'string', description: 'path:line@ref and the quoted line' },
          problem: { type: 'string' },
          corrected: { type: 'string', description: 'Exact replacement text for the field' },
          severity: { type: 'string', enum: ['wrong', 'stale', 'imprecise'] },
        },
        required: ['item', 'mode', 'map_says', 'code_says', 'problem', 'corrected', 'severity'],
      },
    },
  },
  required: ['slice', 'report_path', 'items_checked', 'discrepancies'],
}

const SLICES = [
  { key: 'nodes', task: `YOUR SLICE: every entry of const N (all boxes): title, sub, path, what, code, tip and any up-override, in both modes. Count the boxes and check each one. Also the legend text (lines 213-226) and the layer band names. Report file: ${OUT}/verify-nodes.md` },
  { key: 'edges-command-state', task: `YOUR SLICE: the arrows in const E whose id starts with "c" (commands in) or "s" (state back): f, t, kind, label, title, path, what, code, tip, up-override, in both modes. For each arrow also check that the two boxes it joins really talk that way (function call inside one program vs socket or HTTP message between programs; thin vs thick is derived from kind, see const LINES and KINDS). Report file: ${OUT}/verify-edges-cs.md` },
  { key: 'edges-picture-files-tours', task: `YOUR SLICE: every arrow in const E whose id does NOT start with "c" or "s" (pictures, files, UI.conf, hardware and the rest), in both modes; plus const TOURS: for each tour check every step id exists in N or E, the order matches what the code does hop by hop, and nothing essential is skipped (compare /home/user/apertar-kb/llm/flows.md and then the code); plus the card "Try 3 and 6 from the Mac" (lines 237-246): are the two curl commands valid against Core's HTTP API in both modes (route, method, body shape, the grep pattern matching the real /api/state output)? Report file: ${OUT}/verify-edges-other-tours.md` },
  { key: 'recipes-a', task: `YOUR SLICE: const RECIPES, the FIRST HALF of the recipes by order in the file (count them first; if there are n, take the first ceil(n/2)). For each recipe: is "want / forget / example" sound advice for this code base; for each step: does the file exist, do the unchanged context lines of the diff occur in that file (in the mode the step is shown in; steps can carry up-overrides or fork:true), would the added lines compile or run in that place and follow the surrounding style, is "same:true" (nothing to change) really true, is the note right. A worked example that would not work if a learner typed it is a "wrong" discrepancy. Report file: ${OUT}/verify-recipes-a.md` },
  { key: 'recipes-b', task: `YOUR SLICE: const RECIPES, the SECOND HALF of the recipes by order in the file (count them first; if there are n, skip the first ceil(n/2) and take the rest). For each recipe: is "want / forget / example" sound advice for this code base; for each step: does the file exist, do the unchanged context lines of the diff occur in that file (in the mode the step is shown in; steps can carry up-overrides or fork:true), would the added lines compile or run in that place and follow the surrounding style, is "same:true" (nothing to change) really true, is the note right. A worked example that would not work if a learner typed it is a "wrong" discrepancy. Also check the recipe table plumbing: buildRows, chainHTML, the numbered badges use node ids that exist. Report file: ${OUT}/verify-recipes-b.md` },
  { key: 'forkdata-links-text', task: `YOUR SLICE: const FORKDATA, GH, UP, SRC, the footer (FOOT_TAIL), the header switch text, and README.md. (1) FORKDATA holds, per box, how many commits the fork has that official Apertar does not, and the newest five. Work out from the data how it was computed (most likely: commits in <base>..cinemate-port touching the files that box stands for; find the base and the file set per box by matching the listed commits with git log -- <path>), then recompute it for today's heads: Core cinemate-port 01f170c (base: upstream-1.6.0 or origin/main, decide from the data and say which), UI cinemate-port 7ea9afc, driver. Report each box whose count or newest-five list is stale, with the corrected JSON entry. Give the exact git commands you used so the numbers can be regenerated. (2) Which driver branch does the fork side point at? The map and README say imx585 branch "apertar"; the port's driver work is on branch "cinemate-port" of /home/user/imx585-v4l2-driver, and an imx283 driver fork exists too (/home/user/imx283-v4l2-driver). State what is right today. (3) Every URL: does the branch or path in it exist (use git ls-remote --heads <url> for repositories; do not fetch web pages). (4) Every factual sentence in README.md and in the static HTML text: true for both modes? (For example "Two programs on one Raspberry Pi 5", port numbers, socket path, what each colour means.) Report file: ${OUT}/verify-forkdata-links.md` },
]

// v2: slices from args.slices, two lanes, a slice's check and recheck back to back.
// args.skipCheck: slices whose first check already wrote its report file.
const FILES = { 'nodes': 'verify-nodes.md', 'edges-command-state': 'verify-edges-cs.md', 'edges-picture-files-tours': 'verify-edges-other-tours.md', 'recipes-a': 'verify-recipes-a.md', 'recipes-b': 'verify-recipes-b.md', 'forkdata-links-text': 'verify-forkdata-links.md' }
const wanted = (args && args.slices) ? args.slices : []
const skipCheck = new Set((args && args.skipCheck) ? args.skipCheck : [])
const slices = wanted.map(k => SLICES.find(s => s.key === k)).filter(Boolean)
log(`coding map v2: ${slices.map(s => s.key).join(', ')}`)
const runSlice = async s => {
  let res
  if (skipCheck.has(s.key)) res = { slice: s.key, report_path: `${OUT}/${FILES[s.key]}`, items_checked: 0, discrepancies: [], reused: true }
  else res = await agent(`${COMMON}\n\n${s.task}`, { label: `check:${s.key}`, phase: 'Check', schema: SCHEMA, model: 'sonnet' })
  if (!res) { log(`${s.key}: check failed`); return null }
  if (!res.reused && !res.discrepancies.length) return res
  const list = res.reused
    ? `(The first checker's discrepancies are in ${res.report_path}: read the file and take every discrepancy it reports.)`
    : res.discrepancies.map((d, i) => `${i + 1}. ${d.item} [${d.mode}, ${d.severity}]\n   map: ${d.map_says}\n   code: ${d.code_says}\n   problem: ${d.problem}\n   corrected: ${d.corrected}`).join('\n')
  const r = await agent(`${COMMON}\n\nYOU ARE THE SECOND CHECKER for slice "${s.key}". A first checker reported the discrepancies below (notes: ${res.report_path}). Re-derive each one from the code yourself, in both modes. Drop any that is not a real error (the map was right, or the "correction" is wrong or no better). For the ones that stand, make sure the corrected text is exactly right: it must occur in the named file in the named tree (grep -nF it), fit the field, and stay one short real line where the field is a code line. Fix corrections that are off. Append a section "## Recheck" to ${res.report_path} with your verdict per item (stands / dropped / corrected differently, and why), and below it "## Final discrepancies": every one that stands, in full (item, mode, map says, code says, corrected text), so the file alone is enough to apply the fixes. Return the final list in the same schema (only discrepancies that stand).\n\nREPORTED:\n${list}`,
    { label: `recheck:${s.key}`, phase: 'Recheck', schema: SCHEMA, model: 'opus' })
  if (!r) log(`${s.key}: recheck failed`)
  return r || res
}
const lane = async list => { const out = []; for (const s of list) out.push(await runSlice(s)); return out }
const lanes = [slices.filter((s, i) => i % 2 === 0), slices.filter((s, i) => i % 2 === 1)].filter(l => l.length)
const ok = (await parallel(lanes.map(l => () => lane(l)))).filter(Boolean).flat().filter(Boolean)
return ok.map(r => ({ slice: r.slice, report: r.report_path, items_checked: r.items_checked, discrepancies: r.discrepancies }))
