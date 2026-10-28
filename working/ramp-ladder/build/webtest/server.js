// Mock of Core's web endpoints for the T34 WebUI (Mode Ladder, Speed Ramp, Activated sensor modes).
// GET / serves the page extracted from WebControlPage.cpp on every load, /api/state a snapshot,
// POST /api/command applies the commands the page sends. /__set merges into the state, /__log
// lists the commands, /__ladder sets the saved ladder. Ladder logic follows ModeLadder.hpp.
const http = require("http");
const fs = require("fs");
const path = require("path");
const cppPath = process.argv[2] || path.join(__dirname, "../core/src/web/WebControlPage.cpp");
const PORT = Number(process.env.PORT || 8765);
const EPS = 0.0005;
const COMPS = ["none", "lossless_jpeg", "lossy_3to1", "lossy_5to1"];
const COMP_LABEL = { none: "Uncompressed", lossless_jpeg: "Lossless JPEG", lossy_3to1: "Lossy 3:1", lossy_5to1: "Lossy 5:1" };
const LOSSY_HDR = "Lossy cDNG does not support Clear HDR. Use lossless or uncompressed cDNG, or turn Clear HDR off.";

function page() {
  const src = fs.readFileSync(cppPath, "utf8");
  return src.slice(src.indexOf('R"APERTAR(') + 10, src.indexOf(')APERTAR"'));
}

// IMX585 pool: probed modes in Core identity, with ScalerCropMaximum windows (3840x2200 readout area).
const pool = [];
function addMode(width, height, bits, hdr, ceiling, crop, binning) {
  pool.push({ width, height, bits, clear_hdr: hdr, ceiling, crop, binning });
}
addMode(3840, 2160, 16, true, 25, { x: 0, y: 0, width: 3840, height: 2200 }, 1);
addMode(3840, 2160, 12, true, 30, { x: 0, y: 0, width: 3840, height: 2160 }, 1);
const crops = [2076, 2024, 1920, 1744, 1728, 1632, 1608, 1536, 1504];
const crops2k = [1038, 1012, 960, 872, 864, 816, 804, 768, 752];
for (const bits of [12, 10]) {
  addMode(3840, 2160, bits, false, 60, { x: 0, y: 0, width: 3840, height: 2160 }, 1);
  for (const h of crops) addMode(3840, h, bits, false, 60, { x: 0, y: (2160 - h) / 2, width: 3840, height: h }, 1);
  addMode(1920, 1080, bits, false, 60, { x: 0, y: 0, width: 3840, height: 2160 }, 2);
  for (const h of crops2k) addMode(1920, h, bits, false, 60, { x: 0, y: (2160 - 2 * h) / 2, width: 3840, height: 2 * h }, 2);
}
// A real crop-in: a 2560x1440 window from the middle of the sensor, not binned.
addMode(2560, 1440, 12, false, 60, { x: 640, y: 360, width: 2560, height: 1440 }, 1);
const AREA = { width: 3840, height: 2200 };

const st = {
  state: "ready", recording: false, recording_error: "", fps_phase_lock_active: false,
  fps_ramp_stepping: false, fps_take_base: 0, sound_recording: false, timelapse_active: false,
  backend_name: "libcamera", sensor: "imx585", resolution: "3840x2160", width: 3840, height: 2160,
  fps: 25, iso: 800, iso_auto: false, shutter_us: 20000, shutter_auto: false, exposure_compensation: 0,
  exposure_compensation_available: false, wb_kelvin: 5600, wb_auto: false, wb_available: true,
  timecode_mode: "rec_run", recording_format: "cdng", cdng_compression: "none",
  recording_capabilities: { raw_recording: true, raw_compression: true, prores: true },
  lossy_dng_ratio: "3to1", prores_profile: "422", clear_hdr: true, fps_phase_lock: false, fps_ramp: true,
  fps_ramp_keep_exposure: false, raw_bit_depth: 16, h264_width: 1920, h264_height: 1080,
  af_mode: "manual", media_mounted: true, media_alive: true, media_state: "mounted",
  ui: { photo_mode_enabled: false }, system: { write_speed_result_text: "450 MB/s" },
  capture: { codec: "CinemaDNG", sensor: "imx585" }, media_drives: [],
};
let buildMax = 50;
let probeOff = false;   // /__set {probe_off: true}: get_mode_ladder sends no pool, as with APERTAR_SENSOR_PROBE=0
let dryError = "";     // /__set {dry_error: "..."}: an error only Core knows, added to dry runs and saves
let ladder = { enabled: true, rungs: parseRungs("3840x2160:16:hdr:none:25,3840x2160:12:sdr:none").rungs };
const log = [];

