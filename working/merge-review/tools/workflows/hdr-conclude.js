export const meta = {
  name: 'clearhdr12-conclude',
  description: 'Rank hypotheses for the 12-bit Clear HDR problem, attack each with a skeptic, write the report',
  phases: [
    { title: 'Hypothesize', detail: 'rank the candidate causes across the nine reader reports', model: 'opus' },
    { title: 'Verify', detail: 'one skeptic per hypothesis tries to refute it from the code', model: 'opus' },
    { title: 'Report', detail: 'the report with Pi commands and patch sketches', model: 'opus' },
  ],
}
const DIR = '/home/user/apertar-kb/working/merge-review/hdr12'
const COMMON = `You are part of an investigation for Patrik's Apertar camera project. First read /home/user/apertar-kb/working/merge-review/BRIEF.md (paths, vocabulary, rules) and follow it.

THE QUESTION: on the cinemate-port stack (Apertar-Core cinemate-port 01f170c, Apertar-UI cinemate-port 7ea9afc, imx585 driver cinemate-port cd548ef, libcamera fork branch apertar 6b0b49f, Raspberry Pi CM5, IMX585 sensor) the owner reports: "12 bit clear HDR shows strange output". He gave no more detail. 16-bit Clear HDR is reported fine. "Output" may mean the recorded cDNG / MLV file in a raw converter, the HDMI / touch preview, the WebUI preview, a clip browser or player, exposure / white balance behaviour, or the mode itself.

Nine readers each took one angle (KB history, Core record path, port regressions, preview and ISP, driver, libcamera, Cinemate, a numeric check of the linearisation, playback). Their notes: ${DIR}/G1-kb-history.md ... G9-playback.md. A digest of all their findings: ${DIR}/DIGEST.md.

METHOD: read code at the named refs, quote path:line@ref, label each claim confirmed / probable / unconfirmed (with the command that would settle it). You cannot run the camera. You may compile and run small host programs under /home/user/build/hdr12-numeric (never write into the code repos).`

phase('Hypothesize')
const HYP_SCHEMA = { type: 'object', properties: { hypotheses: { type: 'array', items: { type: 'object', properties: {
  id: { type: 'string' }, statement: { type: 'string' }, symptom: { type: 'string' }, where: { type: 'string' },
  support: { type: 'array', items: { type: 'string' } }, against: { type: 'array', items: { type: 'string' } },
  likelihood: { type: 'string', enum: ['high', 'medium', 'low'] }, provable_from_code: { type: 'boolean' }, pi_test: { type: 'string' } },
  required: ['id', 'statement', 'symptom', 'where', 'support', 'likelihood', 'provable_from_code', 'pi_test'] } },
  contradictions_between_reports: { type: 'array', items: { type: 'string' } } }, required: ['hypotheses'] }
const hyp = await agent(`${COMMON}\n\nASSIGNMENT H, rank the candidate causes. Read ${DIR}/DIGEST.md in full, then the reader notes you need, and re-open the code wherever two reports disagree (settle the disagreement yourself and say how). Produce the list of distinct hypotheses for "12-bit Clear HDR shows strange output", merged across reports, at most ten, most likely first. Use ids H1, H2, ... Each must name one mechanism, the symptom it produces and where the operator sees it, the lines that would change, the support and the counter-evidence, whether it can be proven from code alone, and the cheapest test on the Pi that separates it from the others (prefer read-only checks: a socket get_state, v4l2-ctl --list-ctrls on the sensor subdev, exiftool or tiffdump on one DNG, a journal line). Include the hypothesis that the files are right and only a viewer is wrong, if the evidence allows it. Write ${DIR}/H-hypotheses.md as well.`,
  { label: 'rank-hypotheses', phase: 'Hypothesize', schema: HYP_SCHEMA, model: 'opus' })

