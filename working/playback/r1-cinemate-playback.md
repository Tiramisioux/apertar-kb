# R1: Cinemate playback, read as the reference to port

This is the reader report for the playback project. Patrik's brief: "port the playback function from cinemate, in the most Apertar like style". His decision of 2026-10-28: "make the playback in web ui similar to the current touch ui". The WebUI therefore gets playback that looks and behaves like Apertar's touch-UI clip browser and player. Cinemate supplies the browser-side mechanics.

This file describes **Cinemate only**: its UI, its backend, the recorder that feeds it, its history, and what is worth porting. No tree was edited.

## Sources and labels

| Prefix | Tree | Commit |
| --- | --- | --- |
| `cm:` | `/home/user/tiramisioux/cinemate` (branch `dev`) | `d6cc93e` |
| `cr:` | `/home/user/tiramisioux/cinepi-raw` (branch `dev`) | `63a08d5` |
| `hb:` | `/home/user/tiramisioux/cinemate-handbook` | `c99ff77` |
| `ac:` | Apertar Core, `scratchpad/controls/core-tip` | `eb9cc39` |
| `kb:` | `/home/user/apertar-kb` | `dbcbfca` |

Shorthands:

- `SE.html` means `cm:src/module/app/templates/settings_editor.html`.
- `SE.py` means `cm:src/module/app/settings_editor.py`.
- `pb.py` means `cm:src/module/app/playback.py`.
- `dp.py` means `cm:src/module/app/dng_preview.py`.
- `rf.py` means `cm:src/module/app/raw_files.py`.

Every `path:line` is at the commit in the table above.

Each claim carries one of three labels:

- **[C] CONFIRMED**: I opened that line.
- **[P] PROBABLE**: derived from lines I opened. The derivation is given.
- **[U] UNCONFIRMED**: stated somewhere I could not check, or not checked.

---

## 0. In one screen

- **Where it lives.** Playback is a **tab of the settings editor** (`/settings-editor/`, tab "Playback", hint "review takes"). It is not part of the shooting screen. That screen's only route to it is the settings link titled "Settings, storage and playback". [C] `SE.html:1492`; `cm:src/module/app/templates/template.html:1076`.
- **How the picture travels.** The browser gets **one JPEG per HTTP GET**, shown in a single `<img>` and paced by a JavaScript clock. There is no `<video>`, no MJPEG stream and no WebSocket. [C] `SE.html:6312-6318` (URL), `6625-6635` (show), `6644-6670` (clock).
- **What the picture is.** It is the **colour JPEG thumbnail that cinepi-raw embeds in every DNG** (IFD1, 640×360 by default). The server reads it out of the file and serves it unchanged. Raw decode still exists in the code but is switched off. [C] `pb.py:227-236`, `pb.py:284-294`; `dp.py:570-571`; `cr:cinepi/cinepi_controller.cpp:47,64`.
- **No audio plays in the browser.** The route `/api/playback/clips/<name>/audio` exists, but no page code calls it. [C] `SE.py:1446-1461`. A grep of the templates finds `playback/clips` only at `SE.html:6285` (a comment), `6316`, `6367` and `6403`, and none of them is `/audio`.
- **Recording always wins.** Frame and WAV requests answer **409** in two cases:
  - the card is being written (recording, buffer flush, buffering, storage pre-roll);
  - the camera-status feed is dead.

  The page greys the stage and re-checks every 3 s. [C] `SE.py:249-280`, `1407-1413`, `1447-1456`; `SE.html:6402-6449`, `6687-6714`.
- **What the pane does not have.** There is no delete, zoom, speed control (apart from conform on/off), keyboard shortcut or audio. Delete and download live on the separate **RAW files** pane. [C] The playback script block `SE.html:6284-6745` has no delete, zoom or keydown handler. The transport markup is `SE.html:2618-2627`.

---

## 1. The UI: the Playback pane

### 1.1 Where it lives and when it loads

- **Tab order.** The page tabs are config.txt, i2c, lens, settings, **playback**, raw. [C] `SE.html:1487-1493`.
  - The tab hint is "review takes" and the rail blurb is "Review takes off the card." [C] `cm:resources/gui-text/00-chrome.md:29-31`, `141-143`.
  - The docs give the tab as "Playback · review takes". [C] `cm:docs/playback.md:17`.
- **URL.** The pane is at `http://cinepi.local:5000/settings-editor/`, or `http://10.42.0.1:5000/settings-editor/` on the camera's hotspot. [C] `cm:docs/playback.md:13-17`.
- **It loads with the page, whichever tab is open.** The page-load block calls `refreshPlaybackPane()`. [C] `SE.html:6741-6745`. That call:
  - fetches the clip index [C] `SE.html:6366-6386`;
  - renders every take card, and each card queues a request for its frame-0 thumbnail [C] `SE.html:6481`;
  - selects the newest take, which builds a 16-frame filmstrip and shows frame 0 [C] `SE.html:6383`, `6566-6578`, `6553-6555`.

  So opening the settings editor on *any* tab costs N + 17 frame requests for a card with N takes. [P] Count derived from the lines above: N card thumbnails, 16 filmstrip frames and 1 stage frame.
- **The 3 s poll never stops.** `setInterval(pbCheckRecording, 3000)` runs whichever tab is visible. [C] `SE.html:6449`. The RAW pane's own poll, by contrast, stands down unless its page is active. [C] `SE.html:5956`.

### 1.2 Layout, top to bottom (markup at d6cc93e)

| # | Region | Content | Cite |
| --- | --- | --- | --- |
| 1 | Heading | "Playback" (`pane.playback`). The pane has no description. | [C] `SE.html:2569-2572`; `cm:resources/gui-text/11-playback-playback.md:9-12` |
| 2 | Toolbar | **Sort** select: Oldest first (default), Newest first, Largest first. **View** select: One row (default), Grid. | [C] `SE.html:2574-2595` |
| 3 | Take strip `#pbTakeStrip` | Cards 176 px wide, each with a 16:9 thumbnail. "One row" scrolls sideways; "Grid" wraps. The selected card gets a green border. | [C] `SE.html:2596`; CSS `SE.html:1310-1327` |
| 4 | Stage `#pbStage` | A black 16:9 box with a 2 px white border. It holds `<img id="pbFrame">` (object-fit: contain) and two overlays: the take name top-left (monospace, 11 px, ellipsised at 70% width) and the timecode top-right (`00:00:00:00`). A lock overlay has a red uppercase title and a body text. | [C] `SE.html:2598-2610`; CSS `SE.html:1329-1343` |
| 5 | Scrub | A filmstrip of up to 16 frames (38 px high, 55% opacity), a 2 px white playhead, and an invisible `<input type="range">` laid over the whole strip ("Scrub through take"). | [C] `SE.html:2612-2616`; CSS `SE.html:1345-1350`; `SE.html:6566-6578` |
| 6 | Transport | First frame, Previous frame, **PLAY/PAUSE** (primary button, at least 104 px wide), Next frame, Last frame, Loop (`aria-pressed`), a spacer, then the counter `i / last`. | [C] `SE.html:2618-2627` |
| 7 | HUD | FPS, Resolution, Depth, Sensor and Source, plus a row of boxes on the right (§1.4). | [C] `SE.html:2629-2636` |
| 8 | Rate row | Recorded, Conform, Playing at, Achieved, Frames skipped. | [C] `SE.html:2637-2643` |
| 9 | Note | "**Achieved rate is measured, not assumed.** The player holds the clock and skips frames the camera could not decode in time, and shows the count — rather than letting the take quietly run slow." | [C] `SE.html:2644-2647`; `11-playback-playback.md:15-17` |
| 10 | "Playback settings" | One card, "Use conform frame rate <N>", a toggle that is on by default. | [C] `SE.html:2649-2657`; `11-playback-playback.md:19-22` |

