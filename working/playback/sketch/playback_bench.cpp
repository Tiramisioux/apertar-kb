// Apertar playback, design sketch: does a small Qt-free reader decode Core's own DNGs, and what
// does one browser frame cost? Two modes:
//   playback_bench --synthetic DIR   write 4K frames with Core's CdngEncoder (12/16-bit,
//                                    uncompressed/lossless), read them back, check every sample,
//                                    time each step
//   playback_bench [--cold] FILE.dng ...  time the same steps on real frames (run this on the Pi);
//                                    --cold drops each file from the page cache first (as a first play)
// Build (host or Pi), from this folder:
//   gcc -O2 -c third_party/liblj92/lj92.c -o lj92.o
//   g++ -std=c++20 -O2 -DHAVE_JPEG -Isrc/playback -Ithird_party/liblj92 -I$CORE/src -I$CORE/include
//       playback_bench.cpp $CORE/src/cdng/CdngEncoder.cpp $CORE/src/cdng/LosslessJpegEncoder.cpp
//       $CORE/src/color/ColorProfileConfig.cpp lj92.o -ljpeg -lyaml -lpthread -o playback_bench
// File mode needs no Core sources: add -DNO_CORE_ENCODER and drop the three Core .cpp files and -lyaml.

#include "DngFrameReader.hpp"
#include "RawRender.hpp"

#ifndef NO_CORE_ENCODER
#include "cdng/CdngEncoder.hpp"
#endif
#ifdef HAVE_JPEG
#include <cstdio>
#include <jpeglib.h>
#endif

#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <functional>
#include <iostream>
#include <random>
#include <string>
#include <thread>
#include <vector>

using namespace apertar::playback;
using Clock = std::chrono::steady_clock;

static int failures = 0;
static bool coldReads = false;
static void check(bool ok, const std::string &what)
{
    std::cout << (ok ? "  ok   " : "  FAIL ") << what << "\n";
    if (!ok) ++failures;
}

static double ms(Clock::time_point a, Clock::time_point b)
{
    return std::chrono::duration<double, std::milli>(b - a).count();
}

static double median(std::vector<double> v)
{
    std::sort(v.begin(), v.end());
    return v.empty() ? 0.0 : v[v.size() / 2];
}

#ifdef HAVE_JPEG
static size_t encodeJpeg(const Rgb8Image &img, int quality, std::vector<uint8_t> &out)
{
    jpeg_compress_struct c{};
    jpeg_error_mgr err{};
    c.err = jpeg_std_error(&err);
    jpeg_create_compress(&c);
    unsigned char *mem = nullptr;
    unsigned long size = 0;
    jpeg_mem_dest(&c, &mem, &size);
    c.image_width = img.width;
    c.image_height = img.height;
    c.input_components = 3;
    c.in_color_space = JCS_RGB;
    jpeg_set_defaults(&c);
    jpeg_set_quality(&c, quality, TRUE);
    c.dct_method = JDCT_IFAST;
    jpeg_start_compress(&c, TRUE);
    while (c.next_scanline < c.image_height) {
        JSAMPROW row = const_cast<uint8_t *>(img.rgb.data() + size_t(c.next_scanline) * img.width * 3);
        jpeg_write_scanlines(&c, &row, 1);
    }
    jpeg_finish_compress(&c);
    out.assign(mem, mem + size);
    free(mem);
    jpeg_destroy_compress(&c);
    return out.size();
}
#endif

