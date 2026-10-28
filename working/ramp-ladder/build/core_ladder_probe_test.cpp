// Host test of the T34 helpers in apertar-core's src/camera/CameraController.cpp that need no
// libcamera: compression <-> CaptureSettings, the running resolution and its line, the probe ->
// pool mapping (aliases, dedupe, order, folded crops), the readout area, ladder_tops. The functions
// are copied verbatim from the source by core_ladder_probe_extract.py. Build (from this folder):
//   python3 core_ladder_probe_extract.py core/src/camera/CameraController.cpp core_ladder_probe_extracted.inc
//   g++ -std=c++20 -Wall -Wextra -Werror -Icore/src -Icore/include core_ladder_probe_test.cpp -o /tmp/clpt && /tmp/clpt
#include "camera/CameraController.hpp"
#include <algorithm>
#include <cstdio>
#include <sstream>

namespace apertar {
namespace {
std::mutex probedSensorModesMutex;          // the probe's globals, as in CameraController.cpp
std::vector<CameraController::SensorMode> probedSensorModes;
#include "core_ladder_probe_extracted.inc"
}
}

using namespace apertar;

static int failures = 0;
static void check(bool ok, const char *what) { std::printf("  [%s] %s\n", ok ? "ok" : "FAIL", what); if (!ok) ++failures; }

static CaptureSettings camera(uint32_t w, uint32_t h, uint32_t bits, bool hdr, RecordingFormat format,
                              CdngCompression cdng = CdngCompression::Uncompressed, LossyDngRatio ratio = LossyDngRatio::R3)
{
    CaptureSettings s;
    s.resolution = Resolution{ w, h };
    s.rawBitDepth = bits;
    s.clearHdr = hdr;
    s.recordingFormat = format;
    s.cdngCompression = cdng;
    s.lossyDngRatio = ratio;
    return s;
}

static CameraController::SensorMode probed(uint32_t w, uint32_t h, uint32_t bits, bool hdr, const char *crop, uint32_t binning)
{
    CameraController::SensorMode m;
    m.bitDepth = bits;
    m.size = Resolution{ w, h };
    m.clearHdr = hdr;
    m.crop = crop;
    m.binning = binning;
    return m;
}

