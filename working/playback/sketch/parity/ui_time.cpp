// Design sketch: what the touch UI's own path costs per frame on this host (decode + 640x360 render).
#include "RawPreview.hpp"
#include "dngdecoder.h"
#include <QImage>
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <vector>
int main(int argc, char **argv)
{
    using C = std::chrono::steady_clock;
    for (int a = 1; a < argc; ++a) {
        std::vector<double> dec, ren;
        for (int i = 0; i < 5; ++i) {
            RawFrame f;
            auto t0 = C::now();
            DngDecoder::decodeFileInto(QString::fromLocal8Bit(argv[a]), f);
            auto t1 = C::now();
            QImage q = renderRawFramePreview(f, QSize(640, 360));
            auto t2 = C::now();
            dec.push_back(std::chrono::duration<double, std::milli>(t1 - t0).count());
            ren.push_back(std::chrono::duration<double, std::milli>(t2 - t1).count());
        }
        std::sort(dec.begin(), dec.end()); std::sort(ren.begin(), ren.end());
        std::printf("touch UI path  %-24s decode %6.1f ms | render 640x360 %5.1f ms\n", strrchr(argv[a], '/') + 1, dec[2], ren[2]);
    }
}
