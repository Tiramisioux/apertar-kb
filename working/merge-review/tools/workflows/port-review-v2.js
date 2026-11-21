export const meta = {
  name: 'port-review',
  description: 'Inventory, design-conformance review and skeptic verification of one group of cinemate-port units',
  phases: [
    { title: 'Inventory', detail: 'what the port added or changed in each unit', model: 'sonnet' },
    { title: 'Review', detail: 'measure each unit against original Apertar', model: 'opus' },
    { title: 'Verify', detail: 'a skeptic re-derives every finding from the code', model: 'opus' },
  ],
}

const RAW = '/home/user/apertar-kb/working/merge-review/raw'
const D = '/home/user/build/review/diffs'
const CORE = '/home/user/Apertar-Core'
const UI = '/home/user/Apertar-UI'

const slice = (group, key, file, part, repo, lines, topicHint) => ({
  group, key,
  scope: `One slice of the port's diff of ${file}: read the file ${D}/${part} completely (unified diff, origin/main -> cinemate-port, 10 lines of context; it covers new-file lines ${lines} of ${repo}/${file}). Read around each hunk in ${repo}/${file} for context, and the same region of the original file in the matching *-upstream worktree. To see which port commit wrote a region: git -C ${repo} blame -s -L <a>,<b> cinemate-port -- ${file} | cut -d' ' -f1 | sort | uniq -c | sort -rn, then git -C ${repo} show -s <sha>.`,
  hint: topicHint,
})