const key = (m) => m.width + "x" + m.height + ":" + m.bits + ":" + (m.clear_hdr ? "hdr" : "sdr");
const poolEntry = (m) => pool.find((p) => key(p) === key(m));
const num = (v) => String(Number(v));
const label = (r) => (r.width === 3840 && r.height === 2160 ? "4K" : r.width + "x" + r.height) + (r.clear_hdr ? " Clear HDR " : " SDR ") + r.bits + "-bit";
const classLabel = (r) => (r.clear_hdr ? "ClearHDR" : "SDR") + r.bits;
const aspectText = (r) => { const q = r.width / r.height; return Math.abs(q - 16 / 9) < 0.01 ? "" : q.toFixed(2) + ":1"; };
const cropIn = (c) => !!c && c.width < AREA.width;

function ceilingIn(m, comp) {
  const p = poolEntry(m);
  if (!p) return { ceiling: 0, reason: label(m) + " is not a mode of this sensor." };
  if (comp.startsWith("lossy") && m.clear_hdr) return { ceiling: 0, reason: LOSSY_HDR };
  const c = comp === "lossless_jpeg" ? Math.min(p.ceiling, 30) : p.ceiling;
  return { ceiling: buildMax > 0 ? Math.min(c, buildMax) : c, reason: "" };
}

function parseRungs(text) {
  const rungs = [];
  for (const item of String(text).split(",")) {
    const f = item.split(":");
    const m = /^(\d+)x(\d+)$/.exec(f[0] || "");
    if (f.length < 3 || f.length > 5 || !m || !["10", "12", "16"].includes(f[1]) || !["hdr", "sdr"].includes(f[2]))
      return { error: '"' + item + '": expected WIDTHxHEIGHT:BITS:hdr|sdr[:COMPRESSION][:FPS], with BITS 10, 12 or 16 and COMPRESSION none, lossless_jpeg, lossy_3to1 or lossy_5to1.' };
    const r = { width: +m[1], height: +m[2], bits: +f[1], clear_hdr: f[2] === "hdr", compression: "none", threshold: 0 };
    for (const extra of f.slice(3)) {
      if (!extra) continue;
      if (COMPS.includes(extra)) r.compression = extra;
      else if (Number(extra) > 0 && Number(extra) <= 280) r.threshold = Number(extra);
      else return { error: '"' + item + '": the FPS must be above 0 and at most 280, or empty.' };
    }
    rungs.push(r);
  }
  if (!rungs.length || (rungs.length === 1 && !String(text))) return { error: "Add at least one resolution." };
  return { rungs };
}
const rungsText = (rungs) => rungs.map((r) => key(r) + ":" + r.compression + (r.threshold > 0 ? ":" + num(r.threshold) : "")).join(",");

// Each rung's state: ownCompression (validation, pool) or as the camera would run it now.
function currentComp() {
  if (st.recording_format === "lossydng") return st.lossy_dng_ratio === "5to1" ? "lossy_5to1" : "lossy_3to1";
  if (st.recording_format === "cdng") return st.cdng_compression;
  return "none";
}
const compressionApplies = () => st.recording_format === "cdng" || st.recording_format === "lossydng";
function rungState(r, own) {
  const comp = own || compressionApplies() ? r.compression : "none";
  const valid = !!poolEntry(r);
  const p = poolEntry(r);
  const crop = probeOff || !p ? null : p.crop, binning = probeOff || !p ? 0 : p.binning;
  // H.264 and ProRes: the sanitiser turns every resolution into the processed-video mode (4K 10-bit SDR, 30 fps without the probe).
  if (!own && ["h264", "prores"].includes(st.recording_format))
    return { valid, usable: false, modeCeiling: Math.min(30, buildMax || 280), reason: "The Mode Ladder works in CinemaDNG and MLV video.", crop, binning };
  const { ceiling, reason } = ceilingIn(r, comp);
  return { valid, usable: valid && ceiling > 0, modeCeiling: ceiling, reason, crop, binning };
}
const rungCeiling = (r, s) => (!s.usable ? 0 : r.threshold > 0 ? Math.min(r.threshold, s.modeCeiling) : s.modeCeiling);

