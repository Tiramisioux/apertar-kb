// Host test for apertar-core's src/camera/ModeLadder.hpp (T34).
// Build: g++ -std=c++20 -Wall -Wextra -I<apertar-core>/src mode_ladder_test.cpp -o mode_ladder_test
#include "camera/ModeLadder.hpp"
#include <cstdio>

static int failures = 0;
static void check(bool ok, const char *what) { std::printf("  [%s] %s\n", ok ? "ok" : "FAIL", what); if (!ok) ++failures; }

int main()
{
    using namespace apertar::ladder;
    std::string error;
    Ladder patrik;
    patrik.enabled = true;

    std::printf("1. parse and print\n");
    check(parseRungs("3840x2160:16:hdr:25,3840x2160:12:sdr", patrik.rungs, error), "Patrik's ladder parses");
    check(patrik.rungs.size() == 2 && patrik.rungs[0].clearHdr && patrik.rungs[0].bits == 16 &&
          patrik.rungs[0].threshold == 25.0 && !patrik.rungs[1].clearHdr && patrik.rungs[1].threshold == 0.0,
          "fields read");
    check(rungsText(patrik.rungs) == "3840x2160:16:hdr:25,3840x2160:12:sdr", "prints back the same text");
    std::vector<Rung> tmp;
    check(parseRungs("3840x2160:12:sdr:", tmp, error) && tmp[0].threshold == 0.0, "empty threshold after ':'");
    check(!parseRungs("3840x2160:14:sdr", tmp, error), "14-bit refused");
    check(!parseRungs("3840x2160:12:sdr:abc", tmp, error), "bad threshold refused");
    check(!parseRungs("", tmp, error), "empty ladder refused");
    check(label(patrik.rungs[0]) == "4K Clear HDR 16-bit" && classLabel(patrik.rungs[1]) == "SDR12", "labels");

    std::printf("2. chooser (rung 1 = HDR16 up to 25, rung 2 = SDR12 mode ceiling 50)\n");
    const std::vector<RungState> states{ {true, true, 25.0}, {true, true, 50.0} };
    check(chooseRung(patrik, states, 1.0) == 0, "1 fps -> rung 1");
    check(chooseRung(patrik, states, 24.0) == 0, "24 -> rung 1");
    check(chooseRung(patrik, states, 25.0) == 0, "25 -> rung 1 (upper bound inclusive)");
    check(chooseRung(patrik, states, 25.001) == 1, "25.001 -> rung 2");
    check(chooseRung(patrik, states, 50.0) == 1, "50 -> rung 2");
    check(chooseRung(patrik, states, 60.0) == 1, "60 -> rung 2 (highest ceiling; Core then clamps to 50)");
    check(ladderCeiling(patrik, states) == 50.0, "ladder ceiling 50");
    const std::vector<RungState> lossless{ {true, true, 25.0}, {true, true, 30.0} };
    check(chooseRung(patrik, lossless, 50.0) == 1 && ladderCeiling(patrik, lossless) == 30.0, "lossless: top 30");
    const std::vector<RungState> lossy{ {true, false, 0.0}, {true, true, 50.0} };
    check(chooseRung(patrik, lossy, 24.0) == 1, "rung 1 unusable (lossy has no Clear HDR) -> rung 2");
    const std::vector<RungState> none{ {true, false, 0.0}, {true, false, 0.0} };
    check(chooseRung(patrik, none, 24.0) == -1, "no usable rung -> -1");

    std::printf("3. invariant (Cinemate ff59dd8): no reachable request outruns the rung it lands in\n");
    bool invariant = true;
    for (double fps = 0.5; fps <= ladderCeiling(patrik, states) + 0.0001; fps += 0.5) {
        const int i = chooseRung(patrik, states, fps);
        invariant = invariant && i >= 0 && rungCeiling(patrik.rungs[i], states[i]) >= fps - 0.0005;
    }
    check(invariant, "0.5 .. 50 fps all served");

    std::printf("4. validation\n");
    std::vector<std::string> errors, warnings;
    validate(patrik, states, errors, warnings);
    check(errors.empty() && warnings.size() == 1, "Patrik's ladder: no errors, one look-change warning");
    Ladder bad = patrik;
    parseRungs("3840x2160:12:sdr:30,3840x2160:16:hdr:25,3840x2160:12:sdr", bad.rungs, error);
    errors.clear(); warnings.clear();
    validate(bad, { {true, true, 50.0}, {true, true, 25.0}, {true, true, 50.0} }, errors, warnings);
    check(errors.size() == 2, "falling threshold and a repeat both refused");
    errors.clear(); warnings.clear();
    validate(patrik, { {false, false, 0.0}, {true, true, 50.0} }, errors, warnings);
    check(errors.size() == 1, "not a mode of this sensor refused");
    errors.clear(); warnings.clear();
    Ladder high = patrik;
    high.rungs[1].threshold = 50.0;
    validate(high, lossless, errors, warnings);
    check(errors.empty() && warnings.size() == 2, "threshold above the lossless cap warns");

    std::printf("5. file\n");
    patrik.rampReady = true;
    const Ladder back = parseFile(fileText(patrik));
    check(back.enabled && back.rampReady && rungsText(back.rungs) == rungsText(patrik.rungs), "round trip");
    check(!parseFile("enabled=true\nresolutions=garbage\n").enabled, "a broken file leaves the ladder off");
    check(parseFile("enabled=true\nrungs=3840x2160:12:sdr\n").enabled, "the first file key (rungs) still reads");

    std::printf("6. reply\n");
    const std::string json = toJson(patrik, states, 0, { { patrik.rungs[1], states[1] } }, {}, { "a \"quoted\" note" });
    check(json.find("\"ceiling\":50,\"running_resolution\":1") != std::string::npos, "ceiling and running resolution");
    check(json.find("\"class\":\"HDR16\"") != std::string::npos && json.find("\"from\":25") != std::string::npos,
          "rung 1 class, rung 2 serves from 25");
    check(json.find("\\\"quoted\\\"") != std::string::npos, "quotes escaped");

    std::printf("7. compression per resolution\n");
    {
        std::vector<Rung> c;
        check(parseRungs("3840x2160:16:hdr:25:none,3840x2160:12:sdr::lossy_3to1", c, error), "compression field parses");
        check(c.size() == 2 && c[0].compression == "none" && c[0].threshold == 25.0 && c[1].compression == "lossy_3to1" &&
              c[1].threshold == 0.0, "fields read, empty threshold before a compression");
        check(rungsText(c) == "3840x2160:16:hdr:25:none,3840x2160:12:sdr::lossy_3to1", "prints back the same text");
        check(rungsText(patrik.rungs) == "3840x2160:16:hdr:25,3840x2160:12:sdr", "no compression: the text is unchanged");
        check(!parseRungs("3840x2160:12:sdr::zip", c, error), "unknown compression refused");
        check(effectiveCompression(patrik.rungs[0]) == "none" && effectiveCompression(patrik.rungs[1]) == "lossless_jpeg",
              "defaults: Clear HDR uncompressed, SDR lossless");
        Ladder lossyHdr; std::vector<std::string> e2, w2;
        parseRungs("3840x2160:16:hdr:25:lossy_3to1", lossyHdr.rungs, error);
        validate(lossyHdr, std::vector<RungState>{ {true, true, 25.0} }, e2, w2);
        check(!e2.empty(), "lossy DNG with Clear HDR is an error");
        const std::string json2 = toJson(patrik, states, 0, {}, {}, {});
        check(json2.find("\"compression\":\"none\",\"compression_set\":false") != std::string::npos, "JSON carries the compression");
    }

    std::printf(failures ? "FAILED: %d\n" : "all ok\n", failures);
    return failures ? 1 : 0;
}
