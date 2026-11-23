# Verify FORKDATA, links, README, static text (coding map bff7bd5)

Heads checked: Core cinemate-port 01f170c, UI cinemate-port 7ea9afc, imx585 driver cinemate-port cd548ef. Today 2026-11-17.

## 1. How FORKDATA was computed (reproduced exactly at the heads the map names)

Rule: `git rev-list --count --no-merges upstream-1.6.0..<head> -- <paths>`, newest five from `git log --no-merges --format='%h|%ad|%s' --date=short -5 upstream-1.6.0..<head> -- <paths>`.
Base = tag upstream-1.6.0 (Core 35dbe67, UI 43888e5), NOT origin/main: fork main's Clear HDR commits count as fork-only. Merges excluded.
Driver: base = Apertar-Studio main 70bdb26, no path filter.
Reproduced at Core f4a1393 / UI 7029db1 (the heads the map was built on): all counts and newest-five match the map.

| Box | Paths | Map | Today |
| --- | --- | --- | --- |
| QML | qml | 15 | 24 |
| BRIDGE | src/ApertarControlBridge.{cpp,hpp} | 8 | 12 |
| RENDER | src/PreviewWindowRenderer.{cpp,hpp} | 0 | 8 |
| UICONF | src/SettingsBridge.{cpp,hpp} | 2 | 4 |
| WEBPAGE | src/web | 80 | 82 |
| HWIN | src/hardware | 18 | 20 |
| HUB | src/ApertarCoreApp.{cpp,hpp} | 69 | 73 |
| CAM | src/camera src/util | 71 | 73 |
| RECS | src/cdng src/mlv src/prores src/video src/lossydng src/audio | 16 | 18 |
| SENSOR | whole repo, 70bdb26..cinemate-port | 1 (apertar) | 50 (cinemate-port) |

Commands (run in each repo; B=upstream-1.6.0, H=cinemate-port):
```
git -C /home/user/Apertar-Core rev-list --count --no-merges $B..$H -- src/web
git -C /home/user/Apertar-Core log --no-merges --format='%h|%ad|%s' --date=short -5 $B..$H -- src/web
git -C /home/user/Apertar-UI   rev-list --count --no-merges $B..$H -- qml
git -C /home/user/imx585-v4l2-driver rev-list --count --no-merges 70bdb26..cinemate-port
```
(path sets as in the table.) SENSOR today: 50 non-merge commits over Studio main 70bdb26 (52 counting merges); 53 non-merge if measured from e5b74d3 (the Apertar-Beta image driver).

