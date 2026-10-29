// Design sketch: the Core-side copy of the touch UI's look (RawRender.hpp) against the touch UI's
// own code (ApertarUI d8098d0: dngdecoder.cpp, cdngimageprovider.cpp), on the same Core-written DNGs.
#include "DngFrameReader.hpp"
#include "RawRender.hpp"
#include "RawPreview.hpp"   // touch UI: renderRawFramePreview
#include "dngdecoder.h"     // touch UI: DngDecoder
#include <QImage>
#include <cstdio>
#include <cstdlib>
using namespace apertar::playback;
int main(int argc, char **argv)
{
    int failures = 0;
    for (int a = 1; a < argc; ++a) {
        RawFrame ui;
        DngDecoder::decodeFileInto(QString::fromLocal8Bit(argv[a]), ui);
        const int fd = ::open(argv[a], O_RDONLY);
        DngInfo info; std::string error; std::vector<uint16_t> s; std::vector<uint8_t> scratch;
        const bool ok = readDngInfo(fd, info, error) && (readDngSamples(fd, info, s, scratch, error) == ReadStatus::Ok);
        ::close(fd);
        if (!ok || !ui.valid) { std::printf("FAIL %s: %s %s\n", argv[a], error.c_str(), qPrintable(ui.error)); ++failures; continue; }
        size_t sampleDiff = 0;
        for (size_t i = 0; i < s.size() && i < size_t(ui.pixels.size()); ++i) sampleDiff += s[i] != ui.pixels[int(i)];
        const QImage q = renderRawFramePreview(ui, QSize(640, 360));
        const Rgb8Image m = renderPreview(info, s, 640);
        int maxDiff = 0; size_t differing = 0; double sum = 0;
        for (int y = 0; y < 360; ++y) for (int x = 0; x < 640; ++x) {
            const QRgb p = q.pixel(x, y);
            const uint8_t *c = m.rgb.data() + (size_t(y) * m.width + x) * 3;
            const int d = std::max({std::abs(qRed(p) - c[0]), std::abs(qGreen(p) - c[1]), std::abs(qBlue(p) - c[2])});
            maxDiff = std::max(maxDiff, d); differing += d > 0; sum += d;
        }
        const QVariantList uiBins = DngDecoder::decodeHistogramBins(QString::fromLocal8Bit(argv[a]), 48, 16000);
        const auto bins = rawHistogram(info, s);
        double binDiff = 0;
        for (int i = 0; i < 48 && i < uiBins.size(); ++i) binDiff = std::max(binDiff, std::abs(uiBins[i].toDouble() - bins[size_t(i)]));
        std::printf("%-26s samples differ %zu | black UI %.1f / copy %.1f, white %.0f / %.0f | 640x360: max diff %d, "
                    "pixels differing %zu (%.3f%%), mean %.4f | histogram max bin diff %.4f (UI bins %lld)\n",
                    strrchr(argv[a], '/') + 1, sampleDiff, ui.blackLevel, info.black, ui.whiteLevel, info.white,
                    maxDiff, differing, 100.0 * differing / (640 * 360), sum / (640 * 360), binDiff, (long long)uiBins.size());
        if (sampleDiff || maxDiff > 1 || binDiff > 1e-3 || uiBins.size() != 48) ++failures;
    }
    std::printf(failures ? "PARITY FAILURES: %d\n" : "parity ok (%d)\n", failures);
    return failures ? 1 : 0;
}