**Don't take the layout from the screenshot.** `cm:docs/images/gui-playback.png` is older than the markup. It still shows a "TAKES ON CARD" label (dropped in `066484e`) and a pane sub-heading. [C] I viewed the image and read the `066484e` commit message.

**The order moved twice in one day.**

- `65f45c9` (2026-09-07) put the player above the takes.
- `0ce2208`, the same day, moved the strip back above the player "per operator request". It also added the One row / Grid toggle and made a click scroll *down* to the player.

`0ce2208`'s subject line is about dynamic resolution, so a log search for "playback" misses it. [C] `git log -1 65f45c9`, `git log -1 0ce2208`.

### 1.3 What each take card shows

[C] `SE.html:6451-6484`:

- **Thumbnail.** Frame 0, requested at `scale=8`, lazy-loaded and queued one at a time (§1.5).
- **Name.** The directory name, HTML-escaped, monospace and ellipsised.
- **Meta line.** `<frame_count> frames · <fps to 3 decimals> fps`, or `rate unknown`.
- **Chips:**
  - the storage label (`RAW`, `RAW1`, ...);
  - `HDR` when `hdr` is set;
  - `WAV` when `has_wav` is set;
  - a speed chip such as `0.83× SLOMO` or `2.00× FAST` when the conform rate divided by the take's fps is not 1.

The card shows **no date, duration or size**. [C] Same lines. `size_bytes` is used only by the "Largest first" sort. [C] `SE.html:6332-6339`.

### 1.4 The HUD for the selected take

| Field | Source (clip JSON key) | Format | Cite |
| --- | --- | --- | --- |
| FPS | `fps` (DNG tag 51044 of the first frame) | `25.000` | [C] `SE.html:6526` |
| Resolution | `width`, `height` (IFD0, the raw frame) | `3840×2200` | [C] `SE.html:6527` |
| Depth | `bits` (the source depth; a LOG10 take shows 12 or 16) | `16-bit` | [C] `SE.html:6528`; `dp.py:280-281` |
| Sensor | `sensor` (TIFF Model tag 272) | `imx585` | [C] `SE.html:6529`; `cr:cinepi/dng_encoder.cpp:1046-1048` |
| Source | `source` | `Thumbnail`, `No thumbnail` or `—` | [C] `SE.html:6536-6538` |

The boxes come from `pbRenderBoxes()`. [C] `SE.html:6593-6623`:

- `12b`/`16b`: the bits.
- `SDR`/`HDR`: `mode_label`.
- `CRV`/`LIN`: `encoding`. `LIN` is drawn in the "off" style.
- `LOG10`: shown when `log10` is set.
- `WAV` or `—`.
- `CNF`: shown when conforming changes the speed.
- `DROP N`: purple, shown when `dropped_frames` is above 0.

**Colours are borrowed from the shooting screen** "so reading a recorded take looks like reading the live camera": label grey 136, value 249, box grey 136, badge 205, DROP purple 120/40/180. [C] CSS comment `SE.html:1302-1306`; values `SE.html:1356-1366`.

The rate row. [C] `SE.html:6580-6591`, `6659-6666`:

| Field | Shows |
| --- | --- |
| Recorded | `25.000 fps`, or `unknown`. |
| Conform | `25 fps`, or `off`. |
| Playing at | The speed factor, e.g. `0.50× SLOMO` or `2.00× FAST`, in warning colour when it is not 1. |
| Achieved | Frames whose `<img>` `onload` fired, averaged over windows of at least 500 ms. Colour: "ok" at 97% of target or more, "warn" at 85% or more, "bad" below that. |
| Frames skipped | Frames the clock jumped over. |

### 1.5 Behaviour

**Selecting a take**

- **Default selection.** The newest take by mtime is selected at load, and again whenever the selected take disappears. [C] `SE.html:6383`, `6341-6349`, `6425-6427`.
- **A click on a card** does the following. [C] `SE.html:6501-6523`:
  - pauses playback;
  - highlights the card and scrolls the strip so it is visible ("nearest");
  - scrolls the stage into view, but only on a real click.
- **Then it fills the player.** [C] `SE.html:6524-6556`:
  - resets the skip count;
  - fills the HUD;
  - sets the scrub maximum to `frame_count - 1`;
  - builds the filmstrip;
  - shows frame 0.
- **A take with no thumbnail.** The stage locks with the title "No embedded thumbnail" and the body "This take has no thumbnail — recorded with the toggle off, or before a rebuilt cinepi-raw supported it. Raw decode is far more demanding on the Pi and is not currently used as a fallback." [C] `SE.html:6546-6555`, `6689-6690`.

  Its card thumbnail is still requested, fails with 404 and stays blank. [P] `SE.html:6481` queues the request whatever `source` is. `frame_jpeg` then raises `PlaybackError` (`pb.py:290-294`), which the route turns into a 404 (`SE.py:1431-1432`).

**Playing**

- **The clock.** Playback runs on a wall-clock frame clock: `want = startFrame + floor((now - t0) * rate)`. [C] `SE.html:6644-6680`.
  - If `want` jumps more than one frame ahead, the gap is added to `skipped`.
  - The next tick is scheduled with `setTimeout` at the next frame's due time, not with `requestAnimationFrame`.
  - The rate is the conform rate (default) or the take's recorded fps. [C] `SE.html:6320-6323`.
- **Reaching the end.** Without loop, playback stops on the last frame. With loop, it wraps to 0 and resets the clock. [C] `SE.html:6653-6656`.
- **PLAY on the last frame (docs and code disagree).** `cm:docs/playback.md:48` says "Playing again from the last frame restarts from the beginning unless loop is on". The code does not do that: without loop, pressing PLAY on the last frame stops again at once. [P] `pbPlay` sets `startFrame` to the current `i` (`SE.html:6672-6680`). The next tick computes `want = total`, so it pauses (`6653-6654`).
- **Frame stepping.** ◀ and ▶ pause and step ±1. |◀ and ▶| jump to the first and last frame. [C] `SE.html:6716-6720`.
- **No keyboard shortcuts.** [C] No keydown handler touches a `pb*` element. The page's keydown handlers are at `SE.html:3449`, `4314`, `4723`, `4740`, `4784`, `4927`, `6810`, `6838` and `6873`, and none of them is for playback.
- **Scrubbing.** An `input` event on the hidden range pauses playback and shows that frame. Every event sets a new `<img>.src`; the main stage does not coalesce them. [C] `SE.html:6726`, `6625-6635`. The RAW pane's mini scrubber does coalesce: one request in flight, and the newest wanted frame wins. [C] `SE.html:5789-5810`.
- **Frame counter.** A 0-based index shown as `i / (frame_count - 1)`, e.g. `0 / 99` for 100 frames. [C] `SE.html:6540`, `6632`.
- **Timecode overlay.** Computed as `position / round(rate)` and always starts at `00:00:00:00`. It is **not** the recorded SMPTE timecode; `dp.py` does not read tag 51043. [C] `SE.html:6637-6642`; the tag list at `dp.py:47-64`.
- **Speed.** The only speed control is conform on/off. [C] `SE.html:6727-6732`. Toggling it pauses playback, resets the skip count and shows a toast: "Conformed to N fps" or "Playing at the recorded rate". There is no 0.5×/2×, no reverse and no J/K/L. [C] None of these exists in `SE.html:6284-6745`.
- **Loop.** A toggle button that sets `aria-pressed` and the `.is-on` class. [C] `SE.html:6721-6725`.
- **Zoom.** None. [C] Absent.
- **Audio.** None. [C] Absent; the route is unused.
- **Delete and download.** Not in this pane. [C] Absent. The RAW pane has per-take download and delete, and bulk actions. [C] `SE.html:5906-5909`, `6199-6230`.
- **Background tab.** Playback pauses with the toast "Paused — tab was backgrounded". Browsers clamp timers in a hidden tab to about 1 Hz, so the skip count would be meaningless. [C] `SE.html:6734-6739`.

