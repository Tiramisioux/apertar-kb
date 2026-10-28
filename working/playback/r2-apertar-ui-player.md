# R2: Apertar touch-UI clip browser and player (the model for WebUI playback)

Reader report for the playback project. Patrik's decision (2026-10-28): "make the playback in web ui similar to the current touch ui". This report describes the touch UI that the WebUI must resemble. It covers the browser and the player, the C++ engine behind them, formats, colour, speed, recording, deletion, HDMI, known quirks, what it lacks and what can be reused.

Trees (read only):

- `ui:` = Apertar touch UI at `d8098d0`, `/tmp/claude-0/-home-user-apertar-kb/17fc979d-f346-53ac-97ad-c8caa225a57d/scratchpad/controls/ui-tip`. **A path with no prefix is in this tree.**
- `core:` = Apertar Core at `eb9cc39`, `.../scratchpad/controls/core-tip`.
- `cm:` = Cinemate `dev` at `d6cc93e`, `/home/user/tiramisioux/cinemate`.

Labels: **CONFIRMED** = I opened the line. **PROBABLE** = derived (the reasoning is given). **UNCONFIRMED** = not checked or not checkable here (no Pi, no measurements). One label covers a whole bullet or table row unless a cell has its own label.

Qt colour notation: QML writes `#AARRGGBB` (alpha first). CSS writes `#RRGGBBAA`. Every alpha colour below is also given as `rgba()`. Do not copy the QML hex into CSS as it is.

---

## 0. Summary

