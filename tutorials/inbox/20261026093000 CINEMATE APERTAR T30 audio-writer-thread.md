---
datum: 2026-10-26 09:30:00
kontext: CINEMATE
projekt: "#APERTAR"
fritext: T30 audio-writer-thread
typ: digital anteckning
---

# T30. Audio under storage load: a writer thread and a one-second ring, and why the WAV already had the right length

Status: written 2026-10-26 (cloud session; patch `working/patches/0001-audio-writer-thread-and-a-one-second-capture-ring-on.patch`, Core `25397cd`, on top of T29). Line numbers below are at `25397cd`. `AudioRecordingSession.cpp` passes a host syntax check; `TimestampedAudioCapture.cpp` needs `alsa/asoundlib.h` and is not compiled there. Answer: `working/storage-answer.md` §2, `working/cinemate-lessons.md` §3. Builds **M5** (audio) and the clock story from T27.

**You will learn**
- Cinemate's June 2026 audio campaign in six commits: what each failure looked like in a WAV and what fixed it.
- Where Core's capture thread touches the recording medium today and what its 100 ms ALSA buffer can and cannot absorb.
- Why Core's silence padding is the right reconciliation and must stay, and why its whole-take drift figure can mistake sample loss for clock drift.
- How to set ALSA hardware parameters so buffer depth and wake-up period are independent.

**Risk:** Core rebuild and restart; audio only. Undo: `APERTAR_AUDIO_BUFFER_MS=100` restores the old ring; `git checkout` the four files restores the direct write. **Time:** 2 h plus two takes with a clap.

## 1. The problem

Core's reader thread (`src/audio/AudioRecordingSession.cpp:472@f60e301`) does `capture_.read()` → gain → `rawStream_.write()` into `clipFolder/audio_capture.raw` — a file on the recording medium — with a 100 ms ALSA ring (`snd_pcm_set_params(..., 0, 100000)`, `TimestampedAudioCapture.cpp:189-190`). Cinemate measured what happens to such a thread on exFAT under 4K DNG pressure: `write()` blocks for hundreds of milliseconds, the ring overruns, and the samples are gone — 62 s lost from one take by a cheap 16-bit mic, 1.3 s even from a RØDE (`5021ba3`, `ffb61fd`). Core detects the resulting timestamp jump and pads it with silence (`:431-440`), so the WAV keeps its length but carries holes, and `finalizeWav`'s `measured_drift_ppm` (frames / duration over the whole take, `:526-531`) sees fewer frames per second and may "correct" a loss by stretching — the very mistake Cinemate retired with `7398b62`.

## 2. How this part works

```
 before:  ALSA ring (100 ms) --read--> reader thread --gain/meter--> rawStream_.write()  [medium]
 after:   ALSA ring (1 s, 10 ms period) --read--> reader thread --gain/meter--> RAM queue --> writer thread --> rawStream_.write()  [medium]
                                                   |                                                     |
                                                   htimestamp gap > 10 ms -> zeros into the same queue    backlog > 16 MB -> one journal line
```

Why the hardware parameters are set by hand (`TimestampedAudioCapture.cpp:195-218`): `snd_pcm_set_params()` derives the period from the buffer (latency/4), so asking it for a 1 s buffer would wake the reader four times a second — the VU meter and `snd_pcm_htimestamp` granularity would go to 250 ms. With `snd_pcm_hw_params_set_period_time_near(10 ms)` and `set_buffer_time_near(1 s)` the ring is deep and the wake-ups stay at 10 ms. The negotiated sizes are logged: `ApertarCore audio capture: buffer_frames= period_frames= requested_ms=1000/10`.