Complete replacement for `const FORKDATA = ...` (all entries link to GitHub; heads 01f170c / 7ea9afc / cd548ef):
```
{"QML": {"repo": "Apertar-UI", "count": 24, "recent": [["68e1a41", "2026-11-01", "qml: the dropped-frames chip shows the number of dropped frames", true], ["e061be8", "2026-11-01", "drop-frames: the audio meter outline is red only while recording", true], ["5697b54", "2026-11-01", "drop-frames: faint red outline on the audio meter when sound is recorded, with a switch", true], ["606f137", "2026-11-01", "drop-frames: Clip names card in Settings > Record", true], ["96a7aa4", "2026-11-01", "drop-frames: record button and pill during a safety-stop flush", true]]}, "BRIDGE": {"repo": "Apertar-UI", "count": 12, "recent": [["68e1a41", "2026-11-01", "qml: the dropped-frames chip shows the number of dropped frames", true], ["606f137", "2026-11-01", "drop-frames: Clip names card in Settings > Record", true], ["841d0ed", "2026-10-31", "drop-frames: buffer bar, safety-stop pill, Frames / RAM, Log and storage pre-roll", true], ["ea44bd7", "2026-10-30", "ui: a Controls chip on the camera page and a read-only Controls card", true], ["7029db1", "2026-10-29", "ui: UI timecode and file timecode are set apart (Settings), the tap changes the UI one", true]]}, "RENDER": {"repo": "Apertar-UI", "count": 8, "recent": [["c153c33", "2026-11-02", "ui: drop APERTAR_PREVIEW_PEAKING=fast (park it on drop-count)", true], ["1c7a3ad", "2026-11-02", "ui: drop APERTAR_PREVIEW_DIRECT (a no-op with hdmi_external_only)", true], ["b333343", "2026-11-02", "ui: drop APERTAR_PREVIEW_PEAKING=cpu (park it on drop-count)", true], ["010f8ad", "2026-11-02", "ui: drop APERTAR_PREVIEW_PLANE (park it on preview-plane)", true], ["c13b846", "2026-11-01", "ui: APERTAR_PREVIEW_PLANE shows the live picture on the DRM primary plane", true]]}, "UICONF": {"repo": "Apertar-UI", "count": 4, "recent": [["5697b54", "2026-11-01", "drop-frames: faint red outline on the audio meter when sound is recorded, with a switch", true], ["841d0ed", "2026-10-31", "drop-frames: buffer bar, safety-stop pill, Frames / RAM, Log and storage pre-roll", true], ["da2a9b5", "2026-10-28", "ui: recording frame and red timecode switches", true], ["ed0d7b5", "2026-10-28", "ui: pickers follow the value lists, greyed above the ceiling (T33)", true]]}, "WEBPAGE": {"repo": "Apertar-Core", "count": 82, "recent": [["ba0658d", "2026-11-08", "media: a merge worker flattens split clips while the camera is idle", true], ["d7dd337", "2026-11-08", "cdng: split a take into part folders with [storage] frames_per_folder", true], ["c810f85", "2026-11-04", "web: the frame-rate phase lock on the System pane's Performance card", true], ["e625c68", "2026-11-04", "camera: a Preview temporal denoise switch, off by default", true], ["ce0bd90", "2026-11-04", "media: a switch for the drive trim (set_media_trim, default on) and a Performance card", true]]}, "HWIN": {"repo": "Apertar-Core", "count": 20, "recent": [["ba0658d", "2026-11-08", "media: a merge worker flattens split clips while the camera is idle", true], ["d7dd337", "2026-11-08", "cdng: split a take into part folders with [storage] frames_per_folder", true], ["9b5ea14", "2026-11-04", "web: a GPIO button can be remote only; pins a DPI display holds are greyed", true], ["2a4266e", "2026-11-01", "web: Boot Config marks the lines the card sets, and where your own go", true], ["3b87d99", "2026-11-01", "web: Boot Config card edits config.txt as text too (Edit file)", true]]}, "HUB": {"repo": "Apertar-Core", "count": 73, "recent": [["01f170c", "2026-11-08", "media: read the clip merge switch before the worker's first scan", true], ["68516f1", "2026-11-08", "media: rescan for split clips after a merge pauses", true], ["ba0658d", "2026-11-08", "media: a merge worker flattens split clips while the camera is idle", true], ["d7dd337", "2026-11-08", "cdng: split a take into part folders with [storage] frames_per_folder", true], ["e625c68", "2026-11-04", "camera: a Preview temporal denoise switch, off by default", true]]}, "CAM": {"repo": "Apertar-Core", "count": 73, "recent": [["ba0658d", "2026-11-08", "media: a merge worker flattens split clips while the camera is idle", true], ["d7dd337", "2026-11-08", "cdng: split a take into part folders with [storage] frames_per_folder", true], ["f4a1393", "2026-11-04", "camera: phase lock pins {d, d+1} so the line length stays fixed", true], ["e625c68", "2026-11-04", "camera: a Preview temporal denoise switch, off by default", true], ["ce0bd90", "2026-11-04", "media: a switch for the drive trim (set_media_trim, default on) and a Performance card", true]]}, "RECS": {"repo": "Apertar-Core", "count": 18, "recent": [["ba0658d", "2026-11-08", "media: a merge worker flattens split clips while the camera is idle", true], ["d7dd337", "2026-11-08", "cdng: split a take into part folders with [storage] frames_per_folder", true], ["2edc6d0", "2026-11-02", "config: a media tuning file ~/apertar-media-tune.conf with a test-night override", true], ["adac040", "2026-11-01", "cdng: drop a DNG's pages after the fsync by default (APERTAR_DNG_DONTNEED=sync)", true], ["5e9dd1a", "2026-11-01", "mlv: declare the same black and white level as the cDNG of the take, at every bit depth", true]]}, "SENSOR": {"repo": "imx585-v4l2-driver", "count": 50, "recent": [["cd548ef", "2026-11-01", "docs: README clone URL and branch, and the Bookworm config.txt path", true], ["56de0cc", "2026-11-01", "docs: add APERTAR.md, the install and mode guide for Apertar users", true], ["97649ba", "2026-11-01", "imx585: set the geometry controls read-only in their config, not after creation", true], ["c18f162", "2026-11-01", "imx585: log the per-mode HMAX/VMAX table at debug level", true], ["24172e6", "2026-10-26", "imx585: report each mode's sensor window as its crop rectangle", true]], "branch": "cinemate-port"}}
```
Caveat on RENDER 8: five of the eight are add-then-drop pairs for env switches (APERTAR_PREVIEW_PLANE/PEAKING/DIRECT); net diff of the file is small. The count is still what the formula gives.

