// Apertar playback, design sketch v2 (not in any repository): the WebUI viewer's clock and request
// rules, without the DOM, so node can test them. T50 types these functions into the page script of
// WebControlPage.cpp (the page has no modules; each becomes a plain function there).
//
// Critic points: M1/P1 the number clock; P2 ramp takes; M12/P16 network errors, 503 back-off and the
// look-ahead cap; P18 scrub resume; m12 audio clock interpolation; m13 keep-awake interval;
// P8 middle elide; P14 hold texts.
"use strict";

// clip: the /api/media/clip reply. first/last are frame NUMBERS; holes = [[number, length], ...]
// are numbers never written AND 0-byte frames (Core lists both; neither has a picture).
function clipTimeline(clip) {
  const ramp = clip.ramp && clip.ramp.events && clip.ramp.events.length > 0 ? clip.ramp : null;
  return {
    first: clip.first_number,
    last: clip.last_number,
    count: clip.frame_count,                     // files, as the touch UI counts (FRAMES, the N)
    holes: mergeHoles(clip.holes || []),
    fps: ramp ? ramp.base_fps : clip.fps,        // a ramp take plays as its timeline (P2)
    sound: !!clip.has_audio && !ramp,            // a ramp take's WAV is real time: sound off (P2, Q30)
    ramp: ramp,
  };
}

// Sorted, with touching holes joined: a 0-byte frame next to a missing number is one hole.
function mergeHoles(holes) {
  const out = [];
  for (const [start, length] of holes.slice().sort((a, b) => a[0] - b[0])) {
    const last = out[out.length - 1];
    if (last && start <= last[0] + last[1]) last[1] = Math.max(last[1], start + length - last[0]);
    else out.push([start, length]);
  }
  return out;
}

// Clock time (s from the first frame) -> timeline number. The WAV starts at frame `first`
// (AudioRecordingSession.cpp:606-626), so this is first + floor(t * fps), clamped.
function numberAtTime(tl, t) {
  if (!(t > 0)) return tl.first;
  return Math.min(tl.last, tl.first + Math.floor(t * tl.fps + 1e-9));
}

// The number whose picture is shown at `n`: n itself, or the last number before its hole.
function shownNumber(tl, n) {
  for (const [start, length] of tl.holes) {
    if (n < start) break;
    if (n < start + length) return start - 1 >= tl.first ? start - 1 : tl.first;
  }
  return n;
}

function durationSeconds(tl) {
  return tl.fps > 0 ? (tl.last - tl.first + 1) / tl.fps : 0;   // the span, also the WAV's length
}

// Ask ahead by the measured round trip, but never more than two frame periods (M12): a browser
// with six connections per host can queue requests and inflate the round trip.
function lookAheadSeconds(tl, roundTripMs) {
  return Math.min(Math.max(0, roundTripMs) / 1000, 2 / tl.fps);
}

// One lane per Core decode slot. A lane's answer decides when it may ask again (ms from now).
// 200: at once. 503 (slot busy) or a rejected fetch (the 33rd connection is closed with no reply,
// WebServer.cpp:271-272): skip that frame, wait one frame period; three in a row: 500 ms (P16, M12).
// 409: the hold stops playback; the poll clears it.
function laneAfter(lane, outcome, tl) {
  if (outcome === "ok") { lane.errors = 0; return 0; }
  if (outcome === "hold") { lane.errors = 0; return Infinity; }
  lane.errors = (lane.errors || 0) + 1;
  lane.skipped = (lane.skipped || 0) + 1;
  return lane.errors >= 3 ? 500 : 1000 / tl.fps;
}

// The audio element's currentTime moves in coarse steps in some browsers (m12): between two
// changes, advance by performance.now(); resync on every change and on seeked.
function makeAudioClock() {
  let lastAudio = -1, lastNow = 0;
  return function clock(audioTime, nowMs, playing) {
    if (audioTime !== lastAudio || !playing) { lastAudio = audioTime; lastNow = nowMs; return audioTime; }
    return audioTime + Math.min(0.25, (nowMs - lastNow) / 1000);
  };
}

// Scrub: pause while dragging, ask 640 w frames; on release ask the paused size and play on if it
// was playing (the touch UI keeps playing after a seek, playbackcontroller.cpp:600-608; P18).
function scrubEnd(state) {
  const resume = state.wasPlayingBeforeScrub === true;
  state.wasPlayingBeforeScrub = false;
  return resume;
}

// Keep the camera awake while a clip plays (F17): every min(20 s, timeout / 3), m13.
function keepAwakeIntervalMs(standbyTimeoutSeconds) {
  if (!(standbyTimeoutSeconds > 0)) return 0;              // standby off: no pings
  return Math.min(20000, Math.floor(standbyTimeoutSeconds * 1000 / 3));
}

// Card names on a phone: keep the counter at the end ("cDNG_26…C0007"), P8. The touch UI's date
// line already elides in the middle (ClipBrowserPage.qml:774).
function middleElide(name, maxChars) {
  if (name.length <= maxChars) return name;
  const tail = (name.match(/_([A-Za-z]?\d+)$/) || [null, name.slice(-5)])[1];
  const headChars = Math.max(1, maxChars - tail.length - 1);
  return name.slice(0, headChars) + "…" + tail;
}

// Hold card texts (§4.8). No promise of a resume that is not built (P14): Core's word is "media".
const HOLD_TEXT = {
  recording: ["Recording", "Recording to media. Press Play when the take ends."],
  writing: ["Writing to media", "Finishing the last take. Press Play when it is done."],
  media_test: ["Media test", "A media speed test is running. Press Play when it ends."],
  standby: ["Standby", "Wake the camera to play clips."],
  media: ["Media not available", "Media was removed. Insert or mount media to play clips."],
};

if (typeof module !== "undefined")
  module.exports = { clipTimeline, numberAtTime, shownNumber, durationSeconds, lookAheadSeconds, laneAfter,
                     makeAudioClock, scrubEnd, keepAwakeIntervalMs, middleElide, HOLD_TEXT };
