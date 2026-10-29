// node playclock_test.js  -> "page ok (N checks)"
"use strict";
const P = require("./playclock.js");
let checks = 0, failures = 0;
function check(ok, what) { ++checks; console.log((ok ? "  ok   " : "  FAIL ") + what); if (!ok) ++failures; }

// The take of v2_test "frames": numbers 0 1 2 . . 5 6 . 8(0 B) 9 at 25 fps, with a WAV.
const clip = { first_number: 0, last_number: 9, frame_count: 7, fps: 25, has_audio: true,
               holes: [[8, 1], [3, 2], [7, 1]] };
const tl = P.clipTimeline(clip);
check(JSON.stringify(tl.holes) === "[[3,2],[7,2]]", "holes sorted; the missing 7 and the 0-byte 8 join into one");
check(P.numberAtTime(tl, 0) === 0 && P.numberAtTime(tl, 0.2) === 5 && P.numberAtTime(tl, 5) === 9, "clock -> number, clamped at the last");
check(P.shownNumber(tl, 3) === 2 && P.shownNumber(tl, 4) === 2 && P.shownNumber(tl, 5) === 5, "over the hole 3-4 number 2 stays up");
check(P.shownNumber(tl, 7) === 6 && P.shownNumber(tl, 8) === 6 && P.shownNumber(tl, 9) === 9, "over 7 (missing) and 8 (0 B): number 6");
check(Math.abs(P.durationSeconds(tl) - 0.4) < 1e-9 && tl.sound, "duration = span 10 / 25 fps; sound on");

// A T31 ramp take: every frame tagged 25 fps, numbered by count, WAV in real time (KB ramp-answer.md:92).
const ramp = P.clipTimeline({ first_number: 0, last_number: 749, frame_count: 750, fps: 25, has_audio: true, holes: [],
                              ramp: { base_fps: 25, max_fps: 50, events: [[250, 50]] } });
check(ramp.fps === 25 && !ramp.sound && Math.abs(P.durationSeconds(ramp) - 30) < 1e-9,
      "ramp take: plays as its 25 fps timeline (30 s), sound off");

check(P.lookAheadSeconds(tl, 30) === 0.03 && P.lookAheadSeconds(tl, 900) === 0.08, "look-ahead = round trip, capped at 2 frames");

const lane = {};
check(P.laneAfter(lane, "busy", tl) === 40 && P.laneAfter(lane, "neterr", tl) === 40, "503 or a closed connection: skip, wait one frame");
check(P.laneAfter(lane, "busy", tl) === 500 && lane.skipped === 3, "third failure in a row: back off 500 ms");
check(P.laneAfter(lane, "ok", tl) === 0 && lane.errors === 0, "a decoded frame resets the lane");
check(P.laneAfter(lane, "hold", tl) === Infinity, "409: the lane stops (the hold card shows)");

const clock = P.makeAudioClock();
check(clock(1.0, 1000, true) === 1.0 && Math.abs(clock(1.0, 1040, true) - 1.04) < 1e-9 && clock(1.05, 1050, true) === 1.05,
      "audio clock interpolates between coarse currentTime steps and resyncs");

const s = { wasPlayingBeforeScrub: true };
check(P.scrubEnd(s) === true && P.scrubEnd(s) === false, "scrub ends: play on if it was playing, once");

check(P.keepAwakeIntervalMs(30) === 10000 && P.keepAwakeIntervalMs(600) === 20000 && P.keepAwakeIntervalMs(0) === 0,
      "keep-awake every min(20 s, timeout / 3); none with standby off");

check(P.middleElide("cDNG_26-10-28_C0007", 13) === "cDNG_26…C0007" && P.middleElide("short", 13) === "short",
      "card names keep the clip counter: cDNG_26…C0007");
check(!/resumes/.test(Object.values(P.HOLD_TEXT).map(v => v[1]).join(" ")), "no hold text promises a resume");

console.log(failures ? "PAGE FAILURES " + failures : "page ok (" + checks + " checks)");
process.exit(failures ? 1 : 0);