const UNITS = [
  // Group A: Core app, hardware config, boot config, build
  slice('A', 'App-1', 'src/ApertarCoreApp.cpp', 'App.part01.diff', CORE, '1-4376', 'Includes, anonymous-namespace helpers, shared UI settings, media helpers near the top of the file.'),
  slice('A', 'App-2', 'src/ApertarCoreApp.cpp', 'App.part02.diff', CORE, '4954-8017', 'Hardware config template, media listing, HTTP helpers, state JSON builders.'),
  slice('A', 'App-3', 'src/ApertarCoreApp.cpp', 'App.part03.diff', CORE, '8408-10674', 'handleRequest, HTTP routes, events, media routes.'),
  slice('A', 'App-4', 'src/ApertarCoreApp.cpp', 'App.part04.diff', CORE, 'about 10813-12560 (one large added block)', 'Workers and helpers the port added in one block: controls worker, trim and merge workers, media watcher, boot config, playback hold, read-only hardware commands.'),
  slice('A', 'App-5', 'src/ApertarCoreApp.cpp', 'App.part05.diff', CORE, '12727-14875', 'handleCommand: the commands the port added or changed.'),
  { group: 'A', key: 'HW-config-text-store', scope: `New files, read completely: ${CORE}/src/hardware/HardwareConfigText.hpp (1141 lines), HardwareConfigStore.hpp, HardwareConfigStore.cpp. Then every use: grep -n "hwconf::\\|configStore()\\|HardwareConfigStore" ${CORE}/src -r. Compare with how original Apertar reads and writes apertar-hardware.conf (each hardware class parses its own section; GET/POST /api/config in the upstream App; the UI's DisplayConfigBridge and Ina219Bridge).`, hint: 'KB design: working/controls/README.md, decisions.md, design-controls.md, critique-code.md. The port calls this "the one writer of the hardware file".' },
  { group: 'A', key: 'HW-controls-model', scope: `New files, read completely: ${CORE}/src/hardware/ControlsModel.hpp, ActionCatalog.hpp, ButtonGesture.hpp, GpioChipInfo.hpp/.cpp, I2cProbe.hpp/.cpp. Then their uses in ${CORE}/src (grep). Compare with upstream's src/hardware/ButtonActionList.hpp and the per-class action normalisers, and with how upstream picks the GPIO chip (chip= / gpiochip= key, "auto").`, hint: 'KB design: working/controls/*. Note: the port\'s Controls page no longer lets the operator choose the GPIO chip (ControlsModel.hpp says chip "stays text-only: the Pi 5\'s header needs neither"); the owner wants the chip definition back because GPIO lines can sit on another chip, for example a microcontroller. Look for every other upstream setting or ability that the port narrowed or hid.' },
  { group: 'A', key: 'HW-input-classes', scope: `The port's diffs of the existing hardware classes: git -C ${CORE} diff --minimal origin/main cinemate-port -- src/hardware/GpioInput.cpp src/hardware/GpioInput.hpp src/hardware/Pcf8574Input.cpp src/hardware/Pcf8574Input.hpp src/hardware/NeoRotary4Input.cpp src/hardware/NeoRotary4Input.hpp src/hardware/GroveAnalogInput.cpp src/hardware/TriggerOutput.cpp src/hardware/TriggerOutput.hpp src/hardware/RecordingIndicatorOutput.cpp src/hardware/Mpu6050RecordingSession.cpp (save it to a file under /home/user/build/review/ and read it all). Mpu6050RecordingSession.cpp lost 257 lines: find out what went and where.`, hint: 'Edge events instead of polling, click/hold gestures, two- and three-way switches, 1-0-1 buttons, IMU config writes through the store. KB: working/controls/*.' },
  { group: 'A', key: 'Boot-config', scope: `New files, read completely: ${CORE}/src/hardware/BootConfigText.hpp (1355 lines), scripts/apertar-boot-config, config/apertar-boot-config.sudoers, tools/boot_config_test.cpp, tools/boot_config_helper_test.sh, the README section on Boot Config (grep -n -i "boot config\\|config.txt" ${CORE}/README.md). Uses: grep -n "bootconf::\\|boot_config\\|boot-config" ${CORE}/src -r. On the UI side: git -C ${UI} show 41ff827 (fan mode through Core). Compare with how original Apertar touches /boot/firmware/config.txt (grep -rn "config.txt" in both *-upstream worktrees) and how it gets root (sudoers, helpers).`, hint: 'KB: architecture/config.md section 7.1, working/handoff-boot-config.md. Three commits here were authored by "Claude".' },
  { group: 'A', key: 'Build-scripts-docs', scope: `git -C ${CORE} diff --minimal origin/main cinemate-port -- CMakeLists.txt README.md .gitignore scripts/start-apertar-core.sh config src/ipc src/web/WebServer.cpp src/ApertarCoreApp.hpp src/main.cpp include third_party/liblj92/README.apertar.md third_party/liblj92/LICENSE (read it all), plus the list of tools/ (ls ${CORE}/tools) and how the host tests are built (header comment of each tools/*_test.cpp). Compare with upstream's CMakeLists.txt, README.md, scripts/ and config/.`, hint: 'RT scheduling env vars in the start script, sudoers and tmpfiles additions, the 1 MiB socket line, vendored liblj92, host tests outside CMake, README growth.' },

  // Group B: camera, recorders, media
  slice('B', 'CC-1', 'src/camera/CameraController.cpp', 'CC.part01.diff', CORE, '1-2712', 'Includes, helpers, sensor tables and fps limits, tuning selection.'),
  slice('B', 'CC-2', 'src/camera/CameraController.cpp', 'CC.part02.diff', CORE, '2779-4423', 'CameraSession internals: requests, phase lock, raw copy hand-off.'),
  slice('B', 'CC-3', 'src/camera/CameraController.cpp', 'CC.part03.diff', CORE, '4584-7264', 'Recording queue, writers, sync thread, safety stop, buffer modes.'),
  slice('B', 'CC-4', 'src/camera/CameraController.cpp', 'CC.part04.diff', CORE, '7391-9614', 'Controller setters, sanitising, Clear HDR holds, ISO limits, mode ladder hooks.'),
  slice('B', 'CC-5', 'src/camera/CameraController.cpp', 'CC.part05.diff', CORE, '9732-11567', 'Configure and sensor mode choice, probe, speed ramp, pre-roll.'),
  slice('B', 'CC-6', 'src/camera/CameraController.cpp', 'CC.part06.diff', CORE, '11794-12814', 'Tail of the controller: state, record start and stop, statistics.'),
  { group: 'B', key: 'Camera-headers', scope: `New files, read completely: ${CORE}/src/camera/FpsCeiling.hpp, FramePhaseLock.hpp, Imx283Modes.hpp, Imx585Modes.hpp, ModeLadder.hpp, ScalerCropGeometry.hpp, TuningTdnStrip.hpp; and git -C ${CORE} diff --minimal origin/main cinemate-port -- src/camera/CameraController.hpp include/apertar/core/Types.hpp. Their tests: tools/imx283_modes_test.cpp, imx585_modes_test.cpp, fps_ceiling_test.cpp, tuning_tdn_strip_test.cpp. Compare with how upstream holds sensor facts (grep -n -i "imx585\\|imx477\\|imx283\\|imx294\\|sensorModel\\|sensorId" /home/user/wt/core-upstream/src/camera/CameraController.cpp | head -80) and with fork main's sensor probe (commit f60e301).`, hint: 'KB: working/sensor-capabilities.md, working/phaselock-answer.md, working/ramp-mode-ladder.md, architecture/drivers.md.' },
  { group: 'B', key: 'Encoders-audio', scope: `git -C ${CORE} diff --minimal origin/main cinemate-port -- src/cdng/CdngEncoder.cpp src/cdng/CdngEncoder.hpp src/lossydng src/mlv src/audio src/util/RecordingDropWarning.hpp (read it all), plus new files read completely: src/cdng/BlackLevel.hpp, src/cdng/LogCurve.hpp, src/util/ClipName.hpp, tools/log_curve_test.cpp, tools/gen_log_curve.py, tools/clip_name_test.cpp, tools/black_level_test.cpp, tools/dng_payload_write_test.cpp/.sh.`, hint: 'Direct payload write, DONTNEED modes, Log curve in the files, MLV levels, audio writer thread and ring, drift fit, clip name templates. KB: working/drop-frames/README.md, working/dng-chain-answer.md, working/cinemate-lessons.md section 3.' },
  { group: 'B', key: 'Media-fault-tune', scope: `New files, read completely: ${CORE}/src/util/MediaFault.hpp, MediaIntent.hpp, MediaProbe.hpp, MediaProfile.hpp, MediaTune.hpp, CfeHat.hpp, scripts/apertar-media-tune, scripts/apertar-tune (487 lines), config/apertar-media-tune.conf, config/apertar-media.sudoers, config/apertar-media.tmpfiles.conf. Uses: grep -rn "mediafault::\\|mediaprobe::\\|mediaprofile::\\|mediatune::\\|MediaFault\\|MediaProbe\\|MediaProfile\\|MediaTune\\|CfeHat\\|cfehat::" ${CORE}/src | grep -v "^${CORE}/src/util". On the UI side: git -C ${UI} show 160898c dc471c1 (media state, automounter). Compare with upstream's media handling (grep -n -i "mount\\|eject\\|statvfs\\|/media/RAW" /home/user/wt/core-upstream/src/ApertarCoreApp.cpp | head -80) and its CFE automounter (ui-upstream/src/CfeAutomounter.cpp).`, hint: 'KB: working/yank-answer.md, working/storage-answer.md, working/drop-frames/media-tune-file.md, working/cinemate-lessons.md sections 4-5.' },
  { group: 'B', key: 'Media-buffer-split', scope: `New files, read completely: ${CORE}/src/util/StoragePreroll.hpp, BufferBudget.hpp, src/cdng/ClipMerge.hpp, src/cdng/FramePath.hpp, scripts/apertar-media-trim, config/apertar-media-trim.sudoers, tools/flatten_clip.py, tools/storage_preroll_test.cpp, buffer_budget_test.cpp, storage_buffer_conf_test.cpp, clip_merge_test.cpp, frame_path_test.cpp, media_trim_test.sh. Uses: grep -rn "bufferbudget::\\|storagepreroll::\\|clipmerge::\\|framepath::\\|StoragePreroll\\|BufferBudget" ${CORE}/src | grep -v "/util/\\|/cdng/ClipMerge\\|/cdng/FramePath".`, hint: 'RAM write buffer with safety stop, storage pre-roll, drive trim, split takes into part folders and merge them when idle. KB: working/drop-frames/README.md, working/drop-frames/nvme-campaign/probe-exfat-dir.md. Note atomics exposed through free functions such as bufferbudget::clipMergeRequest().' },

  // Group C: WebUI
  slice('C', 'WCP-01', 'src/web/WebControlPage.cpp', 'WCP.part01.diff', CORE, '22-1804', 'CSS.'),
  slice('C', 'WCP-02', 'src/web/WebControlPage.cpp', 'WCP.part02.diff', CORE, '1969-3960', 'CSS, continued.'),
  slice('C', 'WCP-03', 'src/web/WebControlPage.cpp', 'WCP.part03.diff', CORE, '4041-7162', 'HTML body: cards and panes.'),
  slice('C', 'WCP-04', 'src/web/WebControlPage.cpp', 'WCP.part04.diff', CORE, '7442-8900', 'JS: state rendering, pills, value lists.'),
  slice('C', 'WCP-05', 'src/web/WebControlPage.cpp', 'WCP.part05.diff', CORE, '9168-11399', 'JS: settings, presets, favourites.'),
  slice('C', 'WCP-06', 'src/web/WebControlPage.cpp', 'WCP.part06.diff', CORE, '11639-13823', 'JS: mode ladder, sensor modes, media.'),
  slice('C', 'WCP-07', 'src/web/WebControlPage.cpp', 'WCP.part07.diff', CORE, '13893-16360', 'JS: playback overlay, viewer, system pane.'),
  slice('C', 'WCP-08', 'src/web/WebControlPage.cpp', 'WCP.part08.diff', CORE, 'about 16406-16620', 'JS: one added block.'),
  slice('C', 'WCP-09', 'src/web/WebControlPage.cpp', 'WCP.part09.diff', CORE, 'about 16622-18740 (one large added block)', 'JS: the Controls and Config pages (cards per device, Listen, review, undo, text editor with diff, history, boot config).'),
  slice('C', 'WCP-10', 'src/web/WebControlPage.cpp', 'WCP.part10.diff', CORE, '18748-20840', 'JS: tail, event wiring, init.'),

  // Group D: UI, playback, drivers
  { group: 'D', key: 'UI-bridges', scope: `git -C ${UI} diff --minimal origin/main cinemate-port -- src/ApertarControlBridge.hpp src/SettingsBridge.cpp src/SettingsBridge.hpp src/MediaStatusBridge.cpp src/MediaStatusBridge.hpp src/DisplayConfigBridge.cpp src/DisplayConfigBridge.hpp src/Ina219Bridge.cpp src/SystemActionBridge.cpp src/CfeAutomounter.cpp src/ApertarPreviewSocketClient.cpp src/ApertarPreviewSocketClient.hpp src/main.cpp CMakeLists.txt qml.qrc (save to a file under /home/user/build/review/ and read it all). DisplayConfigBridge.cpp lost about 300 lines and Ina219Bridge.cpp 280: find out what went, and whether a behaviour of original Apertar went with it.`, hint: 'The touch UI no longer writes a default apertar-hardware.conf; HDMI 1080p became the display fallback; fan mode goes through Core. KB: architecture/ui.md, llm/ui-map.md.' },
  slice('D', 'UI-control-bridge', 'src/ApertarControlBridge.cpp', 'UI-ControlBridge.part01.diff', UI, '9-2642', 'New properties and invokables, state mapping, event handling.'),
  { group: 'D', key: 'UI-settings-qml', scope: `Read completely: ${D}/UI-SettingsPage.part01.diff (the port's diff of ${UI}/qml/SettingsPage.qml) and the new files ${UI}/qml/ClipNameCard.qml (601 lines), ${UI}/qml/ClipNamePill.qml, ${UI}/qml/ControlsWarning.qml. Compare with how upstream SettingsPage.qml registers sections and items and which components it reuses (/home/user/apertar-kb/llm/ui-map.md section 1.1).`, hint: 'Value lists, recording indicators, timecode split, Frames/RAM, Log, storage pre-roll, clip names card, Controls card.' },
  { group: 'D', key: 'UI-camera-qml', scope: `Read completely: ${D}/UI-CameraPage.part01.diff (the port's diff of ${UI}/qml/CameraPage.qml) and git -C ${UI} diff --minimal origin/main cinemate-port -- qml/StatusChip.qml qml/TopDropdownStat.qml qml/ExternalMonitorWindow.qml qml/AudioMeterOverlay.qml qml/DroppedFrameWarning.qml. Compare with upstream's CameraPage.qml structure (/home/user/apertar-kb/llm/ui-map.md section 1.2).`, hint: 'Pickers from value lists, italic camera-decided values, buffer bar and safety-stop pill, PRE-ROLL pill, dropped-frame count, recording frame.' },
  { group: 'D', key: 'Playback', scope: `New files, read completely: ${CORE}/src/playback/PlaybackHold.hpp, ClipFrames.hpp, DngTags.hpp, ClipProbe.hpp, DngFrameReader.hpp, RawRender.hpp, DecodeSlots.hpp, PlaybackFrames.hpp, PlaybackFrames.cpp, tools/dng_limits_test.cpp, third_party/liblj92/README.apertar.md. Uses in App: grep -n "playback::\\|/api/media" ${CORE}/src/ApertarCoreApp.cpp. On the UI side: git -C ${UI} diff --minimal origin/main cinemate-port -- src/cdngimageprovider.cpp src/cliplistmodel.cpp src/playbackcontroller.cpp src/ClipFrameFiles.hpp. Compare with upstream: the touch UI owns playback (ui-upstream/src/dngdecoder.cpp, cdngimageprovider.cpp, playbackcontroller.cpp, third_party/), Core's upstream /api/media routes only list, download and delete.`, hint: 'The port made Core decode and render DNG frames for a WebUI clip browser and viewer: a second DNG decoder in the system, with liblj92 vendored in Core. KB: working/playback/README.md, decisions.md, design-playback.md.' },
  { group: 'D', key: 'Driver-imx585', scope: `/home/user/imx585-v4l2-driver: git log --reverse --format='%h %ad %s' --date=short origin/apertar..cinemate-port (55 commits) and git diff origin/apertar cinemate-port --stat; read the diff of imx585.c by chapter (git diff origin/apertar cinemate-port -- imx585.c > /home/user/build/review/imx585.diff, then read it in parts), APERTAR.md, README.md diff, imx585-overlay.dts diff, tools/. The Apertar baseline for this driver is branch apertar (will127534 base 1644466 plus the 18 crop modes the 1.6.0 image shipped). Also how Core depends on the driver's mode set: ${CORE}/src/camera/Imx585Modes.hpp.`, hint: 'This branch merges the mode set Cinemate uses. For the original developer the question is: what does an Apertar user lose or gain by installing it, is every mode Apertar 1.6.0 requests still there, which controls changed defaults. KB: architecture/drivers.md, fork-log.md driver rows.' },
  { group: 'D', key: 'Driver-imx283', scope: `/home/user/imx283-v4l2-driver: git log --reverse --format='%h %ad %s' --date=short origin/master..cinemate-port (93 commits) and git diff origin/master cinemate-port --stat; read the diff of imx283.c by chapter (git diff origin/master cinemate-port -- imx283.c > /home/user/build/review/imx283.diff, then read it in parts), APERTAR.md, EXPERIMENTAL_CROPS.md, README.md diff, overlay diff, dkms files. Also how Core depends on it: ${CORE}/src/camera/Imx283Modes.hpp and the IMX283 parts of CameraController.cpp (grep -n -i imx283). Original Apertar: does 1.6.0 support the IMX283 at all (grep -rn -i imx283 /home/user/wt/core-upstream /home/user/wt/ui-upstream)?`, hint: 'A sensor family the port adds to Apertar (57 modes). History shows many fix and revert commits.' },
]

