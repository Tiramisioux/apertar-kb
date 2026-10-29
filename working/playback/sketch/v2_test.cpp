// Apertar playback, design sketch v2: checks for the points the two critiques raised.
//   frames   ClipFrames: numbers, holes, 0-byte frames, DNG+JPEG stems; the time -> frame map (M1/P1, M7)
//   drift    position clock vs number clock on a 25 fps lossless take with drops (M1/P1, arithmetic)
//   hold     the hold rule and the yield window (M8)
//   stop     a decode in flight stops within one chunk / tile when the yield starts (M8, m2)
//   cache    what a frame read leaves in the page cache, with and without the v2 drop (M4/P19)
//   slots    two slots, three requests: one 503; idle trim and hold trim (M5)
//   alloc    a frame per new thread: v1 per-request buffers against v2 slot buffers (M5, critic A.3)
//   sizes    Core-written 4056x3040 (IMX477) and 3840x2200 frames pass the v2 size cap (M9 cap check)
// Build, from this folder (CORE = Core 0296ed1):
//   gcc -O2 -c third_party/liblj92/lj92.c -o lj92.o
//   g++ -std=c++20 -O2 -Wall -Wextra -Isrc/playback -Ithird_party/liblj92 -I$CORE/src -I$CORE/include v2_test.cpp
//       $CORE/src/cdng/CdngEncoder.cpp $CORE/src/cdng/LosslessJpegEncoder.cpp $CORE/src/color/ColorProfileConfig.cpp
//       lj92.o -lyaml -lpthread -o v2_test
//   ./v2_test frames/ /tmp/v2

#include "ClipFrames.hpp"
#include "DecodeSlots.hpp"
#include "DngFrameReader.hpp"
#include "PlaybackHold.hpp"
#include "RawRender.hpp"
#include "cdng/CdngEncoder.hpp"

#include <algorithm>
#include <chrono>
#include <cstdio>
#include <fstream>
#include <random>
#include <string>
#include <sys/mman.h>
#include <thread>

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

static void testStop(const fs::path &frames)
{
    std::printf("stop\n");
    for (const char *name : {"hdr16_uncompressed.dng", "sdr12_lossless.dng"}) {
        const std::string path = (frames / name).string();
        const int fd = openDngFrame(path.c_str());
        DngInfo info; std::string error; std::vector<uint16_t> s; std::vector<uint8_t> scratch;
        if (fd < 0 || !readDngInfo(fd, info, error)) { check(false, std::string("open ") + name + " " + error); continue; }
        PlaybackYield yield;
        int asked = 0;
        ReadOptions opt;
        opt.stop = [&]() {
            if (++asked == 2) yield.yieldFor(Hold::Recording, steadyMs());   // a take starts after the first chunk
            return yield.active(steadyMs());
        };
        const auto t = Clock::now();
        const ReadStatus st = readDngSamples(fd, info, s, scratch, error, opt);
        const double took = msSince(t);
        closeDngFrame(fd);
        const size_t steps = info.compression == 7 ? info.tileOffsets.size() : (info.height + 127) / 128;
        std::printf("  %s: stopped after %d of %zu %s, %.2f ms, error \"%s\"\n", name, asked - 1, steps,
                    info.compression == 7 ? "tiles" : "chunks of 128 rows", took, error.c_str());
        check(st == ReadStatus::Stopped && asked == 2, std::string(name) + ": Stopped, one chunk read after the yield began");
    }
}

static double residentFraction(const std::string &path)
{
    const int fd = ::open(path.c_str(), O_RDONLY | O_CLOEXEC);
    struct stat st {};
    ::fstat(fd, &st);
    void *map = ::mmap(nullptr, size_t(st.st_size), PROT_READ, MAP_SHARED, fd, 0);
    const long page = ::sysconf(_SC_PAGESIZE);
    const size_t pages = (size_t(st.st_size) + size_t(page) - 1) / size_t(page);
    std::vector<unsigned char> vec(pages);
    ::mincore(map, size_t(st.st_size), vec.data());
    size_t resident = 0;
    for (unsigned char v : vec) resident += v & 1;
    ::munmap(map, size_t(st.st_size));
    ::close(fd);
    return double(resident) / double(pages);
}

static void testCache(const fs::path &frames)
{
    std::printf("cache\n");
    for (const char *name : {"hdr16_uncompressed.dng", "sdr12_lossless.dng"}) {
        const std::string path = (frames / name).string();
        for (int v2 = 0; v2 < 2; ++v2) {
            { const int fd = ::open(path.c_str(), O_RDONLY); ::posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED); ::close(fd); }
            const double before = residentFraction(path);
            const int fd = openDngFrame(path.c_str());
            DngInfo info; std::string error; std::vector<uint16_t> s; std::vector<uint8_t> scratch;
            ReadOptions opt; opt.dropPages = v2 == 1;
            const bool ok = readDngInfo(fd, info, error) && readDngSamples(fd, info, s, scratch, error, opt) == ReadStatus::Ok;
            if (v2) closeDngFrame(fd); else ::close(fd);
            const double after = residentFraction(path);
            std::printf("  %s %s: page cache %.0f %% of the file before, %.0f %% after\n", name,
                        v2 ? "v2 (drop per chunk + at close)" : "v1 (plain pread)", 100 * before, 100 * after);
            if (v2) check(ok && after < 0.02, std::string(name) + ": v2 leaves < 2 % of the frame in the page cache");
            else check(ok && after > 0.9, std::string(name) + ": v1 leaves the whole frame cached (the critic's M4)");
        }
    }
}

