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
fs.writeFileSync(path.join(work, 'gen.cpp'), String.raw`#include "hardware/ControlsModel.hpp"
#include <fstream>
#include <iostream>
#include <sstream>
using namespace apertar;
static std::string periph(const hwconf::Document &doc, const char *id, const char *title, const char *status) {
    return std::string("{\"id\":\"") + id + "\",\"section\":\"" + id + "\",\"title\":\"" + title + "\",\"in_file\":true,\"settings\":" +
        hwconf::peripheralSettingsJson(doc, id) + ",\"status\":" + status + "}";
}
int main(int, char **argv) {
    std::ifstream f(argv[1], std::ios::binary); std::stringstream b; b << f.rdbuf();
    const std::string text = b.str();
    if (std::string(argv[2]) == "actions") { std::cout << "{\"ok\":true," << hardware::actions::catalogJson().substr(1); return 0; }
    const auto doc = hwconf::parse(text);
    std::cout << "{\"ok\":true,\"controls\":{\"revision\":\"" << hwconf::revision(text) << "\",\"errors\":0,\"warnings\":0,\"issues\":[],"
              << "\"replaced\":{\"replaced\":false},\"model\":" << hwconf::modelJson(doc) << ",\"peripherals\":["
              << periph(doc, "gpio_buttons", "Raspberry Pi GPIO", "{\"state\":\"running\",\"detail\":\"Core reads the buttons on /dev/gpiochip0 (pinctrl-rp1).\",\"chip\":{\"ok\":true,\"path\":\"/dev/gpiochip0\",\"label\":\"pinctrl-rp1\",\"lines\":54,\"error\":\"\"},\"pins\":[{\"pin\":6,\"consumer\":\"apertar-gpio-input\",\"core\":true,\"output\":false},{\"pin\":10,\"consumer\":\"apertar-gpio-input\",\"core\":true,\"output\":false},{\"pin\":16,\"consumer\":\"some-driver\",\"core\":false,\"output\":false},{\"pin\":21,\"consumer\":\"apertar-rec-led\",\"core\":true,\"output\":true}]}") << ","
              << periph(doc, "neorotary4", "NeoRotary 4", "{\"state\":\"running\",\"detail\":\"Core reads it on bus 1 at 0x49.\",\"bus\":1,\"address\":\"0x49\"}") << ","
              << periph(doc, "pcf8574", "PCF8574 buttons", "{\"state\":\"found\",\"detail\":\"Found on bus 10 at 0x20, switched off.\",\"bus\":10,\"address\":\"0x20\"}") << ","
              << periph(doc, "grove_analog", "Grove analog (ADC)", "{\"state\":\"missing\",\"detail\":\"Not found on bus 1 at 0x04.\",\"bus\":1,\"address\":\"0x04\"}") << ","
              << periph(doc, "cfexpress_hat", "CFexpress hat", "{\"state\":\"running\",\"detail\":\"Card in the slot: Corsair MP600 MINI, 1.0 TB, 8.0 GT/s PCIe x1, mounted at /media/RAW.\",\"bus\":1,\"address\":\"0x34\"}")
              << "],\"i2c_buses\":[{\"bus\":0,\"name\":\"Synopsys DesignWare I2C adapter\"},{\"bus\":1,\"name\":\"Synopsys DesignWare I2C adapter\"},{\"bus\":10,\"name\":\"Synopsys DesignWare I2C adapter\"}]}}";
}
`);
execFileSync('g++', ['-std=c++20', '-I' + path.join(coreTree, 'src'), path.join(work, 'gen.cpp'), '-o', path.join(work, 'gen')]);
// The fixture plus two switches in a [gpio_switches] that is switched off: a two-way on GPIO 19, a three-way on 22 and 23.
const withSwitches = path.join(work, 'with-switches.conf');
fs.writeFileSync(withSwitches, fs.readFileSync(fixture, 'utf8') + '\n[gpio_switches]\nenabled=false\nswitch0_pins=19\nswitch0_on=photo\n' +
  'switch1_pins=22,23\nswitch1_position0=record_toggle\nswitch1_position2=photo\n');