**While recording**

- **What the operator sees.** [C] CSS `SE.html:1332`, `1339-1343`; markup `SE.html:2606-2609`; JS `6672-6673`, `6687-6688`, `6697-6714`:
  - the frame greys out (opacity 0.25, greyscale);
  - a red title reads "Playback held — recording";
  - the body reads "Reading the card while a take is being written to it risks audio xruns and dropped frames. Playback resumes when recording stops.";
  - PLAY is refused.
- **How the page knows.** Two routes. [C] `SE.html:6378`, `6402-6441`:
  - the `recording` flag in the clip index, read at load and on every 3 s poll;
  - any `<img>` error, which pauses playback and triggers a re-check.
- **When recording stops.** The page shows the current frame again but does not resume playing. [C] `SE.html:6434`.
- **The server's reason never reaches the page.** Strings like "Busy (is_writing_buf) — playback held" or "Camera status is stale — playback held" stay on the server, because the index carries only a boolean. [C] `SE.py:283-286`, `1400-1403`. The page always shows its own fixed text. [C] `SE.html:6687-6688`.

**Updates while the pane is open**

- **New takes.** The poll re-renders the strip when the *list of names* changes. It keeps the current selection by name, so playback is not disturbed. [C] `SE.html:6398-6430`.
- **A take first seen mid-recording keeps stale counts.** It keeps the `frame_count` and `has_wav` it had at that moment until the page reloads. [P] `pbTakeKey` compares names only (`SE.html:6398-6400`), and `pbClips` is reassigned only at `6374` and `6414`. Not observed on hardware. [U]

**Errors and request flow**

- **Any frame error pauses playback**, whether 409, 404 or 503. [C] `SE.html:6438-6441`. But the server's design note says a 503 means "drop the frame and ask for the next one". [C] `pb.py:264-266`. The client does not do that. [P]
- **Thumbnail requests are serialised in the browser.** Only one probe `Image` is in flight at a time (`pbQueueThumb` / `pbPumpThumbs`). The queue is shared with the RAW pane's row thumbnails. [C] `SE.html:6486-6499`, `5812-5821`.

### 1.6 The RAW files pane: a second, smaller "player"

[C] `SE.html:5763-5869`, `5880-5919`.

- **Each row** holds a checkbox, a 16:9 mini thumbnail with a "Preview frames" ▶ button and a scrub bar, the name, "date — N frames", chips (storage, WAV), the size, a download button and a delete button.
- **The mini thumbnail** is frame 0 at `scale=8&q=40`, loaded through the same queue.
  - Dragging scrubs, with one request in flight at a time.
  - ▶ flips through 24 evenly spaced frames at 220 ms each: "a quick flip through the take, not a real playback rate".
  - Only one row auto-plays at a time.
- **A click on the thumbnail** (not on the scrub bar) calls `pbJumpToTake(name)`. That switches to the Playback tab and selects the take. [C] `SE.html:5862-5867`, `6557-6564`.

This is the closest thing Cinemate has to a clip *browser* list with a per-clip preview.

### 1.7 Exact wording (to set against Apertar's touch-UI strings)

| Where | String | Cite |
| --- | --- | --- |
| Tab / hint | "Playback" / "review takes" | [C] `00-chrome.md:29-31`; [P] the heading becomes the label and the paragraph the hint, judging by `t('tab.playback.label')` / `t('tab.playback.hint')` at `SE.html:1492` |
| Sort | "Oldest first", "Newest first", "Largest first" | [C] `SE.html:2582-2586` |
| View | "One row", "Grid" | [C] `SE.html:2590-2593` |
| Transport titles | "First frame", "Previous frame", "Next frame", "Last frame", "Loop"; button text "PLAY"/"PAUSE" | [C] `SE.html:2619-2625`, `6676`, `6684` |
| Scrub aria-label | "Scrub through take" | [C] `SE.html:2615` |
| HUD labels | "FPS", "Resolution", "Depth", "Sensor", "Source" | [C] `SE.html:2630-2634` |
| Rate labels | "Recorded", "Conform", "Playing at", "Achieved", "Frames skipped" | [C] `SE.html:2638-2642` |
| Lock: recording | "Playback held — recording" / "Reading the card while a take is being written to it risks audio xruns and dropped frames. Playback resumes when recording stops." | [C] `SE.html:6687-6688` |
| Lock: no thumbnail | "No embedded thumbnail" / "This take has no thumbnail — recorded with the toggle off, or before a rebuilt cinepi-raw supported it. Raw decode is far more demanding on the Pi and is not currently used as a fallback." | [C] `SE.html:6689-6690` |
| Toasts | "Conformed to N fps", "Playing at the recorded rate", "Paused — tab was backgrounded" | [C] `SE.html:6731`, `6738` |
| Card meta | "N frames · 25.000 fps" or "rate unknown" | [C] `SE.html:6475-6477` |
| Settings card | "Use conform frame rate" + "Plays every take on the project's conform rate, from `settings.conform_frame_rate`. A take shot faster than the conform rate plays as slow motion — the same speed it will run on the timeline. Off plays each take at the rate it was shot." | [C] `11-playback-playback.md:19-22` |

---

## 2. The backend

### 2.1 Endpoints

- **Where they live.** All routes sit on the Flask blueprint prefix `/settings-editor`. [C] `SE.py:72-77`.
- **Server.** Port 5000, run by Flask-SocketIO in threading mode on werkzeug (`allow_unsafe_werkzeug`), over HTTP or optional self-signed HTTPS. [C] `cm:src/main.py:1145-1156`.
- **No token check.** The only `before_request` token check is on `/api/v1`. [C] `cm:src/module/app/api.py:83-94`. A grep of `src` finds no other `before_request`. [C]

| Method and URL | Answer | Errors | Gated by recording? | Cite |
| --- | --- | --- | --- | --- |
| `GET /settings-editor/api/playback/clips` | JSON index (§5.4) | none; always 200 | **No.** It only *reports* `recording`. | [C] `SE.py:1380-1403` |
| `GET /settings-editor/api/playback/clips/<name>/frame/<int:index>?scale=2\|4\|8\|16&q=40..95&mono=1&v=<token>` | `image/jpeg`. Headers: `X-Frame-Size: WxH`, `X-Frame-Source: thumbnail\|decode`, `Cache-Control: private, max-age=3600, immutable`. | 409 `{ok:false,message}` (blocked); 400 (bad `scale`/`q`); 503 `{ok:false,message:"busy"}`; 404 `{ok:false,message}` | **Yes** | [C] `SE.py:1406-1443` |
| `GET /settings-editor/api/playback/clips/<name>/audio` | `audio/wav` via `send_file(..., conditional=True)` | 409 (blocked); 404 "no audio for this take" | **Yes** | [C] `SE.py:1446-1461` |

[P] `conditional=True` is werkzeug's switch for conditional and Range responses, so the WAV route should answer partial requests.

The RAW pane uses these related routes. [C] `SE.py:1464-1606`:

- `GET /api/raw/storage`, `GET /api/raw/takes`
- `DELETE /api/raw/takes/<name>?storage=`
- `GET /api/raw/takes/<name>/download`: a streamed, stored (uncompressed) zip. A 2-permit semaphore answers 429 when full.
- `GET /api/raw/takes/<name>/files` (manifest) and `GET .../files/<path>`
- `POST /api/raw/bulk` (`{action:"delete",names:[...]}`)
- `POST /api/raw/format`
- `GET /api/raw/download` (zip of several takes)

**Query parameters that do nothing on the default path**

- **`v=`** is not read by the server. It only makes the URLs change whenever `dng_preview.py` changes: `RENDER_TOKEN` is the file's mtime and size in hex. [C] `pb.py:37-55`; `SE.html:6312-6318`.
- **`scale` and `mono`** matter only for raw decode; a thumbnail-sourced frame ignores them. The page still sends `scale=4` (stage) and `scale=8` (thumbnails), because the route validates `scale`. [C] Comment at `SE.html:2658-2669`; validation at `SE.py:1414-1420`.

  Result: frame 0 is fetched twice, once at `scale=8` for the card and once at `scale=4` for the stage. The bytes are the same but the cache holds two entries. [P] The URLs differ while the thumbnail output does not.

### 2.2 What a take and a clip are

- **Media roots.** `/media/RAW` (active), then `/media/RAW1`, `/media/RAW2`, ... [C] `rf.py:30-31`, `78-94`.
- **A take** is a directory directly under a root that holds at least one `*.dng`. The directory name is the take name. [C] `rf.py:97-101`, `134-146`.
- **Frame files** are named `<take>/<take>_<9-digit index>.dng` and written by cinepi-raw's disk thread. [C] `cr:cinepi/dng_encoder.cpp:2334-2343`.
- **The WAV sidecar** is `<take>/<take>.wav`, written by cinepi-raw's sound module. [C] `cr:cinepi/cinepi_sound.cpp:835`.
- **Frame order** is the lexical sort of the file names. Playback works on positions in that list, not on the numbers in the names, because a dropped frame leaves a gap. [C] `pb.py:77-100`.
- **Dropped frames** = (max index − min index + 1) − file count, read from the names. The value is `None` when a name cannot be parsed. [C] `pb.py:103-134`.
- **Clip facts come from the first frame's tags only**, about 2 kB of I/O: width, height, bits, white level, LinearizationTable, FrameRate (51044), Model (272), and whether an IFD1 is present. [C] `pb.py:137-191`; `dp.py:151-206`.
- **Mode inference.** cinepi-raw writes no HDR tag, so the mode is read from bits, table and white level. [C] `dp.py:224-283`:

  | Bits | LinearizationTable | WhiteLevel | Result |
  | --- | --- | --- | --- |
  | 12 | none | 4095 | SDR, linear |
  | 16 | none | 65535 | HDR, linear |
  | 12 | present | about 62.7k | HDR, companded |
  | 10 | present | — | log-to-10 take; Depth shows 12 or 16 |
- **Order.** `list_clips` sorts oldest-first by directory mtime. The RAW pane's own list stays newest-first. [C] `pb.py:194-217`; `rf.py:145`.
- **`source` is a property of the whole take.** That holds because cinepi-raw snapshots the thumbnail setting once per take. [C] `pb.py:185-189`; `cr:cinepi/dng_encoder.hpp:363-392`.

### 2.3 How a frame is produced

`frame_source(meta)` returns `thumbnail` when an IFD1 was found, otherwise `decode`. It is the one place that makes this choice. [C] `pb.py:239-254`.

`frame_jpeg()`, step by step. [C] `pb.py:257-299`:

1. Resolve the take name safely against the media roots, get the cached frame list, and bounds-check the index.
2. Take one of two decode slots, without waiting. If none is free, raise `Busy`, which becomes a 503.
3. Read the frame's metadata: the 8-byte header, up to 32 kB at IFD0, then up to 32 kB at IFD1. [C] `dp.py:84`, `170-206`.
4. If the source is `thumbnail`, call `decode_thumbnail`. [C] `dp.py:518-581`:
   - **compression 7 (JPEG mode):** return the strip bytes **as they are on disk**; no decode, no re-encode, and `q` is ignored;
   - **compression 1 (mono or colour):** read the strip and encode it with PIL at quality `q` (default 80, 4:2:0).
5. Otherwise, if `_RAW_DECODE_FALLBACK_ENABLED` were true (it is `False`), call `decode_frame`. With the flag off, raise `PlaybackError`, which the route returns as a 404 with "this take has no embedded thumbnail ... raw playback is currently disabled". [C] `pb.py:236`, `287-294`.

**What the browser actually receives by default**

- **Size.** 640×360, or 628×360 on ClearHDR modes, whose lores stream is 1256×720.
- **Encoding.** A colour JPEG at quality 85, 4:2:0, about 10–25 KB per frame.
- [C] `cr:cinepi/cinepi_controller.cpp:48-53`; `cm:docs/settings-json.md:323`.

**The picture's look.** The image is the **ISP-processed lores stream**, the same stream that feeds the HDMI and MJPEG previews. It has the preview's white balance, colour matrix and tone curve, not a rendering of the raw data. [C] `cr:cinepi/dng_encoder.cpp:1810-1827` (studio-range Rec709 lores); `cr:cinepi/ccmpPreviewStage.cpp:18` ("the DNG thumbnail ... EncodeBuffer takes the lores stream").

**Raw decode** is disabled but kept in the code, re-enabled by one flag. [C] `dp.py:331-516`; `pb.py:227-236`.

- **Libraries.** numpy and Pillow only; no rawpy or libraw.
- **Debayer.** One output pixel per 2×2 Bayer cell, no interpolation.
- **Reads.** Only the rows the output needs; `scale` (2, 4, 8 or 16) is a linear divisor.
- **Processing.**
  - LinearizationTable applied before the cells are collapsed.
  - Black and white levels normalised.
  - Gamma 1/2.2.
  - **No white balance or colour matrix.**
  - Optional mono.
  - JPEG at quality 80, 4:2:0.
- **Inputs it accepts.** Uncompressed 10-, 12- or 16-bit only; it refuses a compressed DNG. [C] `dp.py:488-489`.
- **Speed.** Measured off the Pi, on Apple Silicon: UHD to 964×545 took 13.9 ms reading only the needed rows, against 30.2 ms unpacking the whole frame. The Pi gates had not been run. [C] Commit message `ba9f792`.
- **Bandwidth estimate.** A raw-path estimate of 158 MB/s at 25 fps, against about 23 MB/s for a mono thumbnail. [C] Commit message `8b42d8e`. [P] It is an arithmetic estimate, not a measurement.

### 2.4 Caching

- **The frame list** is cached in the process per take directory and keyed by the directory's mtime. [C] `pb.py:64-66`, `77-100`.
- **Clip metadata is not cached.** Every index request re-reads each take's first-frame tags. [P] `list_clips` calls `clip_info` once per take with no cache (`pb.py:205-207`).
- **Building the index is expensive and repeats every 3 s.**
  - `raw_files.list_takes()` calls `stat()` on every file of every take to sum `size_bytes`. [C] `rf.py:104-131`.
  - The page requests the index every 3 s from the moment it loads. [C] `SE.html:6449`.

  On a big card that is one `stat()` per file every 3 s, and it continues **during recording**, because the index route is not locked out. [P] `SE.py:1380-1403` has no `_playback_blocked()` call. The cost is not measured. [U]
