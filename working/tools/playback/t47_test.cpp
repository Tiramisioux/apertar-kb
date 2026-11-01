// T47 (Core knows its clips), part A: checks for the three headers you type.
//   frames   ClipFrames: numbers, holes, 0-byte frames, DNG+JPEG stems; the time -> frame map
//   drift    position clock vs number clock on a 25 fps lossless take with drops
//   hold     the hold rule and the yield window
//   tags     DngTags: the tags of frames Core's own encoder writes, no liblj92; the recorded timecode (R1)
// Build, on the Pi, from this folder (CORE=~/ApertarCore):
//   g++ -std=c++20 -O2 -Wall -Wextra -I$CORE/src/playback -I$CORE/src -I$CORE/include t47_test.cpp \
//       $CORE/src/cdng/CdngEncoder.cpp $CORE/src/cdng/LosslessJpegEncoder.cpp $CORE/src/color/ColorProfileConfig.cpp \
//       -lyaml -lpthread -o /tmp/t47_test && /tmp/t47_test /tmp/t47
// (While you type, use -I$CORE/src/playback; to check the KB's copy instead, use -Isrc/playback.)

#include "ClipFrames.hpp"
#include "DngTags.hpp"
#include "PlaybackHold.hpp"
#include "cdng/CdngEncoder.hpp"

#include <algorithm>
#include <chrono>
#include <cstdio>
#include <fstream>
#include <random>
#include <string>

using namespace apertar::playback;
namespace fs = std::filesystem;
using Clock = std::chrono::steady_clock;

static int failures = 0, checks = 0;
static void check(bool ok, const std::string &what)
{
    ++checks;
    std::printf("  %s %s\n", ok ? "ok  " : "FAIL", what.c_str());
    if (!ok) ++failures;
}
static double msSince(Clock::time_point t) { return std::chrono::duration<double, std::milli>(Clock::now() - t).count(); }
static double median(std::vector<double> v) { std::sort(v.begin(), v.end()); return v[v.size() / 2]; }

static void touch(const fs::path &p, size_t bytes)
{
    std::ofstream o(p, std::ios::binary | std::ios::trunc);
    std::string s(bytes, 'x');
    o.write(s.data(), std::streamsize(s.size()));
}

static void testFrames(const fs::path &tmp)
{
    std::printf("frames\n");
    const fs::path clip = tmp / "cDNG_26-10-28_C0007";
    fs::remove_all(clip);
    fs::create_directories(clip);
    // numbers 0 1 2 . . 5 6 . 8(0 bytes) 9 ; a WAV and a stray file beside them
    for (int n : {0, 1, 2, 5, 6, 8, 9}) {
        char name[64];
        std::snprintf(name, sizeof name, "cDNG_26-10-28_C0007_%09d.dng", n);
        touch(clip / name, n == 8 ? 0 : 100);
    }
    touch(clip / "cDNG_26-10-28_C0007.wav", 44);
    touch(clip / "notes.txt", 3);
    const FrameList f = listFrames(clip);
    check(f.count() == 7 && f.numbered, "7 frame files, all numbered (FRAMES = 7, as the touch UI counts)");
    check(f.first == 0 && f.last == 9 && f.span() == 10 && f.missing() == 3, "span 10, 3 numbers never written");
    check(f.gaps.size() == 2 && f.gaps[0] == std::make_pair<uint64_t, uint64_t>(3, 2) &&
          f.gaps[1] == std::make_pair<uint64_t, uint64_t>(7, 1), "holes [3,+2] and [7,+1]");
    check(f.empty == 1, "one 0-byte frame");
    check(std::abs(f.durationSeconds(25) - 0.4) < 1e-9, "DURATION = span / fps = 0.40 s (files / fps would say 0.28 s)");
    // clock at 0.25 s, 25 fps -> number 6 -> position 4 (FRAME 5 / 7)
    check(f.numberAtTime(0.25, 25) == 6 && f.positionAtNumber(6) == 4, "t = 0.25 s -> number 6 -> FRAME 5 / 7");
    check(f.positionAtNumber(3) == 2 && f.positionAtNumber(4) == 2, "over the hole 3-4 the frame before it (number 2) stays");
    const size_t pos8 = f.positionAtNumber(8);
    check(pos8 == 5 && f.pictureAtPosition(pos8) == 4, "at the 0-byte number 8: FRAME 6 / 7, picture of number 6");
    check(f.numberAtTime(99, 25) == 9, "past the end: the last number");
    // DNG + JPEG timelapse pairs: one frame per stem, the DNG first
    const fs::path tl = tmp / "Timelapse_26-10-28_0001";
    fs::remove_all(tl);
    fs::create_directories(tl);
    for (int n = 0; n < 3; ++n) {
        char stem[64];
        std::snprintf(stem, sizeof stem, "Timelapse_26-10-28_0001_%09d", n);
        touch(tl / (std::string(stem) + ".dng"), 10);
        touch(tl / (std::string(stem) + ".jpg"), 10);
    }
    const FrameList t = listFrames(tl);
    check(t.count() == 3 && t.files[0].name.size() > 4 && t.files[0].name.substr(t.files[0].name.size() - 4) == ".dng",
          "DNG + JPEG pairs: 3 frames, each the DNG (today's list counts 6)");
    // JPEG-only timelapse; names without a number fall back to name order
    const fs::path jt = tmp / "Timelapse_jpeg";
    fs::remove_all(jt);
    fs::create_directories(jt);
    touch(jt / "b.jpg", 5); touch(jt / "a.jpg", 5);
    const FrameList j = listFrames(jt);
    check(j.count() == 2 && !j.numbered && j.files[0].name == "a.jpg" && j.span() == 2, "unnumbered JPEGs: name order, number = position");
}

