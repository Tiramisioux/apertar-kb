// g++ -std=c++20 -O2 -I$SK/src/playback -I$SK/third_party/liblj92 -I$CORE/src -I$CORE/include sizes_test.cpp \
//   $CORE/src/cdng/CdngEncoder.cpp $CORE/src/cdng/LosslessJpegEncoder.cpp $CORE/src/color/ColorProfileConfig.cpp \
//   lj92.o -lyaml -lpthread -o sizes_test && ./sizes_test /tmp/frames
#include "DngFrameReader.hpp"
#include "RawRender.hpp"
#include "cdng/CdngEncoder.hpp"
#include <cstdio>
#include <random>
#include <fcntl.h>
using namespace apertar::playback;
int main(int argc, char **argv) {
    const std::string dir = argc > 1 ? argv[1] : "/tmp";
    struct Size { uint32_t w, h; } sizes[] = {{1928,1090},{2028,1520},{2028,1080},{1332,990},{3856,2180},{1920,1080}};
    int fails = 0; apertar::CdngEncoder enc; std::mt19937 rng(1);
    for (auto sz : sizes) for (unsigned bits : {12u, 16u}) for (int lossless = 0; lossless < 2; ++lossless) {
        std::vector<uint16_t> s(size_t(sz.w) * sz.h);
        for (auto &v : s) v = uint16_t(rng() % (1u << bits));
        apertar::RawFrameView view;
        view.data = reinterpret_cast<const uint8_t *>(s.data()); view.size = s.size() * 2;
        view.width = sz.w; view.height = sz.h; view.stride = sz.w * 2;
        view.bitDepth = bits == 16 ? apertar::RawBitDepth::Bits16 : apertar::RawBitDepth::Bits12;
        view.unpackedBytesPerSample = 2; view.packing = apertar::PixelPacking::Unpacked;
        view.bayerPattern = apertar::BayerPattern::RGGB;
        apertar::CdngEncoder::Metadata meta;
        meta.compression = lossless ? apertar::CdngCompression::LosslessJpeg : apertar::CdngCompression::Uncompressed;
        meta.fps = 50.0; meta.clipName = "t"; meta.frameFileName = "t_000000000.dng";
        char name[256]; std::snprintf(name, sizeof name, "%s/s_%ux%u_%u_%s.dng", dir.c_str(), sz.w, sz.h, bits, lossless ? "lj" : "unc");
        enc.writeDngFile(name, view, meta);
        int fd = ::open(name, O_RDONLY | O_CLOEXEC);
        DngInfo info; std::string err; std::vector<uint16_t> back; std::vector<uint8_t> scratch;
        bool ok = readDngInfo(fd, info, err) && (readDngSamples(fd, info, back, scratch, err) == ReadStatus::Ok); ::close(fd);
        bool same = ok && back == s;
        std::printf("%s tiles %ux%u x%zu read %s bit-exact %s %s\n", name, info.tileWidth, info.tileLength,
                    info.tileOffsets.size(), ok ? "ok" : "FAIL", same ? "yes" : "NO", err.c_str());
        if (ok) (void)renderPreview(info, back, 640);
        fails += !same;
    }
    std::printf(fails ? "FAILURES %d\n" : "sizes ok\n", fails);
    return fails != 0;
}