const COMMON = `You are part of a merge review for Patrik's Apertar camera project. First read /home/user/apertar-kb/working/merge-review/BRIEF.md (paths, vocabulary, rules) and follow it. The owner's intent is in its first section: the port must read as original Apertar to the original developer; where it brought its own architecture, that is to be re-implemented the Apertar way; new architecture stays only where it was carefully considered.`

const INV_SCHEMA = {
  type: 'object',
  properties: {
    unit: { type: 'string' }, report_path: { type: 'string' }, summary: { type: 'string' },
    features: { type: 'array', items: { type: 'object', properties: {
      name: { type: 'string' }, operator_gets: { type: 'string', description: 'One plain sentence: what the camera operator can now do or see' },
      commits: { type: 'array', items: { type: 'string' } },
      commands: { type: 'array', items: { type: 'string' }, description: 'Socket commands and HTTP routes added or changed' },
      state_fields: { type: 'array', items: { type: 'string' } },
      config_keys: { type: 'array', items: { type: 'string' }, description: 'file:[section] key' },
      env_vars: { type: 'array', items: { type: 'string' } },
      ui_elements: { type: 'array', items: { type: 'string' } },
      files: { type: 'array', items: { type: 'string' } },
      relation_to_upstream: { type: 'string', description: 'extends an upstream function in place / adds a parallel path beside upstream code / replaces upstream code / entirely new area' },
      tested: { type: 'string', description: 'What the commit message or fork-log says was tested, and where (Pi, desk, not at all)' },
    }, required: ['name', 'operator_gets', 'relation_to_upstream'] } },
    upstream_code_changed: { type: 'array', items: { type: 'object', properties: {
      region: { type: 'string' }, where: { type: 'string' }, change: { type: 'string' },
      kind: { type: 'string', enum: ['extended-in-place', 'rewritten', 'removed', 'moved', 'behaviour-changed'] },
    }, required: ['region', 'where', 'change', 'kind'] } },
    new_abstractions: { type: 'array', items: { type: 'object', properties: {
      name: { type: 'string' }, files: { type: 'array', items: { type: 'string' } }, purpose: { type: 'string' },
      used_by: { type: 'string' }, upstream_equivalent: { type: 'string', description: 'What upstream uses for the same job, with path:line, or "none"' },
    }, required: ['name', 'purpose', 'upstream_equivalent'] } },
    removed_or_narrowed: { type: 'array', items: { type: 'object', properties: { what: { type: 'string' }, where: { type: 'string' }, effect: { type: 'string' } }, required: ['what', 'where', 'effect'] } },
    board_assumptions: { type: 'array', items: { type: 'object', properties: { what: { type: 'string' }, where: { type: 'string' } }, required: ['what', 'where'] } },
  },
  required: ['unit', 'report_path', 'summary', 'features', 'upstream_code_changed', 'new_abstractions'],
}

