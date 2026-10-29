// Design sketch: write 4K 12-bit frames with Core's LossyDngEncoder (3:1 and 5:1), so the
// sketch reader and the touch UI's own decoder can be compared on them (parity_test).
#include "lossydng/LossyDngEncoder.hpp"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <random>
#include <string>
#include <vector>
int main(int argc, char **argv)
{
    const std::string dir = argc > 1 ? argv[1] : ".";
    const uint32_t w = 3840, h = 2160; const unsigned bits = 12;
    std::vector<uint16_t> s(size_t(w) * h);
    std::mt19937 rng(1234);
    const double maxv = (1u << bits) - 1;
    std::normal_distribution<double> noise(0.0, maxv * 0.004);
    for (uint32_t y = 0; y < h; ++y)
        for (uint32_t x = 0; x < w; ++x) {
            double v = 0.08 + 0.55 * x / w + 0.25 * std::sin(y * 0.004) * std::cos(x * 0.003);
            if (((x / 480) + (y / 360)) % 3 == 0) v *= 0.5;
            const int c = int((y & 1) * 2 + (x & 1));
            v *= c == 0 ? 0.55 : (c == 3 ? 0.40 : 1.0);
            s[size_t(y) * w + x] = uint16_t(std::clamp(v * maxv * 0.9 + 0.015 * maxv + noise(rng), 0.0, maxv));
        }
    apertar::RawFrameView view;
    view.data = reinterpret_cast<const uint8_t *>(s.data());
    view.size = s.size() * 2; view.width = w; view.height = h; view.stride = w * 2;
    view.bitDepth = apertar::RawBitDepth::Bits12; view.unpackedBytesPerSample = 2;
    view.packing = apertar::PixelPacking::Unpacked; view.bayerPattern = apertar::BayerPattern::RGGB;
    const struct { apertar::LossyDngRatio r; const char *name; } cases[] = {
        {apertar::LossyDngRatio::R3, "sdr12_lossy3.dng"}, {apertar::LossyDngRatio::R5, "sdr12_lossy5.dng"}};
    for (const auto &k : cases) {
        apertar::LossyDngEncoder enc(k.r);
        apertar::CdngEncoder::Metadata meta;
        meta.compression = apertar::CdngCompression::LosslessJpeg;
        meta.fps = 25.0; meta.clipName = "cDNG_3to1_26-10-28_C0001";
        meta.frameFileName = "cDNG_3to1_26-10-28_C0001_000000000.dng";
        enc.writeDngFile(dir + "/" + k.name, view, meta);
        apertar::LossyDngEncoder::drainWrites();
        std::printf("wrote %s\n", k.name);
    }
    return 0;
}