function validate(rungs, states) {
  const errors = [], warnings = [];
  if (!rungs.length) errors.push("Add at least one resolution.");
  if (rungs.length > 8) errors.push("At most 8 resolutions.");
  let reached = 0, previous = -1;
  rungs.forEach((r, i) => {
    const repeat = rungs.slice(0, i).findIndex((o) => key(o) === key(r));
    if (repeat >= 0) { errors.push("Resolution " + (i + 1) + " repeats resolution " + (repeat + 1) + " (" + label(r) + ")."); return; }
    const s = states[i];
    if (!s.valid) { errors.push("Resolution " + (i + 1) + ": " + label(r) + " is not a mode of this sensor."); return; }
    if (!s.usable) { errors.push("Resolution " + (i + 1) + " (" + label(r) + ", " + COMP_LABEL[r.compression] + ") cannot record: " + s.reason); return; }
    if (r.threshold > s.modeCeiling + EPS) { errors.push("Resolution " + (i + 1) + ": " + num(r.threshold) + " fps is above this mode's ceiling of " + num(s.modeCeiling) + " fps."); return; }
    const c = rungCeiling(r, s);
    if (c <= reached + EPS) {
      errors.push(r.threshold > 0 && s.modeCeiling > reached + EPS
        ? "Resolution " + (i + 1) + " must go above " + num(reached) + " fps, where the resolutions above stop."
        : "Resolution " + (i + 1) + " would never be used: the ones above already reach " + num(reached) + " fps.");
      return;
    }
    if (previous >= 0) {
      const p = rungs[previous], parts = [];
      if (p.clear_hdr !== r.clear_hdr || p.bits !== r.bits) parts.push((p.clear_hdr ? "Clear HDR " : "SDR ") + p.bits + "-bit → " + (r.clear_hdr ? "Clear HDR " : "SDR ") + r.bits + "-bit");
      if (p.width !== r.width || p.height !== r.height) parts.push("picture " + p.width + "×" + p.height + " → " + r.width + "×" + r.height);
      if (p.compression !== r.compression) parts.push(COMP_LABEL[p.compression] + " → " + COMP_LABEL[r.compression]);
      warnings.push("Above " + num(reached) + " fps: " + parts.join(", ") + ". Switches between takes only; in a take FPS stops at " + num(reached) + ".");
    }
    reached = c;
    previous = i;
  });
  if (st.recording_format === "mlv") warnings.push("MLV records uncompressed: each resolution's compression applies in cDNG and lossy DNG.");
  if (rungs.some((r) => r.compression === "lossless_jpeg")) warnings.push("Lossless JPEG caps ISO at 800 on this sensor.");
  return { errors, warnings };
}

function chooseRung(rungs, states, target) {
  let best = -1, bestC = 0;
  for (let i = 0; i < rungs.length; i++) {
    const c = rungCeiling(rungs[i], states[i]);
    if (c <= 0) continue;
    if (c >= target - EPS) return i;
    if (c > bestC) { bestC = c; best = i; }
  }
  return best;
}
const currentMode = () => ({ width: st.width, height: st.height, bits: st.raw_bit_depth, clear_hdr: st.clear_hdr });
const runtimeStates = () => ladder.rungs.map((r) => rungState(r, false));
const active = () => ladder.enabled && !st.ui.photo_mode_enabled && ["cdng", "lossydng", "mlv"].includes(st.recording_format)
  && runtimeStates().some((s) => s.usable);
const running = () => ladder.rungs.findIndex((r) => key(r) === key(currentMode()) && (!compressionApplies() || r.compression === currentComp()));
function modeCeiling() {
  const m = currentMode(), p = poolEntry(m);
  if (["h264", "prores"].includes(st.recording_format)) return Math.min(p ? p.ceiling : 30, buildMax || 280, 50);
  return ceilingIn(m, currentComp()).ceiling || 30;
}

function moveTo(r) {
  st.width = r.width; st.height = r.height; st.raw_bit_depth = r.bits; st.clear_hdr = r.clear_hdr;
  st.resolution = r.width + "x" + r.height;
  if (compressionApplies()) {
    if (r.compression.startsWith("lossy")) { st.recording_format = "lossydng"; st.lossy_dng_ratio = r.compression === "lossy_5to1" ? "5to1" : "3to1"; }
    else { st.recording_format = "cdng"; st.cdng_compression = r.compression; }
  }
}
// Core's ladderRewriteLocked: off a take, the ladder picks the resolution for fps; returns true on a mode change.
function rewrite(fps) {
  if (st.recording || !active()) return false;
  const states = runtimeStates();
  const i = chooseRung(ladder.rungs, states, fps);
  if (i < 0) return false;
  const before = key(currentMode());
  moveTo(ladder.rungs[i]);
  st.fps = Math.min(fps, rungCeiling(ladder.rungs[i], states[i]));
  return key(currentMode()) !== before;
}

