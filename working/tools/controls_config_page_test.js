// Controls: the Config page, tried in a real (headless) Chrome against the live camera. T38, part 2.
// Needs: node 22, Google Chrome on this Mac, ssh to the Pi as `apertar`, and the camera's web page reachable at BASE.
// Run:   ORIG=<path of controls_fixture_apertar-hardware.conf> node controls_config_page_test.js
// It saves the live ~/apertar-hardware.conf several times (a comment added, a bad value refused, an old tab refused)
// and puts it back byte for byte; if anything goes wrong it posts the fixture back. Never run during a take.
// Drives the live Config page in headless Chrome over the DevTools protocol (no packages needed).
const { spawn, execSync } = require('child_process');
const fs = require('fs'), os = require('os'), path = require('path');
const BASE = 'http://apertar.local:8000/';
const PORT = 9333;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const ssh = (cmd) => execSync(`ssh apertar '${cmd}'`, { encoding: 'utf8' }).trim();
const fileSha = () => ssh('sha256sum ~/apertar-hardware.conf | cut -c1-12');
const fileTail = () => ssh('tail -c 40 ~/apertar-hardware.conf | tr "\\n" "|"');

async function cdp(wsUrl) {
  const ws = new WebSocket(wsUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  let id = 0; const pending = new Map();
  ws.onmessage = (m) => { const d = JSON.parse(m.data); if (d.id && pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); } };
  const send = (method, params = {}) => new Promise((res) => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
  const evaluate = async (expression) => {
    const r = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
    if (r.result.exceptionDetails) throw new Error('page error: ' + JSON.stringify(r.result.exceptionDetails.exception || r.result.exceptionDetails).slice(0, 300));
    return r.result.result.value;
  };
  return { send, evaluate, close: () => ws.close() };
}

async function openTab(url) {
  const res = await fetch(`http://127.0.0.1:${PORT}/json/new?${encodeURIComponent(url)}`, { method: 'PUT' });
  const target = await res.json();
  const tab = await cdp(target.webSocketDebuggerUrl);
  await tab.send('Runtime.enable'); await tab.send('Page.enable');
  for (let i = 0; i < 40; i++) {                       // wait for the page script to define its functions
    try { if (await tab.evaluate('typeof fetchConfigFile === "function" && !!document.getElementById("settingsConfigEditor")')) break; } catch (e) {}
    await sleep(250);
  }
  await tab.evaluate('window.confirm = () => true; 0');   // "discard unsaved edits?" -> yes
  await tab.evaluate('(async () => { await fetchConfigFile(true); return 0; })()');
  return tab;
}
const pageState = (tab) => tab.evaluate(`JSON.stringify({
  revision: state.configRevision, dirty: state.configDirty,
  editorTail: document.getElementById("settingsConfigEditor").value.slice(-30),
  editorLen: document.getElementById("settingsConfigEditor").value.length,
  box: document.getElementById("settingsConfigIssues").hidden ? "(hidden)" : document.getElementById("settingsConfigIssues").innerText.replace(/\\n+/g, " / "),
  toast: document.getElementById("toast").textContent })`).then(JSON.parse);
// type into the editor like a person: set the value, fire "input", click Save
async function typeAndSave(tab, mutateJs) {
  await tab.evaluate(`(() => { const e = document.getElementById("settingsConfigEditor"); const t = e.value; e.value = (${mutateJs})(t); e.dispatchEvent(new Event("input", { bubbles: true })); return 0; })()`);
  await tab.evaluate('document.getElementById("saveConfigButton").click(); 0');
  await sleep(1800);
}

(async () => {
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'chrome-profile-'));
  const chrome = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`, '--no-first-run', '--disable-gpu', 'about:blank'], { stdio: 'ignore' });
  for (let i = 0; i < 40; i++) { try { await fetch(`http://127.0.0.1:${PORT}/json/version`); break; } catch (e) { await sleep(250); } }
  const origSha = fileSha();
  console.log('start: live file sha', origSha, '| tail', fileTail());
  const results = [];
  try {
    const tab1 = await openTab(BASE);
    const s0 = await pageState(tab1);
    console.log('page loaded: revision', s0.revision, '| editor', s0.editorLen, 'bytes | issues box', s0.box);

    console.log('\n--- Test 1: a normal save ---');
    await typeAndSave(tab1, 't => t + "# hello from the browser test\\n"');
    let s = await pageState(tab1);
    console.log('toast:', s.toast, '| box:', s.box, '| revision now', s.revision);
    console.log('file tail on the Pi:', fileTail(), '| sha', fileSha(), '| .bak ends with original:', ssh('tail -c 25 ~/apertar-hardware.conf.bak | tr "\\n" "|"'));
    results.push(['1a save with a comment', s.toast.startsWith('Config saved') && fileTail().includes('hello from the browser test')]);
    await typeAndSave(tab1, 't => t.replace("# hello from the browser test\\n", "")');
    s = await pageState(tab1);
    console.log('removed again. toast:', s.toast, '| file sha', fileSha());
    results.push(['1b save it back, file identical', fileSha() === origSha]);

    console.log('\n--- Test 2: a new error ---');
    await typeAndSave(tab1, 't => t.replace("bus=1\\naddress=0x49", "bus=999\\naddress=0x49")');
    s = await pageState(tab1);
    console.log('toast:', s.toast);
    console.log('issues box:', s.box);
    console.log('editor kept the bad text:', s.editorTail.length > 0, '| still dirty:', s.dirty, '| file unchanged:', fileSha() === origSha);
    results.push(['2 refused with a line number, text kept, file unchanged', /Line 105/.test(s.box) && s.dirty && fileSha() === origSha]);
    await tab1.evaluate('document.getElementById("reloadConfigButton").click(); 0'); await sleep(1200);
    s = await pageState(tab1);
    console.log('after Reload Config: dirty', s.dirty, '| box', s.box);

    console.log('\n--- Test 3: an old tab ---');
    const tab2 = await openTab(BASE);
    const r2 = (await pageState(tab2)).revision, r1 = (await pageState(tab1)).revision;
    console.log('both tabs loaded at revision', r1, r2);
    await typeAndSave(tab1, 't => t + "# written by tab one\\n"');
    console.log('tab 1 saved:', (await pageState(tab1)).toast, '| file tail', fileTail());
    await typeAndSave(tab2, 't => t + "# written by tab two\\n"');
    const t2 = await pageState(tab2);
    console.log('tab 2 toast:', t2.toast);
    console.log('tab 2 box:', t2.box);
    console.log('tab 2 keeps its text:', t2.editorTail.includes('tab two'), '| file still has tab one only:', fileTail().includes('tab one') && !fileTail().includes('tab two'));
    results.push(['3 old tab refused, text kept, no overwrite', /changed since you loaded/.test(t2.box) && t2.editorTail.includes('tab two') && !fileTail().includes('tab two')]);
    await typeAndSave(tab1, 't => t.replace("# written by tab one\\n", "")');
    console.log('restored via tab 1. file sha', fileSha());
    results.push(['file restored byte for byte', fileSha() === origSha]);
    tab1.close(); tab2.close();
  } catch (e) {
    console.log('TEST ERROR:', e.message);
    results.push(['no script error', false]);
  } finally {
    chrome.kill();
    if (fileSha() !== origSha) {           // never leave the file changed
      execSync(`curl -s -m 8 -X POST http://apertar.local:8000/api/config --data-binary @${process.env.ORIG} > /dev/null`);
      console.log('RESTORED from the fixture; sha now', fileSha());
    }
  }
  console.log('\nRESULTS');
  results.forEach(([n, ok]) => console.log(' ', ok ? 'PASS' : 'FAIL', n));
  console.log('final file sha', fileSha(), fileSha() === origSha ? '(identical to the start)' : '(DIFFERENT)');
  process.exit(0);
})();