const FINDING = {
  type: 'object',
  properties: {
    id: { type: 'string' },
    title: { type: 'string' },
    category: { type: 'string', enum: ['mismatch', 'new-ground', 'removed-upstream-behaviour', 'protocol', 'bug', 'pi-compat', 'slop', 'duplication', 'security'] },
    severity: { type: 'string', enum: ['blocker', 'major', 'minor', 'nit'] },
    where: { type: 'array', items: { type: 'string' }, description: 'path:line@cinemate-port' },
    port_way: { type: 'string' },
    apertar_way: { type: 'string', description: 'How original Apertar does the same kind of thing, with path:line@upstream-1.6.0; "no precedent" for new-ground' },
    why_it_matters: { type: 'string', description: 'What the original developer would trip over, or what breaks' },
    rework: { type: 'string', description: 'The concrete Apertar-style change: which functions and files, what moves where, what is deleted' },
    effort: { type: 'string', enum: ['S', 'M', 'L'] },
    deliberate: { type: 'string', enum: ['yes', 'no', 'unknown'] },
    deliberate_evidence: { type: 'string' },
    rework_risk: { type: 'string' },
  },
  required: ['id', 'title', 'category', 'severity', 'where', 'port_way', 'apertar_way', 'why_it_matters', 'rework', 'effort', 'deliberate'],
}
const REV_SCHEMA = {
  type: 'object',
  properties: {
    unit: { type: 'string' }, report_path: { type: 'string' }, summary: { type: 'string' },
    conforms: { type: 'array', items: { type: 'string' }, description: 'Things in this unit that follow the Apertar way well (one line each, with a pointer)' },
    abstraction_verdicts: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, verdict: { type: 'string', enum: ['keep', 'simplify', 'rework-to-upstream-pattern'] }, reason: { type: 'string' } }, required: ['name', 'verdict', 'reason'] } },
    findings: { type: 'array', items: FINDING },
  },
  required: ['unit', 'report_path', 'summary', 'findings'],
}


