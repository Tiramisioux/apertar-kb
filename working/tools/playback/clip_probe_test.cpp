// T47 part B1: checks for ClipProbe.hpp (per-clip facts, the touch UI's texts, the cache).
// Build, on the Pi, from this folder (CORE=~/ApertarCore; use -I$CORE/src/playback for your typed copy):
//   g++ -std=c++20 -O2 -Wall -Wextra -Isrc/playback -I$CORE/src -I$CORE/include clip_probe_test.cpp \
//       $CORE/src/cdng/CdngEncoder.cpp $CORE/src/cdng/LosslessJpegEncoder.cpp $CORE/src/color/ColorProfileConfig.cpp \
//       -lyaml -lpthread -o /tmp/clip_probe_test && /tmp/clip_probe_test /tmp/cpt

#include "ClipProbe.hpp"
#include "cdng/CdngEncoder.hpp"

#include <chrono>
#include <cstdio>
#include <fstream>
#include <random>
#include <regex>

using namespace apertar::playback;
namespace fs = std::filesystem;

static int failures = 0, checks = 0;
static void check(bool ok, const std::string &what)
{
    ++checks;
    std::printf("  %s %s\n", ok ? "ok  " : "FAIL", what.c_str());
    if (!ok) ++failures;
}

// A small frame written by Core's own encoder (12 or 16 bit, lossless or not) with a given number and timecode.
static void writeFrame(const fs::path &dir, const std::string &clip, int number, unsigned bits, bool lossless,
                       double fps, uint64_t timecodeFrame)
{
    static apertar::CdngEncoder enc;
    static std::mt19937 rng(11);
    const uint32_t w = 1280, h = 720;
    std::vector<uint16_t> src(size_t(w) * h);
    for (auto &v : src) v = uint16_t(rng() % (1u << bits));
    apertar::RawFrameView view;
    view.data = reinterpret_cast<const uint8_t *>(src.data()); view.size = src.size() * 2;
    view.width = w; view.height = h; view.stride = w * 2;
    view.bitDepth = bits == 16 ? apertar::RawBitDepth::Bits16 : apertar::RawBitDepth::Bits12;
    view.unpackedBytesPerSample = 2; view.packing = apertar::PixelPacking::Unpacked;
    view.bayerPattern = apertar::BayerPattern::RGGB;
    apertar::CdngEncoder::Metadata meta;
    meta.compression = lossless ? apertar::CdngCompression::LosslessJpeg : apertar::CdngCompression::Uncompressed;
    meta.fps = fps; meta.clipName = clip;
    char name[128];
    std::snprintf(name, sizeof name, "%s_%09d.dng", clip.c_str(), number);
    meta.frameFileName = name;
    meta.timecodeMode = apertar::TimecodeMode::RecRun; meta.frameIndex = timecodeFrame;
    enc.writeDngFile((dir / name).string(), view, meta);
}

static void touchEmpty(const fs::path &dir, const std::string &clip, int number)
{
    char name[128];
    std::snprintf(name, sizeof name, "%s_%09d.dng", clip.c_str(), number);
    std::ofstream(dir / name, std::ios::binary | std::ios::trunc).close();
}