function derived() {
  const states = runtimeStates(), on = active(), run = running();
  const ceil = Math.max(0, ...ladder.rungs.map((r, i) => rungCeiling(r, states[i])));
  st.ladder_enabled = ladder.enabled;
  st.ladder_active = on;
  st.ladder_rung = on ? run + 1 : 0;
  st.ladder_count = ladder.rungs.length;
  st.fps_max = on ? ceil : modeCeiling();
  st.fps_take_max = on && run >= 0 ? rungCeiling(ladder.rungs[run], states[run]) : modeCeiling();
  st.ladder_tops = on ? ladder.rungs.map((r, i) => rungCeiling(r, states[i])) : [];
  if (!on) st.ladder_text = "";
  else if (run < 0) st.ladder_text = "Mode Ladder on · the next FPS pick chooses the resolution";
  else {
    const r = ladder.rungs[run], a = aspectText(r);
    st.ladder_text = "Resolution " + (run + 1) + " · " + r.width + "×" + r.height + (cropIn(states[run].crop) ? " crop in" : "")
      + " · " + classLabel(r) + (a ? " " + a : "") + " · ≤" + num(rungCeiling(r, states[run])) + " · " + (compressionApplies() ? COMP_LABEL[r.compression] : "MLV");
  }
  st.capture.codec = st.recording_format === "mlv" ? "MLV" : (st.recording_format === "h264" ? "H.264" : "CinemaDNG");
  return st;
}

function modeLadderJson(rungs, enabled, extra) {
  const own = rungs.map((r) => rungState(r, true));
  const states = rungs.map((r) => rungState(r, false));
  const v = validate(rungs, own);
  const runIndex = rungs === ladder.rungs ? running() : -1;
  let from = 0;
  return {
    enabled, active: active(), rungs_text: rungsText(rungs), format: st.recording_format, compression_applies: compressionApplies(),
    build_max: buildMax, ceiling: Math.max(0, ...rungs.map((r, i) => rungCeiling(r, states[i]))),
    running_rung: runIndex + 1, running_text: st.ladder_text, sensor_area: probeOff ? { width: 0, height: 0 } : AREA,
    rungs: rungs.map((r, i) => {
      const s = states[i], c = rungCeiling(r, s);
      const out = { width: r.width, height: r.height, bits: r.bits, clear_hdr: r.clear_hdr, label: label(r), class: classLabel(r),
        size: r.width + "×" + r.height, compression: r.compression, compression_label: COMP_LABEL[r.compression], valid: s.valid,
        usable: s.usable, reason: s.reason, mode_ceiling: s.modeCeiling, threshold: r.threshold, ceiling: c, from,
        crop: s.crop, crop_in: cropIn(s.crop), binning: s.binning };
      from = Math.max(from, c);
      return out;
    }),
    pool: probeOff ? [] : pool.map((p) => {
      const ceilings = {}, reasons = {};
      for (const comp of COMPS) {
        const x = ceilingIn(p, comp);
        ceilings[comp] = x.ceiling;
        if (x.reason) reasons[comp] = x.reason;
      }
      return { width: p.width, height: p.height, bits: p.bits, clear_hdr: p.clear_hdr, label: label(p), class: classLabel(p),
        size: p.width + "×" + p.height, valid: true, ceilings, reasons, crop: p.crop, crop_in: cropIn(p.crop), binning: p.binning };
    }),
    errors: v.errors.concat(extra || []), warnings: v.warnings,
  };
}

function settingsBody() {
  derived();
  const keys = ["fps", "width", "height", "resolution", "raw_bit_depth", "clear_hdr", "cdng_compression", "recording_format",
    "lossy_dng_ratio", "fps_ramp", "fps_ramp_keep_exposure", "fps_max", "fps_take_max", "ladder_enabled", "ladder_active",
    "ladder_rung", "ladder_count", "ladder_text", "ladder_tops", "recording"];
  const out = {};
  for (const k of keys) out[k] = st[k];
  return out;
}