// One frame, timed step by step, as the frame route would do it.
static void timeFrame(const std::string &path, int repeats, bool writeSample)
{
    std::vector<double> tInfo, tRead, tR640, tR960, tR1920, tHist, tJpeg;
    size_t jpegBytes = 0, payloadBytes = 0;
    DngInfo info;
    for (int i = 0; i < repeats; ++i) {
        const int fd = ::open(path.c_str(), O_RDONLY | O_CLOEXEC);
        if (fd < 0) { std::cout << "  cannot open " << path << "\n"; ++failures; return; }
        if (coldReads)
            ::posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED);   // clean pages only; no root needed
        std::string error;
        std::vector<uint16_t> samples;
        std::vector<uint8_t> scratch;
        info = DngInfo{};
        auto t0 = Clock::now();
        const bool okInfo = readDngInfo(fd, info, error);
        auto t1 = Clock::now();
        const bool okRead = okInfo && (readDngSamples(fd, info, samples, scratch, error) == ReadStatus::Ok);
        auto t2 = Clock::now();
        ::close(fd);
        if (!okRead) { std::cout << "  FAIL " << path << ": " << error << "\n"; ++failures; return; }
        payloadBytes = info.compression == 7 ? 0 : info.stripBytes;
        if (info.compression == 7) for (uint32_t b : info.tileBytes) payloadBytes += b;
        const Rgb8Image p640 = renderPreview(info, samples, 640);
        auto t3 = Clock::now();
        const Rgb8Image p960 = renderPreview(info, samples, 960);
        auto t4 = Clock::now();
        const Rgb8Image p1920 = renderPreview(info, samples, 1920);
        auto t5 = Clock::now();
        const auto bins = rawHistogram(info, samples);
        auto t6 = Clock::now();
        (void)bins;
        tInfo.push_back(ms(t0, t1)); tRead.push_back(ms(t1, t2)); tR640.push_back(ms(t2, t3));
        tR960.push_back(ms(t3, t4)); tR1920.push_back(ms(t4, t5)); tHist.push_back(ms(t5, t6));
#ifdef HAVE_JPEG
        std::vector<uint8_t> jpeg;
        auto t7 = Clock::now();
        jpegBytes = encodeJpeg(p960, 80, jpeg);
        tJpeg.push_back(ms(t7, Clock::now()));
        if (writeSample && i == 0) {
            const std::string out = path + ".960.jpg";
            if (FILE *f = std::fopen(out.c_str(), "wb")) { std::fwrite(jpeg.data(), 1, jpeg.size(), f); std::fclose(f); }
        }
#else
        (void)writeSample;
#endif
    }
    std::printf("  %-34s %ux%u %2u-bit %-12s payload %5.1f MB, tail %u B, fps %.3f\n",
                std::filesystem::path(path).filename().c_str(), info.width, info.height, info.bits,
                info.compression == 7 ? "lossless" : "uncompressed", payloadBytes / 1e6, info.tailBytesRead, info.fps);
    std::printf("    ms (median of %d): tags %.2f | samples %.1f | render 640w %.1f, 960w %.1f, 1920w %.1f | "
                "histogram %.2f | jpeg 960w q80 %.2f (%zu B)\n",
                repeats, median(tInfo), median(tRead), median(tR640), median(tR960), median(tR1920),
                median(tHist), median(tJpeg), jpegBytes);
    const double play = median(tInfo) + median(tRead) + median(tR640) + median(tHist) + median(tJpeg);
    const double pause = median(tInfo) + median(tRead) + median(tR1920) + median(tHist) + median(tJpeg);
    std::printf("    one worker: %.0f ms per 640w play frame = %.1f fps; %.0f ms per 1920w paused frame\n",
                play, play > 0 ? 1000.0 / play : 0.0, pause);
}

#ifndef NO_CORE_ENCODER
static std::vector<uint16_t> syntheticScene(uint32_t w, uint32_t h, unsigned bits)
{
    // Gradients, a few hard edges and sensor-like noise, so lossless JPEG compresses about as
    // much as a real scene (pure gradients would flatter the decoder).
    std::vector<uint16_t> s(size_t(w) * h);
    std::mt19937 rng(1234);
    const double maxv = (1u << bits) - 1;
    std::normal_distribution<double> noise(0.0, maxv * 0.004);
    for (uint32_t y = 0; y < h; ++y)
        for (uint32_t x = 0; x < w; ++x) {
            double v = 0.08 + 0.55 * x / w + 0.25 * std::sin(y * 0.004) * std::cos(x * 0.003);
            if (((x / 480) + (y / 360)) % 3 == 0) v *= 0.5;            // blocks: edges
            const int c = int((y & 1) * 2 + (x & 1));                 // R, Gr, Gb, B
            v *= c == 0 ? 0.55 : (c == 3 ? 0.40 : 1.0);               // CFA colour
            s[size_t(y) * w + x] = uint16_t(std::clamp(v * maxv * 0.9 + 0.015 * maxv + noise(rng), 0.0, maxv));
        }
    return s;
}

