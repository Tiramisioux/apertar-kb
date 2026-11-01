// Serves the page from the scratch WebControlPage.cpp and forwards /api to the real Core (read-only
// use: the script only clicks panels and filters). OVERRIDE merges fields into /api/state so the
// ladder-active look can be seen without switching the camera. Drives Chrome over CDP.
// Usage: node harness.js <WebControlPage.cpp> <shots dir>
const http = require("http");
const fs = require("fs");
const { spawn } = require("child_process");

const cppPath = process.argv[2];
const shots = process.argv[3];
fs.mkdirSync(shots, { recursive: true });
const PI = "http://apertar.local:8000";
let override = {};

const page = () => {
  const src = fs.readFileSync(cppPath, "utf8");
  return src.slice(src.indexOf('R"APERTAR(') + 10, src.indexOf(')APERTAR"'));
};

const server = http.createServer(async (req, res) => {
  try {
    if (req.url === "/" || req.url.startsWith("/?")) {
      res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
      return res.end(page());
    }
    if (req.url === "/__override") {
      let body = "";
      for await (const chunk of req) body += chunk;
      override = JSON.parse(body || "{}");
      return res.end("{}");
    }
    let body = "";
    for await (const chunk of req) body += chunk;
    const upstream = await fetch(PI + req.url, { method: req.method, body: req.method === "GET" ? undefined : body, headers: { "Content-Type": "application/json" } });
    const buffer = Buffer.from(await upstream.arrayBuffer());
    if (req.url.startsWith("/api/state") && Object.keys(override).length) {
      const state = JSON.parse(buffer.toString());
      Object.assign(state, override);
      res.writeHead(200, { "Content-Type": "application/json" });
      return res.end(JSON.stringify(state));
    }
    const passed = { "Content-Type": upstream.headers.get("content-type") || "application/octet-stream" };
    upstream.headers.forEach((value, key) => { if (key.toLowerCase().startsWith("x-")) passed[key] = value; });
    res.writeHead(upstream.status, passed);
    res.end(buffer);
  } catch (error) {
    res.writeHead(500);
    res.end(String(error));
  }
});

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  await new Promise((r) => server.listen(8770, r));
  const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", [
    "--headless=new", "--autoplay-policy=no-user-gesture-required", "--mute-audio", "--remote-debugging-port=9333", "--user-data-dir=" + shots + "/profile",
    "--window-size=1280,1000", "--hide-scrollbars", "about:blank"], { stdio: "ignore" });
  let targets;
  for (let i = 0; i < 40; i++) {
    try { targets = await (await fetch("http://127.0.0.1:9333/json")).json(); if (targets.length) break; } catch (e) {}
    await sleep(250);
  }
  const target = targets.find((t) => t.type === "page");
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((r) => (ws.onopen = r));
  let nextId = 1;
  const pending = new Map();
  const errors = [];
  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); return; }
    if (msg.method === "Runtime.exceptionThrown") errors.push("exception: " + JSON.stringify(msg.params.exceptionDetails.exception && msg.params.exceptionDetails.exception.description || msg.params.exceptionDetails.text));
    if (msg.method === "Runtime.consoleAPICalled" && msg.params.type === "error") errors.push("console.error: " + msg.params.args.map((a) => a.value || a.description).join(" "));
  };
  const send = (method, params = {}) => new Promise((resolve) => {
    const id = nextId++;
    pending.set(id, resolve);
    ws.send(JSON.stringify({ id, method, params }));
  });
  const evaluate = async (expression) => {
    const r = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
    return r.result && r.result.result ? r.result.result.value : undefined;
  };
  const shot = async (name, clip) => {
    const r = await send("Page.captureScreenshot", clip ? { format: "png", clip: { ...clip, scale: 1 } } : { format: "png" });
    fs.writeFileSync(shots + "/" + name + ".png", Buffer.from(r.result.data, "base64"));
  };
  const shotElement = async (name, selector, pad = 8) => {
    const box = await evaluate(`(() => { const e = document.querySelector(${JSON.stringify(selector)}); if (!e) return null; e.scrollIntoView({block: "start"}); const r = e.getBoundingClientRect(); return {x: r.x, y: r.y, width: r.width, height: r.height}; })()`);
    if (!box) { console.log("no element", selector); return; }
    await sleep(250);
    const b2 = await evaluate(`(() => { const r = document.querySelector(${JSON.stringify(selector)}).getBoundingClientRect(); return {x: r.x + scrollX, y: r.y + scrollY, width: r.width, height: r.height}; })()`);
    const r = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true,
      clip: { x: Math.max(0, b2.x - pad), y: Math.max(0, b2.y - pad), width: b2.width + pad * 2, height: b2.height + pad * 2, scale: 1 } });
    fs.writeFileSync(shots + "/" + name + ".png", Buffer.from(r.result.data, "base64"));
  };

  await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 2400, deviceScaleFactor: 1, mobile: false });
  await send("Page.enable");
  await send("Runtime.enable");
  await send("Page.navigate", { url: "http://127.0.0.1:8770/" });
  await sleep(2500);

  const steps = JSON.parse(fs.readFileSync(shots + "/steps.json", "utf8"));
  for (const step of steps) {
    if (step.override) { override = step.override; await sleep(1800); }
    if (step.viewport) { await send("Emulation.setDeviceMetricsOverride", { width: step.viewport[0], height: step.viewport[1], deviceScaleFactor: 1, mobile: step.viewport[0] < 700 }); await sleep(400); }
    if (step.fullshot) { const r = await send("Page.captureScreenshot", { format: "png" }); fs.writeFileSync(shots + "/" + step.fullshot + ".png", Buffer.from(r.result.data, "base64")); }
    if (step.eval) { const v = await evaluate(step.eval); console.log(step.label || "eval", "->", JSON.stringify(v)); }
    if (step.shot) await shotElement(step.shot, step.selector);
    if (step.wait) await sleep(step.wait);
  }
  console.log("errors:", errors.length ? "\n  " + errors.join("\n  ") : "none");
  ws.close();
  chrome.kill();
  server.close();
  process.exit(0);
}
main().catch((e) => { console.error(e); process.exit(1); });
