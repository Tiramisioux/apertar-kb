// Controls: the Controls page tried in headless Chrome against a mock backend (T41-lite). No camera needed.
// Builds the page from the Core source, the real rows from a hardware file (the fixture) and the real action list
// from the catalog header, serves them on localhost, and drives the page: dropdowns, changes, Save, add, remove,
// refusals. Needs: node 22, Google Chrome, g++.
// Run:   node controls_page_test.js <core-tree> [fixture]
// Tries the Controls page in headless Chrome against a mock backend: the real page, the real rows of the live file,
// the real action list. The mock records what Save would send.
const http = require('http'), fs = require('fs'), os = require('os'), path = require('path');
const { spawn } = require('child_process');
const { execFileSync } = require('child_process');
const coreTree = path.resolve(process.argv[2] || '');
const fixture = path.resolve(process.argv[3] || path.join(__dirname, 'controls_fixture_apertar-hardware.conf'));
if (!process.argv[2]) { console.log('usage: node controls_page_test.js <core-tree> [fixture]'); process.exit(2); }
const work = fs.mkdtempSync(path.join(os.tmpdir(), 'controls-page-'));
// the page: the raw string in WebControlPage.cpp
const pageSource = fs.readFileSync(path.join(coreTree, 'src/web/WebControlPage.cpp'), 'utf8');
const pageStart = pageSource.indexOf('R"APERTAR(') + 'R"APERTAR('.length;
const pageHtml = pageSource.slice(pageStart, pageSource.indexOf(')APERTAR"', pageStart));
// the data: the real rows of the fixture and the real action list, from Core's own headers
fs.writeFileSync(path.join(work, 'gen.cpp'), `#include "hardware/ControlsModel.hpp"
#include <fstream>
#include <iostream>
#include <sstream>
int main(int, char **argv) {
    std::ifstream f(argv[1], std::ios::binary); std::stringstream b; b << f.rdbuf();
    const std::string text = b.str();
    if (std::string(argv[2]) == "actions") { std::cout << "{\\"ok\\":true," << apertar::hardware::actions::catalogJson().substr(1); return 0; }
    std::cout << "{\\"ok\\":true,\\"controls\\":{\\"revision\\":\\"" << apertar::hwconf::revision(text) << "\\",\\"errors\\":0,\\"warnings\\":0,\\"issues\\":[],"
              << "\\"replaced\\":{\\"replaced\\":false},\\"model\\":" << apertar::hwconf::modelJson(apertar::hwconf::parse(text)) << "}}";
}
`);
execFileSync('g++', ['-std=c++20', '-I' + path.join(coreTree, 'src'), path.join(work, 'gen.cpp'), '-o', path.join(work, 'gen')]);
const getControls = execFileSync(path.join(work, 'gen'), [fixture, 'controls'], { encoding: 'utf8' });
const listActions = execFileSync(path.join(work, 'gen'), [fixture, 'actions'], { encoding: 'utf8' });
const loadedRevision = JSON.parse(getControls).controls.revision;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let sent = [], nextReply = null;
const server = http.createServer((req, res) => {
  if (req.method === 'GET' && (req.url === '/' || req.url === '/index.html')) { res.writeHead(200, { 'Content-Type': 'text/html' }); return res.end(pageHtml); }
  if (req.method === 'POST' && req.url === '/api/command') {
    let body = ''; req.on('data', (c) => body += c); req.on('end', () => {
      const cmd = JSON.parse(body); res.writeHead(200, { 'Content-Type': 'application/json' });
      if (cmd.cmd === 'get_controls') return res.end(getControls);
      if (cmd.cmd === 'list_actions') return res.end(listActions);
      if (cmd.cmd === 'set_controls') { sent.push(cmd); return res.end(nextReply || JSON.stringify({ ok: true, revision: 'hNEW', written: true, issues: [] })); }
      res.end(JSON.stringify({ ok: false, error: 'mock: ' + cmd.cmd }));
    }); return;
  }
  res.writeHead(404); res.end();
});

async function cdp(wsUrl) {
  const ws = new WebSocket(wsUrl); await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
  let id = 0; const pending = new Map();
  ws.onmessage = (m) => { const d = JSON.parse(m.data); if (d.id && pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); } };
  const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
  const evaluate = async (expression) => { const r = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
    if (r.result.exceptionDetails) throw new Error('page error: ' + JSON.stringify(r.result.exceptionDetails.exception || r.result.exceptionDetails).slice(0, 400)); return r.result.result.value; };
  return { send, evaluate, close: () => ws.close() };
}
const results = [];
const check = (name, ok, extra) => { results.push([name, !!ok]); console.log(ok ? '  PASS' : '  FAIL', name, extra !== undefined ? '| ' + extra : ''); };