function command(cmd) {
  const ok = (extra) => Object.assign({ ok: true }, settingsBody(), extra || {});
  const fail = (error) => ({ ok: false, error });
  derived();
  switch (cmd.cmd) {
    case "get_mode_ladder":
      return ok({ mode_ladder: modeLadderJson(ladder.rungs, ladder.enabled) });
    case "set_mode_ladder": {
      let rungs = ladder.rungs, parseError = null;
      if (typeof cmd.rungs === "string") {
        const parsed = parseRungs(cmd.rungs);
        if (parsed.error) parseError = parsed.error; else rungs = parsed.rungs;
      }
      if (cmd.dry_run === "true") {
        if (parseError) return ok({ mode_ladder: Object.assign(modeLadderJson(ladder.rungs, ladder.enabled), { errors: [parseError], warnings: [] }) });
        return ok({ mode_ladder: modeLadderJson(rungs, ladder.enabled, dryError ? [dryError] : []) });
      }
      if (dryError) return fail(dryError);
      if (st.recording) return fail("Stop recording before changing the Mode Ladder.");
      if (parseError) return fail(parseError);
      const v = validate(rungs, rungs.map((r) => rungState(r, true)));
      if (v.errors.length) return fail(v.errors.join(" "));
      ladder = { enabled: typeof cmd.enabled === "string" ? cmd.enabled === "true" : ladder.enabled, rungs };
      derived();
      rewrite(st.fps);
      return ok({ mode_ladder: modeLadderJson(ladder.rungs, ladder.enabled) });
    }
    case "set_fps": {
      const v = Number(cmd.value);
      if (st.recording) {
        if (!st.fps_ramp) return fail("Turn on Speed Ramp before the take to change FPS while recording.");
        st.fps = Math.min(v, st.fps_take_max);
        return ok();
      }
      if (rewrite(v)) return { delay: 900, reply: ok() };
      st.fps = Math.min(v, active() ? st.fps_max : modeCeiling());
      return ok();
    }
    case "set_fps_ramp":
      if (st.recording) return fail("Stop recording before turning FPS ramping on or off.");
      st.fps_ramp = cmd.enabled === "true";
      if (cmd.shutter) st.fps_ramp_keep_exposure = cmd.shutter === "exposure";
      return ok();
    case "set_record_format":
      st.recording_format = cmd.value;
      derived();
      rewrite(st.fps);
      return ok();
    case "set_resolution": case "set_raw_bit_depth": case "set_clear_hdr":
      if (active()) return fail("The Mode Ladder picks the resolution from the FPS. Turn it off in Settings > Record > Mode Ladder to choose by hand.");
      if (cmd.cmd === "set_resolution") { st.width = cmd.width; st.height = cmd.height; st.resolution = cmd.width + "x" + cmd.height; }
      if (cmd.cmd === "set_raw_bit_depth") st.raw_bit_depth = cmd.value;
      if (cmd.cmd === "set_clear_hdr") st.clear_hdr = cmd.enabled === "true";
      return ok();
    case "set_cdng_compression":
      if (active() && compressionApplies()) return fail("The Mode Ladder sets the compression of each resolution. Turn it off in Settings > Record > Mode Ladder to choose by hand.");
      st.cdng_compression = cmd.value;
      return ok();
    default:
      return ok();
  }
}

http.createServer((req, res) => {
  let body = "";
  req.on("data", (c) => body += c);
  req.on("end", () => {
    const json = (o) => { res.writeHead(200, { "Content-Type": "application/json" }); res.end(JSON.stringify(o)); };
    if (req.url === "/") { res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" }); return res.end(page()); }
    if (req.url.startsWith("/api/state")) return json(derived());
    if (req.url === "/__log") return json(log);
    if (req.url.startsWith("/__set")) {
      const patch = JSON.parse(body || "{}");
      if ("build_max" in patch) { buildMax = patch.build_max; delete patch.build_max; }
      if ("probe_off" in patch) { probeOff = patch.probe_off; delete patch.probe_off; }
      if ("dry_error" in patch) { dryError = patch.dry_error; delete patch.dry_error; }
      Object.assign(st, patch);
      return json({ ok: true });
    }
    if (req.url.startsWith("/__ladder")) {
      const o = JSON.parse(body || "{}");
      ladder = { enabled: o.enabled !== false, rungs: parseRungs(o.rungs).rungs };
      derived();
      if (o.move) rewrite(st.fps);
      return json({ ok: true, ladder: rungsText(ladder.rungs) });
    }
    if (req.url === "/api/command") {
      const cmd = JSON.parse(body || "{}");
      if (cmd.cmd !== "user_activity") log.push(cmd);
      const out = command(cmd);
      if (out.delay) return setTimeout(() => json(out.reply), out.delay);
      return json(out);
    }
    if (req.url.startsWith("/icons/")) {
      const icon = path.join(path.dirname(cppPath), "icons", path.basename(req.url));
      if (fs.existsSync(icon)) { res.writeHead(200, { "Content-Type": "image/png" }); return res.end(fs.readFileSync(icon)); }
    }
    return json({});
  });
}).listen(PORT, () => console.log("mock on " + PORT));
