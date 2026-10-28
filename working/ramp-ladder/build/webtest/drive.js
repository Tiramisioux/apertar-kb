// Drives the T34 WebUI against the mock (server.js): Mode Ladder, Speed Ramp, Activated sensor
// modes, Camera settings and Recording format, desktop 1280x1000 and phone 390x844.
// Usage: node drive.js <shots dir>
const { chromium } = require("playwright");
const out = process.argv[2];
const base = "http://localhost:8765";
const errors = [];
const results = [];
const note = (label, value) => { results.push(label + ": " + value); console.log(label + ": " + value); };
const api = (path, obj) => fetch(base + path, { method: "POST", body: JSON.stringify(obj || {}) }).then((r) => r.json());
const PATRIK = "3840x2160:16:hdr:none:25,3840x2160:12:sdr:none";
const reset = async () => {
  await api("/__set", { recording: false, fps: 25, width: 3840, height: 2160, resolution: "3840x2160", raw_bit_depth: 16, clear_hdr: true,
    recording_format: "cdng", cdng_compression: "none", fps_ramp: true, build_max: 50, ui: { photo_mode_enabled: false } });
  await api("/__ladder", { rungs: PATRIK, enabled: true, move: true });
};

async function open(browser, width, height) {
  const page = await browser.newPage({ viewport: { width, height } });
  page.on("pageerror", (e) => errors.push(width + "px pageerror: " + e.message));
  page.on("console", (m) => { if (m.type() === "error") errors.push(width + "px console: " + m.text()); });
  await page.goto(base + "/");
  await page.waitForTimeout(1300);
  return page;
}

async function openRecord(page) {
  await page.click("#settingsButton");
  await page.click('.settings-nav-item[data-panel="record"]');
  await page.waitForTimeout(900);
}

const card = (page, id) => page.locator("#" + id).locator("xpath=ancestor::div[contains(@class,'settings-card')][1]");
const cameraCard = (page) => page.locator("#fpsOptions").locator("xpath=ancestor::div[contains(@class,'card')][1]");

// The whole card in one picture: the viewport grows to fit it, then returns.
async function shot(page, locator, file) {
  const size = page.viewportSize();
  const box = await locator.evaluate((e) => e.getBoundingClientRect().height);
  if (box + 260 > size.height)
    await page.setViewportSize({ width: size.width, height: Math.ceil(box + 300) });
  await locator.evaluate((e) => e.scrollIntoView({ block: "start" }));
  await page.waitForTimeout(250);
  await locator.screenshot({ path: out + "/" + file });
  await page.setViewportSize(size);
  await page.waitForTimeout(150);
  note("shot", file);
}

const rowNames = (page) => page.$$eval("#settingsModeLadderList .ladder-row-name", (e) => e.map((x) => x.textContent).join(" | "));
const draftLine = (page) => page.locator("#settingsModeLadderDraft").innerText();
const messages = (page) => page.$$eval("#settingsModeLadderMessages li", (e) => e.map((x) => x.className + ": " + x.textContent).join(" || "));
const lastCommands = async (n) => (await (await fetch(base + "/__log")).json()).slice(-n).map((c) => JSON.stringify(c)).join(" ");

async function overflow(page, label) {
  const result = await page.evaluate(() => {
    const doc = document.documentElement.scrollWidth > window.innerWidth;
    const wide = [];
    document.querySelectorAll(".settings-panels, .settings-card, .card, .ladder-row, .ladder-pool-item").forEach((e) => {
      if (e.offsetParent !== null && e.scrollWidth > e.clientWidth + 1)
        wide.push((e.id || e.className) + " " + e.scrollWidth + ">" + e.clientWidth);
    });
    return { doc, wide };
  });
  note("horizontal overflow (" + label + ")", result.doc || result.wide.length ? "YES " + JSON.stringify(result) : "none");
}