// v2: units come from args.units (keys). Two lanes, each takes its units one after the other and runs a unit's three
// stages back to back, so verified findings arrive unit by unit instead of after every inventory is done.
// args.skipInv: keys whose inventory report already exists on disk (stage 1 is skipped for them).
const wanted = (args && args.units) ? args.units : []
const skipInv = new Set((args && args.skipInv) ? args.skipInv : [])
const units = wanted.map(k => UNITS.find(u => u.key === k)).filter(Boolean)
log(`port-review v2: ${units.length} units (${units.map(u => u.key).join(', ')})`)

const invStage = u => agent(`${COMMON}\n\nSTAGE 1 of 3: INVENTORY of unit "${u.key}". Say what the port added or changed here, without judging it yet.\n\nSCOPE: ${u.scope}\nHINT: ${u.hint}\n\nRead the scope completely. For each changed region decide which feature it belongs to and which port commits wrote it. Consult /home/user/apertar-kb/fork-log.md for the commits' recorded status and tests. Record: every operator-visible feature touching this unit; every socket command, HTTP route, state field, event, config key, env var, file on disk and UI element added or changed; every region of ORIGINAL code that was modified (and whether it was extended in place, rewritten, removed, moved or changed behaviour); every new abstraction (class, namespace, header-only module, worker thread, helper script) with what upstream uses for the same job; everything upstream had that the port removed, narrowed or hid; every assumption about the board (Pi 5 / CM5 only, four cores, RP1, PCIe, gpiochip numbering, I2C bus numbers, RAM size, fan). Write full notes to ${RAW}/inv-${u.key}.md (tables), then return the structured inventory.`,
  { label: `inv:${u.key}`, phase: 'Inventory', schema: INV_SCHEMA, model: 'sonnet' })