(async () => {
  await new Promise((r) => server.listen(8123, r));
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'chrome-profile-'));
  const chrome = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', ['--headless=new', '--remote-debugging-port=9334', `--user-data-dir=${profile}`, '--no-first-run', '--disable-gpu', '--window-size=1400,1800', 'about:blank'], { stdio: 'ignore' });
  for (let i = 0; i < 40; i++) { try { await fetch('http://127.0.0.1:9334/json/version'); break; } catch (e) { await sleep(250); } }
  try {
    const target = await (await fetch('http://127.0.0.1:9334/json/new?' + encodeURIComponent('http://127.0.0.1:8123/'), { method: 'PUT' })).json();
    const tab = await cdp(target.webSocketDebuggerUrl); await tab.send('Runtime.enable'); await tab.send('Page.enable');
    for (let i = 0; i < 40; i++) { try { if (await tab.evaluate('typeof setSettingsPanel === "function" && typeof loadControls === "function"')) break; } catch (e) {} await sleep(250); }
    await tab.evaluate('window.confirm = () => true; 0');
    const q = (js) => tab.evaluate(js);
    await q('setSettingsPanel("config"); 0'); await sleep(1200);

    console.log('--- the page as loaded');
    check('no separate Controls item in the nav: it lives in Config', await q('![...document.querySelectorAll(".settings-nav-item")].some(b=>b.dataset.panel==="controls")'));
    check('in the Config panel the Controls card comes first, above the text editor', await q('(() => { const p=document.querySelector(".settings-panel.active"); const t=[...p.querySelectorAll(".settings-card-title")].map(e=>e.textContent); return p.dataset.panel==="config" && t[0]==="Controls" && t.indexOf("Apertar Config")>0; })()'));
    check('the Remove button sits in the row, styled like the favourites list (danger-button preset-action)', await q('(() => { const r=[...document.querySelectorAll("#controlsRows .controls-row")].find(r=>r.querySelector(".controls-row-title").textContent==="GPIO 10"); const b=r.querySelector(".controls-row-actions button"); return !!b && b.classList.contains("danger-button") && b.classList.contains("preset-action") && b.textContent==="Remove"; })()'));
    const titles = await q('[...document.querySelectorAll("#controlsRows .controls-row-title")].map(e=>e.textContent).join(", ")');
    console.log('    rows:', titles);
    check('GPIO 10, GPIO 6 and the four knobs are there', ['GPIO 10', 'GPIO 6', 'Knob 1', 'Knob 2', 'Knob 3', 'Knob 4'].every((t) => titles.includes(t)));
    check('the PCF8574 and GPIO encoder groups are collapsed (switched off in the file)', await q('[...document.querySelectorAll("#controlsRows details .controls-group-title")].map(e=>e.textContent).join("|")').then((t) => /PCF8574/.test(t) && /GPIO encoders/.test(t) && /switched off/.test(t)));
    const d10 = await q('(() => { const row=[...document.querySelectorAll("#controlsRows .controls-row")].find(r=>r.querySelector(".controls-row-title").textContent==="GPIO 10"); const s=row.querySelector("select"); return JSON.stringify({value:s.value, label:s.selectedOptions[0].textContent, options:s.options.length, groups:s.querySelectorAll("optgroup").length}); })()').then(JSON.parse);
    console.log('    GPIO 10 dropdown:', JSON.stringify(d10));
    check('GPIO 10 shows "Record or photo (main button)" selected, with grouped options', d10.value === 'capture' && /Record or photo/.test(d10.label) && d10.groups >= 5);
    const knob = await q('(() => { const row=[...document.querySelectorAll("#controlsRows .controls-row")].find(r=>r.querySelector(".controls-row-title").textContent==="Knob 1"); return JSON.stringify([...row.querySelectorAll(".controls-line")].map(l=>l.querySelector(".controls-line-label").textContent+"="+l.querySelector("select").value)); })()').then(JSON.parse);
    console.log('    Knob 1:', knob.join(' | '));
    check('Knob 1: clockwise iso_up, counter-clockwise iso_down, press iso', knob.join('|') === 'Turn clockwise=iso_up|Turn counter-clockwise=iso_down|Press=iso');
    const turnOpts = await q('(() => { const row=[...document.querySelectorAll("#controlsRows .controls-row")].find(r=>r.querySelector(".controls-row-title").textContent==="Knob 1"); const s=row.querySelector("select"); return JSON.stringify([...s.options].map(o=>o.value)); })()').then(JSON.parse);
    console.log('    a turn offers:', turnOpts.join(' '));
    check('a turn offers only stepping actions (no capture, no photo, no zoom)', turnOpts.includes('iso_up') && turnOpts.includes('fps_down') && !turnOpts.includes('capture') && !turnOpts.includes('photo') && !turnOpts.includes('zoom_toggle') && !turnOpts.includes('eject'));
    check('Save is disabled and the pill says Ready', await q('document.getElementById("saveControlsButton").disabled && document.getElementById("controlsStatePill").textContent==="Ready"'));
    check('the add-a-button box is shown, with free pins and without 10, 6, 21', await q('(() => { const b=document.getElementById("controlsAdd"); const pins=[...document.getElementById("controlsAddPin").options].map(o=>o.value); return !b.hidden && pins.length>=15 && !pins.includes("10") && !pins.includes("6") && !pins.includes("21") && !pins.includes("2") && !pins.includes("3"); })()'));

    console.log('--- change a button and a knob, then Save');
    await q('(() => { const row=t=>[...document.querySelectorAll("#controlsRows .controls-row")].find(r=>r.querySelector(".controls-row-title").textContent===t); const set=(s,v)=>{ s.value=v; s.dispatchEvent(new Event("change",{bubbles:true})); }; set(row("GPIO 10").querySelector("select"),"record_toggle"); set(row("Knob 2").querySelectorAll("select")[0],"shutter_down"); return 0; })()'); await sleep(200);
    check('Save is enabled and the pill says Unsaved', await q('!document.getElementById("saveControlsButton").disabled && document.getElementById("controlsStatePill").textContent==="Unsaved"'));
    check('the two changed rows are marked', await q('document.querySelectorAll("#controlsRows .controls-row.changed").length') === 2);
    sent = []; await q('document.getElementById("saveControlsButton").click(); 0'); await sleep(1500);
    const p = sent[0]; console.log('    Save sent:', JSON.stringify(p));
    check('it sent set_controls with the loaded revision and only the two keys', p && p.cmd === 'set_controls' && p.base === loadedRevision && p['set.gpio_buttons.d10'] === 'record_toggle' && p['set.neorotary4.encoder1_cw'] === 'shutter_down' && Object.keys(p).filter((k) => k.startsWith('set.') || k.startsWith('unset.')).length === 2);
    const msg = await q('document.getElementById("controlsMessage").hidden ? "(hidden)" : document.getElementById("controlsMessage").innerText');
    console.log('    message:', msg);
    check('it says Saved and to restart Apertar Core; Save is disabled again', /Saved\. Restart Apertar Core/.test(msg) && await q('document.getElementById("saveControlsButton").disabled'));

    console.log('--- add a GPIO button, remove another, then a refusal');
    await q('(() => { document.getElementById("controlsAddPin").value="17"; document.getElementById("controlsAddAction").value="photo"; document.getElementById("controlsAddButton").click(); const row=[...document.querySelectorAll("#controlsRows .controls-row")].find(r=>r.querySelector(".controls-row-title").textContent==="GPIO 6"); row.querySelector(".controls-row-actions button").click(); return 0; })()'); await sleep(200);
    check('GPIO 17 appears as a new row with "Take a photo"; GPIO 6 is struck', await q('(() => { const r=[...document.querySelectorAll("#controlsRows .controls-row")]; const n=r.find(x=>/GPIO 17 \\(new\\)/.test(x.querySelector(".controls-row-title").textContent)); const o=r.find(x=>x.querySelector(".controls-row-title").textContent==="GPIO 6"); return n && n.querySelector("select").value==="photo" && o.classList.contains("removed"); })()'));
    check('pin 17 is no longer offered for another button', await q('![...document.getElementById("controlsAddPin").options].some(o=>o.value==="17")'));
    nextReply = JSON.stringify({ ok: false, code: 'errors', error: 'Not saved: 1 new error. GPIO 17 is used twice.', new_errors: [{ line: 140, message: 'GPIO 17 is used twice.' }], issues: [] });
    sent = []; await q('document.getElementById("saveControlsButton").click(); 0'); await sleep(1500);
    const p2 = sent[0]; console.log('    Save sent:', JSON.stringify(p2));
    check('it sent the new button and the removal', p2 && p2['set.gpio_buttons.d17'] === 'photo' && p2['unset.gpio_buttons.d6'] === 'true');
    const msg2 = await q('document.getElementById("controlsMessage").innerText.replace(/\\n+/g," / ")'); console.log('    message:', msg2);
    check('a refusal shows the error with its line number and keeps the page as it was', /Not saved/.test(msg2) && /Line 140/.test(msg2) && await q('!document.getElementById("saveControlsButton").disabled && controlsState.added.length===1 && controlsState.removed.size===1'));
    nextReply = JSON.stringify({ ok: false, code: 'stale', error: 'The file changed since you loaded it. Reload, then change it again.', issues: [] });
    await q('document.getElementById("saveControlsButton").click(); 0'); await sleep(1200);
    check('a stale file says the choices stay and to press Reload', /Your choices stay on the page\. Press Reload/.test(await q('document.getElementById("controlsMessage").innerText')));
    nextReply = null;
    await q('document.getElementById("reloadControlsButton").click(); 0'); await sleep(1200);
    check('Reload drops the unsaved choices', await q('controlsState.edits.size===0 && controlsState.added.length===0 && controlsState.removed.size===0 && document.getElementById("saveControlsButton").disabled'));
    tab.close();
  } catch (e) { console.log('TEST ERROR:', e.message); results.push(['no script error', false]); }
  finally { chrome.kill(); server.close(); fs.rmSync(profile, { recursive: true, force: true }); fs.rmSync(work, { recursive: true, force: true }); }
  const bad = results.filter((r) => !r[1]);
  console.log(`\n${results.length - bad.length} of ${results.length} checks passed`);
  process.exit(bad.length ? 1 : 0);
})();