(async () => {
  const browser = await chromium.launch();
  await reset();

  // ---------- desktop 1280x1000 ----------
  let page = await open(browser, 1280, 1000);
  await openRecord(page);
  note("rows (saved)", await rowNames(page));
  note("status pill", await page.locator("#settingsModeLadderValue").innerText());
  note("running now", await page.locator("#settingsModeLadderNow").innerText());
  note("draft line", await draftLine(page));
  note("messages", await messages(page));
  note("coverage", await page.locator("#settingsModeLadderCoverageTitle").innerText() + " / " + await page.locator("#settingsModeLadderCoverageCaption").innerText());
  await shot(page, card(page, "settingsModeLadderList"), "desktop-01-ladder-patrik.png");
  await shot(page, card(page, "settingsSpeedRampSwitch"), "desktop-04-speed-ramp-on.png");

  // Speed Ramp switch: off, then on again
  await page.click("#settingsSpeedRampSwitch");
  await page.waitForTimeout(500);
  note("speed ramp after click", await page.getAttribute("#settingsSpeedRampSwitch", "aria-checked") + " / " + await lastCommands(1));
  await shot(page, card(page, "settingsSpeedRampSwitch"), "desktop-04b-speed-ramp-off.png");
  await page.click("#settingsSpeedRampSwitch");
  await page.waitForTimeout(500);
  note("speed ramp after 2nd click", await page.getAttribute("#settingsSpeedRampSwitch", "aria-checked") + " / " + await lastCommands(1));

  // Illegal threshold: 70 on resolution 2 (ceiling 50)
  await page.fill("#settingsModeLadderThr1", "70");
  await page.press("#settingsModeLadderThr1", "Enter");
  await page.waitForTimeout(200);
  note("after typing 70", "notice=" + await draftLine(page) + " / value='" + await page.inputValue("#settingsModeLadderThr1") + "'");
  await page.fill("#settingsModeLadderThr0", "12");
  await page.press("#settingsModeLadderThr0", "Enter");
  await page.waitForTimeout(200);
  note("after typing 12 on resolution 1", "notice=" + await draftLine(page) + " / value='" + await page.inputValue("#settingsModeLadderThr0") + "' rows: " + await page.$$eval("#settingsModeLadderList .ladder-row-range", (e) => e.map((x) => x.textContent).join(" | ")));
  await shot(page, card(page, "settingsModeLadderList"), "desktop-05-threshold-12-draft.png");
  await page.click("#settingsModeLadderRevert");
  await page.waitForTimeout(200);
  note("after Revert", await draftLine(page) + " / " + await rowNames(page) + " / thr0='" + await page.inputValue("#settingsModeLadderThr0") + "'");

  // Saved "Up to" 25 = the ceiling of 4K Clear HDR 16-bit: an edit undone leaves the draft clean
  await page.fill("#settingsModeLadderThr1", "40");
  await page.press("#settingsModeLadderThr1", "Enter");
  await page.fill("#settingsModeLadderThr1", "");
  await page.press("#settingsModeLadderThr1", "Enter");
  await page.waitForTimeout(200);
  note("edit undone", await draftLine(page) + " / save disabled=" + await page.isDisabled("#settingsModeLadderSave") + " / thr0='" + await page.inputValue("#settingsModeLadderThr0") + "'");

  // Make room above 40, add the crop-in mode from Activated sensor modes, save
  await page.fill("#settingsModeLadderThr1", "40");
  await page.press("#settingsModeLadderThr1", "Enter");
  await page.waitForTimeout(500);
  note("after Up to 40", await draftLine(page) + " / save disabled=" + await page.isDisabled("#settingsModeLadderSave"));
  note("dry run messages", await messages(page));
  note("dry run sent", await lastCommands(1));
  await page.click('#settingsSensorModeGroupFilters button:has-text("Crop")');
  await page.click('#settingsSensorModeDepthFilters button:has-text("12-bit")');
  await page.waitForTimeout(150);
  await shot(page, card(page, "settingsSensorModeList"), "desktop-03-sensor-modes-crop-12bit.png");
  const cropItem = page.locator("#settingsSensorModeList .ladder-pool-item", { hasText: "2560×1440" });
  note("crop-in pool item", (await cropItem.innerText()).replace(/\n/g, " / "));
  await cropItem.locator("button").click();
  await page.waitForTimeout(500);
  note("rows after Add", await rowNames(page));
  note("crop-in row", (await page.locator("#settingsModeLadderList .ladder-row").nth(2).innerText()).replace(/\n/g, " / "));
  await page.click("#settingsModeLadderSave");
  await page.waitForTimeout(900);
  note("save sent", await lastCommands(3));
  note("after Save", await draftLine(page) + " / " + await rowNames(page) + " / pill " + await page.locator("#settingsModeLadderValue").innerText());
  note("messages after save", await messages(page));
  await shot(page, card(page, "settingsModeLadderList"), "desktop-02-ladder-three-cropin.png");
  await page.click('#settingsSensorModeGroupFilters button:has-text("All")');
  await page.click('#settingsSensorModeDepthFilters button:has-text("All")');
  await page.waitForTimeout(150);
  await shot(page, card(page, "settingsSensorModeList"), "desktop-03b-sensor-modes-all.png");

  // Lossy for Clear HDR: the option is disabled; forcing it is refused
  note("lossy options on resolution 1", JSON.stringify(await page.$$eval("#settingsModeLadderComp0 option", (o) => o.map((x) => x.textContent + (x.disabled ? " [disabled]" : "")))));
  try {
    await page.selectOption("#settingsModeLadderComp0", "lossy_3to1", { timeout: 2000 });
    note("selectOption lossy_3to1", "accepted?? value=" + await page.inputValue("#settingsModeLadderComp0"));
  } catch (error) {
    note("selectOption lossy_3to1", "refused by the browser: " + error.message.split("\n")[0]);
  }
  await page.evaluate(() => { const s = document.getElementById("settingsModeLadderComp0"); s.value = "lossy_3to1"; s.dispatchEvent(new Event("change")); });
  await page.waitForTimeout(200);
  note("forced lossy_3to1", "notice=" + await draftLine(page) + " / select now " + await page.inputValue("#settingsModeLadderComp0") + " / dirty=" + !(await page.isDisabled("#settingsModeLadderRevert")));

  // Arrow move that would make the ladder illegal
  await page.click('#settingsModeLadderList button[aria-label="Move 4K Clear HDR 16-bit down"]');
  await page.waitForTimeout(200);
  note("move resolution 1 down", "notice=" + await draftLine(page) + " / " + await rowNames(page));

  // Drag row 1 down onto the line between rows 2 and 3: row 2 is the drop target (then refused)
  {
    const down = page.locator("#settingsModeLadderList .ladder-handle").nth(0);
    const line = page.locator("#settingsModeLadderList .ladder-transition").nth(1);
    await line.scrollIntoViewIfNeeded();
    const a = await down.boundingBox();
    const b = await line.boundingBox();
    await page.mouse.move(a.x + a.width / 2, a.y + a.height / 2);
    await page.mouse.down();
    for (let i = 1; i <= 8; i++)
      await page.mouse.move(a.x + a.width / 2, a.y + a.height / 2 + (b.y + b.height / 2 - a.y - a.height / 2) * i / 8);
    note("drag row 1 onto line 2-3", "drop target: row " + await page.$$eval("#settingsModeLadderList .ladder-row", (e) => e.findIndex((x) => x.classList.contains("drop-target")) + 1));
    await page.mouse.up();
    await page.waitForTimeout(200);
    note("drag row 1 onto line 2-3, dropped", "notice=" + await draftLine(page) + " / " + await rowNames(page));
  }

  // Drag: the crop-in (Up to 45) above 4K SDR 12-bit, released on the line between rows 1 and 2
  await page.fill("#settingsModeLadderThr2", "45");
  await page.press("#settingsModeLadderThr2", "Enter");
  await page.waitForTimeout(200);
  const handle = page.locator("#settingsModeLadderList .ladder-handle").nth(2);
  const target = page.locator("#settingsModeLadderList .ladder-transition").nth(0);
  await handle.scrollIntoViewIfNeeded();
  const from = await handle.boundingBox();
  const to = await target.boundingBox();
  await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2);
  await page.mouse.down();
  for (let i = 1; i <= 8; i++)
    await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2 + (to.y + to.height / 2 - from.y - from.height / 2) * i / 8);
  note("during drag", "drop-target rows: " + await page.$$eval("#settingsModeLadderList .ladder-row.drop-target", (e) => e.length) + ", dragging: " + await page.$$eval("#settingsModeLadderList .ladder-row.dragging", (e) => e.length));
  await page.mouse.up();
  await page.waitForTimeout(500);
  note("after drag", await rowNames(page) + " / " + await draftLine(page) + " / ranges: " + await page.$$eval("#settingsModeLadderList .ladder-row-range", (e) => e.map((x) => x.textContent).join(" | ")));
  note("dry run after drag", await messages(page));
  await shot(page, card(page, "settingsModeLadderList"), "desktop-06-after-drag-draft.png");
  await page.click("#settingsModeLadderRevert");
  await page.waitForTimeout(200);
  note("after Revert", await rowNames(page) + " / " + await draftLine(page));

  // Recording format card with the ladder active
  await shot(page, card(page, "settingsRecordFormatOptions"), "desktop-13-record-format-ladder-on.png");
  note("record format disabled", JSON.stringify(await page.evaluate(() => ({
    resolution: document.getElementById("settingsRecordResolutionSelect").disabled,
    crop: document.getElementById("settingsRecordCropSelect").disabled,
    compression: document.getElementById("settingsCdngCompressionSelect").disabled,
    bitDepth: Array.from(document.querySelectorAll("#settingsRawBitDepthOptions button")).map((b) => b.textContent + (b.disabled ? "x" : "")).join(","),
    note: document.getElementById("settingsRecordLadderNote").textContent,
    noteHidden: document.getElementById("settingsRecordLadderNote").classList.contains("hidden"),
  }))));

  // Favorites > Format with the ladder active: Resolution, Crop, Compression and Bit Depth locked
  await api("/__set", { ui: { photo_mode_enabled: false, favorites_order: ["format"] } });
  await page.click('.settings-nav-item[data-panel="favorites"]');
  await page.waitForTimeout(1300);
  const favorites = page.locator("#settingsFavoriteControls .settings-card").first();
  note("favorites format (ladder on)", JSON.stringify(await favorites.evaluate((card) => ({
    selects: Array.from(card.querySelectorAll("select")).map((s) => s.previousElementSibling.textContent + (s.disabled ? "x" : "")).join(","),
    pills: Array.from(card.querySelectorAll(".select-block")).map((b) => b.querySelector(".select-topline span").textContent + ": "
      + Array.from(b.querySelectorAll("button")).map((x) => (x.classList.contains("active") ? "*" : "") + x.textContent + (x.disabled ? "x" : "")).join(",")).join(" | "),
    note: Array.from(card.querySelectorAll(":scope > .settings-card-copy")).map((p) => p.textContent).join(""),
  }))));
  await shot(page, favorites, "desktop-16-favorites-format-locked.png");
  const savedRungs = (await api("/api/command", { cmd: "get_mode_ladder" })).mode_ladder.rungs_text;
  await api("/__ladder", { rungs: savedRungs, enabled: false });
  await page.waitForTimeout(1300);
  note("favorites format (ladder off)", JSON.stringify(await favorites.evaluate((card) => ({
    selects: Array.from(card.querySelectorAll("select")).map((s) => s.previousElementSibling.textContent + (s.disabled ? "x" : "")).join(","),
    note: Array.from(card.querySelectorAll(":scope > .settings-card-copy")).map((p) => p.textContent).join(""),
  }))));
  await api("/__ladder", { rungs: savedRungs, enabled: true });
  await api("/__set", { ui: { photo_mode_enabled: false } });
  await page.click('.settings-nav-item[data-panel="record"]');
  await page.waitForTimeout(1300);

  // Activate ladder: off, check the Camera settings card, on again
  await page.click("#settingsModeLadderSwitch");
  await page.waitForTimeout(700);
  note("switch off", await page.getAttribute("#settingsModeLadderSwitch", "aria-checked") + " / " + await lastCommands(1) + " / pill " + await page.locator("#settingsModeLadderValue").innerText() + " / now " + await page.locator("#settingsModeLadderNow").innerText());
  await shot(page, card(page, "settingsModeLadderList"), "desktop-07-ladder-off.png");
  await page.click("#closeSettingsButton");
  await page.waitForTimeout(400);
  await shot(page, cameraCard(page), "desktop-08-camera-ladder-off.png");
  await openRecord(page);
  await page.click("#settingsModeLadderSwitch");
  await page.waitForTimeout(700);
  note("switch on", await page.getAttribute("#settingsModeLadderSwitch", "aria-checked") + " / " + await lastCommands(1) + " / pill " + await page.locator("#settingsModeLadderValue").innerText());
  await page.click("#closeSettingsButton");
  await page.waitForTimeout(1200);
  const pills = () => page.$$eval("#fpsOptions button", (b) => b.map((x) => (x.classList.contains("active") ? "*" : "") + x.innerText.replace("\n", "/") + (x.classList.contains("ladder-switch") ? "(dashed)" : "")).join(" "));
  note("camera: fps line", await page.locator("#fpsLadderLine").innerText());
  note("camera: fps pills", await pills());
  note("camera: resolution pills", await page.$$eval("#resolutionOptions button", (b) => b.map((x) => (x.classList.contains("active") ? "*" : "") + x.textContent + (x.disabled ? "(locked)" : "")).join(" ")));
  await shot(page, cameraCard(page), "desktop-09-camera-ladder-on.png");

  // FPS pill that switches the resolution (25 -> 30: resolution 2)
  await cameraCard(page).evaluate((e) => e.scrollIntoView({ block: "start" }));
  await page.click('#fpsOptions button:has-text("30.000")');
  await page.waitForTimeout(250);
  note("while switching", await page.locator("#fpsLadderLine").innerText());
  await page.locator("#fpsOptions").locator("xpath=..").screenshot({ path: out + "/desktop-10-fps-switching.png" });
  note("shot", "desktop-10-fps-switching.png");
  await page.waitForTimeout(1500);
  note("after switch", await page.locator("#fpsLadderLine").innerText() + " / " + await pills() + " / badge " + await page.locator("#resolutionBadge").innerText());

  // Two overlapping switches (50 -> Resolution 3, then 24 -> Resolution 1): the first reply
  // must not clear the second's "Switching to" line
  const t0 = Date.now();
  await page.click('#fpsOptions button:has-text("50.000")');
  await page.waitForTimeout(300);
  await page.click('#fpsOptions button:has-text("24.000")');
  await page.waitForTimeout(Math.max(0, t0 + 1080 - Date.now()));
  note("overlap: after the first reply", await page.locator("#fpsLadderLine").innerText());
  await page.waitForTimeout(1200);
  note("overlap: after both", await page.locator("#fpsLadderLine").innerText());
  await page.click('#fpsOptions button:has-text("30.000")');
  await page.waitForTimeout(1500);
  note("back on resolution 2", await page.locator("#fpsLadderLine").innerText());

  // IMX477 uncompressed (page functions): the current mode's cap does not hide the faster resolutions
  note("imx477 fps options", JSON.stringify(await page.evaluate(() => {
    const snap = { sensor: "imx477", width: 4056, height: 3040, resolution: "4056x3040", raw_bit_depth: 12, recording_format: "cdng",
      cdng_compression: "none", fps_max: 50, fps_take_max: 24, ladder_tops: [24, 50], ladder_rung: 1, recording: false, ui: {} };
    return {
      ladderOn: availableFpsOptionsForSnapshot(Object.assign({}, snap, { ladder_active: true })).join(" "),
      ladderOff: availableFpsOptionsForSnapshot(Object.assign({}, snap, { ladder_active: false })).join(" "),
    };
  })));

  // A clamp in a take: recording starts while the page still shows the pre-take pills
  const preTakePill = await page.$('#fpsOptions button:has-text("50.000")');
  await api("/__set", { recording: true, state: "recording" });
  await preTakePill.evaluate((button) => button.click());
  await page.waitForTimeout(400);
  note("toast after clamp", await page.locator("#toast").innerText());
  await page.locator("#toast").screenshot({ path: out + "/desktop-11-take-clamp-toast.png" });
  note("shot", "desktop-11-take-clamp-toast.png");
  await page.waitForTimeout(1500);
  note("recording: fps line", await page.locator("#fpsLadderLine").innerText());
  note("recording: fps pills", await pills());
  await shot(page, cameraCard(page), "desktop-12-camera-recording.png");
  await openRecord(page);
  note("recording: switch", "disabled=" + await page.isDisabled("#settingsModeLadderSwitch") + " / " + await page.locator("#settingsModeLadderSwitchNote").innerText());
  note("recording: speed ramp", "disabled=" + await page.isDisabled("#settingsSpeedRampSwitch") + " / " + await page.locator("#settingsSpeedRampNote").innerText());
  await page.fill("#settingsModeLadderThr1", "35");
  await page.press("#settingsModeLadderThr1", "Enter");
  await page.waitForTimeout(600);
  note("recording: edit", await draftLine(page) + " / save disabled=" + await page.isDisabled("#settingsModeLadderSave"));
  await shot(page, card(page, "settingsModeLadderList"), "desktop-14-ladder-recording.png");
  await page.click("#settingsModeLadderRevert");
  await api("/__set", { recording: false, state: "ready" });
  await page.waitForTimeout(1200);

  // H.264: the ladder is not in use, Speed Ramp is disabled
  await api("/__set", { recording_format: "h264" });
  await page.waitForTimeout(1300);
  note("h264: switch note", await page.locator("#settingsModeLadderSwitchNote").innerText() + " / now " + await page.locator("#settingsModeLadderNow").innerText());
  note("h264: speed ramp", "disabled=" + await page.isDisabled("#settingsSpeedRampSwitch") + " / " + await page.locator("#settingsSpeedRampNote").innerText());
  await api("/__set", { recording_format: "cdng" });
  await page.waitForTimeout(1200);

  // An error only Core knows (dry run): Save stays disabled and the error shows in red
  await api("/__set", { dry_error: "Resolution 2 (4K SDR 12-bit, Uncompressed) cannot record: test error from Core." });
  await page.fill("#settingsModeLadderThr1", "35");
  await page.press("#settingsModeLadderThr1", "Enter");
  await page.waitForTimeout(700);
  note("core dry-run error", (await messages(page)) + " / save disabled=" + await page.isDisabled("#settingsModeLadderSave"));
  await page.click("#settingsModeLadderRevert");
  await api("/__set", { dry_error: "" });

  // MLV: the ladder runs, each resolution's compression is ignored
  await api("/__set", { recording_format: "mlv" });
  await page.waitForTimeout(1300);
  await page.click('.settings-nav-item[data-panel="audio"]');
  await page.click('.settings-nav-item[data-panel="record"]');
  await page.waitForTimeout(800);
  note("mlv: now", await page.locator("#settingsModeLadderNow").innerText() + " / messages " + await messages(page));
  await api("/__set", { recording_format: "cdng" });

  // Sensor probe off: no pool; the saved resolutions still show
  await api("/__set", { probe_off: true });
  await page.click('.settings-nav-item[data-panel="audio"]');
  await page.click('.settings-nav-item[data-panel="record"]');
  await page.waitForTimeout(800);
  note("probe off: copy", await page.locator("#settingsSensorModesCopy").innerText() + " / filters hidden=" + await page.locator("#settingsSensorModeFilters").evaluate((e) => e.classList.contains("hidden")) + " / items " + await page.locator("#settingsSensorModeList .ladder-pool-item").count());
  note("probe off: rows", await rowNames(page) + " / ceilings " + await page.$$eval("#settingsModeLadderList .ladder-thr .ladder-note", (e) => e.map((x) => x.textContent).join(" | ")));
  note("probe off: crop", "descriptions " + await page.$$eval("#settingsModeLadderList .ladder-row-desc", (e) => e.length)
    + " / crop-in tags " + await page.$$eval("#settingsModeLadderList .crop-tag", (e) => e.length)
    + " / titles " + await page.$$eval("#settingsModeLadderList .crop-frame", (e) => e.map((x) => x.title).join(" | "))
    + " / running now " + await page.locator("#settingsModeLadderNowCrop").getAttribute("title"));
  const ladderView = async () => "ceilings " + await page.$$eval("#settingsModeLadderList .ladder-thr .ladder-note", (e) => e.map((x) => x.textContent).join(" | "))
    + " / ranges " + await page.$$eval("#settingsModeLadderList .ladder-row-range", (e) => e.map((x) => x.textContent).join(" | "))
    + " / problems " + await page.$$eval("#settingsModeLadderList .ladder-problem", (e) => e.map((x) => x.textContent).join(" | "))
    + " / gap '" + await page.locator("#settingsModeLadderGap").innerText() + "'";
  // cDNG, a compression changed in the draft: that resolution's ceiling is unknown, the ones below stay usable
  await page.selectOption("#settingsModeLadderComp0", "lossless_jpeg");
  await page.waitForTimeout(700);
  note("probe off, row 1 lossless", await draftLine(page) + " / " + await ladderView() + " / messages " + await messages(page));
  await page.click("#settingsModeLadderRevert");
  // H.264: Core's mode_ceiling values are H.264's, so no ceiling is known; the editor's own ladder
  // (empty "Up to" on resolution 1) shows no "Never used" and takes edits
  const probeOffRungs = (await api("/api/command", { cmd: "get_mode_ladder" })).mode_ladder.rungs_text;
  await api("/__ladder", { rungs: "3840x2160:16:hdr:none,3840x2160:12:sdr:none", enabled: true });
  await api("/__set", { recording_format: "h264" });
  await page.click('.settings-nav-item[data-panel="audio"]');
  await page.click('.settings-nav-item[data-panel="record"]');
  await page.waitForTimeout(800);
  note("probe off, h264", await ladderView());
  await page.fill("#settingsModeLadderThr0", "20");
  await page.press("#settingsModeLadderThr0", "Enter");
  await page.waitForTimeout(700);
  note("probe off, h264: Up to 20 on resolution 1", await draftLine(page) + " / " + await ladderView()
    + " / transition " + await page.locator("#settingsModeLadderList .ladder-transition").first().innerText() + " / messages " + await messages(page));
  await shot(page, card(page, "settingsModeLadderList"), "desktop-17-ladder-probe-off-h264.png");
  await page.click("#settingsModeLadderRevert");
  await page.waitForTimeout(200);
  note("probe off, h264: reverted", await draftLine(page));
  await api("/__ladder", { rungs: probeOffRungs, enabled: true });
  await api("/__set", { recording_format: "cdng" });
  await shot(page, card(page, "settingsSensorModeList"), "desktop-15-sensor-modes-probe-off.png");
  await api("/__set", { probe_off: false });
  await page.waitForTimeout(1200);
  await overflow(page, "1280");
  await page.close();

  // ---------- phone 390x844 ----------
  await reset();
  await api("/__ladder", { rungs: "3840x2160:16:hdr:none:25,3840x2160:12:sdr:none:40,2560x1440:12:sdr:none", enabled: true, move: true });
  page = await open(browser, 390, 844);
  await overflow(page, "390 main page");
  await shot(page, cameraCard(page), "phone-01-camera-ladder-on.png");
  await api("/__set", { ui: { photo_mode_enabled: false, favorites_order: ["format"] } });
  await page.click("#settingsButton");
  await page.waitForTimeout(1300);
  await overflow(page, "390 favorites format");
  await api("/__set", { ui: { photo_mode_enabled: false } });
  await page.click('.settings-nav-item[data-panel="record"]');
  await page.waitForTimeout(900);
  await overflow(page, "390 record panel");
  await shot(page, card(page, "settingsModeLadderList"), "phone-02-ladder.png");
  await shot(page, card(page, "settingsSpeedRampSwitch"), "phone-03-speed-ramp.png");
  await page.click('#settingsSensorModeGroupFilters button:has-text("Crop")');
  await page.click('#settingsSensorModeDepthFilters button:has-text("12-bit")');
  await page.waitForTimeout(150);
  await shot(page, card(page, "settingsSensorModeList"), "phone-04-sensor-modes.png");
  await shot(page, card(page, "settingsRecordFormatOptions"), "phone-05-record-format.png");
  await page.fill("#settingsModeLadderThr1", "70");
  await page.press("#settingsModeLadderThr1", "Enter");
  await page.waitForTimeout(200);
  note("phone: typing 70", await draftLine(page));
  await overflow(page, "390 after edit");
  await page.close();

  await reset();
  note("console errors", errors.length ? errors.join("\n") : "none");
  await browser.close();
})();