const revStage = (u, inv) => agent(`${COMMON}\n\nSTAGE 2 of 3: REVIEW of unit "${u.key}" against original Apertar.\n\nSCOPE: ${u.scope}\nHINT: ${u.hint}\nINVENTORY from stage 1: ${inv.report_path} (read it first; it lists features, changed upstream regions, new abstractions, removed things).\n\nYARDSTICK: if /home/user/apertar-kb/working/merge-review/apertar-conventions.md exists, read it and cite its rule ids. If not, read whichever of ${RAW}/conv-*.md exist (they describe how original Apertar is built, topic by topic; some may still be missing). In every case open the ORIGINAL code for the same kind of thing in the *-upstream worktree yourself: a finding of category "mismatch" needs both sides quoted.\n\nJUDGE, in this order of importance (milestone 1 is design conformance):\n1. mismatch: the port solves something original Apertar already has a pattern for, in another way (its own layer, file format, protocol shape, naming, threading model, a generic framework where upstream writes it out by hand, nested JSON where upstream is flat ...). Give the rework that turns it into the upstream pattern.\n2. removed-upstream-behaviour: something original Apertar offers that the port removed, narrowed, hid or changed the default of. Example already known and already fixed on the improvement branch: upstream lets the operator name the GPIO chip for buttons and outputs; the port's Controls page had dropped that setting.\n3. new-ground: no upstream precedent. Is the shape chosen the least foreign one for this code base? Verdict keep / simplify / rework, with reasons a maintainer would accept. Check whether the KB or the commit message shows the contributor weighed it (deliberate yes/no).\n4. protocol: socket or HTTP changes that break an unmodified original UI or original Core, or the flat JSON parser.\n5. Also record what you notice of: bug (give the failing input), pi-compat (works only on some Raspberry Pi models), slop (tutorial or ticket numbers such as T33 or Q21 in code or UI text, comments that narrate history, dead code, debug leftovers, over-built generality, env-var knobs left from experiments), duplication, security (root helpers, sudoers, unauthenticated routes that write system files).\n\nBe calibrated. Do not report code that follows the upstream pattern. Do not report personal taste. Severity: blocker = the original developer would refuse the merge or it breaks original behaviour; major = clearly foreign or risky; minor = small deviation; nit. For every abstraction listed in the inventory give a verdict. Also list what conforms well, so the handoff can say so. Write full notes to ${RAW}/rev-${u.key}.md, then return the structured result. Finding ids: "${u.key}-F<n>".`,
  { label: `rev:${u.key}`, phase: 'Review', schema: REV_SCHEMA, model: 'opus' })