What does *not* change: the 10 ms discontinuity padding (Cinemate's `6ccfabd`, already in Core), the BOOTTIME stamps, `finalizeWav`, the resampler.

Reading assignments: `AudioRecordingSession.cpp:694-730` (queue + writer), `:359`, `:380-400` (stop ordering), `TimestampedAudioCapture.cpp:155-220`; cinemate-lessons §3.

## 3. Find it yourself

**3.1 Which thread writes the audio file, and where is the file?** (Pi, read-only)

```bash
grep -n 'rawPath_ = \|rawStream_.write\|snd_pcm_set_params' ~/ApertarCore/src/audio/AudioRecordingSession.cpp ~/ApertarCore/src/audio/TimestampedAudioCapture.cpp
```

> [!tip]- Answer
> `rawPath_ = clipFolder_ / "audio_capture.raw"` — on the medium; the writes are in `readerLoop`; the buffer is 100 000 µs. The three facts Cinemate's fixes are about, in one grep.

**3.2 Does your medium stall the audio today?** (Pi, before the patch; Clear HDR 16-bit, a USB mic, 3-minute take, clap at start and end)

```bash
journalctl -u apertar-core -b --no-pager | grep -E 'audio discontinuity|audio clock|audio sync' | tail -5
```

Prediction: on NVMe/ext4 none or one `audio discontinuity: padded_us=`; on exFAT with Clear HDR several. `measured_drift_ppm` — write it down; also record the same mic on an idle 2K take: the two figures should agree within a few ppm if they measure the ALSA crystal.

> [!tip]- Answer
> Every `padded_us` line is a hole Cinemate's writer thread would have avoided. A drift figure that differs between the 2K and the Clear HDR take is not a crystal: it is loss masquerading as drift (`7398b62`: "applying +1797 ppm was itself the source of the late drift").

**3.3 USB topology** (Pi 5)

```bash
lsusb -t
```

> [!tip]- Answer
> Two xHCI root hubs (RP1). Cinemate's Pi 4 fix (`521dc72`) existed because mic and SSD shared one controller; on a Pi 5 you can simply put a USB SSD and the mic on different controllers.

## 4. Make the change

**4.1 Independent buffer and period** — `TimestampedAudioCapture`: `open(..., unsigned bufferUs = 100000, unsigned periodUs = 10000)` (`.hpp`); add `snd_pcm_hw_params_set_buffer_time_near`, `set_period_time_near`, `snd_pcm_hw_params`, `get_buffer_size`, `get_period_size` to `ALSA_FUNCTIONS`; replace `snd_pcm_set_params` with the hand-set sequence and log the negotiated sizes (`TimestampedAudioCapture.cpp:159`, `:195-218`). `#include <iostream>`.

**4.2 The queue and the writer** — `AudioRecordingSession`: members `writerThread_`, `writeMutex_`, `writeCv_`, `writeQueue_`, `queuedWriteBytes_`, `peakQueuedWriteBytes_`, `writerStop_`, `writeFailed_` (`.hpp`); `enqueueWrite()` and `writerLoop()` (`.cpp:694-730`); the reader enqueues blocks and gap zeros instead of writing (`:508`, the gap at `:431-440`); `start()` launches the writer before the reader (`:359`); `stop()` drains it (or lets it discard when `finalize == false`, T28) before closing the stream and logs `peak_backlog_kb` (`:380-400`); `recordCaptureBufferUs()` reads `APERTAR_AUDIO_BUFFER_MS` (`:209`) and `capture_.open` passes it with a 10 ms period (`:252`).

Design points: first failure latches (`failure_`, `writeFailed_`) and the reader stops; `capturedBytes_` counts what the reader handed over, so `finalizeWav`'s arithmetic is unchanged; the queue is unbounded on purpose (audio is 100–300 kB/s; a backlog beyond 16 MB means the medium stalled for a minute and is logged).

## 5. Build, deploy, test

```bash
cmake --build ~/ApertarCore-build -j2 2>&1 | tail -3
sudo systemctl restart apertar-core
python3 -I ~/apertar-kb/working/tools/core.py record_start; sleep 10; python3 -I ~/apertar-kb/working/tools/core.py record_stop
journalctl -u apertar-core -b --no-pager | grep -E 'audio capture:|audio writer:' | tail -3
```

Prediction: `audio capture: buffer_frames=48000 period_frames=480 requested_ms=1000/10` (a device may negotiate neighbours, e.g. 44100/441); `audio writer: peak_backlog_kb=<small>`.

**5.1 Repeat 3.2** with the patch: same mode, same mic, same 3 minutes. Prediction: zero `audio discontinuity` lines on the medium that showed them; `measured_drift_ppm` now equals the idle 2K figure within a few ppm; the WAV length equals the picture (`audio sync: ... output_samples=` = frames × rate / fps).

**5.2 A clap at both ends** in Resolve or `ffprobe -show_packets`: the end clap within one frame of the picture (Cinemate's `8282087` is the WAV that ran long by 7 frames).

**5.3 Drift by hand** — a 10-minute take on the quiet 2K mode: `measured_drift_ppm` is your mic's crystal; keep that number in `lessons/hardware-log.md`. If a future take reports something far from it, suspect loss first.

## 6. Commit and push

```bash
git -C ~/ApertarCore add src/audio
git -C ~/ApertarCore commit -m "audio: writer thread and a one-second capture ring on the record path

The reader never touches the medium; blocks and gap zeros go through a RAM
queue to a writer thread. Hardware parameters set by hand so a 1 s ring
keeps a 10 ms period. Logic ported from Cinemate's audio campaign
(ffb61fd, 5021ba3; the padding is 6ccfabd and was already here).
Tested: <discontinuity counts before/after, drift figures, clap test>."
git -C ~/ApertarCore push -u origin main
```

## 7. If it went wrong

| You see | It means | Do |
| --- | --- | --- |
| `ALSA capture: Invalid argument` at open | the device refused the period/buffer combination | `APERTAR_AUDIO_BUFFER_MS=500`; print the negotiated sizes; some USB class devices want period = buffer/4 |
| VU meter sluggish | period negotiated far above 10 ms | check `period_frames=` in the journal; try buffer 500 ms |
| `audio writer: backlog above 16 MB` | the medium stalled for a minute of audio | that is the measurement; look at the DNG side (`peak_queue`, `write_failures`) |
| `audio capture write failed` immediately after a pull | expected; T28 marks the medium gone and the writer discards | nothing |
| `measured_drift_ppm` still differs between 2K and Clear HDR | loss is upstream of the ring (USB bus contention) | 3.3: separate controllers; Cinemate's last resort was SCHED_FIFO + a reserved core (`521dc72`) |

Undo: `APERTAR_AUDIO_BUFFER_MS=100` for the ring only; `git checkout -- src/audio` for everything.

## 8. What you learned, going further

- A capture thread must never block on the medium; the ring must outlast the stall; reconcile against the clock, not against the sample count.
- A whole-take ratio cannot tell drift from loss; a per-device crystal figure measured on a quiet take can.
- Exercise: clamp `finalizeWav`'s resampler to the crystal figure ± 50 ppm, log when the measurement disagrees, and count `padded_us` in the stats line.
- Going further: a tolerance study of the 10 ms padding threshold against your mic's period (Cinemate landed on period/4 after /16 and /8 injected false silence, `8e21f4a`).

## 9. Sources

- cinepi-raw commits `fed2ede`, `b9dd1c1`, `6ccfabd`, `5021ba3`, `ffb61fd`, `521dc72`, `cab91a9`, `8e21f4a`, `8282087`, `7398b62`, `c740406` (bodies read in full; `working/cinemate-lessons.md` §3); cinemate `7551a16`, `d7a8d2b`.
- `Apertar-Core@90e2415`: `src/audio/AudioRecordingSession.{hpp,cpp}` (`:209`, `:252`, `:359`, `:380-400`, `:431-440`, `:508`, `:694-730`), `src/audio/TimestampedAudioCapture.{hpp,cpp}` (`:159`, `:195-218`); at f60e301: `AudioRecordingSession.cpp:233`, `:472`, `:526-531`; `TimestampedAudioCapture.cpp:189-190`.
- `working/storage-answer.md` §2, `working/port-raw/p2-phaselock-core.md` §3 (audio clock), `working/cinemate-lessons.md` §3.

%% tutor
ref core src/audio/TimestampedAudioCapture.cpp 159 unsigned bufferUs, unsigned periodUs)
ref core src/audio/TimestampedAudioCapture.cpp 208 s.result(s.snd_pcm_hw_params_set_buffer_time_near(s.pcm, hw, &bufferTime, nullptr), error) &&
ref core src/audio/AudioRecordingSession.cpp 209 unsigned recordCaptureBufferUs()
ref core src/audio/AudioRecordingSession.cpp 359 writerThread_ = std::thread(&AudioRecordingSession::writerLoop, this);
ref core src/audio/AudioRecordingSession.cpp 508 enqueueWrite(buffer.data(), static_cast<size_t>(bytesRead));
ref core src/audio/AudioRecordingSession.cpp 694 void AudioRecordingSession::enqueueWrite(const char *data, size_t size)
ref core src/audio/AudioRecordingSession.cpp 708 void AudioRecordingSession::writerLoop()
check 3.1 | grep -c 'rawStream_.write' /home/pi/ApertarCore/src/audio/AudioRecordingSession.cpp | ^[0-9]+$
check 4.1 | grep -c 'snd_pcm_hw_params_set_buffer_time_near' /home/pi/ApertarCore/src/audio/TimestampedAudioCapture.cpp | ^2$
check 4.2 | grep -c 'writerLoop' /home/pi/ApertarCore/src/audio/AudioRecordingSession.cpp | ^[2-9]$
check 5 | journalctl -u apertar-core -b --no-pager | grep -c 'audio capture: buffer_frames=' | ^[1-9][0-9]*$
check 5.1 | journalctl -u apertar-core -b --no-pager | grep -c 'audio writer: peak_backlog_kb=' | ^[1-9][0-9]*$
%%

#CINEMATE
#APERTAR