// A 10 s, 25 fps lossless take that lost 43 of 250 frames (the KB's C0002-11 pattern: one frame every
// 5-9, lessons/hardware-log.md:108, :165). The WAV is 10 s (the span). Where is the picture against the sound?
static void testDrift()
{
    std::printf("drift\n");
    std::vector<uint64_t> numbers;
    std::mt19937 rng(3);
    std::uniform_int_distribution<int> step(5, 7);
    int nextDrop = step(rng);
    for (uint64_t n = 0; n < 250; ++n) {
        if (int(n) == nextDrop && n + 1 < 250) { nextDrop += step(rng); continue; }
        numbers.push_back(n);
    }
    const double fps = 25.0;
    const size_t files = numbers.size();
    auto shownNumberByPosition = [&](double t) { return numbers[std::min<size_t>(files - 1, size_t(t * fps))]; };
    auto shownNumberByNumber = [&](double t) {
        const uint64_t n = std::min<uint64_t>(249, uint64_t(t * fps));
        return *(std::upper_bound(numbers.begin(), numbers.end(), n) - 1);
    };
    const double lead5 = shownNumberByPosition(5.0) / fps - 5.0;
    const double endPos = double(files) / fps;
    std::printf("  files %zu of 250; position clock: at 5.0 s the picture shows %.2f s (%.2f s ahead); "
                "the last file is reached at %.2f s and held to 10 s\n",
                files, shownNumberByPosition(5.0) / fps, lead5, endPos);
    double worst = 0;
    for (double t = 0; t < 10.0; t += 0.01) worst = std::max(worst, t - shownNumberByNumber(t) / fps);
    std::printf("  number clock: the picture is never ahead; at most %.3f s behind (one hole)\n", worst);
    check(lead5 > 0.5 && endPos < 9.0, "position clock: picture ahead of the sound by > 0.5 s at 5 s and ends before 9 s");
    check(worst <= 2.0 / fps + 1e-9, "number clock: picture within one hole (<= 2 frames here) of the sound");
}

static void testHold()
{
    std::printf("hold\n");
    HoldSignals s;
    check(playbackHoldFor(s) == Hold::None, "idle: no hold");
    s.writesPending = true; s.standby = true;
    check(playbackHoldFor(s) == Hold::Writing, "writes pending before standby");
    s.timelapse = true;
    check(playbackHoldFor(s) == Hold::Recording, "a timelapse is a recording hold");
    HoldSignals m; m.mediaUsable = false;
    check(playbackHoldFor(m) == Hold::Media && std::string(holdName(Hold::Media)) == "media", "media gone: media");
    PlaybackYield y;
    const int64_t t0 = 1000000;
    y.yieldFor(Hold::Recording, t0);
    HoldSignals w; w.yieldReason = y.reasonIfActive(t0 + 10);
    check(playbackHoldFor(w) == Hold::Recording, "record_start's yield holds before recording_ is visible");
    check(y.reasonIfActive(t0 + 3001) == Hold::None, "the window ends after 3 s (the real signal takes over)");
    PlaybackYield k;
    k.yieldFor(Hold::Recording, t0);                       // record_start
    for (int64_t t = t0 + 250; t <= t0 + 10000; t += 250)  // the watcher, every 250 ms in the take
        k.yieldFor(Hold::Recording, t, 1500);
    check(k.active(t0 + 11000) && !k.active(t0 + 11501), "the watcher keeps it open through the take; it closes 1.5 s after");
    k.yieldFor(Hold::Recording, t0 + 11000, 100);
    check(k.active(t0 + 11400), "a shorter call never shortens an open window");
}