## 2. Driver branch

Map and README say imx585 branch `apertar` (footer line, GH link `tree/apertar`, FORKDATA.SENSOR.branch). Today:
- `apertar` = e5b74d3 = the driver shipped on the Apertar-Beta 1.6.0 image = 1 commit over Studio main 70bdb26. It is the OFFICIAL image's driver, not the port's.
- The port's driver work is branch `cinemate-port` (cd548ef, 52 commits over 70bdb26, remote exists). Core's code names it: `src/camera/Imx585Modes.hpp:3` "modes the cinemate-port driver advertises"; `src/camera/CameraController.cpp:441-442` "(cinemate-modes, the cinemate-port driver branch)".
- imx283: Tiramisioux/imx283-v4l2-driver branch `cinemate-port` (68b7dc9, 93 commits over master). Core uses it: `src/camera/Imx283Modes.hpp:1-2` "57 modes of the cinemate-port driver (Tiramisioux/imx283-v4l2-driver, branch cinemate-port)". The map mentions no imx283 driver at all. Studio has no imx283 repo in the map's links.
- Right today for the fork side: imx585 `tree/cinemate-port`, plus imx283 `tree/cinemate-port`. Official side: Studio imx585 main (70bdb26) is a different layout from what official Core 1.6.0 was built against (apertar branch e5b74d3, 21-entry supported_modes[]); the official footer's "imx585 driver" link goes to main. Imprecise, see items below.

## 3. URLs (git ls-remote --heads, 2026-11-17)

| URL | Result |
| --- | --- |
| Apertar-Studio/Apertar-Core | main 35dbe67 ok (footer SHA ok) |
| Apertar-Studio/Apertar-UI | main 43888e5 ok (footer SHA ok) |
| Apertar-Studio/imx585-v4l2-driver | main 70bdb26 ok; no `apertar` branch (compare link base `main` valid) |
| Tiramisioux/Apertar-Core | cinemate-port 01f170c ok (footer says f4a1393: stale) |
| Tiramisioux/Apertar-UI | cinemate-port 7ea9afc ok (footer says 7029db1: stale) |
| Tiramisioux/imx585-v4l2-driver | apertar e5b74d3 exists; cinemate-port cd548ef exists |
| Tiramisioux/imx283-v4l2-driver | cinemate-port 68b7dc9 exists |
| Tiramisioux/apertar-coding-map | main bff7bd5 ok |
| github.com/Apertar-Studio (org page) | not a repo, ls-remote not applicable; not fetched |
| tiramisioux.github.io/apertar-coding-map | page, not checked |

Compare links built at line 537: `<Studio repo>/compare/main...Tiramisioux:<repo>:cinemate-port` is valid for Core and UI; for the driver with branch apertar it works but compares the wrong branch (see 2).

## 4. README and static text

True in both modes: two programs on one Pi 5 (map is Pi 5 specific, brief); WebUI port 8000 (`webPort = 8000`, ApertarCoreApp.hpp upstream:36, fork:42); socket `/tmp/apertar-core.sock` (ApertarCoreApp.hpp:33 upstream, :39 fork); `/api/state` GET and `/api/command` POST with `cmd` key (ApertarCoreApp.cpp:7154/7637 upstream, 8428/9214 fork; ControlProtocol.cpp:220 `string("cmd")`); `"iso":<number>` in state (upstream 7861, fork 9485); apertar.local:8000 (upstream READMEs); legend colours and line meanings match LINES/GROUPS (thin 2 = function call, thick 5 = socket/HTTP, dashed back, 8 px picture, dotted file); arrow numbers 1-7 used; "Try 3 and 6" match c3/c5 (3) and s1/s2 (6).
Wrong or stale: see discrepancies (footer SHAs, driver branch, README branch line). Cross-slice, seen in passing: `N.WEBPAGE.tip` says the file "is about 12k lines"; upstream 11618, fork 20963, no up override. `N.WEBPAGE.code` setInterval line is true in both (upstream 11609, fork 20954).

## Recheck

Second checker, 2026-11-17. Re-derived from: `git rev-parse` (Core HEAD = cinemate-port = 01f170c, UI = 7ea9afc), the same `rev-list --count --no-merges upstream-1.6.0..cinemate-port -- <paths>` per box (Core/UI) and `70bdb26..cinemate-port` (imx585, 50), `git log --no-merges -5` for `recent`, index.html lines 420/421/537/914/916, README.md:27.