- **No JPEG cache on the server.** The browser keeps frames for an hour (`private, max-age=3600, immutable`). `RENDER_TOKEN` stops a cached frame from an older decoder being served after an update. [C] `SE.py:1440-1442`; `pb.py:37-55`.
- **The page itself has no cache-buster.** On 2026-09-13 an old page running against a new API showed "NO EMBEDDED THUMBNAIL" on every take; a hard reload fixed it. [C] `hb:working/browser-side-traps.md:243-276`; `hb:lessons/hardware-log.md:2064-2104`.

### 2.5 Concurrency and the CPU/IO budget

- **Two decode slots.** `MAX_CONCURRENT_DECODES = 2`, a `BoundedSemaphore` taken without waiting around **every** frame, thumbnails included. Past two, the server answers 503 "busy" instead of queueing, "so a client that cannot keep up backs off instead of building a backlog". [C] `pb.py:57-62`, `279-280`, `298-299`; `SE.py:1427-1430`.
- **The browser keeps its side small.** Thumbnails load strictly one at a time, and the stage is one `<img>` whose new `src` replaces the old one. [C] `SE.html:6486-6499`, `6625-6628`.
- **Downloads have their own semaphore** of 2 permits and answer 429 when it is full. [C] `rf.py:44`; `SE.py:1502-1503`.
- **Measured on hardware: the recorder side only** (see §3.3). Nothing in `hb:lessons/hardware-log.md` measures the serving side, such as the achieved fps over Wi-Fi or the Flask process's CPU. [U] A grep for playback, "Achieved" and "G3" finds no pane measurement.
- **I/O per frame on the thumbnail path.** Three seeks: up to 32 kB of tags at IFD0, up to 32 kB at IFD1, then the strip (about 10–25 KB). [P] `dp.py:84`, `179-191`, `564-566`.

### 2.6 Blocking rules

`_playback_blocked()`. [C] `SE.py:243-280`:

- **Blocks** when Redis reads "1" for any of `is_recording`, `is_writing_buf`, `is_buffering` or `storage_preroll_active`. The comment explains why: "pre-roll in particular writes at full rate with is_recording still 0".
- **Fails closed:**
  - if the Redis listener thread is dead: "Camera status is stale — playback held";
  - on any exception: "Camera status unavailable — playback held".
- **Does not block** when no Redis controller is wired (desk and test use).

**Where it applies.** The frame route and the WAV route, both 409. The WAV route gained its check in `f2b55aa`, because a WAV is unfinished while a take is running. The clip index is **not** gated. [C] `SE.py:1380-1461`.

**Delete is a different rule.** Only the take or takes being written are refused: the parent directories of `last_dng_cam0/cam1`, and only while `is_recording` is set. A bulk delete is refused as a whole if any selected take is recording. [C] `SE.py:1474-1493`, `1568-1603`; `rf.py:244-257`.

**History.** The lockout first read `is_recording` alone and failed open. `4d3bca4` widened it and made it fail closed. [C] Commit message `4d3bca4`.

### 2.7 Security fixes that came out of review

- **Take names.** No separators, `.` or `..`; the resolved parent must be the media root; a name with an embedded null byte is skipped. [C] `rf.py:180-213`.
- **Files inside a take.** A symlink that resolves outside the take directory is dropped (`safe_take_children`). Without this, a `*.dng` link to `/etc/passwd` would have been served like a frame. [C] `rf.py:216-241`; commit `00f6f65`.
- **Escaping.** Take names are escaped before they go into `innerHTML`. The page inlines the API token and has no CSP, so an unescaped crafted directory name would be stored XSS. [C] Comment at `SE.html:6460-6466`; token inlined at `SE.html:3033`; commit `00f6f65`.

### 2.8 Formats

- **Playable.** cinepi-raw CinemaDNG takes that carry an IFD1 thumbnail (modes 1, 2 or 3). [C]
- **Listed but not playable.** Takes without a thumbnail (mode 0, or recorded before the feature). [C]
- **Accepted by the disabled raw decoder.** Uncompressed 10-, 12- or 16-bit, with the IFD at the end of the file and one strip. [C] `dp.py:7-23`, `345-362`, `488-489`.
- **Not supported at all.** Compressed DNG, MLV, any movie container, and stills. [P] There is no reader for them in `cm:src/module/app`, and `_is_take_dir` requires a `*.dng` (`rf.py:97-101`).

---

## 3. The recorder side: the embedded thumbnail

### 3.1 Settings and keys