static void testTags(const fs::path &tmp)
{
    std::printf("tags\n");
    struct Case { unsigned bits; bool lossless; apertar::TimecodeMode mode; uint64_t frameIndex; } cases[] = {
        {12, false, apertar::TimecodeMode::RecRun, 25}, {16, true, apertar::TimecodeMode::RecRun, 3},
        {12, true, apertar::TimecodeMode::FreeRun, 0}};
    apertar::CdngEncoder enc;
    std::mt19937 rng(7);
    for (const Case &c : cases) {
        const uint32_t w = 3840, h = 2160;
        std::vector<uint16_t> src(size_t(w) * h);
        for (auto &v : src) v = uint16_t(rng() % (1u << c.bits));
        apertar::RawFrameView view;
        view.data = reinterpret_cast<const uint8_t *>(src.data()); view.size = src.size() * 2;
        view.width = w; view.height = h; view.stride = w * 2;
        view.bitDepth = c.bits == 16 ? apertar::RawBitDepth::Bits16 : apertar::RawBitDepth::Bits12;
        view.unpackedBytesPerSample = 2; view.packing = apertar::PixelPacking::Unpacked;
        view.bayerPattern = apertar::BayerPattern::RGGB;
        apertar::CdngEncoder::Metadata meta;
        meta.compression = c.lossless ? apertar::CdngCompression::LosslessJpeg : apertar::CdngCompression::Uncompressed;
        meta.fps = 25.0; meta.clipName = "t"; meta.frameFileName = "t_000000000.dng";
        meta.timecodeMode = c.mode; meta.frameIndex = c.frameIndex;
        const std::string name = (tmp / ("tags_" + std::to_string(c.bits) + (c.lossless ? "_lj" : "_unc") + ".dng")).string();
        enc.writeDngFile(name, view, meta);
        const int fd = openDngFrame(name.c_str());
        DngInfo info; std::string error;
        const bool ok = readDngInfo(fd, info, error);
        closeDngFrame(fd);
        const std::string label = std::to_string(c.bits) + "-bit " + (c.lossless ? "lossless" : "uncompressed");
        check(ok, label + ": readDngInfo opens Core's file" + (error.empty() ? "" : " (" + error + ")"));
        check(info.width == w && info.height == h && info.bits == c.bits, label + ": size and bit depth from IFD0");
        check(info.compression == (c.lossless ? 7 : 1), label + ": compression tag");
        check(std::abs(info.fps - 25.0) < 1e-9 && info.pageName == "t_000000000.dng", label + ": FrameRate and PageName");
        check(info.hasTimecode, label + ": the TimeCodes tag is there");
        // SMPTE BCD, frame first: Rec Run counts frames at the clip rate from the first frame.
        if (c.mode == apertar::TimecodeMode::RecRun) {
            const int frame = (info.timecode[0] >> 4) * 10 + (info.timecode[0] & 15);
            const int sec = (info.timecode[1] >> 4) * 10 + (info.timecode[1] & 15);
            check(frame == int(c.frameIndex % 25) && sec == int(c.frameIndex / 25),
                  label + ": Rec Run timecode = frame " + std::to_string(c.frameIndex) + " of the take (00:00:" +
                  std::to_string(c.frameIndex / 25) + ":" + std::to_string(c.frameIndex % 25) + ")");
        }
        check(info.tailBytesRead > 0 && info.tailBytesRead < 4096, label + ": the tags cost one small tail read");
        fs::remove(name);
    }
}

int main(int argc, char **argv)
{
    if (argc < 2) { std::fprintf(stderr, "usage: t47_test TMP_DIR\n"); return 2; }
    const fs::path tmp = argv[1];
    fs::create_directories(tmp);
    testFrames(tmp);
    testDrift();
    testHold();
    testTags(tmp);
    std::printf(failures ? "FAILURES %d of %d\n" : "t47 ok (%d checks)\n", failures ? failures : checks, checks);
    return failures ? 1 : 0;
}