int main()
{
    using ladder::Compression;

    std::printf("1. compression <-> settings\n");
    check(ladderCompressionOf(camera(3840, 2160, 12, false, RecordingFormat::Cdng)) == Compression::None, "cDNG uncompressed");
    check(ladderCompressionOf(camera(3840, 2160, 12, false, RecordingFormat::Cdng, CdngCompression::LosslessJpeg)) ==
          Compression::LosslessJpeg, "cDNG lossless JPEG");
    check(ladderCompressionOf(camera(3840, 2160, 12, false, RecordingFormat::LossyDng, CdngCompression::LosslessJpeg)) ==
          Compression::Lossy3, "lossy DNG 3:1 (cdngCompression ignored)");
    check(ladderCompressionOf(camera(3840, 2160, 12, false, RecordingFormat::LossyDng, CdngCompression::Uncompressed,
                                     LossyDngRatio::R5)) == Compression::Lossy5, "lossy DNG 5:1");
    check(ladderCompressionOf(camera(3840, 2160, 12, false, RecordingFormat::Mlv, CdngCompression::LosslessJpeg)) ==
          Compression::None, "MLV: none, whatever the cDNG profile holds");
    bool roundTrip = true;
    for (const Compression c : ladder::kCompressions) {
        CaptureSettings s = camera(3840, 2160, 12, false, RecordingFormat::Mlv, CdngCompression::LosslessJpeg, LossyDngRatio::R5);
        applyLadderCompression(s, c);
        roundTrip = roundTrip && ladderCompressionOf(s) == c &&
            (s.recordingFormat == RecordingFormat::LossyDng) == (c == Compression::Lossy3 || c == Compression::Lossy5);
    }
    check(roundTrip, "applyLadderCompression then ladderCompressionOf: the same, for all four");
    CaptureSettings lossy = camera(3840, 2160, 12, false, RecordingFormat::Cdng, CdngCompression::LosslessJpeg);
    applyLadderCompression(lossy, Compression::Lossy5);
    check(lossy.recordingFormat == RecordingFormat::LossyDng && lossy.lossyDngRatio == LossyDngRatio::R5 &&
          lossy.cdngCompression == CdngCompression::Uncompressed, "lossy leaves cdngCompression uncompressed (as a Favorite)");
    const ladder::Rung r = ladderRungOf(camera(3840, 2160, 16, true, RecordingFormat::Cdng, CdngCompression::LosslessJpeg));
    check(r.width == 3840 && r.height == 2160 && r.bits == 16 && r.clearHdr && r.compression == Compression::LosslessJpeg &&
          r.threshold == 0.0, "ladderRungOf");

    std::printf("2. formats\n");
    check(ladderRunsIn(camera(3840, 2160, 12, false, RecordingFormat::Cdng)) &&
          ladderRunsIn(camera(3840, 2160, 12, false, RecordingFormat::LossyDng)) &&
          ladderRunsIn(camera(3840, 2160, 12, false, RecordingFormat::Mlv)), "runs in cDNG, lossy DNG, MLV");
    check(!ladderRunsIn(camera(1920, 1080, 10, false, RecordingFormat::H264)) &&
          !ladderRunsIn(camera(3840, 2160, 10, false, RecordingFormat::Prores)), "not in H.264, ProRes");
    CaptureSettings photo = camera(3840, 2160, 12, false, RecordingFormat::Cdng);
    photo.photoModeEnabled = true;
    check(!ladderRunsIn(photo), "not in photo mode");
    check(ladderCompressionApplies(camera(3840, 2160, 12, false, RecordingFormat::LossyDng)) &&
          !ladderCompressionApplies(camera(3840, 2160, 12, false, RecordingFormat::Mlv)), "compression applies in cDNG/lossy, not MLV");
    const CaptureSettings hdrNone = camera(3840, 2160, 16, true, RecordingFormat::Cdng);

    std::printf("3. the running resolution and its line (resolution 1 = ClearHDR16 up to 25, 2 = SDR12)\n");
    ladder::Ladder l;
    l.enabled = true;
    std::string error;
    ladder::parseRungs("3840x2160:16:hdr:none:25,3840x2160:12:sdr:none", l.rungs, error);
    std::vector<ladder::RungState> states(2);
    states[0].valid = states[0].usable = true;
    states[0].modeCeiling = 25.0;
    states[0].crop = { 0, 0, 3840, 2160 };
    states[1].valid = states[1].usable = true;
    states[1].modeCeiling = 50.0;
    states[1].crop = { 0, 0, 3840, 2160 };
    const ladder::Crop area{ 0, 0, 3840, 2160 };
    check(runningLadderRung(l, states, hdrNone) == 0, "Clear HDR 16-bit uncompressed is resolution 1");
    check(runningLadderRung(l, states, camera(3840, 2160, 12, false, RecordingFormat::Cdng, CdngCompression::LosslessJpeg)) == -1,
          "SDR12 lossless in cDNG: off the ladder");
    check(runningLadderRung(l, states, camera(3840, 2160, 12, false, RecordingFormat::Mlv)) == 1, "SDR12 in MLV: resolution 2");
    check(runningLadderRung(l, states, camera(3840, 2076, 12, false, RecordingFormat::Cdng)) == -1, "a crop not on the ladder");
    std::vector<ladder::RungState> skipped = states;
    skipped[1].usable = false;
    check(runningLadderRung(l, skipped, camera(3840, 2160, 12, false, RecordingFormat::Cdng)) == -1, "a skipped resolution: off");
    check(ladderRunningText(l, states, 0, hdrNone, area) == "Resolution 1 · 3840×2160 · ClearHDR16 · ≤25 · Uncompressed",
          "running line, cDNG");
    check(ladderRunningText(l, states, 1, camera(3840, 2160, 12, false, RecordingFormat::Mlv), area) ==
          "Resolution 2 · 3840×2160 · SDR12 · ≤50 · MLV", "running line, MLV");
    check(ladderRunningText(l, states, -1, hdrNone, area) == "Mode Ladder on · the next FPS pick chooses the resolution",
          "off the ladder");
    ladder::Ladder crops;
    ladder::parseRungs("3840x1608:12:sdr:lossless_jpeg:30,1920x1080:12:sdr:lossy_3to1", crops.rungs, error);
    std::vector<ladder::RungState> cropStates = states;
    cropStates[0].modeCeiling = 30.0;
    cropStates[0].crop = { 0, 276, 3840, 1608 };
    cropStates[1].modeCeiling = 60.0;
    cropStates[1].crop = { 960, 540, 1920, 1080 };
    check(ladderRunningText(crops, cropStates, 0, camera(3840, 1608, 12, false, RecordingFormat::Cdng), area) ==
          "Resolution 1 · 3840×1608 · SDR12 2.39:1 · ≤30 · Lossless JPEG", "full-width crop: aspect, no crop in");
    check(ladderRunningText(crops, cropStates, 1, camera(1920, 1080, 12, false, RecordingFormat::LossyDng), area) ==
          "Resolution 2 · 1920×1080 crop in · SDR12 · ≤60 · Lossy 3:1", "narrower window: crop in");

    std::printf("4. probe -> pool\n");
    const std::vector<CameraController::SensorMode> probe{
        probed(3840, 2160, 10, false, "(0, 0)/3840x2160", 1),
        probed(3840, 2076, 10, false, "(0, 42)/3840x2076", 1),
        probed(1920, 1080, 10, false, "(0, 0)/3840x2160", 2),
        probed(1920, 804, 10, false, "(0, 276)/3840x1608", 2),
        probed(3840, 2160, 12, false, "(0, 0)/3840x2160", 1),
        probed(3856, 2180, 12, false, "(0, 0)/3856x2180", 1),   // the same mode under its readout size
        probed(3840, 2076, 12, false, "(0, 42)/3840x2076", 1),
        probed(1928, 1090, 12, false, "(0, 0)/3856x2180", 2),   // 1920x1080 under its readout size
        probed(1920, 804, 12, false, "(0, 276)/3840x1608", 2),
        probed(1920, 1080, 8, false, "(0, 0)/3840x2160", 2),    // 8-bit: not a ladder mode
        probed(3840, 2160, 12, true, "(0, 0)/3840x2160", 1),
        probed(3840, 2200, 16, true, "(0, 0)/3840x2200", 1),    // 16-bit Clear HDR readout = 4K
    };
    const auto pool = ladderPoolModes(probe);
    std::string order;
    for (const auto &entry : pool)
        order += (order.empty() ? "" : ",") + ladder::rungsText({ entry.mode });
    const std::string want = "3840x2160:16:hdr:none,3840x2160:12:hdr:none,3840x2160:12:sdr:none,3840x2160:10:sdr:none,"
                             "3840x2076:12:sdr:none,3840x2076:10:sdr:none,1920x1080:12:sdr:none,1920x1080:10:sdr:none,"
                             "1920x804:12:sdr:none,1920x804:10:sdr:none";
    check(order == want,
          "Clear HDR first (16, 12), then 4K, crops by height, binned; 12 before 10; aliases folded, 8-bit left out");
    if (order != want)
        std::printf("    got: %s\n", order.c_str());
    check(pool.size() == 10 && pool[0].crop.x == 0 && pool[0].crop.y == 0 && pool[0].crop.width == 3840 &&
          pool[0].crop.height == 2160 && pool[0].binning == 1, "16-bit Clear HDR: its 3840x2200 window folded to 4K");
    check(pool[2].crop.width == 3840 && pool[2].crop.height == 2160, "the first of two aliases wins (its crop)");
    check(pool[8].crop.y == 276 && pool[8].crop.height == 1608 && pool[8].binning == 2, "binned crop: window and binning");
    check(!pool[0].valid && pool[0].ceilings[0] == 0.0, "valid and ceilings are left for CameraController");
    check(ladderPoolModes({}).empty(), "probe off: empty pool");

    std::printf("5. folded crops and the readout area (IMX585: the 16-bit Clear HDR mode reads 3840x2200)\n");
    const auto cropOf = [](const CameraController::SensorMode &m) {
        const ladder::Crop c = ladderCropOf(m);
        return std::to_string(c.x) + "," + std::to_string(c.y) + "/" + std::to_string(c.width) + "x" + std::to_string(c.height);
    };
    check(cropOf(probed(3840, 2200, 16, true, "(0, 0)/3840x2200", 1)) == "0,0/3840x2160", "3840x2200 -> 3840x2160");
    check(cropOf(probed(3856, 2180, 12, false, "(8, 10)/3856x2180", 1)) == "8,10/3840x2160", "3856x2180: origin kept");
    check(cropOf(probed(1928, 1090, 12, false, "(0, 0)/3856x2180", 2)) == "0,0/3840x2160", "1928x1090 binned: 2 x 1920x1080");
    check(cropOf(probed(1920, 1080, 12, false, "(0, 0)/3856x2180", 2)) == "0,0/3856x2180" &&
          cropOf(probed(3840, 2076, 12, false, "(0, 42)/3840x2076", 1)) == "0,42/3840x2076" &&
          cropOf(probed(1920, 804, 12, false, "(0, 276)/3840x1608", 2)) == "0,276/3840x1608",
          "modes not folded keep their window");
    check(cropOf(probed(3840, 2200, 16, true, "", 0)) == "0,0/0x0", "no crop: unknown");
    {
        std::lock_guard<std::mutex> lock(probedSensorModesMutex);
        probedSensorModes = probe;
    }
    const ladder::Crop readout = probedSensorArea();
    check(readout.width == 3840 && readout.height == 2160, "readout area 3840x2160, not 3840x2200");
    bool whole = true;
    for (const auto &entry : pool)
        if (entry.mode.width == 3840 && entry.mode.height == 2160)
            whole = whole && entry.crop.x == 0 && entry.crop.y == 0 && entry.crop.width == readout.width &&
                    entry.crop.height == readout.height && !ladder::cropIn(entry.crop, readout);
    check(whole, "every 4K mode is the whole readout area (no letterbox, no crop in)");
    check(ladder::cropIn(pool[8].crop, readout) == false && pool[8].crop.height < readout.height,
          "binned 2.39:1: full width, less height (an aspect, not a crop in)");
    {
        std::lock_guard<std::mutex> lock(probedSensorModesMutex);
        probedSensorModes.clear();
    }
    check(probedSensorArea().width == 0, "probe off: area unknown");

    std::printf("6. ladder_tops\n");
    check(ladderTopsJson({}) == "[]", "empty");
    check(ladderTopsJson({ 25.0, 50.0 }) == "[25,50]", "whole numbers");
    check(ladderTopsJson({ 29.97, 0.0 }) == "[29.97,0]", "decimals and a skipped resolution");

    std::printf(failures ? "FAILED: %d\n" : "all ok\n", failures);
    return failures ? 1 : 0;
}