phase('Verify')
const VERDICT_SCHEMA = { type: 'object', properties: { id: { type: 'string' },
  verdict: { type: 'string', enum: ['confirmed-defect', 'refuted', 'plausible-needs-pi', 'not-a-cause'] },
  reasoning: { type: 'string' }, evidence: { type: 'array', items: { type: 'string' } },
  fix_sketch: { type: 'string' }, pi_test: { type: 'string' } }, required: ['id', 'verdict', 'reasoning', 'evidence'] }
const hyps = (hyp && hyp.hypotheses ? hyp.hypotheses : []).slice(0, 10)
const verdicts = (await parallel(hyps.map(h => () =>
  agent(`${COMMON}\n\nASSIGNMENT V, try to refute one hypothesis. You are a skeptic: your job is to show this hypothesis is wrong, by reading the code yourself (do not trust the readers' notes; open the files). If it survives, say exactly how sure the code makes you and what remains for the Pi. If it is a defect provable from code, give a fix sketch that follows the style of the surrounding original Apertar code (small, local, no new abstractions) and the host test that would show it (the port keeps host tests in Apertar-Core/tools/*_test.cpp). Do not edit the repos.\n\nHYPOTHESIS ${h.id}: ${h.statement}\nSymptom: ${h.symptom}\nWhere: ${h.where}\nClaimed support: ${(h.support || []).join(' | ')}\nClaimed counter-evidence: ${(h.against || []).join(' | ')}\nProposed Pi test: ${h.pi_test}\n\nWrite your notes to ${DIR}/V-${h.id.replace(/[^A-Za-z0-9_-]/g, '_')}.md.`,
    { label: `verify:${h.id}`, phase: 'Verify', schema: VERDICT_SCHEMA, model: 'opus' })
))).filter(Boolean)

phase('Report')
const vdigest = verdicts.map(v => `- ${v.id}: ${v.verdict}. ${v.reasoning}\n  evidence: ${(v.evidence || []).slice(0, 5).join(' | ')}\n  fix: ${(v.fix_sketch || '').slice(0, 1500)}\n  pi: ${(v.pi_test || '').slice(0, 800)}`).join('\n')
const report = await agent(`${COMMON}\n\nASSIGNMENT R, write the report. Hypotheses were ranked (${DIR}/H-hypotheses.md) and each was attacked by a skeptic (${DIR}/V-*.md). Verdict digest:\n${vdigest}\n\nWrite ${DIR}/REPORT.md for Patrik, an intermediate coder who knows cameras well, in the knowledge base's style (short sentences, tables, no filler; label confirmed / probable / unconfirmed; path:line@ref on every code claim). Sections: (1) Answer in five lines: the most likely cause or causes, and how sure. (2) What 12-bit Clear HDR is on this stack today: one table, hop by hop, sensor to file to viewer, with what each hop does to the pixel values. (3) Defects confirmed from code: each with the lines, the effect, and the fix sketch. (4) Causes that need the Pi: each with the exact commands in order, cheapest and read-only first, and what each outcome means. (5) Refuted ideas, one line each, so nobody chases them again. (6) What to ask Patrik: the two or three facts about the symptom that would cut the list fastest. (7) Rules for future work drawn from this (at most six). Read the V and G notes in full where the digest is thin. Return a summary of the report.`,
  { label: 'write-report', phase: 'Report', model: 'opus', schema: { type: 'object', properties: { summary: { type: 'string' }, report_path: { type: 'string' }, confirmed_defects: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, title: { type: 'string' }, where: { type: 'string' }, fix: { type: 'string' } }, required: ['title'] } }, needs_pi: { type: 'array', items: { type: 'string' } }, questions_for_owner: { type: 'array', items: { type: 'string' } } }, required: ['summary', 'report_path'] } })
return { report, verdicts: verdicts.map(v => ({ id: v.id, verdict: v.verdict, reasoning: v.reasoning, fix_sketch: v.fix_sketch || '' })), hypotheses: hyps.map(h => ({ id: h.id, statement: h.statement, likelihood: h.likelihood })) }