const verStage = (u, rev) => {
  const list = rev.findings.map(f => `### ${f.id} [${f.category}, ${f.severity}] ${f.title}\nwhere: ${(f.where || []).join(' ; ')}\nport: ${f.port_way}\napertar way: ${f.apertar_way}\nmatters: ${f.why_it_matters}\nrework: ${f.rework}\neffort ${f.effort}, deliberate ${f.deliberate} ${f.deliberate_evidence || ''}`).join('\n\n')
  return agent(`${COMMON}\n\nSTAGE 3 of 3: SKEPTIC for unit "${u.key}". A reviewer produced the findings below (notes: ${rev.report_path}). For EACH finding open the code yourself, on both sides, and try to knock it down: Is the port line really there and does it do what is claimed? Does original Apertar really do it the other way, or does upstream do the same thing somewhere (then it is not a mismatch)? Is the proposed rework actually possible without losing the feature, and is it really closer to the original code? Is the severity right? Is "deliberate" right (check the commit message with git show -s, /home/user/apertar-kb/fork-log.md and the KB design pages named in the hint)? Drop findings that do not survive. Correct the ones that are half right. You may add a finding only if you hit something serious while checking. Append "## Skeptic" to ${rev.report_path} with a verdict per id (stands / corrected / dropped, one line why), and below it a section "## Final findings" holding every surviving finding in full (id, category, severity, where, port way, Apertar way, why it matters, rework, effort, deliberate), so the file alone is enough for the next reader. Return the surviving findings in full, corrected, in the same schema.\n\nHINT for this unit: ${u.hint}\n\nFINDINGS:\n${list}`,
    { label: `verify:${u.key}`, phase: 'Verify', schema: REV_SCHEMA, model: 'opus' })
}

