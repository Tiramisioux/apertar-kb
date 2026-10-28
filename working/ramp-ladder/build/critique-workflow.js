export const meta = {
  name: 't34-critique',
  description: 'Adversarial critique of the T33/T34 code in Core, WebUI and touch UI, each finding verified',
  phases: [
    { title: 'Review', detail: 'five reviewers, one lens each' },
    { title: 'Verify', detail: 'one skeptic per reviewer re-checks every finding against the code' },
  ],
}

const S = '/tmp/claude-0/-home-user-apertar-kb/17fc979d-f346-53ac-97ad-c8caa225a57d/scratchpad'
const FINDINGS = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string', description: 'short slug' },
          severity: { type: 'string', enum: ['high', 'medium', 'low'] },
          file: { type: 'string', description: 'repo-relative path' },
          line: { type: 'integer' },
          claim: { type: 'string', description: 'the defect in one or two sentences' },
          scenario: { type: 'string', description: 'concrete inputs/state -> wrong result' },
          fix: { type: 'string', description: 'the smallest fix' },
        },
        required: ['id', 'severity', 'file', 'line', 'claim', 'scenario', 'fix'],
      },
    },
  },
  required: ['findings'],
}
const VERDICTS = {
  type: 'object',
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          real: { type: 'boolean' },
          evidence: { type: 'string', description: 'file:line quotes that prove or refute it' },
          fix: { type: 'string', description: 'the fix to apply if real (may refine the reviewer\'s)' },
        },
        required: ['id', 'real', 'evidence', 'fix'],
      },
    },
  },
  required: ['verdicts'],
}

const CONTEXT = `
Code under review (uncommitted T34 on top of committed T33; nothing else changed):
- Core: ${S}/t34/core. T33 = HEAD commit (git show HEAD); T34 = git diff HEAD (plus untracked src/camera/ModeLadder.hpp).
- Touch UI: ${S}/t34/ui. T33 = HEAD commit; T34 = git diff HEAD.
- The contract: ${S}/t34/SPEC.md (wins over the design). Background: ${S}/ladder-design/design-T34.md sections 3-4.
- Approved mockups: ${S}/ladder-mock/project/Main.dc.html, Quick.dc.html.
- Host checks available: ${S}/t34/hostcheck-core.sh (g++ -fsyntax-only with libcamera headers), the header test
  ${S}/t34/mode_ladder_test.cpp, node --check of the page script, ninja -C ${S}/t34/ui-build, the WebUI mock
  ${S}/t34/webtest/ (Playwright + Chromium installed).
Report only real defects you can point to with file:line and a concrete scenario: wrong behaviour, crashes, races,
deadlocks, invalid JSON, protocol mismatches between layers, violations of SPEC.md, user-visible text that breaks
Patrik's rules (say "resolution" not "rung"; "ClearHDR16" as the compact tag), illegal values reachable from a UI.
No style nits, no "consider adding". Do not edit any file.
`