- **`image_capture.thumbnail`** takes `"off"`, `"mono"`, `"colour"` (or `"color"`), `"jpeg"`, or 0–3. The default is **`"jpeg"` (3)**. [C] `cm:src/module/config_loader.py:305-317`, `320-356`, `359-400`; `cm:resources/settings/settings_default.jsonc:183`.
- **`image_capture.thumbnail_size`** is a right-shift of the lores plane, 0–4 (cinepi-raw itself accepts 0–12). The default is **1**, half the lores plane. [C] `config_loader.py:403-440`; `settings_default.jsonc:186`.
- **Startup.** Both values are written to the Redis keys `thumbnail` and `thumbnail_size` before cinepi-raw starts. [C] `cm:src/main.py:842-871`.
- **Live changes.**
  - `set thumbnail <word|0-3>` (CLI and the settings editor's action list) takes effect at the next take.
  - A live `thumbnail_size` change restarts the camera (`cameraInit_ = true`).
  - [C] `cm:src/module/cinepi_controller.py:1418-1440`; `cr:cinepi/cinepi_controller.cpp:1031-1058`.
- **The settings editor shows one on/off toggle.** It writes `"jpeg"` or `"off"` and keeps a hand-set `mono`/`colour`. Hidden inputs carry both keys so a save does not delete them (bug B-2). [C] `SE.html:2070-2104`; commit `b141a8c`.

  The card text, in the operator's own words:
  - "By default DNGs carry a small preview image, used by the Playback pane for renderless playback."
  - "Disable to slightly increase write speed and reduce cpu load during recording (disables web GUI playback)."
  - [C] `cm:resources/gui-text/05-settings-exposure-and-steps.md:78-84`.
- **cinepi-raw's compiled-in defaults** are `CP_DEF_THUMBNAIL 3` and `CP_DEF_THUMBNAIL_SIZE 1`. [C] `cr:cinepi/cinepi_controller.cpp:47`, `64`. Its startup sync clamps the mode to 0..3. A shift that would make the lores plane narrower than 16 px is reset to the default. [C] `cr:cinepi/cinepi_controller.cpp:276-322`.

### 3.2 How cinepi-raw writes it

1. **One snapshot per take.** `setup_encoder()` runs lazily at the first frame of each take. It copies the mode and shift (clamped to 0–3 and 0–12) into `thumb_mode_` and `thumb_shift_`. A change mid-take therefore reaches the file only at the **next** take. [C] `cr:cinepi/dng_encoder.cpp:974-1009`; `cr:cinepi/dng_encoder.hpp:363-392`.
2. **Buffer reservation.** The per-frame buffer reserves the worst case, width × height × samples per pixel. JPEG mode reserves the uncompressed colour size. [C] `dng_encoder.cpp:1011-1039`; `cr:cinepi/dng_thumbnail.hpp:85-100`.
3. **The log line names the values.** Either "DNG writer: embedded lores thumbnail jpeg at WxH (shift N, quality 85)" or "DNG writer: raw-only frames; embedded lores thumbnail disabled". [C] `dng_encoder.cpp:1092-1105`.
4. **The lores buffer must be YUV420 of exactly the expected size.** Otherwise the writer warns once per take and writes no thumbnail. [C] `dng_encoder.cpp:1768-1793`.
5. **Pixels.** [C] `dng_encoder.cpp:1797-1922`:
   - each output pixel takes the nearest source sample at `(x << shift, y << shift)`; there is no filtering, so aliasing is possible;
   - **mono:** Y, expanded from studio range to full range;
   - **colour and JPEG:** fixed-point limited-range YUV to RGB, with Rec709 or Rec601 coefficients picked from the stream's own colour space.
6. **JPEG mode.** [C] `dng_encoder.cpp:97-104`, `1862-1878`, `1943-1976`:
   - libjpeg with RGB input and default settings (4:2:0), quality **85** (`kThumbnailJpegQuality`), encoded into memory;
   - if the result fits the reservation it is copied into the frame buffer;
   - if not, only that frame's thumbnail is skipped (one warning per take). The raw frame is never dropped.
7. **The IFD1 tags.** [C] `dng_encoder.cpp:1980-2004`; `dng_thumbnail.hpp:129-163`:
   - first the strip is padded to a 4-byte boundary;
   - NewSubfileType 1, width, height, BitsPerSample 8 per sample, Compression 1 or 7, Photometric 1/2/6;
   - StripOffsets, SamplesPerPixel, RowsPerStrip = height, StripByteCounts, PlanarConfiguration 1;
   - JPEG mode adds YCbCrSubSampling {2,2} and YCbCrPositioning 1;
   - finally IFD0's next-IFD field is pointed at IFD1.

**File layout:** 8-byte header (holds the IFD0 offset) | raw strip at offset 8 | IFD0 | thumbnail strip | IFD1. [P] Header written at `dng_encoder.cpp:1138-1140`; IFD0 at the end of the raw data (`dp.py:8-10`); thumbnail strip written after IFD0 (`dng_encoder.cpp:1844`); IFD1 after the strip (`1993-1998`).

**Why IFD1 and not a SubIFD ("decision 7").** The thumbnail is chained as IFD1 instead of the standard IFD0-plus-SubIFD shape. IFD0 stays byte-identical, so post software keeps reading the raw image from IFD0. [C] Commit `4b1acd4`; `dng_encoder.cpp:1750-1757`.

Whether Resolve or Adobe DNG Converter accept photometric 6 in IFD1 has not been checked. The handbook lists it as open (`hb:lessons/hardware-log.md:2041-2045`). [U]

### 3.3 Costs (measured)

Measured 2026-09-13 on an imx585 in 4K 16-bit ClearHDR with CineMate Log 12, 25 fps, eight takes of 250+ frames, against a 22.2 ms no-thumbnail baseline. [C] `cm:docs/settings-json.md:318-339`.

| Mode | Bytes/frame at 640×360 | Extra encode time per frame | Write rate | Recording time per TB |
| --- | --- | --- | --- | --- |
| off | 0 | 0 (22.2 ms) | 317.0 MB/s | 52.6 min |
| mono | 230,400 | +1.2 ms | 322.7 MB/s | 51.7 min |
| colour | 691,200 | +3.2 ms | 334.0 MB/s | 49.9 min |
| **jpeg (default)** | ~10–25 KB | **+4.0 ms (+18%)** | 317.4 MB/s | 52.5 min |

- **Phase 2 gate, at 314×180.** A JPEG thumbnail averaged 4,959 B, against 169,560 B for uncompressed colour: 34 times smaller. "off" was a true no-op, adding only 680 B per file. [C] `hb:lessons/hardware-log.md:2000-2062`.
- **Caveat from the docs.** At HD, or at higher frame rates, the same thumbnail is a larger share of the encode time. [C] `settings-json.md:339`.

### 3.4 Thumbnail commit trail (cinemate)

| Commit | Date | What changed |
| --- | --- | --- |
| `37d977f` | 2026-09-02 | Exposed the toggle (ints 0–2, default 0) |
| `58fa6a6` | 2026-09-02 | The reader: parse IFD1 and serve the thumbnail |
| `5124a1d` | 2026-09-02 | Default 0 → 2 (colour); thumbnail made the standard path; raw decode disabled |
| `227af05` | 2026-09-13 | Size and mode put under operator control (interim default: mono at half size) |
| `7634dd5` | 2026-09-13 | Default changed to colour at quarter size |
| `318a0cf` | 2026-09-13 | JPEG mode 3 added; mode words accepted; JPEG served unchanged |
| `13dfcc6` | 2026-09-13 | Default size changed to half (640×360) |
| `b141a8c` | 2026-09-13 | One on/off toggle in the settings editor; **default jpeg** |
| `dbaed5d`, `c1ef4d4` | 2026-09-13/14 | Operator's own wording for the card |
| `2c76d37` | 2026-09-14 | Merged into `dev` |

[C] `git log -i --grep thumbnail` and the commit messages.

### 3.5 Stale statements not to copy

- **cinepi-raw comments.** `cr:cinepi/dng_encoder.cpp:967` ("Thumbnail (mono 8-bit Y-plane)") and `:1025-1026` ("the shipped default is colour at shift 2") are superseded by the compiled-in defaults 3 and 1. [C]
- **Cinemate comment.** `cm:src/main.py:844` says `CP_DEF_THUMBNAIL` is 2; it is 3 (`cr:cinepi/cinepi_controller.cpp:47`). [C]
- **Handbook.** All three are superseded by `b141a8c`. [C]
  - `hb:architecture/cinepi-raw.md:136` lists the modes as "0 off, 1 mono, 2 colour";
  - `:147` says "shipped default is colour at shift 1";
  - `:193` says JPEG "stays an opt-in ... rather than the default".
- **Docs vs code.** `cm:docs/playback.md:48` (PLAY on the last frame restarts) does not match the code; see §1.5. [P]
- **Screenshot.** `cm:docs/images/gui-playback.png` shows an older layout. [C]
- **Missing design files.** Commits and comments cite the C9 plan, FEASIBILITY and FINDINGS files under `development/`, but that directory is not in the `dev` tree at d6cc93e. [C] `git ls-tree -d HEAD` shows no `development/`. Their contents could not be checked. [U]

---

## 4. History and lessons

### 4.1 Timeline (C9, "clip playback")

[C] `git log -i --grep playback` (47 commits) and the messages of the commits named below.

| Date | Commit | What happened |
| --- | --- | --- |
| 2026-08-27 | `4a83428` | C9 registered as a project, ordered measurement-first. |
| 2026-08-27 | `ba9f792` | The `dng_preview` decoder (numpy + Pillow, tail IFD, row-selective reads). |
| 2026-08-27 | `e0f1cae` | The Playback pane added as the settings editor's fifth tab: 3 endpoints, 2-slot cap with 503, conform pacing, skip count, render token. |
| 2026-08-27 | `f0986e5`, `75676c7` | `conform_frame_rate` defaults to 25 from one place; a fix for a reachable rate of 24. |
| 2026-09-01 | `8b42d8e` | **Operator steer: thumbnail-first.** "not expecting playback of raw files, the system can use the thumbnails instead". cinepi-raw "Phase 0" adds IFD1. |
| 2026-09-01 | `4b1acd4` | Decision 7: IFD1 chained after IFD0, IFD0 left untouched. |
| 2026-09-02 | `4d3bca4` | LinearizationTable applied to pixels; lockout widened and made to fail closed; the Live tab's MJPEG stream stopped when the tab is left. |
| 2026-09-02 | `58fa6a6` | The reader for IFD1. |
| 2026-09-02 | `8c461f4` | Lockout recovery poll; "Achieved" counted from `onload`; conform rate rounded with `smpte_frame_base`. |
| 2026-09-02 | `00f6f65`, `f2b55aa` | Stored-XSS and symlink-escape fixes; the WAV route given the lockout. |
| 2026-09-02 | `a4d56cd` | 10-bit takes no longer 404 on every frame. |
| 2026-09-02 | `5124a1d` | Thumbnail made the standard path; raw decode disabled; DROP read from file names; oldest-first order; a second lock reason (no thumbnail). |
| 2026-09-02 | `35656b7`, `51d7808` | RAW pane mini scrub thumbnail and jump to Playback; PR #185 merged. |
| 2026-09-05 | `9113e73` | The strip wraps instead of scrolling; new takes appear without a reload (name-keyed). |
| 2026-09-05 | hb hardware-log `1514-1607` | Thumbnails "off" on every take after the move to `dev`: the running binary had no writer. |
| 2026-09-07 | `65f45c9`, `0ce2208` | Player moved above the strip, then the strip moved back above it, plus the Sort and View controls. |
| 2026-09-08 | `066484e` | "Takes on card" label dropped. |
| 2026-09-13 | `227af05` … `b141a8c` | Thumbnail cost measured; size and mode under control; JPEG mode; default jpeg at half size (§3.4). |
| 2026-09-13 | hb hardware-log `2064-2104` | The cached-page incident. |

### 4.2 Lessons

1. **Let the recorder write the preview; the reader only serves bytes.** After the hardware gates (G10/G11), raw decode was dropped as "far more demanding on the Pi". The pane serves the embedded JPEG unchanged. [C] `8b42d8e`, `5124a1d`; `pb.py:227-236`.
2. **Show the honest rate.** [C] `e0f1cae`, `8c461f4`; `SE.html:6448`.
   - Pace on the frame clock and let the clock win under load.
   - Show the skip count and the achieved fps.
   - "Achieved" must count frames the browser *loaded*, not `src` assignments. Counting assignments made a refusing camera look healthy.
3. **Refuse rather than queue,** with a small concurrency cap and a 503. [C] `pb.py:57-62`. The client must then skip the frame, not pause; Cinemate's client pauses. [P] §1.5.
4. **Recording wins, and every path to the card has to be gated.** [C] `4d3bca4`, `f2b55aa`; `SE.py:243-280`. [P] The index scan in §2.4 is still ungated.
   - Include every state that writes the card: buffer flush, buffering, pre-roll.
   - Fail closed when the status feed is dead (handbook trap 1, F-204).
   - The WAV route was missed at first.
5. **The lock must show and must recover.** [C] `8c461f4`, `5124a1d`; `SE.html:6697-6714`.
   - Checking only at page load left the stage unlocked and the 409s silent.
   - An `<img>` `onerror` cannot read the JSON body, so a poll and an `onerror` re-check were added.
   - "Recording" and "no thumbnail" are two lock reasons, kept separate so the poll cannot clear the wrong one.
6. **Stop anything invisible that competes for the same link.** The Live tab's MJPEG iframe kept streaming behind other tabs. [C] `4d3bca4`. The pane's own 3 s poll still runs whichever tab is open. [C] `SE.html:6449`.
7. **Cache-busting covers frames, not the page.** Immutable frame URLs need a decoder token. The page itself is not busted, so when the pane disagrees with a file, ask the API first. [C] `e0f1cae`; `hb:working/browser-side-traps.md:243-276`.
8. **The file is the witness.** The per-clip `source` is read from the DNG, not from Redis, and that is what diagnosed the 2026-09-05 episode. The lesson that came with it: a log line is evidence only if just one build could have printed it. [C] `hb:lessons/what-the-pi-taught-us.md:124-142`; `hb:lessons/hardware-log.md:1514-1607`.
9. **Measure the preview's cost on real files.** CineMate 3.4 shipped a full-size colour thumbnail at 2.7 MB per frame, +22% on 4K and +89% on HD. Nobody noticed until files were measured. [C] `hb:lessons/hardware-log.md:1830-1891`; `cr:cinepi/cinepi_controller.cpp:54-58`.
10. **Round the conform rate to a frame base,** never truncate. 23.976 must become 24, not 23. [C] `8c461f4`; `SE.py:1381-1399`.
11. **Escape names read off the card, and drop symlinks inside take directories.** [C] `00f6f65`.
12. **Raw-decoder traps,** relevant only if Apertar ever decodes raw for the browser. [C] `4d3bca4`; `dp.py:286-312`, `397-409`; `a4d56cd`.
    - Apply the LinearizationTable before normalising the levels.
    - BlackLevel and WhiteLevel are already in the table's output domain.
    - 10-bit packing needs its own unpacker.
13. **A settings form that lacks a control for a key deletes that key on save** (B-2). This applies to any WebUI form that writes a config file. [C] `95da41f`, `5124a1d`, `b141a8c`.
14. **Expect layout churn.** Strip above or below the player flipped twice in one day before the operator settled on "strip above, with a grid option". [C] `65f45c9`, `0ce2208`.
15. **Benchmarks can be flattered by a warm page cache.** Report the first (cold) iteration and flag a device that reads nothing. [C] `4fdd52e`.

---

## 5. Port assessment

**The Apertar side, for context only.** Apertar's WebUI already has a **Clip Browser**: "Download or delete clips, stills, timelapses, and audio recordings from mounted media", with filter buttons. [C] `ac:src/web/WebControlPage.cpp:3988-4000`. The KB says the touch UI's player plays the WAV sidecar on the device through `aplay`. [U] `kb:architecture/ui.md:51`; not re-checked in code here.

### 5.1 Worth porting: the mechanics

| # | Mechanic | Cinemate source | What changes for Apertar | Label |
| --- | --- | --- | --- | --- |
| 1 | **A clip-index endpoint** whose per-clip facts come from the files, not from current settings | `pb.py:137-217`; `SE.py:1380-1403` | Must cover Apertar's own formats: CDNG (uncompressed, or lossless-compressed when Clear HDR is off), MLV and movies. | [C] source; [P] need |
| 2 | **A frame endpoint, one JPEG per GET,** indexed by position. Immutable caching, a render token, `X-Frame-Size` and `X-Frame-Source` headers. | `SE.py:1406-1443`; `pb.py:37-55` | Served by Core, the front door. | [C] |
| 3 | **The recorder writes the preview** ("thumbnail-first"), so serving costs a few kB of reads and no decode | `cr:` §3.2 | Apertar's CDNG writer writes one IFD with NewSubfileType 0 at `ac:src/cdng/CdngEncoder.cpp:1529`; grepping `src/cdng` finds no "thumbnail" or "SubIFD". The options (a design decision): add an IFD1 in Core's `CdngEncoder`, decode on the server, or record proxy files. | [P] the absence comes from a grep, not a full read |
| 4 | **A concurrency cap with 503 refusal**; one thumbnail request in flight in the browser; a coalescing scrub (newest wanted frame wins) | `pb.py:57-62`; `SE.html:6486-6499`, `5789-5810` | Skip the frame on a 503 instead of pausing. | [C] / [P] |
| 5 | **Frame-clock pacing** with a skip count and an achieved-fps readout | `SE.html:6644-6670` | Usable in the browser as is. | [C] |
| 6 | **Recording lockout** | `SE.py:243-280`; `SE.html:6402-6449`, `6687-6714` | Use Core's own recording, flush and pre-roll states. **Also gate the index scan.** | [C] / [P] |
| 7 | **The conform-rate option** with SLOMO/FAST/CNF labels | `SE.html:6320-6323`, `6580-6623` | An option; depends on whether the touch UI has an equivalent. | [C] |
| 8 | **Dropped frames counted from file-name gaps** | `pb.py:103-134` | Needs Apertar's CDNG numbering to be gap-preserving. | [U] for Apertar |
| 9 | **Path safety:** validate the take name, filter symlinks inside takes, escape names in HTML | `rf.py:180-241`; `SE.html:6460-6476` | Port as is. | [C] |
| 10 | **Pause on a hidden tab**; stop streams that are not visible | `SE.html:6734-6739`; `4d3bca4` | Port as is. | [C] |
| 11 | **Audio** | Only a WAV route (`send_file(..., conditional=True)`) | Playing audio in the browser, in sync with the frame clock, is **new work**; Cinemate never did it. | [C] absence; [P] design |

### 5.2 Cinemate-specific: do not port as is

- **Placement.** The pane is a settings-editor tab on Flask/werkzeug, with its own markdown text system (`gui-text`). Apertar's WebUI is one Core-served page (`ac:src/web/WebControlPage.cpp`, 11,661 lines). [C] Line count from `wc`.
- **Redis key names** (`is_writing_buf`, `storage_preroll_active`, ...) and the listener-alive check. [C] `SE.py:249-280`.
- **The raw decoder.** Tuned to cinepi-raw: IFD at the end of the file, uncompressed, 2×2 cells, no white balance. Apertar's commit `eb9cc39` is titled "Clear HDR on = uncompressed, off = lossless", and `ac:src/cdng/LosslessJpegEncoder.cpp` exists, so most Apertar DNGs would hit `dp.py:488-489` ("compressed DNG frames are not supported"). [P]
- **Vestigial parameters and fixed conventions.**
  - The `scale` and `mono` query parameters. [C]
  - The `/media/RAW*` root convention. [C]
  - cinepi file-name parsing. [C]
  - The B-2 hidden-input workaround. [C]
- **HUD colours** taken from Cinemate's HDMI GUI (`simple_gui`). Apertar should use its own WebUI tokens. [C] `SE.html:1302-1306`.

### 5.3 Cinemate features Patrik may want as options

Each needs checking against the touch UI before it is offered.

- **Conform-rate playback**, with SLOMO/FAST chips and the CNF box.
- **The honest rate row:** Recorded / Conform / Playing at / Achieved / Frames skipped.
- **A `DROP N` badge** read from the recording itself.
- **A "Source" readout** that says which picture you are looking at.
- **Sort** (oldest/newest/largest) and a **One row / Grid** view.
- **A filmstrip scrubber** of 16 evenly sampled frames with a playhead.
- **Loop.**
- **The file list's mini scrub thumbnail** and 24-frame quick flip, with a click that opens the player on that take.
- **Mode boxes:** `12b/16b`, `SDR/HDR`, `CRV/LIN`, `LOG10`, `WAV`.
- **A lock overlay that names its reason**, and a pane that picks up new takes without a reload.

### 5.4 Key data shapes

**Clip index.** `GET /settings-editor/api/playback/clips`. [C] Field names from `pb.py:149-191`, `210-214` and `SE.py:1400-1403`. The values below are illustrative; the name is a real take from `hb:lessons/hardware-log.md:2058`.

```json
{
  "ok": true,
  "clips": [
    {
      "name": "CINEPI_26-09-13_224059_F22_C00001_cam0",
      "frame_count": 126,
      "has_wav": false,
      "dropped_frames": 0,
      "width": 3840,
      "height": 2200,
      "bits": 16,
      "log10": false,
      "fps": 25.0,
      "hdr": true,
      "encoding": "linear",
      "mode_label": "HDR",
      "sensor": "imx585",
      "source": "thumbnail",
      "storage": "RAW",
      "size_bytes": 2129620000,
      "mtime": 1757796059.2
    }
  ],
  "conform_frame_rate": 25,
  "render_token": "66c5a1f24a3c1",
  "recording": false
}
```

**Field notes.** [C] `pb.py:144-190`; `dp.py:209-221`, `224-283`:

| Field | Values |
| --- | --- |
| `dropped_frames` | `null` when the count cannot be determined. |
| `source` | `"thumbnail"` or `"decode"`; `"decode"` means "no thumbnail". |
| `encoding` | `"linear"` or `"companded"`. |
| `mode_label` | `"SDR"` or `"HDR"`. |
| `fps` | Rounded to 3 decimals, or `null`. |

**Take shapes that carry fewer keys:**

- **A take whose first frame cannot be parsed** has only `name`, `frame_count`, `has_wav`, `dropped_frames` and `"unreadable": true`, plus `storage`, `size_bytes` and `mtime`.
- **An empty take** has no image keys.

**Frame.** `GET /settings-editor/api/playback/clips/<urlencoded name>/frame/<index>?scale=4&v=<render_token>`. [C] `SE.html:6312-6318`.

- `index` is 0-based within the sorted frame list.
- The thumbnails use `scale=8`; the RAW pane adds `&q=40`.
- The answer is a JPEG body with `X-Frame-Size` and `X-Frame-Source`, or a JSON error `{"ok":false,"message":"..."}` with status 409, 400, 503 or 404.

**Audio.** `GET /settings-editor/api/playback/clips/<name>/audio` returns `audio/wav`, or 409 / 404 JSON. [C] `SE.py:1446-1461`.

**RAW take list.** `GET /settings-editor/api/raw/takes` returns `{"ok":true,"takes":[{"name","storage","frame_count","has_wav","size_bytes","mtime"}]}`, newest first. [C] `rf.py:124-131`, `145`; `SE.py:1469-1471`.

### 5.5 Gaps and defects in Cinemate not to copy

- **The client pauses on any frame error,** although the server's 503 means "skip this frame". [P] `SE.html:6438-6441` vs `pb.py:264-266`.
- **The clip index rescans the whole card** (a `stat()` per file) every 3 s from page load, on every tab and during recording, with no metadata cache. [C] code path / [P] cost: `SE.html:6449`; `rf.py:104-131`; `pb.py:205-207`; `SE.py:1380-1403`.
- **A take first seen mid-recording keeps a stale frame count** until reload, because the poll keys on names only. [P] `SE.html:6398-6430`.
- **The docs say PLAY on the last frame restarts; the code does not.** [P] `cm:docs/playback.md:48` vs `SE.html:6653-6654`, `6672-6680`.
- **Thumbnail-less takes still request a card thumbnail,** which 404s. [P] `SE.html:6481`.
- **Frame 0 is fetched twice** under two `scale` values. [P] §2.1.
- **The overlay timecode is position ÷ rate,** not the recorded timecode. [C] `SE.html:6637-6642`.
- **The settings-editor routes have no authentication,** even though the page inlines the API token. [C] `cm:src/module/app/api.py:83-94` (the only token check); `SE.html:3033`.
- **Possible:** after a 409, resetting `src` to the identical frame URL may not issue a new request in some cases. [U] Untested; see the identical-URL `src` trap at `hb:working/browser-side-traps.md:122-158`. That trap is measured only for in-flight requests.

### 5.6 Open questions for the design (not answered by Cinemate)

- **Pictures.** Which Apertar take formats must the WebUI play: CDNG uncompressed, CDNG lossless, MLV, H.264/ProRes? And where does each picture come from: an embedded preview written by Core, a decode in Core, or proxies? [U]
- **Audio.** Does the WebUI play the WAV in the browser, and how is it synced to a clock that skips frames? [U]
- **CPU budget.** How much may Apertar's Pi spend on serving frames while idle? Cinemate allowed 2 decode slots, refused everything while recording, and never measured the serving side. [U]
- **One browser or two.** Does WebUI playback merge with the existing Clip Browser (download/delete), or sit beside it like Cinemate's RAW pane and Playback pane, joined by a "jump to player" link? [U]