const getControls = execFileSync(path.join(work, 'gen'), [withSwitches, 'controls'], { encoding: 'utf8' });
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
    await q('document.getElementById("settingsButton").click(); 0'); await sleep(600);
    await q('setSettingsPanel("controls"); 0'); await sleep(1200);
    const rowOf = (title) => `[...document.querySelectorAll("#controlsRows .controls-row")].find(r=>r.querySelector(".controls-row-title").textContent===${JSON.stringify(title)})`;
    // a button line is gesture | action | Remove: its action is the second select
    const actionOf = (line) => `${line}.querySelectorAll("select")[${'1'}]`;
    const change = (select, value) => `(() => { const s=${select}; s.value=${JSON.stringify(value)}; s.dispatchEvent(new Event("change",{bubbles:true})); return 0; })()`;
    const lineOf = (title, index) => `[...${rowOf(title)}.querySelectorAll(".controls-line")][${index}]`;
    const clickText = (text) => `[...document.querySelectorAll("#controlsRows button")].find(b=>b.textContent===${JSON.stringify(text)}).click(), 0`;
    const sentKeys = (p) => Object.keys(p || {}).filter((k) => k.startsWith('set.') || k.startsWith('unset.'));

    console.log('--- Controls: one card per device that is there');
    check('Controls and Config are two nav items, Controls first', await q('(() => { const n=[...document.querySelectorAll(".settings-nav-item")].map(b=>b.dataset.panel); return n.indexOf("controls")>=0 && n.indexOf("controls")<n.indexOf("config"); })()'));
    const heads = await q('JSON.stringify([...document.querySelectorAll("#controlsRows .controls-peripheral")].map(c=>({title:c.querySelector(".controls-peripheral-head .controls-row-title").textContent, pill:c.querySelector(".online-pill").textContent, details:[...c.querySelectorAll(".controls-peripheral-head .controls-row-detail")].map(e=>e.textContent), settings:c.querySelectorAll(".controls-settings").length, groups:[...c.querySelectorAll(".controls-group-title")].map(e=>e.textContent), rows:c.querySelectorAll(".controls-row").length, addBar:!!c.querySelector(".controls-add-bar")})))').then(JSON.parse);
    console.log('    devices on Controls:', JSON.stringify(heads));
    check('Controls shows the GPIO, the NeoRotary and the PCF8574 (found); not the Grove ADC (not found) nor the CFexpress hat (no controls)', heads.map((h) => h.title).join('|') === 'Raspberry Pi GPIO|NeoRotary 4|PCF8574 buttons');
    check('each card holds its heading, its groups and rows: the GPIO card has buttons, switches, encoders and the add bar; the NeoRotary its four knobs',
      heads[0].groups.join('|') === 'GPIO buttons|GPIO switches (switched off in the file)|GPIO encoders (switched off in the file)' && heads[0].addBar && heads[1].rows === 4 && !heads[1].addBar &&
      await q('document.querySelectorAll("#controlsRows > .controls-group, #controlsRows > .controls-row").length === 0'));
    check('no settings on Controls; a running device shows no message, a found-but-off one says so', heads.every((h) => h.settings === 0) && heads[0].pill === 'Detected' && heads[0].details.length === 0 && heads[2].pill === 'Detected, off' && /switched off/.test(heads[2].details.join(' ')));
    const titles = await q('[...document.querySelectorAll("#controlsRows .controls-row-title")].map(e=>e.textContent).join(", ")');
    console.log('    rows:', titles);
    check('GPIO 10, GPIO 6, the two switches and the four knobs are there', ['GPIO 10', 'GPIO 6', 'GPIO 19', 'GPIO 22 + 23', 'Knob 1', 'Knob 4'].every((t) => titles.includes(t)));
    const switchLines = await q(`JSON.stringify([...${rowOf("GPIO 22 + 23")}.querySelectorAll(".controls-line")].map(l=>l.querySelector(".controls-line-label").textContent+"="+l.querySelector("select").value))`).then(JSON.parse);
    check('the three-way switch shows its three positions with their actions', switchLines.join('|') === 'Position 1 (GPIO 22)=record_toggle|Position 2 (middle)=none|Position 3 (GPIO 23)=photo');
    const d10 = await q(`(() => { const s=${actionOf(lineOf("GPIO 10", 0))}; return JSON.stringify({value:s.value, label:s.selectedOptions[0].textContent, groups:s.querySelectorAll("optgroup").length}); })()`).then(JSON.parse);
    check('GPIO 10 shows "Record or photo (main button)" selected, with grouped options', d10.value === 'capture' && /Record or photo/.test(d10.label) && d10.groups >= 5);
    const knob = await q(`JSON.stringify([...${rowOf("Knob 1")}.querySelectorAll(".controls-line")].map(l=>l.querySelector(".controls-line-label").textContent+"="+l.querySelector("select").value))`).then(JSON.parse);
    check('Knob 1: clockwise iso_up, counter-clockwise iso_down, press iso', knob.join('|') === 'Turn clockwise=iso_up|Turn counter-clockwise=iso_down|Press=iso');
    const turnOpts = await q(`JSON.stringify([...${rowOf("Knob 1")}.querySelector("select").options].map(o=>o.value))`).then(JSON.parse);
    check('a turn offers only stepping actions (no capture, no photo, no zoom)', turnOpts.includes('iso_up') && turnOpts.includes('fps_down') && !turnOpts.includes('capture') && !turnOpts.includes('photo') && !turnOpts.includes('zoom_toggle'));
    check('Save is disabled and the pill says Ready', await q('document.getElementById("saveControlsButton").disabled && document.getElementById("controlsStatePill").textContent==="Ready"'));

    console.log('--- a button line is a gesture dropdown, like Cinemate; + Add action');
    const gestures = await q(`JSON.stringify([...${lineOf("GPIO 10", 0)}.querySelector(".controls-gesture").options].map(o=>o.textContent))`).then(JSON.parse);
    check('the Press line\'s gesture is a dropdown: Press, Single, Double, Triple click, Hold', gestures.join('|') === 'Press|Single click|Double click|Triple click|Hold');
    await q(`[...${rowOf("GPIO 10")}.querySelectorAll("button")].find(b=>b.textContent==="+ Add action").click(), 0`); await sleep(200);
    const added = await q(`(() => { const l=[...${rowOf("GPIO 10")}.querySelectorAll(".controls-line")]; const g=l[1].querySelector(".controls-gesture"); const pressOpt=[...g.options].find(o=>o.value===""); const dblInPress=[...l[0].querySelector(".controls-gesture").options].find(o=>o.value==="_double"); return JSON.stringify({gesture:g.value, pressGreyed:pressOpt.disabled, doubleGreyedOnPress:dblInPress.disabled}); })()`).then(JSON.parse);
    check('+ Add action adds a line on Double click (Press is taken); each line greys out the gesture the other uses', added.gesture === '_double' && added.pressGreyed && added.doubleGreyedOnPress);
    await q(change(actionOf(lineOf("GPIO 10", 1)), 'photo')); await sleep(200);
    const look = await q(`(() => { const lines=[...${rowOf("GPIO 10")}.querySelectorAll(".controls-line")].slice(0,2); const card=document.querySelector("#controlsRows .controls-peripheral").getBoundingClientRect(); const box=e=>e.getBoundingClientRect(); const a=lines.map(l=>box(l.querySelectorAll("select")[1])); const r=lines.map(l=>box(l.querySelector(".controls-line-remove button"))); return JSON.stringify({actionLeft:a.map(x=>Math.round(x.left)), actionWidth:a.map(x=>Math.round(x.width)), removeLeft:r.map(x=>Math.round(x.left)), removeToCard:Math.round(card.right-r[0].right), color:getComputedStyle(lines[0].querySelector(".controls-line-remove button")).color, sameLine:Math.abs((r[0].top+r[0].bottom)/2-(a[0].top+a[0].bottom)/2)<12}); })()`).then(JSON.parse);
    console.log('    alignment:', JSON.stringify(look));
    check('both lines\' action dropdowns start and end at the same place; both Removes line up, red, at the far right, on the dropdown\'s line',
      look.actionLeft[0] === look.actionLeft[1] && look.actionWidth[0] === look.actionWidth[1] && look.removeLeft[0] === look.removeLeft[1] && look.removeToCard <= 20 && look.color === 'rgb(252, 165, 165)' && look.sameLine);
    sent = []; await q('document.getElementById("saveControlsButton").click(); 0'); await sleep(1500);
    console.log('    Save sent:', JSON.stringify(sent[0]));
    check('Save sends set.gpio_buttons.d10_double=photo and nothing else', sent[0] && sent[0]['set.gpio_buttons.d10_double'] === 'photo' && sentKeys(sent[0]).length === 1);
    await q(change(`${lineOf("GPIO 6", 0)}.querySelector(".controls-gesture")`, '_hold')); await sleep(200);
    sent = []; await q('document.getElementById("saveControlsButton").click(); 0'); await sleep(1500);
    console.log('    Save sent:', JSON.stringify(sent[0]));
    check('moving GPIO 6\'s Press to Hold sends unset d6 and set d6_hold with the same action', sent[0] && sent[0]['unset.gpio_buttons.d6'] === 'true' && sent[0]['set.gpio_buttons.d6_hold'] && sentKeys(sent[0]).length === 2);

    console.log('--- Config: the Hardware card');
    await q('setSettingsPanel("config"); 0'); await sleep(1200);
    check('the Hardware card is first on Config, above the text editor', await q('(() => { const p=document.querySelector(".settings-panel.active"); const t=[...p.querySelectorAll(".settings-card-title")].map(e=>e.textContent); return p.dataset.panel==="config" && t[0]==="Hardware" && t.indexOf("Apertar Config")>0; })()'));
    const hw = await q('JSON.stringify([...document.querySelectorAll("#hardwareDevices .controls-peripheral")].map(c=>({title:c.querySelector(".controls-row-title").textContent, pill:(c.querySelector(".online-pill")||{}).textContent||"", details:[...c.querySelectorAll(".controls-row-detail")].map(e=>e.textContent), fields:[...c.querySelectorAll(".controls-settings .field-stack")].map(f=>f.querySelector(".input-label").textContent+"="+(f.querySelector("select,input").value))})))').then(JSON.parse);
    console.log('    hardware:', JSON.stringify(hw.map((h) => h.title + ' [' + h.pill + '] ' + h.details.join(' / '))));
    check('it lists the I2C buses, with what Core finds on each', hw[0].title === 'I2C buses' && hw[0].details.some((d) => /^Bus 1 \(Synopsys DesignWare I2C adapter\): NeoRotary 4, CFexpress hat/.test(d)) && hw[0].details.some((d) => /^Bus 10 .*PCF8574 buttons/.test(d)));
    check('then every device, detected or not: GPIO, NeoRotary 4, PCF8574, Grove ADC (Not found, with where it looked), CFexpress hat', hw.slice(1).map((h) => h.title).join('|') === 'Raspberry Pi GPIO|NeoRotary 4|PCF8574 buttons|Grove analog (ADC)|CFexpress hat' && hw[4].pill === 'Not found' && /Not found on bus 1 at 0x04/.test(hw[4].details.join(' ')));
    check('the CFexpress hat card: Detected, its settings from the file (on, bus 1, 0x34)', hw[5].pill === 'Detected' && hw[5].fields.join('|') === 'On=true|I2C bus=1|Address=0x34');
    check('a supported device that is not found is greyed out (the Grove ADC), the detected ones are not', await q('(() => { const c=[...document.querySelectorAll("#hardwareDevices .controls-peripheral")]; const by=t=>c.find(x=>x.querySelector(".controls-row-title").textContent===t); return by("Grove analog (ADC)").classList.contains("undetected") && getComputedStyle(by("Grove analog (ADC)")).opacity==="0.5" && !by("NeoRotary 4").classList.contains("undetected") && !by("Raspberry Pi GPIO").classList.contains("undetected") && !by("PCF8574 buttons").classList.contains("undetected") && !by("CFexpress hat").classList.contains("undetected"); })()'));
    check('the GPIO settings show the file: On, active low, pull up, 60 ms, 12 ms, chip auto', hw[1].fields.join('|') === 'On=true|Pressed reads low (button to GND)=true|Pull=up|Debounce (ms)=60|Poll every (ms), chips without edge events=12|GPIO chip=auto');
    check('the NeoRotary shows bus 1 and 0x49 from the file', hw[2].fields.includes('I2C bus=1') && hw[2].fields.includes('Address=0x49'));
    await q('(() => { const f=[...document.querySelectorAll("#hardwareDevices .controls-settings .field-stack")].find(f=>/Debounce/.test(f.textContent)); const i=f.querySelector("input"); i.focus(); i.value="80"; i.dispatchEvent(new Event("input",{bubbles:true})); return 0; })()'); await sleep(200);
    check('typing in Debounce enables Save Hardware at once, and the cursor stays in the field', await q('!document.getElementById("saveHardwareButton").disabled && document.activeElement && document.activeElement.type==="number" && document.activeElement.value==="80"'));
    sent = []; await q('document.getElementById("saveHardwareButton").click(); 0'); await sleep(1500);
    console.log('    Save Hardware sent:', JSON.stringify(sent[0]));
    check('Save Hardware sends set.gpio_buttons.debounce_ms=80 and nothing else', sent[0] && sent[0]['set.gpio_buttons.debounce_ms'] === '80' && sentKeys(sent[0]).length === 1);
    await q('setSettingsPanel("controls"); 0'); await sleep(1200);

    console.log('--- change a button and a knob, then Save');
    await q(change(actionOf(lineOf("GPIO 10", 0)), 'record_toggle')); await q(change(`${rowOf("Knob 2")}.querySelector("select")`, 'shutter_down')); await sleep(200);
    check('Save is enabled and the pill says Unsaved', await q('!document.getElementById("saveControlsButton").disabled && document.getElementById("controlsStatePill").textContent==="Unsaved"'));
    check('the two changed rows are marked', await q('document.querySelectorAll("#controlsRows .controls-row.changed").length') === 2);
    sent = []; await q('document.getElementById("saveControlsButton").click(); 0'); await sleep(1500);
    const p = sent[0]; console.log('    Save sent:', JSON.stringify(p));
    check('it sent set_controls with the loaded revision and only the two keys', p && p.cmd === 'set_controls' && p.base === loadedRevision && p['set.gpio_buttons.d10'] === 'record_toggle' && p['set.neorotary4.encoder1_cw'] === 'shutter_down' && sentKeys(p).length === 2);
    const msg = await q('document.getElementById("controlsMessage").hidden ? "(hidden)" : document.getElementById("controlsMessage").innerText');
    console.log('    message:', msg);
    check('it says Saved and to restart Apertar Core; Save is disabled again', /Saved\. Restart Apertar Core/.test(msg) && await q('document.getElementById("saveControlsButton").disabled'));

    console.log('--- add a button, a two-way and a three-way switch; remove a button and a switch; then a refusal');
    check('the GPIO card has three add buttons', await q('[...document.querySelectorAll("#controlsRows .controls-add-bar button")].map(b=>b.textContent).join("|")') === '+ Add GPIO button|+ Add GPIO two-way switch|+ Add GPIO three-way switch');
    await q(clickText('+ Add GPIO button')); await sleep(200);
    const pins = await q(`JSON.stringify([...${rowOf("New button")}.querySelector(".controls-pin").options].map(o=>o.value))`).then(JSON.parse);
    check('a new button row has its pin dropdown in the row, with free pins only (not 2, 3, 6, 10, 21, nor 16 held by another program)', pins.length >= 15 && !['2', '3', '6', '10', '21', '16'].some((pin) => pins.includes(pin)));
    await q(change(`${rowOf("New button")}.querySelector(".controls-pin")`, '17')); await q(change(actionOf(lineOf("New button", 0)), 'photo')); await sleep(200);
    await q(clickText('+ Add GPIO two-way switch')); await sleep(200);
    check('pin 17 is no longer offered to the new switch', await q(`![...${rowOf("New two-way switch")}.querySelector(".controls-pin").options].some(o=>o.value==="17")`));
    const two = await q(`JSON.stringify({pin:${rowOf("New two-way switch")}.querySelector(".controls-pin").value, lines:[...${rowOf("New two-way switch")}.querySelectorAll(".controls-line-label")].map(e=>e.textContent)})`).then(JSON.parse);
    check('a new two-way switch has On and Off', two.lines.join('|') === 'On|Off');
    await q(change(`${lineOf("New two-way switch", 0)}.querySelector("select")`, 'record_toggle')); await sleep(200);
    await q(clickText('+ Add GPIO three-way switch')); await sleep(200);
    const three = await q(`JSON.stringify({pins:[...${rowOf("New three-way switch")}.querySelectorAll(".controls-pin")].map(s=>s.value), lines:[...${rowOf("New three-way switch")}.querySelectorAll(".controls-line-label")].map(e=>e.textContent)})`).then(JSON.parse);
    console.log('    three-way:', JSON.stringify(three));
    check('a new three-way switch has two different pins and a line per position, named after its pins', three.pins.length === 2 && three.pins[0] !== three.pins[1] && three.lines.join('|') === `Position 1 (GPIO ${three.pins[0]})|Position 2 (middle)|Position 3 (GPIO ${three.pins[1]})`);
    await q(change(`${lineOf("New three-way switch", 0)}.querySelector("select")`, 'photo')); await sleep(200);
    check('the switches group opens and says Save switches it on', await q(`${rowOf("New two-way switch")}.querySelector(".controls-row-detail").textContent === "Saving switches this group on."`));
    await q(`${lineOf("GPIO 6", 0)}.querySelector(".controls-line-remove button").click(), 0`); await sleep(200);
    await q(`${lineOf("GPIO 22 + 23", 0)}.querySelector(".controls-line-remove button").click(), 0`); await sleep(200);
    check('GPIO 6 (its one line removed) and the existing three-way switch are struck', await q(`${rowOf("GPIO 6")}.classList.contains("removed") && ${rowOf("GPIO 22 + 23")}.classList.contains("removed")`));
    nextReply = JSON.stringify({ ok: false, code: 'errors', error: 'Not saved: 1 new error. GPIO 17 is used twice.', new_errors: [{ line: 140, message: 'GPIO 17 is used twice.' }], issues: [] });
    sent = []; await q('document.getElementById("saveControlsButton").click(); 0'); await sleep(1500);
    const p2 = sent[0]; console.log('    Save sent:', JSON.stringify(p2));
    check('it sent the new button, both new switches (next free indexes 2 and 3, group switched on) and the removals',
      p2 && p2['set.gpio_buttons.d17'] === 'photo' && p2['set.gpio_switches.switch2_pins'] === two.pin && p2['set.gpio_switches.switch2_on'] === 'record_toggle' &&
      p2['set.gpio_switches.switch3_pins'] === three.pins.join(',') && p2['set.gpio_switches.switch3_position0'] === 'photo' && p2['set.gpio_switches.enabled'] === 'true' &&
      p2['unset.gpio_buttons.d6'] === 'true' && p2['unset.gpio_switches.switch1_pins'] === 'true' && p2['unset.gpio_switches.switch1_position0'] === 'true' && p2['unset.gpio_switches.switch1_position2'] === 'true' &&
      !('set.gpio_switches.switch2_off' in p2));
    const msg2 = await q('document.getElementById("controlsMessage").innerText.replace(/\\n+/g," / ")'); console.log('    message:', msg2);
    check('a refusal shows the error with its line number and keeps the page as it was', /Not saved/.test(msg2) && /Line 140/.test(msg2) && await q('!document.getElementById("saveControlsButton").disabled && controlsState.added.length===3 && controlsState.removed.size===1'));
    nextReply = JSON.stringify({ ok: false, code: 'stale', error: 'The file changed since you loaded it. Reload, then change it again.', issues: [] });
    await q('document.getElementById("saveControlsButton").click(); 0'); await sleep(1200);
    check('a stale file says the choices stay and to press Reload', /Your choices stay on the page\. Press Reload/.test(await q('document.getElementById("controlsMessage").innerText')));
    nextReply = null;
    await q('document.getElementById("reloadControlsButton").click(); 0'); await sleep(1200);
    check('Reload drops the unsaved choices', await q('controlsState.edits.size===0 && controlsState.added.length===0 && controlsState.removed.size===0 && !controlsDirty() && document.getElementById("saveControlsButton").disabled'));
    tab.close();
  } catch (e) { console.log('TEST ERROR:', e.message); results.push(['no script error', false]); }
  finally { chrome.kill(); server.close(); fs.rmSync(profile, { recursive: true, force: true }); fs.rmSync(work, { recursive: true, force: true }); }
  const bad = results.filter((r) => !r[1]);
  console.log(`\n${results.length - bad.length} of ${results.length} checks passed`);
  process.exit(bad.length ? 1 : 0);
})();