static void testSlots()
{
    std::printf("slots\n");
    DecodeSlots slots(2);
    std::atomic<int> got{0}, refused{0}, arrived{0};
    std::vector<std::thread> threads;
    for (int i = 0; i < 3; ++i)
        threads.emplace_back([&]() {
            auto lease = slots.tryTake();
            ++arrived;
            while (arrived.load() < 3) std::this_thread::yield();   // hold the lease until all three asked
            if (lease) { ++got; lease->samples.resize(1 << 20); } else ++refused;
            std::this_thread::sleep_for(std::chrono::milliseconds(20));
        });
    for (auto &t : threads) t.join();
    check(got == 2 && refused == 1, "2 slots, 3 requests at once: 2 decode, 1 gets 503");
    const size_t held = slots.bytesHeld();
    check(slots.trimIdle(steadyMs(), 30000, false) == 0 && slots.bytesHeld() == held, "buffers kept while used recently");
    check(slots.trimIdle(steadyMs() + 30001, 30000, false) == held && slots.bytesHeld() == 0, "freed after 30 s idle");
    { auto lease = slots.tryTake(); lease->samples.resize(1 << 20); }
    check(slots.trimIdle(steadyMs(), 30000, true) > 0 && slots.bytesHeld() == 0, "freed at once when a hold starts");
}

static double decodeOnNewThread(const std::string &path, DecodeSlot *slot)
{
    double took = 0;
    std::thread([&]() {
        const auto t = Clock::now();
        const int fd = openDngFrame(path.c_str());
        DngInfo info; std::string error;
        std::vector<uint16_t> freshSamples; std::vector<uint8_t> freshScratch;
        auto &s = slot ? slot->samples : freshSamples;
        auto &scratch = slot ? slot->scratch : freshScratch;
        ReadOptions opt; opt.dropPages = false;   // timing of compute only (warm cache), as critic A.3
        if (readDngInfo(fd, info, error) && readDngSamples(fd, info, s, scratch, error, opt) == ReadStatus::Ok) {
            const Rgb8Image img = renderPreview(info, s, 640);
            (void)rawHistogram(info, s);
            (void)img;
        }
        ::close(fd);
        took = msSince(t);
    }).join();
    return took;
}

static void testAlloc(const fs::path &frames)
{
    std::printf("alloc\n");
    for (const char *name : {"hdr16_uncompressed.dng", "sdr12_uncompressed.dng", "sdr12_lossless.dng"}) {
        const std::string path = (frames / name).string();
        DecodeSlot slot;
        decodeOnNewThread(path, &slot);   // warm the slot and the page cache
        std::vector<double> fresh, kept;
        for (int i = 0; i < 7; ++i) { fresh.push_back(decodeOnNewThread(path, nullptr)); kept.push_back(decodeOnNewThread(path, &slot)); }
        std::printf("  %-24s new thread per frame: per-request buffers %.1f ms, slot buffers %.1f ms (medians of 7)\n",
                    name, median(fresh), median(kept));
        check(median(kept) <= median(fresh) * 1.05, std::string(name) + ": slot buffers no slower");
    }
}

static void testSizes(const fs::path &tmp)
{
    std::printf("sizes\n");
    struct Size { uint32_t w, h; unsigned bits; bool lossless; } sizes[] = {
        {4056, 3040, 12, true}, {4056, 3040, 12, false}, {3840, 2200, 16, false}, {3840, 2200, 16, true}};
    apertar::CdngEncoder enc;
    std::mt19937 rng(5);
    for (const Size &z : sizes) {
        std::vector<uint16_t> src(size_t(z.w) * z.h);
        for (auto &v : src) v = uint16_t(rng() % (1u << z.bits));
        apertar::RawFrameView view;
        view.data = reinterpret_cast<const uint8_t *>(src.data()); view.size = src.size() * 2;
        view.width = z.w; view.height = z.h; view.stride = z.w * 2;
        view.bitDepth = z.bits == 16 ? apertar::RawBitDepth::Bits16 : apertar::RawBitDepth::Bits12;
        view.unpackedBytesPerSample = 2; view.packing = apertar::PixelPacking::Unpacked;
        view.bayerPattern = apertar::BayerPattern::RGGB;
        apertar::CdngEncoder::Metadata meta;
        meta.compression = z.lossless ? apertar::CdngCompression::LosslessJpeg : apertar::CdngCompression::Uncompressed;
        meta.fps = 25.0; meta.clipName = "t"; meta.frameFileName = "t_000000000.dng";
        char name[256];
        std::snprintf(name, sizeof name, "%s/size_%ux%u_%u_%s.dng", tmp.c_str(), z.w, z.h, z.bits, z.lossless ? "lj" : "unc");
        enc.writeDngFile(name, view, meta);
        const int fd = openDngFrame(name);
        DngInfo info; std::string error; std::vector<uint16_t> back; std::vector<uint8_t> scratch;
        const bool ok = readDngInfo(fd, info, error) && readDngSamples(fd, info, back, scratch, error) == ReadStatus::Ok;
        closeDngFrame(fd);
        check(ok && back == src, std::string(name).substr(tmp.string().size() + 1) + ": passes the cap, bit-exact" +
              (error.empty() ? "" : " (" + error + ")"));
        fs::remove(name);
    }
}

int main(int argc, char **argv)
{
    if (argc < 3) { std::fprintf(stderr, "usage: v2_test FRAMES_DIR TMP_DIR\n"); return 2; }
    const fs::path frames = argv[1], tmp = argv[2];
    fs::create_directories(tmp);
    testFrames(tmp);
    testDrift();
    testHold();
    testStop(frames);
    testCache(frames);
    testSlots();
    testAlloc(frames);
    testSizes(tmp);
    std::printf(failures ? "FAILURES %d of %d\n" : "v2 ok (%d checks)\n", failures ? failures : checks, checks);
    return failures ? 1 : 0;
}
