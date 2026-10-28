// Host test for apertar-core's src/camera/ModeLadder.hpp (T34).
// Build: g++ -std=c++20 -Wall -Wextra -I<apertar-core>/src mode_ladder_test.cpp -o mode_ladder_test
#include "camera/ModeLadder.hpp"
#include <cstdio>

static int failures = 0;
static void check(bool ok, const char *what) { std::printf("  [%s] %s\n", ok ? "ok" : "FAIL", what); if (!ok) ++failures; }
static apertar::ladder::RungState st(bool valid, bool usable, double ceiling, const char *reason = "")
{
    apertar::ladder::RungState s;
    s.valid = valid;
    s.usable = usable;
    s.modeCeiling = ceiling;
    s.reason = reason;
    return s;
}

int main()
{
    using namespace apertar::ladder;
    std::string error;
    Ladder patrik;
    patrik.enabled = true;

    std::printf("1. parse and print\n");
    check(parseRungs("3840x2160:16:hdr:none:25,3840x2160:12:sdr:none", patrik.rungs, error), "Patrik's ladder parses");
    check(patrik.rungs.size() == 2 && patrik.rungs[0].clearHdr && patrik.rungs[0].bits == 16 &&
          patrik.rungs[0].threshold == 25.0 && !patrik.rungs[1].clearHdr && patrik.rungs[1].threshold == 0.0 &&
          patrik.rungs[1].compression == Compression::None, "fields read");
    check(rungsText(patrik.rungs) == "3840x2160:16:hdr:none:25,3840x2160:12:sdr:none", "prints back the same text");
    std::vector<Rung> tmp;
    check(parseRungs("3840x2160:16:hdr:25,3840x2160:12:sdr", tmp, error) && rungsText(tmp) == rungsText(patrik.rungs),
          "the design's text without compression reads as uncompressed");
    check(parseRungs("3840x1608:12:sdr:30:lossy_5to1", tmp, error) && tmp[0].threshold == 30.0 &&
          tmp[0].compression == Compression::Lossy5, "FPS and compression in either order");
    check(parseRungs("3840x2160:12:sdr:", tmp, error) && tmp[0].threshold == 0.0, "empty threshold after ':'");
    check(!parseRungs("3840x2160:14:sdr", tmp, error), "14-bit refused");
    check(!parseRungs("3840x2160:12:sdr:abc", tmp, error), "bad threshold refused");
    check(!parseRungs("3840x2160:12:sdr:25:30", tmp, error), "two FPS refused");
    check(!parseRungs("3840x2160x:12:sdr", tmp, error) && !parseRungs("38a0x2160:12:sdr", tmp, error), "bad size refused");
    check(!parseRungs("", tmp, error) && error == "Add at least one resolution.", "empty ladder refused");
    check(!parseRungs("3840x2160:12:sdr\a\n", tmp, error) && error.find("\"3840x2160:12:sdr\":") == 0 &&
          std::none_of(error.begin(), error.end(), [](char c) { return static_cast<unsigned char>(c) < 0x20; }),
          "the error quotes the item without control characters (it goes into JSON as is)");
    check(label(patrik.rungs[0]) == "4K Clear HDR 16-bit" && classLabel(patrik.rungs[0]) == "ClearHDR16" &&
          classLabel(patrik.rungs[1]) == "SDR12", "labels");

    std::printf("2. chooser (resolution 1 = ClearHDR16 up to 25, resolution 2 = SDR12 mode ceiling 50)\n");
    const std::vector<RungState> states{ {true, true, 25.0, "", {}, 1}, {true, true, 50.0, "", {}, 1} };
    check(chooseRung(patrik, states, 1.0) == 0, "1 fps -> resolution 1");
    check(chooseRung(patrik, states, 24.0) == 0, "24 -> resolution 1");
    check(chooseRung(patrik, states, 25.0) == 0, "25 -> resolution 1 (upper bound inclusive)");
    check(chooseRung(patrik, states, 25.001) == 1, "25.001 -> resolution 2");
    check(chooseRung(patrik, states, 50.0) == 1, "50 -> resolution 2");
    check(chooseRung(patrik, states, 60.0) == 1, "60 -> resolution 2 (highest ceiling; Core then clamps to 50)");
    check(ladderCeiling(patrik, states) == 50.0, "ladder ceiling 50");
    const std::vector<RungState> lossless{ st(true, true, 25.0), st(true, true, 30.0) };
    check(chooseRung(patrik, lossless, 50.0) == 1 && ladderCeiling(patrik, lossless) == 30.0, "lossless: top 30");
    const std::vector<RungState> skipped{ st(true, false, 0.0), st(true, true, 50.0) };
    check(chooseRung(patrik, skipped, 24.0) == 1, "resolution 1 unusable -> resolution 2");
    const std::vector<RungState> none{ st(true, false, 0.0), st(true, false, 0.0) };
    check(chooseRung(patrik, none, 24.0) == -1, "nothing usable -> -1");

    std::printf("3. invariant (Cinemate ff59dd8): no reachable request outruns the resolution it lands in\n");
    bool invariant = true;
    for (double fps = 0.5; fps <= ladderCeiling(patrik, states) + 0.0001; fps += 0.5) {
        const int i = chooseRung(patrik, states, fps);
        invariant = invariant && i >= 0 && rungCeiling(patrik.rungs[i], states[i]) >= fps - kFpsEpsilon;
    }
    check(invariant, "0.5 .. 50 fps all served");

    std::printf("4. the running resolution\n");
    Rung running = patrik.rungs[1];
    check(findRung(patrik, running, true) == 1, "SDR12 uncompressed is resolution 2");
    running.compression = Compression::LosslessJpeg;
    check(findRung(patrik, running, true) == -1, "another compression is off the ladder in cDNG");
    check(findRung(patrik, running, false) == 1, "in MLV the compression does not count");

    std::printf("5. validation (states in each resolution's own compression)\n");
    std::vector<std::string> errors, warnings;
    validate(patrik, states, errors, warnings);
    check(errors.empty() && warnings.size() == 1 && warnings[0].find("Above 25 fps: Clear HDR 16-bit") == 0,
          "Patrik's ladder: no errors, one look-change warning");
    Ladder bad = patrik;
    parseRungs("3840x2160:12:sdr:none:30,3840x2160:16:hdr:none:25,3840x2160:12:sdr:lossless_jpeg", bad.rungs, error);
    errors.clear(); warnings.clear();
    validate(bad, { st(true, true, 50.0), st(true, true, 25.0), st(true, true, 30.0) }, errors, warnings);
    check(errors.size() == 2 && errors[0].find("Resolution 2 would never be used") == 0 &&
          errors[1].find("Resolution 3 repeats resolution 1") == 0, "a resolution below the ones above, and a repeat");
    errors.clear(); warnings.clear();
    validate(patrik, { st(false, false, 0.0), st(true, true, 50.0) }, errors, warnings);
    check(errors.size() == 1 && errors[0] == "Resolution 1: 4K Clear HDR 16-bit is not a mode of this sensor.",
          "not a mode of this sensor");
    errors.clear(); warnings.clear();
    Ladder lossy = patrik;
    lossy.rungs[0].compression = Compression::Lossy3;
    validate(lossy, { st(true, false, 25.0, "Lossy cDNG does not support Clear HDR."), st(true, true, 50.0) }, errors, warnings);
    check(errors.size() == 1 && errors[0].find("Resolution 1 (4K Clear HDR 16-bit, Lossy 3:1) cannot record: Lossy") == 0,
          "lossy Clear HDR refused with Core's reason");
    errors.clear(); warnings.clear();
    Ladder high = patrik;
    high.rungs[1].threshold = 40.0;
    validate(high, lossless, errors, warnings);
    check(errors.size() == 1 && errors[0] == "Resolution 2: 40 fps is above this mode's ceiling of 30 fps.",
          "a threshold above the mode's ceiling");
    errors.clear(); warnings.clear();
    Ladder low = patrik;
    low.rungs[1].threshold = 20.0;
    validate(low, states, errors, warnings);
    check(errors.size() == 1 && errors[0] == "Resolution 2 must go above 25 fps, where the resolutions above stop.",
          "a threshold at or below the one above");
    errors.clear(); warnings.clear();
    validate(Ladder{}, {}, errors, warnings);
    check(errors.size() == 1, "no resolutions");
    Ladder many;
    for (int i = 0; i < 9; ++i)
        many.rungs.push_back(Rung{ 3840, static_cast<uint32_t>(2160 - i * 8), 12, false, Compression::None, double(20 + i) });
    errors.clear(); warnings.clear();
    validate(many, std::vector<RungState>(9, st(true, true, 60.0)), errors, warnings);
    check(errors.size() == 1 && errors[0] == "At most 8 resolutions.", "nine resolutions");

    std::printf("6. text for the screens\n");
    check(runningText(0, patrik.rungs[0], 25.0, false, compressionLabel(patrik.rungs[0].compression)) ==
          "Resolution 1 · 3840×2160 · ClearHDR16 · ≤25 · Uncompressed", "running line");
    Rung crop{ 1920, 804, 12, false, Compression::Lossy5, 0.0 };
    check(runningText(2, crop, 50.0, true, "MLV") ==
          "Resolution 3 · 1920×804 crop in · SDR12 2.39:1 · ≤50 · MLV", "crop-in line with aspect");
    Crop c;
    check(parseCrop("(0, 0)/3840x2160", c) && c.width == 3840 && c.height == 2160, "libcamera crop text");
    check(parseCrop("(960, 540)/1920x1080", c) && c.x == 960 && c.y == 540, "offset crop");
    check(!parseCrop("", c) && !parseCrop("garbage", c), "no crop");
    const Crop area = sensorArea({ { 0, 0, 3840, 2160 }, { 0, 276, 3840, 1608 }, {} });
    check(area.width == 3840 && area.height == 2160, "readout area");
    check(!cropIn({ 0, 276, 3840, 1608 }, area), "same width, less height: not a crop-in");
    check(cropIn({ 960, 540, 1920, 1080 }, area), "narrower window: crop-in");
    check(!cropIn({ 960, 540, 1920, 1080 }, Crop{}), "unknown area: no claim");

    std::printf("7. file\n");
    const Ladder back = parseFile(fileText(patrik));
    check(back.enabled && rungsText(back.rungs) == rungsText(patrik.rungs), "round trip");
    check(parseFile("enabled=true\r\nramp_ready=true\r\nrungs=3840x2160:12:sdr\r\n").enabled, "CRLF and the old ramp_ready key");
    check(!parseFile("enabled=true\nrungs=garbage\n").enabled, "a broken file leaves the ladder off");

    std::printf("8. reply\n");
    Reply reply;
    reply.ladder = patrik;
    reply.states = { {true, true, 25.0, "", { 0, 0, 3840, 2200 }, 1}, {true, true, 50.0, "", { 0, 0, 3840, 2160 }, 1} };
    reply.active = true;
    reply.running = 0;
    reply.runningText = "a \"quoted\"\tline";
    reply.format = "cdng";
    reply.buildMax = 50.0;
    reply.area = { 0, 0, 3840, 2200 };
    PoolEntry entry;
    entry.mode = patrik.rungs[0];
    entry.valid = true;
    entry.ceilings = { 25.0, 25.0, 0.0, 0.0 };
    entry.reasons[2] = "Lossy cDNG does not support Clear HDR.";
    reply.pool = { entry };
    const std::string json = toJson(reply);
    check(json.find("\"ceiling\":50,\"running_rung\":1") != std::string::npos, "ceiling and running resolution");
    check(json.find("\"class\":\"ClearHDR16\"") != std::string::npos && json.find("\"from\":25") != std::string::npos,
          "resolution 1 class, resolution 2 serves from 25");
    check(json.find("\\\"quoted\\\"\\u0009line") != std::string::npos, "quotes and control characters escaped");
    check(json.find("\"ceilings\":{\"none\":25,\"lossless_jpeg\":25,\"lossy_3to1\":0,\"lossy_5to1\":0}") != std::string::npos &&
          json.find("\"reasons\":{\"lossy_3to1\":") != std::string::npos, "pool ceilings and reasons per compression");
    check(json.find("\"crop\":{\"x\":0,\"y\":0,\"width\":3840,\"height\":2200}") != std::string::npos, "crop object");
    check(json.find("ramp_ready") == std::string::npos, "no Ramp-ready");

    std::printf(failures ? "FAILED: %d\n" : "all ok\n", failures);
    return failures ? 1 : 0;
}
