# Headless-Chrome test of the WebUI against the real Core

`harness.js`: serves the page from a `WebControlPage.cpp` (the raw string between `R"APERTAR(` and `)APERTAR"`) on 127.0.0.1:8770, proxies
`/api/*` (and the `X-` headers) to the Pi's real Core (`http://apertar.local:8000`), and drives Chrome over the DevTools protocol (Node 22
has `WebSocket`; no Playwright needed). It starts Chrome with `--autoplay-policy=no-user-gesture-required --mute-audio`.

    node harness.js <path to WebControlPage.cpp> <shots dir>      # reads <shots dir>/steps.json

`steps.json` is a list of steps: `{"viewport":[w,h]}`, `{"eval":"<js, may be async>","label":"..","wait":ms}`, `{"override":{...}}` (merged
into `/api/state`, e.g. `{"playback_hold":"recording"}` or a faked `ladder_active`), `{"shot":"name","selector":"#id"}` (an element) and
`{"fullshot":"name"}` (the viewport). The script prints each eval's result and the page's script errors. It does what a
person clicking does against the real Core: use only read-only steps (do not click Remove or Save on a card you care about; the
mode ladder autosaves, so a test that edits it writes the Pi's `mode_ladder.conf`).
