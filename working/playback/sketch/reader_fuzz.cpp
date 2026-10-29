// Design sketch: feed truncated and byte-flipped copies of Core-written DNGs to the reader.
// Pass = no crash, no sanitizer report; every bad file gives ok or an error string.
#include "DngFrameReader.hpp"
#include "RawRender.hpp"
#include <cstring>
#include <fstream>
#include <iostream>
#include <iterator>
#include <random>
#include <sys/resource.h>
using namespace apertar::playback;
int main(int argc, char **argv)
{
    std::mt19937 rng(7);
    int runs = 0, rejected = 0;
    const std::string tmp = std::string(argv[1]) + "/fuzz.dng";
    for (int a = 2; a < argc; ++a) {
        std::ifstream in(argv[a], std::ios::binary);
        const std::vector<char> orig((std::istreambuf_iterator<char>(in)), {});
        for (int i = 0; i < 160; ++i) {
            std::vector<char> b = orig;
            if (i % 2 == 0) {
                b.resize(std::uniform_int_distribution<size_t>(0, orig.size())(rng));      // truncation
            } else {
                const int flips = 1 + i % 16;
                for (int f = 0; f < flips; ++f) {                                             // flips, half in the tail
                    const size_t lo = (f % 2) ? orig.size() - 4096 : 0;
                    b[std::uniform_int_distribution<size_t>(lo, orig.size() - 1)(rng)] ^= char(1 << (f % 8));
                }
                if (i % 4 == 1) {                                  // also hit the entry values of IFD0 head-on
                    const uint32_t ifd = uint32_t(uint8_t(orig[4])) | uint32_t(uint8_t(orig[5])) << 8 |
                                         uint32_t(uint8_t(orig[6])) << 16 | uint32_t(uint8_t(orig[7])) << 24;
                    const size_t entry = ifd + 2 + 12 * std::uniform_int_distribution<size_t>(0, 12)(rng);
                    if (entry + 12 <= b.size()) b[entry + 8 + (i % 4)] ^= char(0xA5);
                }
            }
            { std::ofstream out(tmp, std::ios::binary | std::ios::trunc); out.write(b.data(), std::streamsize(b.size())); }
            const int fd = ::open(tmp.c_str(), O_RDONLY);
            DngInfo info; std::string error; std::vector<uint16_t> s; std::vector<uint8_t> scratch;
            bool ok = readDngInfo(fd, info, error) && (readDngSamples(fd, info, s, scratch, error) == ReadStatus::Ok);
            if (ok) { auto img = renderPreview(info, s, 320); (void)rawHistogram(info, s); (void)img; }
            ::close(fd);
            ++runs; if (!ok) ++rejected;
        }
    }
    std::cout << "fuzz runs " << runs << ", rejected with an error " << rejected << ", no crash\n";

    // v2 (critic M9): lie about the size in IFD0. Every lie must be refused by readDngInfo, before
    // readDngSamples allocates anything, and the process must stay small.
    struct Lie { uint32_t w, h; } lies[] = {{16384, 16384}, {4096, 3072}, {8192, 2}, {2, 65535}, {4056, 3040}};
    int lieRuns = 0, lieRefusedByInfo = 0;
    for (int a = 2; a < argc; ++a) {
        std::ifstream in(argv[a], std::ios::binary);
        const std::vector<char> orig((std::istreambuf_iterator<char>(in)), {});
        const auto rd16 = [&](size_t o) { return uint32_t(uint8_t(orig[o])) | uint32_t(uint8_t(orig[o + 1])) << 8; };
        const uint32_t ifd = rd16(4) | rd16(6) << 16;
        for (const Lie &lie : lies) {
            std::vector<char> b = orig;
            for (uint32_t i = 0; i < rd16(ifd); ++i) {
                const size_t e = ifd + 2 + 12 * i;
                const uint32_t tag = rd16(e), type = rd16(e + 2);
                if (tag != 256 && tag != 257) continue;
                const uint32_t v = tag == 256 ? lie.w : lie.h;
                if (type == 3) { b[e + 8] = char(v & 0xff); b[e + 9] = char(v >> 8); }
                else for (int k = 0; k < 4; ++k) b[e + 8 + k] = char((v >> (8 * k)) & 0xff);
            }
            { std::ofstream out(tmp, std::ios::binary | std::ios::trunc); out.write(b.data(), std::streamsize(b.size())); }
            const int fd = ::open(tmp.c_str(), O_RDONLY);
            DngInfo info; std::string error; std::vector<uint16_t> s; std::vector<uint8_t> scratch;
            const bool okInfo = readDngInfo(fd, info, error);
            const bool ok = okInfo && readDngSamples(fd, info, s, scratch, error) == ReadStatus::Ok;
            ::close(fd);
            ++lieRuns; if (!okInfo) ++lieRefusedByInfo;
            std::cout << "  size lie " << lie.w << "x" << lie.h << " in " << strrchr(argv[a], '/') + 1 << ": "
                      << (ok ? "decoded" : "refused") << (okInfo ? " after readDngInfo" : " by readDngInfo")
                      << (error.empty() ? "" : " (" + error + ")") << "\n";
        }
    }
    rusage ru{}; getrusage(RUSAGE_SELF, &ru);
    std::cout << "size lies " << lieRuns << ", refused by readDngInfo " << lieRefusedByInfo
              << ", max RSS " << ru.ru_maxrss / 1024 << " MB\n";
}
