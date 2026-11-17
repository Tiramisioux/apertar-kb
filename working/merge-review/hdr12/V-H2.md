# V-H2: stale raw storage depth after set_record_format cDNG <-> MLV (skeptic pass)

Verdict: **H2 survives. Confirmed defect, provable from code.** I could not refute it. The only open
question is whether the owner's take actually went through this sequence. That needs the Pi.

Refs: Apertar-Core `cinemate-port` `01f170c` (all `CC` lines below), fork `origin/main` `f60e301`,
`upstream-1.6.0` `35dbe67`. CC = `src/camera/CameraController.cpp`.

## Chain, link by link

| # | Link | Evidence | Label |
| --- | --- | --- | --- |
| 1 | Storage depth depends on the format. 12-bit Clear HDR cDNG stores 12, MLV stores 16 | CC:1640-1643 `clearHdrStoresCodes12` = `clearHdr && !photo && rawBitDepth == 12 && recordingFormat == Cdng`; CC:1686-1687 `if (settings.clearHdr) return clearHdrStoresCodes12(settings) ? Bits12 : Bits16;` | confirmed |
| 2 | `rawStreamInfo_.bitDepth` gets the storage depth only in configure | CC:8615-8622 is the only place `storageRawBitDepthForSettings` feeds `rawStreamInfo_` (grep: other hits are 1682 def, 9629 photo path). All `rawStreamInfo_` writes: 7535, 8281 (reset), 8584-8622 (configure) | confirmed |
| 3 | `set_record_format` reaches `CameraController::setRecordingFormat` with nothing else | `src/ApertarCoreApp.cpp:13054-13066` | confirmed |
| 4 | `setRecordingFormat` asks for reconfigure only on processed stream, size or `rawBitDepth` change | CC:11385-11389 | confirmed |
| 5 | `applySettingsLocked` adds only photo mode, ISP colour profile, Clear HDR toggle | CC:12725-12727 | confirmed |
| 6 | ISP colour profile does not differ cDNG vs MLV at default | `include/apertar/core/Types.hpp:223-229`: cDNG returns `cdngPreviewColorProfile`, MLV returns `Standard`; default `cdngPreviewColorProfile = Standard` (Types.hpp:196) | confirmed |
| 7 | Without reconfigure the session only swaps controls and `settings_` | CC:7565-7604 `applyControls`: sets `pendingControls_`, `settings_ = sanitized`; no `rawStreamInfo_` touch | confirmed |
| 8 | Take start does not re-derive the depth | CC:7610-7613 `startRecording` reconfigures only for `photoStreamOverride_`; CC:7739-7740 passes stale `rawStreamInfo_.bitDepth` to `buildCdngLogTake` | confirmed |
| 9 | Each frame takes the new format from `settings_` and the old depth from `rawInfo` | CC:9491-9492 `mapCodes12 = clearHdrStoresCodes12(settings_) && ... && rawInfo.bitDepth == Bits12`; CC:9496 `copy.view.bitDepth = rawInfo.bitDepth`. Same copy queue for MLV and cDNG (`recorder_.enqueueCopy`, CC:9504) | confirmed |

## Outcome A: cDNG -> MLV (stream configured 12, take is MLV)

| Step | Evidence | Label |
| --- | --- | --- |
| `mapCodes12` false (format is MLV), frame keeps libcamera linear 16-bit samples | CC:9491, CC:1640-1643 | confirmed |
| View `bitDepth = Bits12` -> MLV layout 12-bit | `src/mlv/MlvEncoder.cpp:824-834` | confirmed |
| Packer keeps the low 12 bits | `MlvEncoder.cpp:333-336` `(p >> sourceShift) & 0x0fff`, shift 0 | confirmed |
| RAWI declares 12 / 200 / 4095 | `MlvEncoder.cpp:1154-1158` + `src/cdng/BlackLevel.hpp:22-35`; host run below | confirmed |
| Linear black 3200 stored as 3200 (< 4096) = 77.0 % of declared white | host run below | confirmed |
| Highs wrap: 4096 -> 0, 8000 -> 3904, 20000 -> 3616, 65520 -> 4080 | host run below | confirmed |
| Picture in a reader: grey/magenta-tinted raised black, speckle and banding where the scene crosses multiples of 4096 | follows from the two rows above; exact look per reader not run | probable |

## Outcome B: MLV -> cDNG (stream configured 16, take is cDNG)

| Step | Evidence | Label |
| --- | --- | --- |
| `mapCodes12` false (`rawInfo.bitDepth` is 16) | CC:9491-9492 | confirmed |
| Metadata still gets the 4096-entry CCMP expansion as `LinearizationTable` (decided by settings, not by the stream) | CC:4090-4095; `src/cdng/ClearHdrCcmp.hpp:61-63` size 4096 | confirmed |
| CineMate Log on does not rescue it: `viewDepth` 12 != view 16, falls to the `else if (mapCodes12)` branch, also false | CC:4029-4031, CC:5121-5137 | confirmed |
| `writeDngFile` throws `Invalid RAW linearization table.` (4096 != 1<<16) | `src/cdng/CdngEncoder.cpp:1338-1340` | confirmed |
| Worker catches it and calls `failRecording`; journal has `ApertarCore DNG write failed for ... Invalid RAW linearization table.` | CC:5299-5304 | confirmed (the message); "stops at frame 1" probable (first frame hits it; workers may have more in flight) |