int main(int argc, char **argv)
{
    if (argc < 2) { std::fprintf(stderr, "usage: clip_probe_test TMP_DIR\n"); return 2; }
    const fs::path tmp = argv[1];
    fs::remove_all(tmp);
    fs::create_directories(tmp);

    std::printf("texts\n");
    check(durationCardText(12.4) == "00:12" && durationCardText(0.2) == "00:00" && durationCardText(0) == "00:00",
          "card duration: 00:12, under half a second 00:00, none 00:00");
    check(durationCardText(3723) == "01:02:03" && durationCardText(59.6) == "01:00", "an hour or more: hh:mm:ss; rounded seconds");
    check(sizeText(4150000000ULL) == "3.9 GB" && sizeText(150ULL * 1024 * 1024) == "150 MB" && sizeText(512) == "512 B",
          "sizes: base 1024, one decimal below 100");
    std::string text; int64_t ms = 0;
    check(shotDate("2026:10:28 14:03:12", text, ms) && text == "28 Oct 2026  14:03" && ms > 0, "shot date: '28 Oct 2026  14:03', two spaces");
    check(!shotDate("garbage", text, ms), "a bad date is refused");
    const uint8_t tc[8] = {0x05, 0x12, 0x03, 0x14, 0, 0, 0, 0};
    check(timecodeText(tc) == "14:03:12:05", "timecode text from the BCD bytes (frame first): 14:03:12:05");

    std::printf("clips\n");
    const std::string a = "cDNG_26-10-28_C0007";        // numbers 0,1,3 (a hole at 2); 24 fps; first frame is frame 49 of the take
    fs::create_directories(tmp / a);
    writeFrame(tmp / a, a, 0, 12, false, 24.0, 49);
    writeFrame(tmp / a, a, 1, 12, false, 24.0, 50);
    writeFrame(tmp / a, a, 3, 12, false, 24.0, 52);
    ClipFacts fa = probeClip(tmp / a);
    check(fa.ok && fa.frames.count() == 3 && fa.frames.span() == 4, "3 files, span 4");
    check(std::abs(fa.fps - 24.0) < 1e-9 && !fa.fpsFallback && fa.fpsText == "24 FPS", "the clip's own FPS from its first frame, not the camera's");
    check(fa.holes.size() == 1 && fa.holes[0] == std::make_pair<uint64_t, uint64_t>(2, 1), "one hole: [2, +1]");
    check(fa.droppedText == "1 missing · 0 empty", "DROPPED: 1 missing · 0 empty");
    check(fa.timecodeStart == "00:00:02:01", "R1: timecode_start 00:00:02:01 (frame 49 at 24 fps), from the first frame");
    check(fa.formatText == "SDR 12-bit · uncompressed" && !fa.companded, "FORMAT: SDR 12-bit · uncompressed");
    check(fa.durationText == "00:00", "duration = span / fps = 0.17 s -> 00:00");
    check(std::regex_match(fa.shotDateText, std::regex("\\d\\d \\w{3} \\d{4}  \\d\\d:\\d\\d")), "shot date from DateTimeOriginal: '" + fa.shotDateText + "'");
    check(fa.bytes > 0 && !fa.sizeText_.empty(), "size: " + fa.sizeText_);

    const std::string b = "cDNG_26-10-28_C0008";        // 0 real, 1 empty (0 bytes), 2 real: 16-bit lossless
    fs::create_directories(tmp / b);
    writeFrame(tmp / b, b, 0, 16, true, 25.0, 0);
    touchEmpty(tmp / b, b, 1);
    writeFrame(tmp / b, b, 2, 16, true, 25.0, 2);
    const ClipFacts fb = probeClip(tmp / b);
    check(fb.droppedText == "0 missing · 1 empty" && fb.holes.size() == 1 && fb.holes[0].first == 1, "a 0-byte frame is a hole too: DROPPED 0 missing · 1 empty");
    check(fb.formatText == "Clear HDR 16-bit · lossless", "FORMAT: Clear HDR 16-bit · lossless");

    const std::string c = "cDNG_26-10-28_C0009";        // a speed-ramp take
    fs::create_directories(tmp / c);
    writeFrame(tmp / c, c, 0, 12, true, 25.0, 0);
    std::ofstream(tmp / c / "fps-ramp.txt") << "# applied_us\n";
    const ClipFacts fc = probeClip(tmp / c);
    check(fc.ramp && fc.droppedText == "unknown (speed ramp)", "a ramp take: DROPPED unknown (speed ramp)");

    std::printf("cache\n");
    ClipFactsCache cache(1761660000000LL);
    const ClipFacts first = cache.get(tmp / a);
    const ClipFacts again = cache.get(tmp / a);
    check(cache.probes() == 1 && first.token == again.token && !first.token.empty(), "an unchanged folder is probed once");
    writeFrame(tmp / a, a, 4, 12, false, 24.0, 53);
    const ClipFacts grown = cache.get(tmp / a);
    check(cache.probes() == 2 && grown.frames.count() == 4 && grown.token != first.token, "a new frame: probed again, new token");
    const ClipFacts other = cache.get(tmp / b);
    check(cache.probes() == 3 && other.name == b, "another folder is its own entry");
    const ClipFacts none = probeClip(tmp / "missing_folder");
    check(!none.ok && !none.error.empty(), "a missing folder: not ok, with a reason");

    std::printf(failures ? "FAILURES %d of %d\n" : "clip_probe ok (%d checks)\n", failures ? failures : checks, checks);
    return failures ? 1 : 0;
}