| # | Item | Verdict | Why |
| --- | --- | --- | --- |
| 1 | SRC.fork.foot Core SHA | stands | f4a1393 is a mid-branch commit; HEAD 01f170c |
| 2 | SRC.fork.foot UI SHA | stands | 7029db1 is a mid-branch commit; HEAD 7ea9afc |
| 3 | fork footer / README / SENSOR.branch | corrected differently | Branch `apertar` (e5b74d3, "as shipped on the Apertar-Beta 1.6.0 image") is not the port's driver; Core names `cinemate-port` (Imx585Modes.hpp:3@cinemate-port). Fix kept to the imx585 link and branch. Adding the imx283 driver dropped: that is fork growth, the existing statement does not become false by omitting it. `GH` const needs no change (it holds the repo root; the branch comes from FORKDATA.SENSOR.branch at line 537). SENSOR.branch folded into item 4 |
| 4 | FORKDATA.SENSOR | stands | 50 non-merge commits over Studio main 70bdb26 (the compare base at line 537), recent five verified, branch cinemate-port |
| 5-13 | FORKDATA QML BRIDGE RENDER UICONF WEBPAGE HWIN HUB CAM RECS | stand | Counts 24/12/8/4/82/20/73/73/18 and the five recent rows re-run and match exactly |
| 14 | SRC.official.foot driver link | dropped | Not false: the link is the official driver repo and no official-mode field quotes driver code (N.SENSOR has no code line). The proposed text adds a claim about the image build that does not fit the footer |

Seen in passing, other slice (RECIPES): index.html:661 fork intro "Apertar-Core f4a1393, Apertar-UI 7029db1" has the same stale SHAs; corrected: `(Apertar-Core 01f170c, Apertar-UI 7ea9afc)`.

## Final discrepancies

1. **SRC.fork.foot (Core SHA)**, fork, stale. Map: `Apertar-Core</a> (<code>f4a1393</code>)`. Code: `git -C /home/user/Apertar-Core rev-parse cinemate-port` = 01f170c. Corrected: `Apertar-Core</a> (<code>01f170c</code>)`
2. **SRC.fork.foot (UI SHA)**, fork, stale. Map: `Apertar-UI</a> (<code>7029db1</code>)`. Code: `git -C /home/user/Apertar-UI rev-parse cinemate-port` = 7ea9afc. Corrected: `Apertar-UI</a> (<code>7ea9afc</code>)`
3. **SRC.fork.foot (driver) + README.md:27**, fork, wrong. Map: `<a href="https://github.com/Tiramisioux/imx585-v4l2-driver/tree/apertar">imx585 driver</a> (branch <code>apertar</code>)`; README: `[imx585 driver](https://github.com/Tiramisioux/imx585-v4l2-driver/tree/apertar) (branch `apertar`);`. Code: `src/camera/Imx585Modes.hpp:3@cinemate-port` "// The IMX585 modes the cinemate-port driver advertises"; driver branch `apertar` = e5b74d3 "imx585: aspect-ratio crop modes, as shipped on the Apertar-Beta 1.6.0 image". Corrected footer: `<a href="https://github.com/Tiramisioux/imx585-v4l2-driver/tree/cinemate-port">imx585 driver</a> (branch <code>cinemate-port</code>)`. Corrected README: `[imx585 driver](https://github.com/Tiramisioux/imx585-v4l2-driver/tree/cinemate-port) (branch `cinemate-port`);`
4. **FORKDATA.SENSOR**, fork, stale. Map: count 1, recent [e5b74d3], branch "apertar". Code: `git -C /home/user/imx585-v4l2-driver rev-list --count --no-merges 70bdb26..cinemate-port` = 50. Corrected: `"SENSOR": {"repo": "imx585-v4l2-driver", "count": 50, "recent": [["cd548ef", "2026-11-01", "docs: README clone URL and branch, and the Bookworm config.txt path", true], ["56de0cc", "2026-11-01", "docs: add APERTAR.md, the install and mode guide for Apertar users", true], ["97649ba", "2026-11-01", "imx585: set the geometry controls read-only in their config, not after creation", true], ["c18f162", "2026-11-01", "imx585: log the per-mode HMAX/VMAX table at debug level", true], ["24172e6", "2026-10-26", "imx585: report each mode's sensor window as its crop rectangle", true]], "branch": "cinemate-port"}`
5-13. **FORKDATA QML, BRIDGE, RENDER, UICONF, WEBPAGE, HWIN, HUB, CAM, RECS**, fork, stale. Map counts 15/8/0/2/80/18/69/71/16. Code counts 24/12/8/4/82/20/73/73/18. Corrected: the entries as in the first checker's "Complete replacement for `const FORKDATA`" block above (verified identical to a re-run).
