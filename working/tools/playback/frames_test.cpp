// T48: checks for PlaybackFrames (one frame of a clip as a JPEG).
// Build, on the Pi, from this folder (CORE=~/ApertarCore):
//   gcc -O2 -c third_party/liblj92/lj92.c -o /tmp/lj92.o
//   g++ -std=c++20 -O2 -Wall -Wextra -DAPERTARCORE_HAS_TURBOJPEG=0 -DAPERTARCORE_HAS_JPEG=1 -Isrc/playback -Ithird_party/liblj92 \
//       -I$CORE/src -I$CORE/include frames_test.cpp src/playback/PlaybackFrames.cpp $CORE/src/cdng/CdngEncoder.cpp \
//       $CORE/src/cdng/LosslessJpegEncoder.cpp $CORE/src/color/ColorProfileConfig.cpp /tmp/lj92.o -ljpeg -lyaml -lpthread \
//       -o /tmp/frames_test && /tmp/frames_test /tmp/ft
// (Use -DAPERTARCORE_HAS_TURBOJPEG=1 -DAPERTARCORE_HAS_JPEG=1 -lturbojpeg to test the encoder Core is built with.)

#include "DecodeSlots.hpp"
#include "PlaybackFrames.hpp"
#include "cdng/CdngEncoder.hpp"

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

static void writeFrame(const fs::path &dir, const std::string &clip, int number, unsigned bits, bool lossless)
{
    static apertar::CdngEncoder enc;
    static std::mt19937 rng(3);
    const uint32_t w = 1920, h = 1080;
    std::vector<uint16_t> src(size_t(w) * h);
    for (size_t i = 0; i < src.size(); ++i)             // a gradient with noise, so the picture is not flat
        src[i] = uint16_t(((i % w) * ((1u << bits) - 1) / w + rng() % 64) & ((1u << bits) - 1));
    apertar::RawFrameView view;
    view.data = reinterpret_cast<const uint8_t *>(src.data()); view.size = src.size() * 2;
    view.width = w; view.height = h; view.stride = w * 2;
    view.bitDepth = bits == 16 ? apertar::RawBitDepth::Bits16 : apertar::RawBitDepth::Bits12;
    view.unpackedBytesPerSample = 2; view.packing = apertar::PixelPacking::Unpacked;
    view.bayerPattern = apertar::BayerPattern::RGGB;
    apertar::CdngEncoder::Metadata meta;
    meta.compression = lossless ? apertar::CdngCompression::LosslessJpeg : apertar::CdngCompression::Uncompressed;
    meta.fps = 25.0; meta.clipName = clip;
    char name[128];
    std::snprintf(name, sizeof name, "%s_%09d.dng", clip.c_str(), number);
    meta.frameFileName = name;
    enc.writeDngFile((dir / name).string(), view, meta);
}

static bool isJpeg(const std::vector<uint8_t> &b) { return b.size() > 4 && b[0] == 0xFF && b[1] == 0xD8 && b[b.size() - 2] == 0xFF && b[b.size() - 1] == 0xD9; }

int main(int argc, char **argv)
{
    if (argc < 2) { std::fprintf(stderr, "usage: frames_test TMP_DIR\n"); return 2; }
    const fs::path tmp = argv[1];
    fs::remove_all(tmp);
    const std::string clip = "cDNG_26-10-29_C0001";
    fs::create_directories(tmp / clip);
    // numbers 0, 1, 2 (lossless 12-bit), 4 (a hole at 3), 5 (0 bytes), 6; the last is 16-bit uncompressed
    for (int n : {0, 1, 2, 4}) writeFrame(tmp / clip, clip, n, 12, true);
    { std::ofstream(tmp / clip / (clip + "_000000005.dng"), std::ios::binary).close(); }
    writeFrame(tmp / clip, clip, 6, 16, false);
    const FrameList frames = listFrames(tmp / clip);
    const auto never = [] { return false; };
    const auto held = [] { return true; };

    std::printf("frames\n");
    FrameOut a = frameJpeg(clip, tmp / clip, frames, 1, 640, "tok", never);
    check(a.status == 200 && isJpeg(a.jpeg), "frame 1 at 640 w: 200, a complete JPEG (" + std::to_string(a.jpeg.size()) + " B, " + std::to_string(int(a.decodeMs)) + " ms)");
    check(a.number == 1 && a.index == 1 && a.count == 6 && !a.fromCache, "served number 1, index 1 of 6, from a decode");
    check(a.histogram.find(',') != std::string::npos && std::count(a.histogram.begin(), a.histogram.end(), ',') == 47, "histogram: 48 values");
    FrameOut again = frameJpeg(clip, tmp / clip, frames, 1, 640, "tok", never);
    check(again.status == 200 && again.fromCache && again.jpeg == a.jpeg && again.histogram == a.histogram, "the same request again: from the cache, identical");
    FrameOut other = frameJpeg(clip, tmp / clip, frames, 1, 640, "new-token", never);
    check(!other.fromCache, "another token (the clip changed): not from the cache");
    FrameOut thumb = frameJpeg(clip, tmp / clip, frames, 0, 320, "tok", never);
    check(thumb.status == 200 && isJpeg(thumb.jpeg) && thumb.jpeg.size() < a.jpeg.size() + 20000, "a 320 w thumbnail of frame 0");

    std::printf("holes\n");
    FrameOut hole = frameJpeg(clip, tmp / clip, frames, 3, 640, "tok", never);
    check(hole.status == 200 && hole.number == 2, "number 3 was never written: the picture of number 2");
    FrameOut empty = frameJpeg(clip, tmp / clip, frames, 5, 640, "tok", never);
    check(empty.status == 200 && empty.number == 4, "number 5 is a 0-byte file: the picture of number 4");
    FrameOut sixteen = frameJpeg(clip, tmp / clip, frames, 6, 640, "tok", never);
    check(sixteen.status == 200 && sixteen.number == 6 && isJpeg(sixteen.jpeg), "a 16-bit uncompressed frame");
    FrameOut far = frameJpeg(clip, tmp / clip, frames, 99, 640, "tok", never);
    check(far.status == 404, "a number past the last: 404");

    std::printf("hold\n");
    FrameOut stopped = frameJpeg(clip, tmp / clip, frames, 2, 960, "tok", held);
    check(stopped.status == 409 && stopped.error == "Playback is held.", "a take starting during the read: stopped, 409");
    FrameOut cachedInHold = frameJpeg(clip, tmp / clip, frames, 1, 640, "tok", held);
    check(cachedInHold.status == 200 && cachedInHold.fromCache, "a cached picture needs no read, so a hold does not matter to it");
    check(trimIdleFrameSlots(steadyMs(), true) > 0, "a hold gives the slot buffers back");
    check(!allowedFrameWidth(500) && allowedFrameWidth(960), "widths: 960 yes, 500 no");

    std::printf(failures ? "FAILURES %d of %d\n" : "frames ok (%d checks)\n", failures ? failures : checks, checks);
    return failures ? 1 : 0;
}
