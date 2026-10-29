# Playback: where it stands (2026-10-29) and where to pick up

For the next session. Read `decisions.md` first (Patrik's answers), then `measurements.md` (what ran), then this.

## Built, tested on the Pi (Core on `cinemate-port`, local; nothing of T47-T51 is on GitHub yet)

| Step | Core commits | What | Tested |
| --- | --- | --- | --- |
| T47 | `bc5d29d`, `ee246ff` | `src/playback/{PlaybackHold,ClipFrames,DngTags,ClipProbe}.hpp`; `/api/media` from a facts cache keyed on the folder mtime (4.2 s once, then 20 ms; was 6.8 s every call); each clip's own fps, span, holes, `timecode_start`; `/api/media/clip`; `playback_hold` in `/api/state`; the yield window in `handleCommand` and the media watcher | host 41 + 24 checks; live |
| T48 | `8d6aae9` | `GET /api/media/frame` by frame number, liblj92 in `third_party/`, `DngFrameReader`, `RawRender`, `DecodeSlots`, `PlaybackFrames`; 2 slots, JPEG caches 8 + 24 MB | host 14 checks; live, pictures looked at |
| T49 | `26742ce`, `3042652` | the Clip Browser (`#playbackOverlay`), cards with a full-bleed thumbnail, DROP N, recorded timecode, long-press selection, Remove/Download Selected | headless Chrome on the real Core; Patrik tried it |
| T50 | `6ffe564`, `e69dc24` | the Clip Viewer (frame-number clock, black holes R2, scrub, step O1, honest rate O4, histogram, metadata, hold card); downloads and deletes yield to a take (Q21, Q23) | Chrome; live take (download stopped within 0.3 s); Patrik: works well; Q23 not tested live |
| T51 | `0c9d194`, `727c9c8` | `GET /api/media/file` (WAV with Range), the `<audio>` as the clock, look-ahead = round trip | Range/416/names live; Chrome playback with sound; Patrik to listen in his browser |

Also done in the same session (not playback): the Mode Ladder WebUI (`cbeeb9d`..`a9abd76`, pushed), the UI timecode / file timecode split
(`2f4f0f6`, UI `92125a7`, **not pushed**), fork-log rows for all of it.

## Open, in the order Patrik would want them

1. **Push** (only when Patrik asks): Core `cinemate-port` from `7678cbf` to `727c9c8` (11 commits), UI `92125a7`, KB. Route: Pi -> Mac clone
   (`git fetch pi cinemate-port`, ff-only) -> `git push origin cinemate-port`; the Pi has no GitHub access.
2. Sound works in Patrik's browser (he did not say which); still untested: a phone (iPhone or Android? Q10), Safari, Firefox, Bluetooth latency (M6/M12 skipped).
3. T52 MLV frame reader, T53 ProRes and H.264 (Core builds the touch UI's movie decoder as a plugin), W2 (a "Review last take" chip on the main page,
   accepted), O19 (fullscreen, accepted; hidden on iPhone).
4. T54 (touch UI pauses in a take, number clock, span duration): **Patrik has no touch screen** (`decisions.md`, Constraint). Ask whether it stays.
5. Q23 live (record_start refused while a delete runs): needs a delete long enough to race; only the code is checked.
6. Thumbnails for stills, timelapse, MLV, ProRes, H.264, audio: "NO PREVIEW" today.
7. Playback speed of lossless: 9-11 fps (two workers); O11 (a preview track) only if Patrik finds it too choppy (Q1: decide after he has used it).
8. Older open items (not playback): the touch UI for the Mode Ladder (postponed, `working/ramp-ladder/ui-design/DIFFERENCES.md`), "Libcamera
   constants hdr spamming" in the journal, `fsck.exfat` after the power cut, listening to the stretched WAV, the longer 50 fps test.

## How to work on it (what bit us)

- Scratch trees on the Mac: Core `.../scratchpad/rc`, UI `.../scratchpad/ru` (gone with the session; the truth is the Pi's `~/ApertarCore`, `~/ApertarUI`).
  Edit in a scratch tree with asserted replacements, `git format-patch -1`, `scp`, `git am` on the Pi, build on the Pi (`~/build-core.sh`: `cmake --build
  ~/ApertarCore-build -j2`, about 1-2 min for `WebControlPage.cpp`), then Patrik restarts: `ssh -t apertar 'sudo systemctl restart apertar-core'`.
- The build script, `~/hold-test.sh` and `~/dl-test.sh` live in the Pi's home (not `/tmp`: a reboot wipes it; the Pi reboots now and then).
- **Never `pkill -f` over ssh** (it kills the ssh shell), and never wait with `pgrep -f "cmake --build"` inside a `bash -c` (it matches itself).
  Name the patch file exactly in `git am`; a glob can match two patches.
- The page is one C++ raw string: check it with `node --check` on the extracted script, then drive it with `working/tools/playback/webtest/harness.js`
  against the real Core (read-only steps). The harness must pass `X-` headers through (it does since 2026-10-29).
- Host tests, all built on the Pi against Core's own encoder: `working/tools/playback/{t47_test,clip_probe_test,frames_test}.cpp` (build lines at the top).
- Facts about Patrik's card: exFAT, 105,000 files, a readdir costs 3.7 s (so the facts cache keys on the folder mtime alone); PCIe Gen 3, 800 MB/s read.
- Commit author: Patrik's noreply address, `Co-Authored-By: Claude Sonnet 5.5`; a fork-log row for every Core/UI commit; nothing pushed unless asked.