1. Two pages, `ClipBrowserPage.qml` (grid of cards) and `ClipPlayerPage.qml` (preview, badges, scrub bar, transport, histogram, metadata). `Main.qml` loads each in a `Loader` keyed on `currentPage` = `"browser"` / `"player"`. CONFIRMED `qml/Main.qml:580-640`.
2. The browser has a black page, a title block ("PLAYBACK" / "Clip Browser"), three top-right buttons (Refresh Media, Capture Clip/Still Mode, Back), and a dark rounded sheet. The sheet holds a header row, a sort chip, a count chip, a status line and a 2/3/4-column grid of 16:9 thumbnail cards. CONFIRMED `qml/ClipBrowserPage.qml:156-806`.
3. Card = thumbnail with a duration pill, then name, format label and shot date. Tap opens the clip. Long press starts multi-selection. Selected clips are deleted through a red confirmation dialog. There is no protect/lock feature. CONFIRMED `qml/ClipBrowserPage.qml:602-804`, `:808-1024`.
4. The player has a 16:9 preview with three badges (fps, PLAYING/PAUSED, FRAME i / N), a press-and-drag scrub bar, and prev clip / play-pause / next clip. It also has a red Remove button, a 48-bin histogram, and "Clip Metadata" with 9 fields. In landscape the metadata is a side panel. On a square or compact screen it is an Info overlay. CONFIRMED `qml/ClipPlayerPage.qml:211-2271`.
5. Formats: cDNG folders (uncompressed, lossless LJ92, Apertar "lossy" = LJ92 plus LinearizationTable, mono LinearRaw), single-file uncompressed MLV, ProRes and H.264 (through a dlopen'ed libav plugin), and stills (DNG/JPEG/PNG/TIFF). A WAV sidecar plays through an `aplay` subprocess. CONFIRMED `src/cliplistmodel.cpp:443-586`, `src/dngdecoder.cpp:1005`, `src/MlvReader.cpp:153-216`, `src/VideoPlaybackLibav.cpp:56-57`, `src/playbackcontroller.cpp:996-1005`.
6. Everything decodes on the Pi CPU inside the UI process: full raw decode of every DNG, a half-resolution quad debayer, a fixed tone curve and sRGB. There is no LUT and no use of Core's preview colour profile. Log ProRes plays flat. CONFIRMED `src/cdngimageprovider.cpp:577-698`, grep shows no LUT in the playback files.
7. Blocking during recording is weak. The on-screen folder button is disabled while recording (`qml/CameraPage.qml:3754`). The hardware `clip_browser` action, Delete and playback are not blocked. Core's WebUI delete is blocked (`core:src/ApertarCoreApp.cpp:7660-7666`). CONFIRMED.
8. HDMI: while the browser or player is up, the external-monitor window is hidden. Playback is never shown on HDMI. CONFIRMED `src/ExternalMonitorManager.cpp:111-126`, `src/main.cpp:202-209`.
9. Performance: the scan and the paused-frame decode run on the GUI thread. Every browser open rescans the card and throws away all thumbnails. The player opens paused at frame 0 and loops forever. cDNG playback fps is capped at 60. CONFIRMED/PROBABLE, see §9.
10. Reuse: the WebUI already has a Core-served "Clip Browser" overlay (list, filters, sort, select, download, delete) and `/api/media*` routes, but no player (`core:src/web/WebControlPage.cpp:3979-4030`, `core:src/ApertarCoreApp.cpp:7307-7312`). The touch UI's decoders are Qt-bound. Only the libav plugin (pure C ABI) and the parsing rules carry over without changes. See §12.

---

## 1. How it opens and the flow

### 1.1 Page state machine (`Main.qml`)

`currentPage` is one of `"camera"`, `"browser"`, `"player"` (CONFIRMED `qml/Main.qml:16`, `:39`).

| From | Trigger | To | Ref |
| --- | --- | --- | --- |
| camera | On-screen folder button `ClipBrowserButton` (bottom row, left of the timecode). Closes the quick menu | browser | CONFIRMED `qml/CameraPage.qml:3746-3759`, `qml/Main.qml:507-510` |
| camera / settings | Hardware action `clip_browser` (GPIO, PCF8574, NeoRotary). Settings are closed first | browser (toggle) | CONFIRMED `qml/Main.qml:319-322` |
| browser or player | Hardware action `clip_browser` again | camera | CONFIRMED `qml/Main.qml:321` (`browserLayerVisible ? "camera" : "browser"`) |
| browser | Tap a card (not in selection mode) | player (`selectClip` → `playbackController.loadClip(path)`) | CONFIRMED `qml/ClipBrowserPage.qml:791-801`, `qml/Main.qml:417-424`, `:602-604` |
| browser | Back (when nothing is selected) | camera | CONFIRMED `qml/ClipBrowserPage.qml:348-356`, `qml/Main.qml:601` |
| player | Back: `playbackController.stop()`, then back | browser | CONFIRMED `qml/ClipPlayerPage.qml:284-291`, `qml/Main.qml:634` |
| player | Prev / Next clip | player, at index ±1 of the browser's current sort order | CONFIRMED `qml/Main.qml:426-443`, `:635-636` |
| player | Remove, then confirm | player on the clip that now has the same index, or browser if the list is now empty | CONFIRMED `qml/Main.qml:445-467` |
| any | Hardware `settings` | camera, settings toggled | CONFIRMED `qml/Main.qml:313-317` |
| any | Standby | playback stopped, providers flushed | CONFIRMED `src/main.cpp:336-348`, `:368-375` |

Core's role: Core only forwards the hardware action. It publishes `{"event":"hardware_action","action":"clip_browser"}` and keeps no state about it (CONFIRMED `core:src/ApertarCoreApp.cpp:9142-9144`). The input drivers accept the action names `clip_browser`, `browser` and `playback` (CONFIRMED `core:src/hardware/GpioInput.cpp:133-134`, `core:src/hardware/Pcf8574Input.cpp:167-168`, `core:src/hardware/NeoRotary4Input.cpp:146-147`). The WebUI does not get this event as a navigation today (UNCONFIRMED for the web page; not read).

### 1.2 Side effects of leaving the camera page

- Audio-meter monitoring is suspended whenever `currentPage !== "camera"` (CONFIRMED `qml/Main.qml:75-86`, `:181-186`).
- The external HDMI monitor window is hidden (§6).
- The camera page and its live preview stay loaded under the browser (z 900/901 above the camera page). No code pauses the preview (PROBABLE: grep for preview pausing in `Main.qml`/`CameraPage.qml` found nothing).

### 1.3 Lifetime

- Both pages are `Loader`s. `active` follows `currentPage`, so each page is **destroyed** when you leave it and rebuilt when you return (CONFIRMED `qml/Main.qml:580-640`).
- PROBABLE consequences of the rebuild:
  - The browser comes back scrolled to the top.
  - Selection is cleared.
  - `clipModel.browserOpen` goes false → true, which runs `refresh()`, a full rescan (`cliplistmodel.cpp:311-322`).
  - The thumbnail cache is cleared (`ClipBrowserPage.qml:71-81`, `Main.qml:587-590`).
- The browser highlights the last-opened clip (`selectedClipPath` from `Main`) with a lighter card (CONFIRMED `qml/Main.qml:598`, `qml/ClipBrowserPage.qml:623-628`).

### 1.4 Flow, open to close

1. Folder button. The browser loads and `browserOpen = true` runs a synchronous scan of `/media/RAW` (§4.1). Thumbnails load asynchronously.
2. Tap a card. `loadClip` lists frames or probes the movie, reads the fps, finds the WAV, builds the metadata (decodes the first frame fully for cDNG) and sets frame 0. The player opens **paused on frame 0**, with no autoplay (CONFIRMED `src/playbackcontroller.cpp:638-747`, `setPlaying(false)` at `:720`).
3. Play. A timer at `round(1000/fps)` ms advances the frames. If a WAV exists, the audio clock drives the frame index. At the end the clip **loops** to frame 0 and goes on, with no stop at the end (CONFIRMED `:749-775`, `:567`, `:827-859`).
4. Scrub. Press or drag on the progress bar calls `seekToFrame` (CONFIRMED `qml/ClipPlayerPage.qml:95-103`, `:658-665`).
5. Back. `stop()` (pause, frame 0), then the browser, which rescans.
6. Back again. Camera.

---

## 2. Browser anatomy (`qml/ClipBrowserPage.qml`)

### 2.1 Layouts

`displayLayout` comes from `[display]` in the hardware config. Documented pairs (CONFIRMED `src/DisplayConfigBridge.cpp:305-311`):

- `square` = 720x720 (default)
- `landscape_compact` = 640x480 / 800x480
- `landscape_medium` = 1024x600
- `landscape` = 1280x720
- `landscape_large` = 1920x1080

When no layout is given, auto-detection never picks `landscape`; 1280x720 becomes `landscape_medium` (CONFIRMED `src/DisplayConfigBridge.cpp:509-522`). Portrait layouts exist, but the clip pages set no flag for them. PROBABLE: they render with the `square` values, because no `portrait*` test appears in either page.

Derived flags (CONFIRMED `qml/ClipBrowserPage.qml:14-22`):

- `large` = landscape_large
- `standard` = landscape or large
- `medium` = landscape_medium
- `regular` = medium or standard
- `compact` = landscape_compact or regular (it is true for **all** landscape layouts)
- Grid columns: standard 4, regular 3, else 2.

Size tokens. The order is large / standard / medium / compact / square. Where one value is listed for several layouts, they share it.

| Token | Value | Ref |
| --- | --- | --- |
| Top button height | 72 / 60 / 52 / 40 / 54 | `:43` |
| Top button radius | 24 / 20 / 18 / 15 / 18 | `:44` |
| Top button top margin | 30 (large), else 22 | `:45` |
| Gap between top buttons | 16 / 12 / 9 / 8 / 12 | `:46` |
| Back width | 158 / 132 / 116 / 90 / 112 | `:47` |
| Mode width | 178 / 148 / 128 / 94 / 136 | `:48` |
| Refresh width | 254 / 204 / 176 / 136 / 166 | `:49` |
| Card margin | 7 (large) / 4 (compact) / 5 | `:25` |
| Card radius | 30 / 22 / 24 | `:26` |
| Thumb inset (left, right) | 16 (large) / 12 | `:27` |
| Thumb top margin | 16 / 10 / 12 | `:28` |
| Thumb radius | 23 / 16 / 18 | `:31` |
| Thumb to footer gap | 18 / 12 / 14 | `:30` |
| Footer side margin | 18 / 14 | `:32` |
| Footer bottom margin | 28 / 18 / 24 | `:33` |
| Footer height | 76 / 54 / 58 | `:34` |
| Name font | 22 / 15 / 17 | `:35` |
| Format font | 16 / 11 / 13 | `:36` |
| Date font | 14 / 10 / 11 | `:37` |
| Duration pill height / radius / font | 34/17/13 · 24/12/10 · 28/14/11 | `:38-40` |
| Selection badge size / font | 34/18 · 24/13 · 28/15 | `:41-42` |
| Grid "column gap" | 16 / 10 / 14 | `:23` |

All rows CONFIRMED (`qml/ClipBrowserPage.qml` lines given).

Notes:

- `clipCellHeight` (`:24`) and `clipThumbnailHeight` (`:29`) are declared but never used. The real cell height is computed (CONFIRMED: grep finds only the declarations).
- Formulas (CONFIRMED `:128-140`, `:589-590`):
  - `cellWidth = (gridWidth − (cols−1)·gap) / cols`
  - `thumbH = round((cellWidth − 2·cardMargin − 2·thumbInset) · 9/16)`
  - `cellHeight = 2·cardMargin + thumbTop + thumbH + footerGap + footerH + footerBottom`
- The grid has no spacing of its own. The "gap" is only subtracted from the cell width. So the visible space between cards is 2 × card margin, and an extra `gap` px is left free at the right edge of the grid (PROBABLE, from the formula: n cells of `(W−(n−1)gap)/n` fill `W−(n−1)gap`).

Worked example, `square` 720x720 (PROBABLE, arithmetic from the tokens): sheet width 672, grid width 644, cell width 315, thumbnail 281x158, cell height 276, about two rows visible.

### 2.2 Regions, top to bottom

**Page.** `Rectangle` `#000000` full screen (CONFIRMED `:156-159`). Fonts are Inter Regular, Medium and Bold from `qrc:/qml/fonts/Inter/` (CONFIRMED `:142-144`).

**Title block**, top-left (CONFIRMED `:161-185`):

- Position: left 24 (32 large), top 22 (28 large, 20 compact).
- Line 1: "PLAYBACK". Inter Medium 12 px (15 large, 9 compact). Colour `#66ffffff` = rgba(255,255,255,0.40). Uppercase, letter-spacing 3.
- Line 2: "Clip Browser", or "Still Browser" in still mode. Inter Bold 34 px (46 large, 36 standard, 26 compact). White.

**Top-right buttons**, right to left: Back, Capture mode, Refresh. Each is anchored to the left of the previous one with `browserTopButtonGap` (CONFIRMED `:187-358`).

Common style:

- Background `#14ffffff` = rgba(255,255,255,0.078). Pressed `#20ffffff` = rgba(255,255,255,0.125).
- Border 1 px `#1affffff` = rgba(255,255,255,0.10).
- Pressed scale 0.985. Colour and scale animate over 150 ms, OutCubic.

| Button | Content | Behaviour | Ref |
| --- | --- | --- | --- |
| Back (right margin 24/32) | Text "←" (font 18) + "Back". Shows "Cancel" in selection mode | In selection mode: clear the selection. Else: `backRequested()` | CONFIRMED `:305-358` |
| Capture mode | Two centred lines. "CAPTURE": Medium 10 px, uppercase, letter-spacing 2.1, `#8f9096` (cyan `#79ddff` in still mode). Then "Clip Mode" / "Still Mode": Medium 15 px, white. In still mode: background `#1f2c36` (pressed `#22323c`), border `#3fd0ff` | Toggles `settingsBridge.photoModeEnabled`. **This switches the camera's capture mode**, not only the browser filter. Disabled while scanning | CONFIRMED `:187-246`, `:115-119`. Camera page reads the same property: CONFIRMED `qml/CameraPage.qml:215` |
| Refresh | Icon `refresh.png` (18 px; opacity 0.92, or 0.48 when disabled) + "Refresh Media", or "Scanning..." while loading. Disabled text colour `#8a8a8f` | Clears the selection, then `clipModel.refresh()`. Disabled while loading | CONFIRMED `:248-303` |

**Sheet ("browserPanel")** (CONFIRMED `:360-396`):

- Margins 24 (32 large). Top margin 112 square, 100 standard, 90 medium, 82 compact, 124 large.
- Bottom margin −32 on non-compact layouts, so the sheet runs off the bottom of the screen. Two filler rectangles square off its bottom. The effect is a sheet with rounded top corners only.
- Radius 28 (34 large, 24 compact). Colour `#151515`. Border 1 px `#1affffff`.

**Sheet header row**, top-left of the sheet: left 24, top 20 (CONFIRMED `:398-426`).

- Icon `film.png` (a film strip), 24 px (38/30/20).
- Label "CLIPS", "STILLS" or "SELECTION". Medium 13 px (20/16/11), uppercase, letter-spacing 3, white.

**Chips**, top-right of the sheet: right margin 20, top 14. Right to left (CONFIRMED `:428-554`):

- Count chip, a pill:
  - Height 30. Width 108, or 148 in selection mode.
  - Background `#14ffffff`, border `#1affffff`.
  - Text "N items" or "N selected" shown uppercase ("12 ITEMS"; "1 ITEMS" is not pluralised). Bold 11 px, letter-spacing 2.
- Sort chip (hidden in selection mode):
  - Pill of height 30. Width = label + 34.
  - Background `#171717` (pressed `#1f2c36`). Border `#3fd0ff`.
  - Text `clipModel.sortMode` ("Newest First" / "Oldest First"), uppercase. Bold 11 px, `#79ddff`, letter-spacing 1.8.
  - Tap toggles the sort and clears the selection. Disabled while scanning.
- "Remove Selected" button (in place of the sort chip, selection mode only):
  - 178x40, radius 16.
  - Background `#8d2020` (pressed `#a32828`), border `#ba4a4a`.
  - Icon `delete.png` (a trash can) 16 px + "Remove Selected", Medium 14 px, white.
  - Tap opens the confirmation dialog. Fades in over 160 ms.

**Status line**: left 24, right 140, top 52 (64 in selection mode). Regular 12 px, `#6f7076`, elided on the right (CONFIRMED `:556-575`). It shows:

- Normal mode: `clipModel.statusText` (strings in §2.5).
- Selection mode: "Long press starts selection. Tap clips to add or remove them." In still mode: "…Tap stills…".

**Grid** (CONFIRMED `:577-600`):

- `GridView`. Insets: left 16, right 12, top 78 (92 in selection mode; 64/100/124 compact/standard/large), bottom 44 (0 compact).
- Vertical flick with overshoot. Scrollbar shown only when needed.
- `reuseItems`. Cache buffer of 2 rows. `model` is `clipModel`.

**Card** (one delegate) (CONFIRMED `:602-803`):

- Outer rectangle:
  - Margin 5, radius 24, colour `#181818`, border 1 px `#1affffff`.
  - Last-opened clip: `#1d1d1d`, border `#33ffffff` = rgba(255,255,255,0.20).
  - Marked for deletion: `#241c1f`, border `#ba4a4a`.
  - Pressed scale 0.985. Colour and border animate over 180 ms.
- Thumbnail frame:
  - Inset 12 left and right, top 12. Height = `thumbH` (16:9). Radius 18. Clipped.
  - Background `#171717` (`#202020` last-opened, `#2a1d1d` selected). Border `#16ffffff` = rgba(255,255,255,0.086).
  - Image: `PreserveAspectFit`, `asynchronous`, `cache:false`, `smooth:false`, `sourceSize` = 90 % of the frame.
  - Tint overlay on top: `#12000000` = rgba(0,0,0,0.07), or `#25101010` when selected.
  - "NO PREVIEW": centred, Medium 12 px, `#72737a`, letter-spacing 2.4. Shown while the image is not ready.
  - Duration pill, bottom-left, inset 12:
    - Height 28, radius 14.
    - Background `#66000000` = rgba(0,0,0,0.40). Border `#22ffffff` = rgba(255,255,255,0.133).
    - Text e.g. "00:12" or "1:02:03". For stills: "DNG STILL". Bold 11 px, letter-spacing 2.
  - Selection badge, top-left, inset 12, selection mode only:
    - 28 px circle. Unselected: `#55000000` = rgba(0,0,0,0.33), border `#22ffffff`.
    - Selected: `#8d2020`, border `#ba4a4a`, with "✓" (Bold 15 px).
- Footer: side margins 14, bottom 24, height 58. A column with spacing 4:
  - Name: Bold 17 px, white, elided on the right.
  - Format label: Regular 13 px, `#8f9096`. Values: "cDNG clip", "ProRes clip", "H.264 clip", "MLV clip", "Video clip". For stills it shows the duration text with " STILL" replaced by " still", e.g. "DNG still".
  - Shot date: Regular 11 px, `#5f6066`, letter-spacing 1.2, elided in the middle. Format "dd MMM yyyy  HH:mm" (two spaces). Shows "Shot date unavailable" if empty.

**Delete confirmation** (CONFIRMED `:808-1024`):

- Scrim: full screen, `#cc000000` = rgba(0,0,0,0.80), z 20. Fades over 180 ms. Tapping it cancels.
- Card:
  - 408x308 (340x218 compact). Centred, offset −12 px vertically. Radius 26. `#151515`, border `#1affffff`.
  - Opens with opacity 220 ms and scale 0.96→1 over 240 ms, OutCubic.
- Card contents:
  - Icon disc: 40 px, `#2a1717`, border `#4a2a2a`, trash icon 18 px.
  - Title "Remove Selected Clips?": Bold 24 px.
  - Text "This will permanently delete the selected clips from media.": 14 px, `#8f9096`, wrapped at 290 px.
  - Summary box: height 82, radius 18, `#181818`. Lines:
    - "N clip(s) selected" (Bold 16)
    - The first selected file name (13 px, `#8f9096`, elided in the middle)
    - "+N more", or "This action cannot be undone." (13 px, `#6f7076`)
  - Buttons:
    - "Cancel": 156x54, radius 18, ghost style.
    - "Remove Clips": 192x54, red, trash icon. It runs `clipModel.removeClip(path)` for each selected path.
- The wording stays "Clips" in still mode (CONFIRMED `:878`, `:911`, `:1008`).

### 2.3 Per-clip data (`ClipListModel` roles)

The roles are `name`, `path`, `frameCount`, `durationText`, `thumbnailSource`, `shotDate`, `formatLabel` (CONFIRMED `src/cliplistmodel.h:19-27`, `src/cliplistmodel.cpp:230-241`). There is no resolution, fps, bit depth, codec profile, size, audio flag or dropped-frame count on the card. The player shows these only after a clip is opened (CONFIRMED).

| Field | cDNG folder | Movie (MOV/MP4/MLV) | Still |
| --- | --- | --- | --- |
| name | folder name | folder name (or file base name for a root-level movie) | file base name |
| frameCount | number of `*.dng` | `info.frames` from the probe, or 0 | 1 |
| durationText | `mm:ss` / `hh:mm:ss` from frames ÷ the first frame's FrameRate tag (24 if none). Seconds are rounded; under 0.5 s shows "00:00" | same, from the probe; "VIDEO" if the probe failed | "DNG STILL" / "JPEG STILL" / "PNG STILL" / "TIFF STILL" |
| formatLabel | "cDNG clip" (default, no bit depth or compression) | "`<codec>` clip" (ProRes / H.264 / MLV), or "Video clip" | not used (the QML shows the duration text instead) |
| shotDate | first frame's DateTimeOriginal, then DateTime, then a regex sniff of the first 64 KB, then mtime (mtime gives no display text) | same order for the movie file; non-TIFF files use mtime | same |
| thumbnail | `image://cdngthumb/thumb?path64=…&radius=18` of the first frame | `image://videothumb/frame?path64=…&frame=0` | `image://cdngthumb/…` |

Refs, all CONFIRMED: `src/cliplistmodel.cpp:47-57`, `:65-69`, `:71-145`, `:147-169`, `:494-556`, `src/cliplistmodel.h:74`.

### 2.4 Sorting, filtering, selection, gestures

- **Sort:**
  - Key: shot timestamp, then a numeric-aware name comparison.
  - "Newest First" (default) or "Oldest First". The tap toggles between them.
  - The sort is not persisted. The model object lives for the whole app run, so it survives page reloads (PROBABLE: `m_sortMode` is a member of a stack object from `main.cpp:309`).
  - CONFIRMED `src/cliplistmodel.cpp:287-299`, `:559-568`, `qml/ClipBrowserPage.qml:121-126`.
- **Filter:** only clips vs stills, and that follows the camera capture mode. There is no search and no format filter. Stills come only from `/media/RAW/Photos`. Clips come from the other folders and from movies in the root. CONFIRMED `src/cliplistmodel.cpp:465-557`.
- **Still pairs:** a DNG and a JPEG with the same base name are shown as one item. The first file in numeric name order wins. Delete removes every file with that base name. CONFIRMED `:473-479`, `:409-418`.
- **Gestures:**

| Gesture | Effect |
| --- | --- |
| Tap a card | Open the player. In selection mode, toggle the card instead |
| Long press a card | Start selection with that card, or toggle it if selection is already on |
| Vertical drag / flick | Scroll the grid |

  CONFIRMED `qml/ClipBrowserPage.qml:780-801`. The long-press time is Qt's MouseArea default (800 ms per Qt docs). PROBABLE: `pressAndHoldInterval` is not set (grep).
- **Not present:** swipe, pinch, double-tap, "select all", keyboard or rotary navigation of the grid. CONFIRMED by reading all handlers. The only hardware actions `Main.qml` handles are `power_button_press`, `standby_power_*`, `zoom_toggle`, `settings`, `clip_browser` and `quick_menu` (`qml/Main.qml:288-331`).
- **Selection is cleared** by: changing capture mode, changing the sort, Refresh, Back/Cancel, page visibility changes, and a finished delete. CONFIRMED `:63-81`, `:103-126`.

### 2.5 States and status strings

| State | What is shown | Ref |
| --- | --- | --- |
| Loading | Refresh shows "Scanning..." and is disabled. Mode and sort are disabled. But `scanClips()` sets `loading` true and false **within one synchronous call on the GUI thread**, so this state probably never paints | CONFIRMED `src/cliplistmodel.cpp:443-586`. PROBABLE that it never paints (one call, no event loop) |
| Empty | Status "No cDNG, ProRes, H.264 or MLV clips found in /media/RAW." or "No still files found in /media/RAW/Photos.", chip "0 ITEMS", empty grid. There is no empty-state illustration | CONFIRMED `:575-578` |
| Root missing | "/media/RAW is not available." | CONFIRMED `:452-460` |
| Pulled card | No special state. The model does not watch `mediaBridge`. The watcher fires on the root directory and a rescan shows "not available" or the empty text, depending on whether the mount-point directory still exists | PROBABLE (no `mediaBridge` use in `cliplistmodel.*`, watcher at `:178-189`) |
| Found | "Found N clip(s) in /media/RAW." / "Found N still(s) in /media/RAW/Photos." | CONFIRMED `:579-583` |
| Thumbnail error | "NO PREVIEW" while not ready. A DNG that fails gives a placeholder image with the text drawn in ("Decode failed: …" / "Could not render …"). A movie that fails gives a 480x270 image with the error text | CONFIRMED `qml/ClipBrowserPage.qml:676-686`, `src/cdngimageprovider.cpp:966-975`, `src/VideoPlayback.cpp:174-181` |
| Deletion results | "Removed X.", "Failed to remove X.", "Only listed media inside the recording folder can be deleted.", "Unsafe media deletion target.", "Clip folder is not available: …", "Item is not available: …" | CONFIRMED `src/cliplistmodel.cpp:382-441` |
| Recording | No state at all (§7) | CONFIRMED |
| Live refresh | While the browser is open, a `QFileSystemWatcher` on the root, each clip folder and each `.mlv` file triggers `refresh()` 150 ms after the **last** change. The single-shot timer is restarted, so changes are debounced | CONFIRMED `:176-189`, `:588-622` |

---

## 3. Player anatomy (`qml/ClipPlayerPage.qml`)

### 3.1 Three layout families

| Family | Layouts | Shape | Ref |
| --- | --- | --- | --- |
| Stacked | `square` (and portrait, PROBABLE) | Preview on top. Below it the title + info line + Info button, then the scrub bar. A bottom row with Remove (left), transport (centre) and histogram (right). Metadata in an overlay | CONFIRMED `:519-667`, `:1317-1656` |
| Compact | `landscape_compact` | Preview 248 px high. No title row. Full-width scrub bar above the transport. Bottom row: Remove (100x38), transport, an icon-only Info (42 wide) and the histogram (92x48) | CONFIRMED `:374`, `:1254-1315`, `:1465-1519` |
| Split | `landscape_medium`, `landscape`, `landscape_large` | Preview at the left. Below it a scrub bar of the same width, then a centred control row: Remove, transport, histogram. At the right an always-visible, scrollable "Clip Metadata" panel. No Info button and no overlay | CONFIRMED `:28`, `:306-345`, `:670-1252` |

Split sizes (CONFIRMED `qml/ClipPlayerPage.qml:306-345`):

- Info panel width:
  - large: 410–470 (25 % of the sheet)
  - standard: 340–420 (27 %)
  - medium: 300–320 (32 %)
- Gap: 32 / 24 / 18.
- Preview height = max(300 standard / 260, min(maxWidth·9/16, sheetH − 196 large / 132, 820 / 720 / 360)).
- Preview width = height · 16/9.

Worked examples (PROBABLE, arithmetic from those lines):

| Screen | Sheet | Preview | Info panel |
| --- | --- | --- | --- |
| 1280x720 | 1232x610 | 832x468 | 340 wide |
| 1024x600 | 976x490 | 610x343 | 312 wide |
| 1920x1080 | 1856x936 | 1312x738 | 464 wide |
| square 720 | 672x584 | 612x344 | (overlay) |

### 3.2 Regions

**Header** (CONFIRMED `:211-292`):

- Title block: "PLAYBACK" (same style as the browser), then "Clip Viewer" in Bold 34 px (40 large, 31 standard, 26 compact). The title does not change for stills.
- Back button, top-right: 112x54, radius 18 (158x72 large, 132x60 standard, 108x48 medium, 90x40 compact). "←" + "Back".
- Back stops playback (back to frame 0, paused) and returns to the browser.

**Sheet ("playerPanel")** (CONFIRMED `:294-305`): margins 24 (32 large). Top 112 (86 for all compact/landscape layouts except large, which is 112). Radius 28. `#151515`, border `#1affffff`. Unlike the browser, it does not run off the bottom.

**Preview frame** (CONFIRMED `:359-517`):

- Rectangle: top 18 (16 compact). Centred (stacked) or left-aligned (split). Radius 24 (30 large, 22 compact). `#171717`, border `#1affffff`. Clipped.
- Image: `PreserveAspectFit`. Letterboxed on black, because the decoder draws the picture centred on a black canvas (`src/cdngimageprovider.cpp:105-131`). `retainWhileLoading: true` keeps the previous frame on screen, so there is no flash between frames.
- Rounded corners are baked into the image (`&radius=24` in the URL, `src/cdngimageprovider.cpp:133-149`). In HTML use CSS `border-radius` instead.
- Badges. Common style: pill of height 30 (26 compact, 38 large), radius 15. Background `#66000000`, border `#22ffffff`. Bold 11 px uppercase, letter-spacing 2. Inset 14 (12 compact, 18 large).

| Corner | Content |
| --- | --- |
| Top-right | Frame rate: `clipMetadata.frameRate` in uppercase, e.g. "25.000 FPS" or "SINGLE FRAME" |
| Bottom-left | "PLAYING" / "PAUSED" |
| Bottom-right | "FRAME i / N" (1-based), or "FRAME 0 / 0" |

- There is no tap or gesture on the picture itself (CONFIRMED: no MouseArea between `:359` and `:517`).

**Title row**, stacked layout only, below the preview, margins 20 (CONFIRMED `:519-610`). Height 72:

- Clip name: Bold 27 px, white, elided.
- Info line: Regular 14 px, `#8f9096`. Value "`<type>` • N frames" (e.g. "cDNG sequence • 250 frames", "ProRes HQ • 1200 frames"). If there are no frames, the controller's status text is shown instead.
- "Info" button at the right: 126x52, radius 18, ghost. Icon `info.png` (circled i) 20 px + "Info" in Medium 17 px. Visible once a clip name exists. Opens the metadata overlay.

**Scrub bar** (CONFIRMED `:612-666` stacked; `:1254-1315` compact/split):

- Track height 28 (22 compact, 30 regular, 38 large).
- Rail: 8 px (6 compact, 10 large), round, `#1e1f23`.
- Fill: `#d7d9de`, width = (frame+1)/N.
- Handle: 24 px circle (18 compact, 30 large), `#f4f5f7`, border `#131417`. Centre dot 8 px, `#151515` at opacity 0.28.
- Interaction: press or drag anywhere on the track seeks to `round(x/width·(N−1))`. Each move event seeks; there is no throttling. There is no hover preview and no timecode readout.

**Control row** (CONFIRMED `:1317-1656` stacked/compact; `:983-1252` split):

- **Remove**: 132x54, radius 18 (stacked; 100x38 compact; 142x58 split, 176x72 large). Background `#8d2020` (pressed `#a32828`), border `#ba4a4a`. Trash icon + "Remove". Pressed scale 0.95. Opens the confirmation.
- **Transport**: a row of three circles. Spacing 14 (8 compact, 10 regular/split, 14 large). Ghost style (`#14ffffff`, border `#1affffff`).
  - Previous clip: 58 px (40 compact, 50 regular/split, 68 large). Icon `previous.png` (a bar plus a left-pointing outline triangle). Opacity 0.45 and disabled when there is no previous clip. Pressed scale 0.95.
  - Play/Pause: 78 px (54 compact, 64 split, 84 large). `play.png` (outline triangle) or `pause.png` (two bars). Pressed scale 0.94.
  - Next clip: mirror of Previous.
  - **These are clip skips, not frame steps.** `nextFrame()` / `previousFrame()` exist in C++ but no QML calls them (CONFIRMED: grep of `qml/`).
- **Histogram card**: 152x68, radius 18 (stacked; 92x48 compact; 142x58 split; 176x72 large). Background `#14ffffff`, border `#1affffff`.
  - Label "HISTOGRAM": Medium 10 px, `#ccffffff` = rgba(255,255,255,0.80), letter-spacing 2.2.
  - Canvas 30 px high (22 compact, 28 split, 36 large).
  - Drawing: baseline 1 px rgba(255,255,255,0.18). 48 bars with a 1 px gap. Fill is a vertical white gradient, 0.96 at the top to 0.42 at the bottom. Minimum bar height 2 px. Bin values are 0..1.
  - Redrawn on `histogramChanged`.

**Metadata.** The split panel is at `:670-981`; the overlay at `:1696-2053`; both CONFIRMED.

- Header: an "i" disc (42 px split / 40 overlay, `#1f1f1f` / `#1d1d1d`), then "Clip Metadata" (Bold 25/31 split, 24 overlay), then the clip name (14 px, `#8f9096`, elided in the middle).
- A two-column grid of label and value. Labels: Medium 11 px, `#66ffffff`, uppercase, letter-spacing 2. Values: Bold 15 px (18 large), white.
- The fields and their values:

| Label | Key | cDNG folder | Still | MOV/MP4/MLV |
| --- | --- | --- | --- | --- |
| CAPTURED | `captured` | first frame's DateTimeOriginal / DateTime / sniff, as "dd MMM yyyy  HH:mm" | same | `creation_time` (ISO, converted to local time), else the file mtime |
| TYPE | `type` | "cDNG sequence" | "DNG still" / "JPEG still" / "PNG still" / "TIFF still" | codec + profile, e.g. "ProRes HQ", "H.264 High", "MLV RAW" |
| RESOLUTION | `resolution` | active-area "W x H" | image size | "W x H" (coded, not pixel-aspect corrected) |
| BIT DEPTH | `bitDepth` | "N-bit" from the decoded frame (**16-bit for any file with a LinearizationTable**: lossy, Clear HDR 12-bit) | DNG "N-bit"; others "8-bit RGB" | "N-bit YUV" or "N-bit RAW" (MLV) |
| FRAME RATE | `frameRate` | "%.3f fps" | "Single frame" | "%.3f fps" |
| DURATION | `duration` | "mm:ss" or "hh:mm:ss" | "Still frame" | same |
| FRAMES | `frames` | count | 1 | count |
| CLIP SIZE | `clipSize` | sum of the files in the folder, recursive, "1.2 GB" (base 1024) | file size | folder or file size |
| PATH | `path` | full path, in a box (radius 18, `#151515` split / `#181818` overlay), wraps anywhere, 13 px | same | same |

  Refs, all CONFIRMED: `src/playbackcontroller.cpp:1149-1205`, `:121-164`, `:245-259`. The "16-bit" note follows from `src/dngdecoder.cpp:1065-1074` (`bitsPerSample = 16` after the linearization table).
- Missing values show "Unavailable" ("0" for FRAMES) (CONFIRMED `qml/ClipPlayerPage.qml:109-112`).
- The overlay (stacked and compact):
  - Scrim `#cc000000`, z 18; tapping it closes the overlay.
  - Card 448 wide, radius 26.
  - Grid columns 188 wide, row spacing 10, column spacing 20.
  - A "Close" button, 132x52, centred.
  - Opening the delete dialog closes the info overlay (`:130-133`).

**Remove confirmation** (CONFIRMED `:2055-2270`): 392x300 (340x218 compact).

- Title "Remove Clip?".
- Text "This will permanently delete the current clip from media.".
- A box with the clip name and "This action cannot be undone.".
- Buttons "Cancel" (150x54) and "Remove Clip" (182x54, red).
- Confirm: close the dialog, `stop()`, `deleteRequested()`, which runs `Main.removeSelectedClip()`. If the deletion fails, nothing is shown in the player. The error is only in the browser's status line (PROBABLE: `Main.qml:450-452` returns quietly; `clipModel.statusText` is shown only by the browser).

### 3.3 Animations and transitions

- **Clip change (prev/next):**
  - Content slides in from x = ±44. Opacity 0→1 over 260 ms. Scale 0.985→1 over 320 ms. x→0 over 320 ms. All OutCubic.
  - Prev/next are disabled while this runs.
  - CONFIRMED `:114-119`, `:125-128`, `:1658-1694`.
- `beginClipTransition()` (`:182-209`) is **dead code**. It refers to `outgoingClipContent` and `clipTransitionAnim`, which do not exist. No code calls it. It was already dead in the first upload. CONFIRMED (grep at `d8098d0`; `git show ac2b412:qml/ClipPlayerPage.qml:104-130`).
- Buttons: press scale and colour animations (140–150 ms). Dialogs: opacity 220 ms and scale 0.96→1 over 240 ms. CONFIRMED.

### 3.4 Player states

| State | Behaviour | Ref |
| --- | --- | --- |
| Just opened | Paused on frame 0. Badge "PAUSED". Histogram computed. Neighbouring frames prefetched (`warmPlaybackFrames`: the next 8 frames at 75 % size) | CONFIRMED `src/playbackcontroller.cpp:714-747`, `qml/ClipPlayerPage.qml:157-166` |
| Playing | Uses the fast source (`image://cdngplay`, 75 % size, cached and prefetched) for cDNG, or the video provider for movies. Audio runs if there is a WAV | CONFIRMED `qml/ClipPlayerPage.qml:393-411` |
| Pause | Goes back to the full-size uncached `image://cdng/frame?...&token=` (a full decode) for cDNG, so the paused frame is sharper. Histogram updated | CONFIRMED `:399-411`, `src/playbackcontroller.cpp:485-495` |
| End of clip | Wraps to frame 0 and keeps playing (cDNG `% frameCount`; video wraps its clock and restarts the audio) | CONFIRMED `:567`, `:754-766` |
| No frames | Info line shows the status text, e.g. "No DNG frames found in X." Play shows "No frames to play in the selected clip." | CONFIRMED `:532-540`, `:722-728` |
| Decode failure | DNG: a placeholder image with the error text. Video: `decodeFailed` → pause, status "Video playback failed: …", and an error frame drawn into the picture. MLV: e.g. "Could not read MLV pixels; check the recording media." | CONFIRMED `src/cdngimageprovider.cpp:966-975`, `src/playbackcontroller.cpp:424-429`, `src/MlvReader.cpp:48` |
| Still | One frame. Play toggles but nothing moves. FPS chip shows "SINGLE FRAME" | CONFIRMED `src/playbackcontroller.cpp:1195-1200` |

Status strings exist ("Playing X at 25.0 fps.", "Paused X on frame 3 of 250.", "Stopped on frame 1 of N.", "Loaded …"), but the page shows the status text **only when frameCount ≤ 0** (CONFIRMED `qml/ClipPlayerPage.qml:168-174`, `src/playbackcontroller.cpp:1114-1124`).

---

## 4. Engine

### 4.1 `ClipListModel` (`src/cliplistmodel.*`)

- **Root:** `/media/RAW`, hard-coded. It ignores `APERTAR_MEDIA_ROOT`, which `SettingsBridge` honours for LUTs and tuning files. CONFIRMED `src/cliplistmodel.cpp:174`, `src/SettingsBridge.cpp:145`, `:169`.
- **Clip rules** (CONFIRMED `:494-556`):
  - Each non-symlink subfolder except `Photos` is checked.
  - If it holds `*.dng` it is a cDNG clip.
  - If not, and it holds a `.mov`/`.mp4`/`.mlv`, the first one by name is the clip.
  - Otherwise the folder is skipped. So `Audio/`, `LUTs/` and `Tuning-Files/` never appear.
  - Movies directly in the root are listed too.
- What Core writes, so it lands in the browser (all CONFIRMED in `core:`):

| Item | Path | Ref |
| --- | --- | --- |
| cDNG frames | `<clip>/<frames>.dng` | (folder rule above) |
| MLV | `<clip>/<clip>.MLV` | `src/camera/CameraController.cpp:3483` |
| H.264 | `<clip>/<clip>.mp4`, written as `.mp4.writing` while recording | `src/camera/CameraController.cpp:4609-4610` |
| ProRes | `<folder>/<folder>.mov` | `src/prores/ProresRecorder.cpp:59` |
| WAV | `<clip>/<clip>.wav` | `src/audio/AudioRecordingSession.cpp:251` |
| Sound-only recordings | `/media/RAW/Audio/…` (**not shown** in the touch browser) | `src/ApertarCoreApp.cpp:1476` |

- **Cost per refresh:** for every clip, list all of its frames and sort them, open the first frame with libtiff for the date, and call `DngDecoder::detectFrameRate`. Movies use a probe cache keyed on path:size:mtime. All of this runs synchronously on the GUI thread. CONFIRMED `:443-586`, `src/VideoPlayback.cpp:65-90`.
- **`removeClip`:**
  - Canonical path must be under the canonical root. No symlinks. The path must be listed in the model.
  - A folder is removed recursively.
  - In still mode, all files with the same base name are removed.
  - Then a rescan.
  - There is no recording check and no protect flag.
  - CONFIRMED `:382-441`.

### 4.2 `PlaybackController` (`src/playbackcontroller.*`)

- **QML API:**
  - Properties: `currentClipName`, `currentClipPath`, `frameCount`, `currentFrameIndex`, `playing`, `fps`, `currentFramePath`, `frameSource`, `fastFrameSource`, `statusText`, `histogramBins`, `clipMetadata`, `videoClip`.
  - Methods: `loadClip`, `togglePlayback`, `stop`, `nextFrame`, `previousFrame`, `seekToFrame`.
  - CONFIRMED `src/playbackcontroller.h:21-62`.
- **fps:**
  - cDNG: from the first frame's CinemaDNG FrameRate tag `0xC764`, otherwise 24. Clamped to 1–60. A clip shot above 60 fps plays at 60.
  - Movie: from the probe, clamped to 1–1000.
  - CONFIRMED `:715-716`, `:619-636`, `src/dngdecoder.cpp:35`, `:1523-1570`.
  - PROBABLE: speed-ramped takes (the KB's T31/T33, where fps changes during a raw take) play at the first frame's rate only, because no per-frame rate is read.
- **Clock:**
  - cDNG without audio: a `PreciseTimer` at `round(1000/fps)` ms calls `nextFrame()` on each tick, so 23.976 plays at 42 ms ≈ 23.81 fps. A slow decode stretches the playback; nothing is dropped. PROBABLE, from synchronous image loading plus the tick-driven advance.
  - cDNG with audio: the frame index comes from the audio wall clock, so frames are skipped to stay in sync.
  - Movies: the frame index comes from an elapsed-time clock. Decodes in flight are not replaced (`updateVideoFrame` skips while the image is `Loading`), so slow decodes drop frames rather than drift.
  - CONFIRMED `:1094-1098`, `:749-775`, `:827-859`, `qml/ClipPlayerPage.qml:141-151`.
- **Histogram:**
  - DNG: a 48-bin histogram of **raw linear sensor values** (black..white, gamma 0.65 on the counts) on one worker thread, with an LRU cache of 64 frames.
  - Movies and MLV: a 48-bin **display-luma** histogram of the decoded RGB image, at most every 150 ms.
  - So the two scales differ.
  - CONFIRMED `:261-367`, `:410-422`, `:1207-1263`.
- **Audio** (CONFIRMED `:861-1087`):
  - Search order: for movies, `<movie base>.wav`. Then `<clipdir>/<dirname>.wav`, then `audio.wav`, then any `*.wav`, by name.
  - Accepted WAV: RIFF or RF64, PCM 16/24/32-bit or float 32-bit.
  - Playback: the PCM is fed through `aplay -q -D <device> -f … -c … -r … -t raw` from a 12 ms feed timer.
  - Device: `settingsBridge.audioOutputDevice`; `hw:` is rewritten to `plughw:`, and the fallback is "default".
  - Every seek while playing restarts `aplay`. Each stop can wait up to 300 ms on the GUI thread.
  - There is no volume, mute or audio indicator in the UI.
  - MLV-embedded audio is not read (the reader ignores AUDF/WAVI; CONFIRMED `src/MlvReader.cpp:197-212` handles only RAWI/WBAL/IDNT/EXPO/DEBG).

### 4.3 Image providers

All CONFIRMED (`src/main.cpp:352-363`, `src/cdngimageprovider.cpp:845-1090`, `src/VideoPlayback.cpp:100-187`).

| Id | Used for | Threading | Cache | Prefetch | Size |
| --- | --- | --- | --- | --- | --- |
| `cdng` | Paused cDNG frame | **synchronous on the GUI thread** (no async flag, and `Image.asynchronous` = `videoClip` = false) | none | no | full preview size |
| `cdngthumb` | Browser thumbnails (DNG and stills) | forced async | 96 images / 24 MB | no | 90 % of the box |
| `cdngplay` | Playing cDNG frames | **synchronous** for the frame asked for; prefetch on 2 worker threads | 32 images / 32 MB, LRU | the next 8 frames, re-armed when within 8 of the frontier | 75 % of the box |
| `video` | Movie and MLV frames | forced async; one decoder kept open per path | none | no | ≤ 1280x1280 |
| `videothumb` | Movie and MLV thumbnails | forced async; decoder closed after every thumbnail | none | no | ≤ 480x480 |

"Synchronous on the GUI thread" is PROBABLE. It follows from the Qt rule that a provider without `ForceAsynchronousImageLoading` runs in the GUI thread when the `Image` is not asynchronous (`qml/ClipPlayerPage.qml:386`).

The thumbnail and play providers are named "previewOnly", but they still **decode the full raw frame** and only fall back to an embedded preview when the raw decode fails (CONFIRMED `src/cdngimageprovider.cpp:733-743`). Core writes no preview IFD: one IFD with NewSubFileType = full resolution (CONFIRMED `core:src/cdng/CdngEncoder.cpp:1529`; no SubIFD found by grep). So every thumbnail is a full raw decode.

### 4.4 Decoding per format

| Format | Path | Notes | Label |
| --- | --- | --- | --- |
| cDNG uncompressed | `DngDecoder::decodeFileInto`, own TIFF parser plus libtiff | full frame into a `QVector<quint16>` | CONFIRMED `src/dngdecoder.cpp:940-1078` |
| cDNG lossless (LJ92, compression 7, tiled) | `third_party/liblj92` | Core writes 7 = lossless, 1 = uncompressed | CONFIRMED `src/dngdecoder.cpp:16`, `:50-64`, `:1005`; `core:src/cdng/CdngEncoder.cpp:1365` |
| Apertar "lossy" DNG | Same LJ92 path. Core quantises in a companded domain, writes SOF3 and stores the inverse in `LinearizationTable`. The UI applies the table, then sets 16-bit | | CONFIRMED `core:src/lossydng/LossyDngEncoder.hpp:12-13`, `core:src/lossydng/LossyDngEncoder.cpp:509`, `src/dngdecoder.cpp:1065-1074` |
| Standard lossy DNG (compression 34892) | Rejected by the decoder. Then `loadTopLevelPreview` is tried | PROBABLE: libtiff can't read 34892, so it fails; Core does not write it | CONFIRMED rejection `src/dngdecoder.cpp:1005-1006` |
| Mono (Photometric LinearRaw) | Grey, sRGB curve, no white balance or matrix | | CONFIRMED `src/dngdecoder.cpp:957`, `src/cdngimageprovider.cpp:630-638` |
| MLV | `MlvReader`: one file, uncompressed, finalized | Rejects split files (`.M00`), compressed MLV, frame count 0 (still recording) and geometry changes mid-clip. Reads per-frame WBAL and the APCM preview matrix. Reads 4-row windows from disk, which survives a pulled card | CONFIRMED `src/MlvReader.cpp:153-278` |
| ProRes / H.264 (MOV/MP4) | `apertar-video-libav.so`, loaded with `QLibrary`, C ABI v2 | Rejects other codecs. ProRes skips packets on seek; H.264 seeks back if the jump is more than 120 frames. Uses 4 threads and `lowres` = min(max_lowres, 1). Output through swscale `FAST_BILINEAR` to BGRA, ≤ 1920 px | CONFIRMED `src/VideoPlaybackLibav.cpp:46-217`. PROBABLE: lowres stays 0 for these codecs (FFmpeg does not give them lowres) |
| JPEG / PNG / TIFF stills | `QImageReader` / libtiff RGBA | | CONFIRMED `src/cdngimageprovider.cpp:52-70`, `src/playbackcontroller.cpp:166-220` |
| WAV | `aplay` (above) | | CONFIRMED |

The debayer is quad binning: each 2x2 CFA cell becomes one RGB sample, at half resolution, followed by bilinear interpolation between cells. CONFIRMED `src/cdngimageprovider.cpp:477-533`.

### 4.5 Speed

There are no timings in the repo, the KB or the git log. Real playback fps for 4K cDNG on a Pi 5 is UNCONFIRMED. What the code implies (PROBABLE):

- cDNG playback speed is bound by reading the whole DNG, a full unpack and LJ92 decode, and a CPU render per frame.
- Two prefetch threads plus the GUI thread do this work.
- Pausing a cDNG frame costs one full-size synchronous decode on the GUI thread.
- Movies are bound by libav decode plus the swscale BGRA conversion, ≤ 1280 px.

---

## 5. Colour

- **cDNG** (CONFIRMED `src/cdngimageprovider.cpp:380-475`, `:577-698`):
  1. Camera to XYZ D50. Uses the ForwardMatrix, blended FM1/FM2 by a heuristic on the blue/red neutral ratio. If there is none, the inverted ColorMatrix.
  2. Bradford D50 → D65, then XYZ → sRGB.
  3. White balance from AsShotNeutral (× AnalogBalance), normalised to green. With no neutral, fixed "daylight" gains 2.8 / 1 / 1.6.
  4. Reinhard `x/(1+x)` per channel.
  5. Saturation × 1.35, fading out in the highlights.
  6. Highlights roll to white above 0.93 of sensor level.
  7. Pure gamma 1/2.2 (not the sRGB curve).
  8. A fixed look, with no exposure or ISO-based rendering.
- **MLV** (CONFIRMED `src/MlvReader.cpp:140-151`, `:256-278`; `src/cdngimageprovider.cpp:655-663`):
  - When the file carries Apertar's APCM DEBG preview matrix (or an older Apertar IDNT), the "ISP" path is used: clip the balanced channels × a common gain (digital gain ÷ the smallest WB gain), apply the CCM, then the sRGB OETF. No tone curve and no saturation boost.
  - So the same scene in MLV and cDNG can look different. PROBABLE, from the two code paths.
- **Movies:** YUV → RGB with a BT.709 matrix (BT.601 for 470BG/170M, BT.2020 for 2020-NCL). The range is honoured. No transfer-function conversion. CONFIRMED `src/VideoPlaybackLibav.cpp:190-210`.
  - Core offers ProRes colour profiles `arri_logc4`, `sony_slog3`, `davinci_intermediate`, `p3_d60_linear` and `standard` (CONFIRMED `core:include/apertar/core/ProresColorProfile.hpp:7-18`). Log clips play **flat** (PROBABLE).
- **Not used:** monitoring LUTs (`/media/RAW/LUTs`), Core's `cdng_preview_color_profile` (CONFIRMED `core:src/ApertarCoreApp.cpp:210`), false colour, zebra and peaking. Grep of the playback QML and C++ found no LUT or monitoring-aid references; the "lut" hits were "resolution" and "absolute". CONFIRMED.

---

## 6. HDMI / external monitor during playback

- **In-process monitor window** (`ExternalMonitorManager`): `mainUiAllowsExternalMonitor()` is true only when `currentPage == "camera"` or `hdmi_external_only`. So the HDMI window is **hidden** while the browser or player is up. CONFIRMED `src/ExternalMonitorManager.cpp:111-126`, used at `:169`, page change hooked at `:74`.
- **Monitor-only process:** the main window publishes `cameraPageActive = (currentPage == "camera")`. The monitor window hides when it is false. CONFIRMED `src/ExternalMonitorRuntimeBridge.cpp:136-137`, `src/main.cpp:202-209`.
- **`hdmi_external_only`:** the main UI window is never shown, so the touch browser and player are unreachable. CONFIRMED `src/main.cpp:430-431`.
- **Result:** playback never reaches HDMI. What the HDMI output shows meanwhile (black, or the last frame) is UNCONFIRMED.

## 7. Recording interplay (what is and is not blocked)

| Path | During recording | Ref |
| --- | --- | --- |
| On-screen folder button | Disabled (opacity 0.42) | CONFIRMED `qml/CameraPage.qml:3754`, `qml/ClipBrowserButton.qml:26` |
| Hardware `clip_browser` | **Not blocked**, in either Core or the UI | CONFIRMED `core:src/ApertarCoreApp.cpp:9142-9144`, `qml/Main.qml:319-322` |
| Recording starts (GPIO, WebUI) while the browser or player is open | Nothing reacts. No state shows recording; the page stays up | CONFIRMED: no `recording` use in either page. `Main.qml` uses `cameraPage.recording` only for auto-power-off (`:248`, `:375`, `:511-516`) |
| Delete in the browser or player | **Not blocked.** A clip being recorded can be deleted | CONFIRMED `src/cliplistmodel.cpp:382-441` (no check). The outcome for the writer is UNCONFIRMED |
| Clip being written | cDNG: listed with its frames so far. H.264: not listed (`.mp4.writing`). MLV: listed, but the probe fails ("not finalized"), so it shows as "VIDEO" / "Video clip" | PROBABLE, from §4.1 rules and `src/MlvReader.cpp:176-177` |
| Refresh while recording | The watcher keeps restarting its 150 ms timer while files change. The rescan runs about 150 ms after writes stop | PROBABLE (`QTimer::start` restarts a single-shot timer; `:176-189`) |
| Core WebUI media delete | Blocked: "Stop recording before deleting media." | CONFIRMED `core:src/ApertarCoreApp.cpp:7660-7666` |

## 8. Deletion and protection

- **Multi-delete in the browser** (long press → Remove Selected → confirm). **Single delete in the player** (Remove → confirm, then the next clip opens).
- Path safety:
  - The canonical path must be under the canonical root.
  - No symlinks, either for the target or for still siblings.
  - The path must be in the current list.
  - CONFIRMED `src/cliplistmodel.cpp:389-425`.
- Missing features: no protect, lock, star, rating, rename, undo or trash. There is no download or copy in the touch UI (the WebUI has download; §12). CONFIRMED by a grep for "protect" and "lock" in the pages and the model (no hits).

## 9. Performance limits

All rows PROBABLE (from the code), unless marked.

1. **Scan on the GUI thread.** Every browser open, Refresh or watcher refresh lists every frame of every take and opens two TIFF headers per take. With long takes (thousands of files each) the UI freezes for that time. `src/cliplistmodel.cpp:443-586`.
2. **Thumbnails thrown away on every visit.** The cache is cleared on open and close. Each thumbnail is a full raw decode. CONFIRMED `qml/ClipBrowserPage.qml:71-81`, `qml/Main.qml:587-590`.
3. **Opening a clip.** `updateClipMetadata` decodes the whole first frame and stats every file in the folder, on the GUI thread. CONFIRMED `src/playbackcontroller.cpp:1173-1203`, `:245-259`.
4. **Pause and scrub.** A full-size synchronous decode for each scrub position, on the GUI thread. While playing with audio, each scrub move also restarts `aplay`.
5. **Play.** cDNG is limited to 60 fps (CONFIRMED `:621`). Without audio it slows down rather than dropping frames. The fast path decodes at 75 % size. The cache is 32 frames.
6. **Live preview keeps running** under the player (no pause found).
7. Video output is capped at 1280 px (CONFIRMED `src/VideoPlayback.cpp:155`), thumbnails at 480 px, and the plugin rejects more than 1920 px (CONFIRMED `src/VideoPlaybackLibav.cpp:142`).

## 10. Known bugs, quirks and history

Git history is not useful here. Only two commits touch these files (CONFIRMED `git log`):

- `ac2b412` "Add files via upload" (2026-04-26): the first browser and player.
- `8847105` "Updated to version 1.6.0" (2026-10-23): +4405/−511. It added `MlvReader`, `VideoPlayback*`, `RawPreview.hpp`, audio and most of the current QML.

There are no bug-fix commits. The later commits (`2d27c46` … `d8098d0`) are camera-page work. So the list below comes from reading the code.

| # | Quirk | Label |
| --- | --- | --- |
| 1 | `beginClipTransition` refers to items that do not exist (dead code since the first upload) | CONFIRMED `qml/ClipPlayerPage.qml:182-209` |
| 2 | `clipCellHeight` and `clipThumbnailHeight` are unused | CONFIRMED |
| 3 | The "Scanning..." state cannot paint (the scan is synchronous) | PROBABLE |
| 4 | "N ITEMS" is not pluralised ("1 ITEMS"). The delete dialog says "Clips" in still mode | CONFIRMED `:545`, `:878` |
| 5 | BIT DEPTH shows "16-bit" for lossy and Clear HDR 12-bit DNG (after the linearization table) | PROBABLE (`src/dngdecoder.cpp:1073`) |
| 6 | FRAME RATE and DURATION use the first frame only (speed-ramped takes) | PROBABLE |
| 7 | The capture-mode toggle in the browser changes the **camera's** photo/video mode | CONFIRMED `qml/ClipBrowserPage.qml:115-119` |
| 8 | Player status strings are invisible unless the clip has no frames | CONFIRMED `:168-174` |
| 9 | Deleting or opening during recording is allowed through hardware or the player | CONFIRMED |
| 10 | Back in the player resets to frame 0. Returning to the browser rescans and scrolls to the top | CONFIRMED / PROBABLE |
| 11 | DNG histogram (raw linear) and movie histogram (display luma) use different scales | CONFIRMED |
| 12 | The media root is fixed to `/media/RAW` (no `APERTAR_MEDIA_ROOT`) | CONFIRMED |
| 13 | `previousFrame` / `nextFrame` and `setFps` (an fps override) are exposed but unused | CONFIRMED |
| 14 | 23.976 fps plays at 1000/42 ≈ 23.81 fps when there is no audio (integer-ms timer) | PROBABLE |

## 11. What it lacks compared with a browser player

The point of reference is a typical HTML5 player and Cinemate's Playback pane at `cm:d6cc93e`. All rows are CONFIRMED absent in the touch UI unless noted.

- **Frame stepping** (±1 frame) and a frame or timecode readout. Only "FRAME i / N" is shown, with no TC and no duration position.
- **Speed control** (0.5×/2×, playing at the recorded vs a chosen rate), a loop toggle, play-once, and in/out points.
- **Audio:** volume, mute, a has-audio indicator, a waveform, and MLV-embedded audio.
- **Fullscreen**, zoom/pan at 1:1 for focus checking, keyboard shortcuts, and swipe between clips.
- **Monitoring:** LUT, log-to-Rec.709 view, false colour, zebra, peaking, and anamorphic desqueeze. MOV pixel aspect is honoured for movies only (`src/VideoPlayback.cpp:156`).
- **Per-card data:** resolution, fps, bit depth or compression, size, has-WAV, and dropped frames. Cinemate shows has_wav, dropped_frames (gaps in the frame index), mode label, sensor and frame source per take (CONFIRMED `cm:src/module/app/playback.py:137-191`).
- **Library tools:** download, multi-select-all, search and filter by format, and the Audio and Timelapse categories.
- **Robustness patterns Cinemate has:**
  - A bounded decode slot pool that answers Busy/503, so the client drops frames instead of lagging (CONFIRMED `cm:src/module/app/playback.py:257-299`).
  - A render-token cache-buster (`:37-56`).
  - Serving the embedded thumbnail rather than a raw decode (`:239-254`).
- **Recording safety:** pages that react to recording, and delete blocked while recording.

## 12. What could serve a WebUI player

### 12.1 Reusable as-is: the design and the wording

- All tokens in §2–§3 (colours, radii, sizes, fonts, animations) and all strings can be copied verbatim. The WebUI already uses the same words in places: "Clip Browser", "Refresh Media", "Newest First" / "Oldest First", "Back" (CONFIRMED `core:src/web/WebControlPage.cpp:3988`, `:4008-4013`, `:3993-3994`).
- Icons are white-on-transparent PNGs in `qml/icons/`:
  - `film`, `refresh`, `delete`, `info`, `previous`, `next` (28x28)
  - `play` (26x30), `pause` (20x30)
  - `folder`

  The WebUI already serves icons from `/icons/` (e.g. `/icons/folder.png`, CONFIRMED `core:src/web/WebControlPage.cpp:3985`). Whether the same files are already there is UNCONFIRMED.
- Suggested HTML outline (PROBABLE mapping, one element per QML region):

```
.pb-page
  .pb-title > .pb-eyebrow("PLAYBACK") + h1("Clip Browser"|"Still Browser"|"Clip Viewer")
  .pb-topbar > button.refresh, button.capture-mode(2 lines), button.back
  .pb-sheet
     browser: .pb-sheet-head(icon+CLIPS) .chips(sort, count | remove-selected, count) .pb-status
              .pb-grid > .pb-card(.thumb(img, .duration-pill, .select-badge), .name, .format, .date)
     player:  .preview(img|canvas, .badge.fps, .badge.state, .badge.frame) .title-row(.name,.info,button.info)
              .scrub(.rail,.fill,.handle) .controls(button.remove, .transport(prev,play,next), .histogram(canvas))
              .meta-panel | dialog.meta
  dialog.confirm (scrim rgba(0,0,0,.8), card #151515 r26)
```

- Breakpoints: map the browser viewport to the five layouts (§2.1). The WebUI user is usually on a phone, laptop or tablet, so the split landscape player suits a desktop and stacked suits a phone (PROBABLE design choice; Patrik to decide).

### 12.2 Logic portable to Core or the browser (rules, not code)

The rules below are PROBABLE portable, because each is plain parsing or ordering logic:

- Clip discovery rules (§4.1).
- The shot-date fallback order.
- Duration formatting.
- The still-pair dedupe.
- The delete safety rules.
- WAV discovery order and parsing (RIFF/RF64, PCM/float).
- MLV block parsing (RAWI/WBAL/DEBG-APCM/IDNT/EXPO/VIDF, the 4-row reader).
- The metadata field set and value formats.

Core already has its own media classifier and library. It is a **second, separate implementation** from the UI's `ClipListModel`:

- Its JSON covers kind, category, type, name, size, file count, frame count, duration, fps, modified time and download URL (CONFIRMED `core:src/ApertarCoreApp.cpp:5609-5626`, `:5807-5836`, `:6422-6580`, `:7819-7832`).
- Routes: `GET /api/media`, `/api/media/download`, `/api/media/download-selected`, `POST /api/media/delete`, `/api/media/delete-selected` (CONFIRMED `core:src/ApertarCoreApp.cpp:7307`, `:7343`, `:7464`, `:7649`, `:7721`).

Do the two implementations agree on clip, still and audio categories? UNCONFIRMED; the Core reader should compare them.

### 12.3 Code that could be shared

- `src/VideoPlaybackLibav.cpp` + `src/VideoPlaybackApi.h`:
  - Pure C++ with libav and a C ABI. No Qt (CONFIRMED by its includes, `:1-13`).
  - Core already links libavcodec, libavformat and libavutil for its encoders, but not libswscale (CONFIRMED `core:CMakeLists.txt:45`, `:62`). Reuse needs libswscale, or another way to scale.
  - Note that a browser can play H.264 MP4 natively, and ProRes usually not (PROBABLE). So for H.264 a WebUI could stream the file itself, and for ProRes it needs server-side frames.
- **Qt-bound code** (needs a rewrite or a Qt dependency in Core; Core has no Qt, CONFIRMED `core:CMakeLists.txt:25-31` versus `CMakeLists.txt:10`):
  - `dngdecoder.cpp` (1574 lines, Qt + libtiff)
  - `cdngimageprovider.cpp` renderer (QImage/QPainter)
  - `MlvReader` (QFile/QImage)
  - `playbackcontroller` (QObject/QProcess)
- Core's existing pieces a WebUI player could build on (Core reader to detail):
  - turbojpeg for JPEG output and the MJPEG endpoint `/preview.mjpeg` (CONFIRMED `core:CMakeLists.txt:30-31`, `:120-123`; `core:src/ApertarCoreApp.cpp:7255`)
  - The DNG writer knowledge in `src/cdng/*` (tag layout, LJ92)
- The touch UI has **no HTTP server** and no command for "render frame N". The current architecture offers no way for the browser to obtain frames from the UI process (PROBABLE: no such command found in `ApertarControlBridge`; not exhaustively checked).

### 12.4 Gaps a WebUI version would have to settle (options for Patrik)

1. Should the web "Capture: Clip/Still Mode" button switch the camera mode as the touch UI does (§10 #7), or only filter the list?
2. Should playback be blocked during recording? The touch UI does not block it. The WebUI's delete does.
3. Frame source: a full raw decode per frame (touch UI), or a lighter proxy (Cinemate thumbnail or quarter-res)? This is speed versus fidelity.
4. Colour: copy the touch UI's fixed look, or use Core's `cdng_preview_color_profile` and LUTs?
5. Should the web show the extra per-card data the touch UI lacks (resolution, fps, has-audio, dropped frames)?

---

## Appendix A. Colour sheet (QML → CSS)

| QML | CSS | Use |
| --- | --- | --- |
| `#000000` | `#000` | page |
| `#151515` | `#151515` | sheet, dialogs, path box (split) |
| `#181818` | `#181818` | card, summary box, side panel |
| `#171717` | `#171717` | thumbnail / preview background, sort chip |
| `#1d1d1d` / `#202020` | same | last-opened card / thumbnail |
| `#241c1f` / `#2a1d1d` | same | selected card / thumbnail |
| `#14ffffff` | `rgba(255,255,255,.078)` | ghost button, count chip, histogram card |
| `#20ffffff` | `rgba(255,255,255,.125)` | ghost pressed |
| `#1affffff` | `rgba(255,255,255,.10)` | 1 px borders |
| `#16ffffff` | `rgba(255,255,255,.086)` | thumbnail border |
| `#22ffffff` | `rgba(255,255,255,.133)` | pill / badge border |
| `#33ffffff` | `rgba(255,255,255,.20)` | last-opened card border |
| `#66ffffff` | `rgba(255,255,255,.40)` | "PLAYBACK" eyebrow, metadata labels |
| `#ccffffff` | `rgba(255,255,255,.80)` | "HISTOGRAM" label |
| `#66000000` | `rgba(0,0,0,.40)` | badges, duration pill |
| `#55000000` | `rgba(0,0,0,.333)` | unselected badge |
| `#12000000` / `#25101010` | `rgba(0,0,0,.07)` / `rgba(16,16,16,.145)` | thumbnail tint |
| `#cc000000` | `rgba(0,0,0,.80)` | dialog scrim |
| `#8d2020` / `#a32828` / `#ba4a4a` | same | danger fill / pressed / border |
| `#2a1717` / `#4a2a2a` | same | dialog icon disc / border |
| `#3fd0ff` / `#79ddff` / `#1f2c36` / `#22323c` | same | accent border / text / fill / pressed |
| `#8f9096` / `#6f7076` / `#5f6066` / `#72737a` / `#8a8a8f` | same | secondary / tertiary / date / NO PREVIEW / disabled text |
| `#1e1f23` / `#d7d9de` / `#f4f5f7` / `#131417` | same | scrub rail / fill / handle / handle border |

Source: `qml/ClipBrowserPage.qml` and `qml/ClipPlayerPage.qml` at the lines cited above (CONFIRMED). The QML → CSS conversion uses Qt's `#AARRGGBB` convention.

## Appendix B. Every user-visible string

**Browser** (CONFIRMED, `qml/ClipBrowserPage.qml`):

- Titles and buttons: "PLAYBACK", "Clip Browser" / "Still Browser", "Capture", "Clip Mode" / "Still Mode", "Refresh Media" / "Scanning...", "←", "Back" / "Cancel".
- Sheet: "CLIPS" / "STILLS" / "SELECTION", "Remove Selected", "Newest First" / "Oldest First", "N items" / "N selected".
- Hints and cards: "Long press starts selection. Tap clips to add or remove them." (stills variant), "NO PREVIEW", "Shot date unavailable".
- Dialog: "Remove Selected Clips?", "This will permanently delete the selected clips from media.", "N clip(s) selected", "+N more", "This action cannot be undone.", "Cancel", "Remove Clips".

**Model** (CONFIRMED, `src/cliplistmodel.cpp`):

- Status: "%1 is not available.", "No still files found in %1/Photos.", "No cDNG, ProRes, H.264 or MLV clips found in %1.", "Found %1 still(s) in %2/Photos.", "Found %1 clip(s) in %2.".
- Deletion: "Removed %1.", "Failed to remove %1.", "Only listed media inside the recording folder can be deleted.", "Unsafe media deletion target.", "Clip folder is not available: %1", "Item is not available: %1", "No clip path provided.".
- Labels: "cDNG clip", "%1 clip", "Video clip", "VIDEO", "DNG STILL" / "JPEG STILL" / "PNG STILL" / "TIFF STILL".

**Player** (CONFIRMED, `qml/ClipPlayerPage.qml`):

- Page: "PLAYBACK", "Clip Viewer", "Back".
- Badges and info line: "… FPS", "PLAYING" / "PAUSED", "FRAME i / N", "FRAME 0 / 0", "`<type>` • N frames" / "frame".
- Controls: "Info", "HISTOGRAM", "Remove".
- Metadata: "Clip Metadata", "CAPTURED", "TYPE", "RESOLUTION", "BIT DEPTH", "FRAME RATE", "DURATION", "FRAMES", "CLIP SIZE", "PATH", "Unavailable", "Close".
- Dialog: "Remove Clip?", "This will permanently delete the current clip from media.", "This action cannot be undone.", "Cancel", "Remove Clip".

**Controller** (CONFIRMED, `src/playbackcontroller.cpp`):

- Status: "Select a clip to preview.", "Loaded %1 %2.", "Loaded still %1.", "Loaded %1 with %2 frame(s) at %3 fps.", "Loaded %1 with %2 frame(s). Using %3 fps fallback.", "No DNG frames found in %1.", "Still file is not available: %1", "Clip folder is not available: %1", "Playing %1 at %2 fps.", "Paused %1 on frame %2 of %3.", "Stopped on frame 1 of %1.", "No frames to play in the selected clip.", "Video playback failed: %1".
- Metadata values: "cDNG sequence", "DNG still" / "JPEG still" / "PNG still" / "TIFF still", "Single frame", "Still frame", "8-bit RGB", "N-bit", "N-bit YUV" / "N-bit RAW".

**Placeholders** (CONFIRMED, `src/cdngimageprovider.cpp:961-973`, `src/VideoPlayback.cpp:35`, `:181`): "Select a clip from /media/RAW", "No frame path provided", "Decode failed: %1", "Could not render %1", "Video playback decoder unavailable. Build apertar-video-libav (libswscale-dev required).", "Could not decode video".
