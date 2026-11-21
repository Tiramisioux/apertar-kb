// Checks every "code" line of the coding map against the trees it claims to quote.
//   node check_map.js [index.html] [core-fork-dir] [ui-fork-dir]
// A node or edge shows `code` in fork mode and `up.code` (or `code` when there is no override) in official mode.
// Each is searched, whitespace-normalised, in the file named by `path` (fork: the given dirs; official: the
// upstream-1.6.0 worktrees). Recipe diffs: every context line (and removed line) must occur in the step's file.
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const MAP = process.argv[2] || '/home/user/apertar-coding-map/index.html';
const TREES = {
  fork: { core: process.argv[3] || '/home/user/Apertar-Core', ui: process.argv[4] || '/home/user/Apertar-UI' },
  official: { core: '/home/user/wt/core-upstream', ui: '/home/user/wt/ui-upstream' },
};
const norm = (s) => String(s).replace(/\s+/g, ' ').trim();
const cache = {};
const read = (f) => { if (!(f in cache)) { try { cache[f] = norm(fs.readFileSync(f, 'utf8')); } catch (e) { cache[f] = null; } } return cache[f]; };
function filesFor(p, mode, hintRepo) {
  // "~/ApertarUI/qml/X.qml", "~/ApertarCore/src/a.cpp + src/b.cpp", "src/x.cpp" (recipes: repo from the node kind)
  const out = [];
  let repo = hintRepo;
  // "src/hardware/ (Pcf8574Input, NeoRotary4Input, GpioInput)" names files in a folder; "X.hpp / .cpp" a pair.
  let text = String(p).replace(/([\w\/~.-]*\/)\s*\(([^)]*)\)/g, (m, dir, names) =>
    names.split(/\s*,\s*/).map((n) => /\.\w+$/.test(n) ? dir + n : dir + n + '.cpp').join(' + '));
  text = text.replace(/(\S+)\.(hpp|h|cpp)\s*\/\s*\.(hpp|h|cpp)/g, '$1.$2 + $1.$3').replace(/→.*$/, '');
  for (const part of text.split(/\s*(?:\+|,| and )\s*/)) {
    let q = part.trim().replace(/\s*\(.*\)\s*$/, '');
    if (q.startsWith('~/ApertarUI/')) { repo = 'ui'; q = q.slice(12); }
    else if (q.startsWith('~/ApertarCore/')) { repo = 'core'; q = q.slice(14); }
    if (!repo || !q || q.endsWith('/')) continue;
    out.push(path.join(TREES[mode][repo], q));
  }
  return out;
}
// A quoted line may be shortened with "…": then every piece between the dots must occur, in order.
function has(files, code) {
  const pieces = norm(code).split('…').map((x) => x.trim()).filter((x) => x.length > 2);
  if (!pieces.length) return true;
  return files.some((f) => {
    const t = read(f);
    if (t === null) return false;
    let at = 0;
    for (const piece of pieces) { const i = t.indexOf(piece, at); if (i < 0) return false; at = i + piece.length; }
    return true;
  });
}
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  // The map's script is one IIFE, so its data is not global: hand it out through window before the IIFE ends.
  const html = fs.readFileSync(MAP, 'utf8');
  const hook = 'window.__MAP = { N, E, RECIPES, TOURS, UIP, COREP, FORKDATA };\n})();';
  const patched = html.replace(/\}\)\(\);\s*<\/script>\s*<\/body>|\}\)\(\);\s*<\/script>\s*(?=\s*<\/html>)/, (m) => hook + m.slice(m.indexOf('</script>')));
  if (patched === html) throw new Error('could not find the end of the map script');
  await page.setContent(patched, { waitUntil: 'domcontentloaded' });
  const data = JSON.parse(await page.evaluate('JSON.stringify(window.__MAP)'));
  await browser.close();
  let checked = 0; const bad = [];
  const kindRepo = { ui: 'ui', core: 'core', web: 'core', hw: 'core', file: null };
  const items = Object.entries(data.N).map(([id, n]) => ['N.' + id, n]).concat(data.E.map((e) => ['E.' + e.id, e]));
  for (const [id, it] of items) {
    if (!it.path) continue;
    for (const mode of ['fork', 'official']) {
      const code = mode === 'official' && it.up && ('code' in it.up) ? it.up.code : it.code;
      const p = mode === 'official' && it.up && it.up.path ? it.up.path : it.path;
      if (!code || /^https?:|^curl |^\$ /.test(code)) continue;
      if (mode === 'official' && it.fork && !(it.up && 'code' in it.up)) continue;   // fork-only line with no official variant
      const files = filesFor(p, mode);
      if (!files.length) continue;
      ++checked;
      // a code field may hold several lines: every line must be found
      const lines = String(code).split('\n').map((l) => norm(l.replace(/\s\/\/ .*$/, ''))).filter((l) => l && l !== '…' && !l.startsWith('//'));
      const missing = lines.filter((l) => !has(files, l));
      if (missing.length) bad.push(`${id} [${mode}] not in ${files.map((f) => f.replace('/home/user/', '')).join(', ')}: ${missing[0].slice(0, 110)}`);
    }
  }
  for (const r of data.RECIPES) {
    r.steps.forEach((st, i) => {
      const node = data.N[st.node] || {};
      for (const mode of ['fork', 'official']) {
        const diff = mode === 'official' && st.up && ('diff' in st.up) ? st.up.diff : st.diff;
        const file = mode === 'official' && st.up && st.up.file ? st.up.file : st.file;
        if (!diff || !file) continue;
        if (mode === 'official' && st.fork && !(st.up && 'diff' in st.up)) continue;
        const files = filesFor(file.replace(/ \/ \./g, ' + '), mode, kindRepo[node.kind] || (/\.qml|Bridge|Preview|main\.cpp/.test(file) ? 'ui' : 'core'));
        if (!files.length) continue;
        const ctx = String(diff).split('\n').filter((l) => !l.startsWith('+')).map((l) => norm(l.replace(/^[- ]/, '').replace(/\s\/\/ .*$/, ''))).filter((l) => l && l !== '…' && !l.startsWith('//') && !l.startsWith('#') && !l.startsWith('<!--') && l.length > 6);
        for (const l of ctx) {
          ++checked;
          if (!has(files, l)) bad.push(`RECIPES.${r.id}.steps[${i}] (${st.node}) [${mode}] context not in ${files.map((f) => path.basename(f)).join(', ')}: ${l.slice(0, 110)}`);
        }
      }
    });
  }
  for (const t of data.TOURS) for (const s of t.steps) if (!data.N[s] && !data.E.find((e) => e.id === s)) bad.push(`TOURS.${t.id}: unknown step ${s}`);
  console.log(`${checked} code lines checked, ${bad.length} not found`);
  bad.forEach((b) => console.log('  ' + b));
  process.exit(bad.length ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(2); });