const runUnit = async u => {
  let inv
  if (skipInv.has(u.key)) inv = { unit: u.key, report_path: `${RAW}/inv-${u.key}.md`, features: [], reused: true }
  else inv = await invStage(u)
  if (!inv) { log(`${u.key}: inventory failed`); return { unit: u.key, failed: 'inventory' } }
  const rev = await revStage(u, inv)
  if (!rev) { log(`${u.key}: review failed`); return { unit: u.key, inv, failed: 'review' } }
  let fin = rev, verified = false
  if (rev.findings.length) {
    const v = await verStage(u, rev)
    if (v) { fin = v; verified = true } else log(`${u.key}: skeptic failed, findings unverified`)
  } else verified = true
  log(`${u.key}: ${fin.findings.length} findings${verified ? '' : ' (unverified)'}; blocker ${fin.findings.filter(f => f.severity === 'blocker').length}, major ${fin.findings.filter(f => f.severity === 'major').length}`)
  return { unit: u.key, inv, rev: fin, verified }
}
const lane = async list => { const out = []; for (const u of list) out.push(await runUnit(u)); return out }
const lanes = [units.filter((u, i) => i % 2 === 0), units.filter((u, i) => i % 2 === 1)].filter(l => l.length)
const done = (await parallel(lanes.map(l => () => lane(l)))).filter(Boolean).flat()

return done.map(r => ({
  unit: r.unit, failed: r.failed || null, verified: !!r.verified,
  inv_report: r.inv ? r.inv.report_path : null, rev_report: r.rev ? r.rev.report_path : null,
  features: r.inv && r.inv.features ? r.inv.features.map(f => ({ name: f.name, operator_gets: f.operator_gets, relation: f.relation_to_upstream })) : [],
  abstractions: r.rev && r.rev.abstraction_verdicts ? r.rev.abstraction_verdicts : [],
  findings: r.rev ? r.rev.findings.map(f => ({ id: f.id, title: f.title, category: f.category, severity: f.severity, effort: f.effort, deliberate: f.deliberate, where: (f.where || []).slice(0, 3), rework: f.rework })) : [],
}))