static void synthetic(const std::string &dir, int repeats)
{
    std::filesystem::create_directories(dir);
    const uint32_t w = 3840, h = 2160;
    struct Case { unsigned bits; apertar::CdngCompression compression; const char *name; };
    const Case cases[] = {
        {12, apertar::CdngCompression::Uncompressed, "sdr12_uncompressed.dng"},
        {12, apertar::CdngCompression::LosslessJpeg, "sdr12_lossless.dng"},
        {16, apertar::CdngCompression::Uncompressed, "hdr16_uncompressed.dng"},
        {16, apertar::CdngCompression::LosslessJpeg, "hdr16_lossless.dng"},
    };
    apertar::CdngEncoder encoder;
    for (const Case &k : cases) {
        const auto scene = syntheticScene(w, h, k.bits);
        apertar::RawFrameView view;
        view.data = reinterpret_cast<const uint8_t *>(scene.data());
        view.size = scene.size() * 2;
        view.width = w;
        view.height = h;
        view.stride = w * 2;
        view.bitDepth = k.bits == 16 ? apertar::RawBitDepth::Bits16 : apertar::RawBitDepth::Bits12;
        view.unpackedBytesPerSample = 2;
        view.packing = apertar::PixelPacking::Unpacked;
        view.bayerPattern = apertar::BayerPattern::RGGB;
        apertar::CdngEncoder::Metadata meta;
        meta.compression = k.compression;
        meta.fps = 25.0;
        meta.clipName = "cDNG_26-10-28_C0001";
        meta.frameFileName = "cDNG_26-10-28_C0001_000000000.dng";
        const std::string path = dir + "/" + k.name;
        const auto t0 = Clock::now();
        encoder.writeDngFile(path, view, meta);
        const double encodeMs = ms(t0, Clock::now());

        const int fd = ::open(path.c_str(), O_RDONLY | O_CLOEXEC);
        DngInfo info;
        std::string error;
        std::vector<uint16_t> back;
        std::vector<uint8_t> scratch;
        const bool ok = fd >= 0 && readDngInfo(fd, info, error) && (readDngSamples(fd, info, back, scratch, error) == ReadStatus::Ok);
        if (fd >= 0) ::close(fd);
        std::cout << k.name << " (Core encoder " << int(encodeMs) << " ms on this host)\n";
        check(ok, "reader opens Core's file" + (error.empty() ? std::string() : ": " + error));
        if (!ok) continue;
        check(info.width == w && info.height == h && info.bits == k.bits, "size and bit depth from IFD0");
        check(info.compression == (k.compression == apertar::CdngCompression::LosslessJpeg ? 7 : 1), "compression tag");
        check(std::abs(info.fps - 25.0) < 1e-6, "FrameRate 51044 = 25");
        check(info.pageName == meta.frameFileName, "PageName = frame file name");
        check(!info.dateTimeOriginal.empty(), "DateTimeOriginal present");
        check(info.hasCm1 && info.hasNeutral, "ColorMatrix1 and AsShotNeutral present");
        check(info.tailBytesRead < 8192, "tags cost one small tail read (" + std::to_string(info.tailBytesRead) + " B)");
        check(back == scene, "every sample equals what Core encoded (bit-exact)");
        timeFrame(path, repeats, true);
    }
}
#endif

int main(int argc, char **argv)
{
    if (argc < 2) {
        std::cerr << "usage: playback_bench --synthetic DIR | FILE.dng ...\n";
        return 2;
    }
    const int repeats = 5;
    std::cout << "threads available: " << std::thread::hardware_concurrency() << "\n";
    if (std::string(argv[1]) == "--synthetic") {
#ifndef NO_CORE_ENCODER
        synthetic(argc > 2 ? argv[2] : "bench-frames", repeats);
#else
        std::cerr << "built without Core's encoder\n";
        return 2;
#endif
    } else {
        for (int i = 1; i < argc; ++i) {
            if (std::string(argv[i]) == "--cold") { coldReads = true; continue; }
            timeFrame(argv[i], repeats, false);
        }
    }
    std::cout << (failures ? "FAILURES: " + std::to_string(failures) : std::string("all ok")) << "\n";
    return failures ? 1 : 0;
}