const LENSES = [
  { key: 'core-runtime', prompt: `Lens: Core runtime correctness. CameraController.cpp/.hpp: mutex discipline (every *Locked helper
called with mutex_ held, no lock taken twice, no callback into the App under the lock), a single apply per command, rollback
(setModeLadder restores the old ladder on a failed apply; the file is written only after success), reconfigure decisions
(compression-only change must not reconfigure; mode change must), the T31 speed-ramp stepper and ramp_fps capped at the
running resolution's ceiling in a take, start()/standby/wake paths, simulate mode (SensorFamily::Unknown), T33's
setBuildMaximumFps re-sanitise, persisted settings (does a ladder switch persist correctly per format profile?).` },
  { key: 'core-semantics', prompt: `Lens: ladder semantics and JSON. Compare the Core code with SPEC 2.3-2.7 line by line:
ownCompression vs runtime states, valid/usable/reason, active, compressionApplies (MLV), findRung, the rewrite in each
command listed, refusals and their exact texts, apply_preset, hardware inputs, help list, the pool (identity mapping
3840x2200 -> 3840x2160, dedup, sort, ceilings per compression, crop parsing, sensor area), state fields in ALL THREE writers
(settingsEvent in CameraController.cpp, settingsBody and buildWebStateJson in ApertarCoreApp.cpp): names, types, JSON
validity (commas, quoting, numbers like NaN/inf), and ModeLadder.hpp itself (parse/validate/toJson edge cases). Build a
small host program if it helps prove a JSON or parsing bug.` },
  { key: 'webui', prompt: `Lens: the WebUI (src/web/WebControlPage.cpp, git diff HEAD). Compare with SPEC section 3 and the mockups.
Look for: JS errors and dead references (ids that no longer exist after the Speed Ramp block was removed), state merge bugs,
the 1 s poll rebuilding the rows (focus loss), drag and drop on touch, illegal values reachable (threshold, compression,
Add), Save while Core reports errors, wrong use of the mode_ladder JSON keys (check against ladder::toJson), the FPS pills'
resolution mapping from ladder_tops, the switching note, disabled states, phone layout at 390 px. Run the mock harness in
${S}/t34/webtest if it exists, and node --check.` },
  { key: 'touchui-protocol', prompt: `Lens: the touch UI and cross-layer protocol. In ${S}/t34/ui: bridge properties and parsing of
the new state fields (types: numbers vs strings vs arrays; missing keys), signals, QML bindings (undefined ids, properties on
the wrong object), the FORMAT line, the disabled mode controls and their guards, the Mode Ladder row, applyFps and timeouts.
Across layers: every command name, field name, value format and state key used by the WebUI and the touch UI must exist in
Core with the same spelling and type; every refusal Core sends must be shown sensibly. Build with ninja -C ${S}/t34/ui-build.` },
  { key: 'operator', prompt: `Lens: the operator (Patrik) in the field, using his ladder: Resolution 1 = 4K Clear HDR 16-bit
uncompressed up to 25 fps, Resolution 2 = 4K SDR 12-bit uncompressed up to 50 (build maximum 50 in apertar-hardware.conf).
Walk through, in the code (Core, WebUI and touch UI), what happens step by step: boot with the ladder saved; pick 24, 25, 30,
50, 60 on the WebUI pills, the touch picker, the PCF pot and fps_up/fps_down; start a take at 24 and ramp to 50 with speed
ramping allowed; stop and pick 50; switch the format to MLV, to H.264 and back to cDNG; enter and leave photo mode; turn the
ladder off and on; load a Favorite saved before the ladder; change max_fps to 30 in the Config panel; a lossless JPEG
resolution (ISO 800 cap). Report every step where the camera ends up in a state the screens do not show, a control lies,
an FPS outruns its resolution, or a command fails without a message.` },
]

phase('Review')
const results = await pipeline(
  LENSES,
  (lens) => agent(`${CONTEXT}\n${lens.prompt}`, { label: 'review:' + lens.key, phase: 'Review', schema: FINDINGS }),
  (review, lens) => {
    const findings = (review && review.findings) || []
    if (!findings.length) return { lens: lens.key, findings: [], verdicts: [] }
    return agent(`${CONTEXT}
You are a skeptic. A reviewer (lens: ${lens.key}) reported the findings below. For EACH one, try to refute it by reading
the code at and around the cited lines (and its callers). Mark real=false when the code does not do what the claim says,
when the scenario cannot happen, or when it is not a defect under SPEC.md. Default to real=false when you cannot confirm it.
Give file:line evidence either way, and for real ones the fix you would apply.

Findings:
${JSON.stringify(findings, null, 1)}`, { label: 'verify:' + lens.key, phase: 'Verify', schema: VERDICTS })
      .then((v) => ({ lens: lens.key, findings, verdicts: (v && v.verdicts) || [] }))
  },
)

const confirmed = []
for (const r of results.filter(Boolean)) {
  for (const f of r.findings) {
    const v = r.verdicts.find((x) => x.id === f.id)
    if (v && v.real) confirmed.push({ lens: r.lens, ...f, evidence: v.evidence, fix: v.fix || f.fix })
  }
}
const total = results.filter(Boolean).reduce((n, r) => n + r.findings.length, 0)
log(`${confirmed.length} of ${total} findings confirmed`)
return { confirmed, total, raw: results }