Preview: unaffected in both directions (the ISP input is the configured stream, which is consistent with
itself). probable; not part of this check.

## Attempts to refute, and why each fails

| Refutation tried | Result |
| --- | --- |
| Some other check forces a reconfigure on cDNG <-> MLV | Only if `cdngPreviewColorProfile != Standard` (Types.hpp:223-229, CC:12726). Default is Standard. That is a narrowing, not a refutation |
| The saved MLV profile differs and triggers a reconfigure | True when it exists and differs in size, `rawBitDepth` or `clearHdr` (CC:11338-11372, then CC:11387-11389, CC:12727). If there is no saved MLV profile, `next = settings_` keeps everything: defect. If the saved profile also is Clear HDR 12 at the same size: defect |
| The ladder rewrites the mode | `ladderRewriteLocked` (CC:10866-10883) changes size / depth / Clear HDR only when the rung differs; same rung = no reconfigure |
| Lossy DNG also flips the depth | Lossy DNG + Clear HDR is rejected (`include/apertar/core/RecordingCapabilities.hpp:76-78`). Only cDNG <-> MLV |
| Take start re-configures | Only for `photoStreamOverride_` (CC:7612) |
| The defect is a port regression | No. Carried from fork main: `git merge-base --is-ancestor 57c8fb0 origin/main` = yes; `origin/main` has the same `storageRawBitDepthForSettings` (CC@main:1348-1360) and the same `requiresReconfigure` (CC@main:8306-8309). Upstream 1.6.0 storage depth depended on `rawBitDepth` only (CC@upstream-1.6.0:1301-1308), so its `next.rawBitDepth != settings_.rawBitDepth` test was complete. 57c8fb0 made the depth depend on format and did not extend the test |

What clears the stale state: any reconfigure (size, `rawBitDepth`, Clear HDR toggle, photo mode, non-Standard
cDNG preview profile, ladder rung change, Core restart, wake from standby that reconfigures).

## Host run

`/home/user/build/hdr12-numeric/v-h2/vh2.cpp`, built against the real headers
(`g++ -std=c++20 -I Apertar-Core/src -I Apertar-Core/include`):

```
RAWI stale (12,200,4095) healthy (16,3201,65535)
linear black 3200 -> low12 3200 = 0.770 of white
expansionTable size 4096 vs 1<<16 65536 -> mismatch throws
lin 4000 -> low12 4000
lin 4096 -> low12 0
lin 8000 -> low12 3904
lin 20000 -> low12 3616
lin 65520 -> low12 4080
```

## How sure, and what remains for the Pi

- The code path is certain: if the sequence happens, the file is wrong (A) or the take fails (B).
- Not certain: that the owner's "strange output" is this. It needs the exact order "Clear HDR 12 configured in
  one of cDNG/MLV, switch to the other, record" with no reconfigure between. Outcome A matches "strange output";
  outcome B is a failed take, not "strange output".

Pi checks:

1. `journalctl -u apertar-core | grep 'camera configured'` last line vs `get_state` `recording_format`
   (MLV with `storage_bits=12` or cDNG with `storage_bits=16` = stale). (Check the exact field name in the
   configure log line before relying on it.)
2. On a suspect MLV: RAWI bits / black / white = (12, 200, 4095) = defect, (16, 3201, 65535) = healthy.
3. Reproduce: Clear HDR 12 in cDNG, Core restart, `set_record_format mlv`, record 2 s -> expect (12, 200, 4095).
   Then `set_record_format cdng`, record -> expect journal `Invalid RAW linearization table.`

## Fix sketch (Apertar style: one line next to its siblings)

`applySettingsLocked` already lists the settings that change the stream (CC:12725-12727). The storage depth is
one of them since 57c8fb0:

```cpp
    requiresReconfigure |= nextSettings.clearHdr != settings_.clearHdr;
    requiresReconfigure |= storageRawBitDepthForSettings(nextSettings) != storageRawBitDepthForSettings(settings_);
```

Why here and not in `setRecordingFormat` CC:11387-11389: every setter goes through `applySettingsLocked`, so a
future setter that touches format, photo mode or depth is covered too. `storageRawBitDepthForSettings` is in the
same file (CC:1682), defined before use. Cost: cDNG <-> MLV in Clear HDR 12 restarts the stream, as a size change
does today. 16-bit Clear HDR and SDR are unaffected (depth equal on both sides).

Host test: no `tools/*_test.cpp` reaches `CameraController` (the session is libcamera-only; the simulated path
skips it). Two options, smallest first:

1. Encoder-level guard, no code move: `tools/clear_hdr_storage_test.cpp` builds a 16-bit linear frame
   (black 3200, a ramp to 65520), feeds `MlvEncoder` with `bitDepth = Bits12` and asserts RAWI is not
   (12, 200, 4095) for a Clear HDR take; feeds `CdngEncoder::writeDngFile` with `bitDepth = Bits16` plus the
   4096 table and asserts the throw. This documents the two failure signatures, it does not test the fix.
2. To test the fix itself, `clearHdrStoresCodes12` and `storageRawBitDepthForSettings` would have to move to a
   header next to `RecordingCapabilities.hpp` (they need only `CaptureSettings`). Then the test asserts
   `storageRawBitDepthForSettings(cdng12hdr) != storageRawBitDepthForSettings(mlv12hdr)` and that the
   reconfigure predicate includes it. That is a code move; decide with the original developer.
