// Host test for src/hardware/ActionCatalog.hpp (controls plan, T36): the catalog gives what the old normalizers gave.
// Build: g++ -std=c++20 -Wall -Wextra -Werror -I. -I<core>/src controls_test.cpp -o controls_test
// Run:   ./controls_test <core-tree>      (the tree whose ApertarCoreApp.cpp the coverage check reads)
// The old_* copies are the code T36 deleted, read from the tree before the change (controls_make_old.sh, _old2.sh).
#include "hardware/ActionCatalog.hpp"
#include "controls_old_normalizers.inc"
#include "controls_old_extra.inc"

#include <cmath>
#include <cstdlib>
#include <fstream>
#include <sstream>

#include <cstdio>

static int failures = 0, checks = 0;
static void check(bool ok, const std::string &what)
{
    ++checks;
    std::printf("  [%s] %s\n", ok ? "ok" : "FAIL", what.c_str());
    if (!ok) ++failures;
}
static bool has(const std::string &text, const std::string &part) { return text.find(part) != std::string::npos; }

int main(int argc, char **argv)
{
    const std::string coreTree = argc > 1 ? argv[1] : "../core-tip";
    using namespace apertar;
    namespace act = hardware::actions;

    std::printf("1. one vocabulary: the catalog gives what the three old normalizers gave\n");
    std::vector<std::string> tokens = {"", "  ", "none", "OFF", "disabled", "tally", "RecIndicatorLED", "rec-led", "record_led",
        "unknown_thing", "iso200", "fps23.976", "ev-1", "ev+0.7", "wb5k", "shutter1/48", "resolution4056x2280", "Run Script 3",
        "script_5", "script6", "run_script_0", "ev_up", "ev_down", "Zoom", "preview-zoom", "Color Bars", "focus peaking"};
    for (const auto &spec : act::kSpecs) {
        tokens.push_back(std::string(spec.id));
        std::string aliases(spec.aliases);
        size_t start = 0;
        while (start < aliases.size()) {
            const auto end = aliases.find(',', start);
            const auto alias = aliases.substr(start, end == std::string::npos ? std::string::npos : end - start);
            tokens.push_back(alias);
            std::string upper = alias;
            for (auto &c : upper) c = static_cast<char>(std::toupper(static_cast<unsigned char>(c)));
            tokens.push_back(" " + upper + " ");
            if (end == std::string::npos) break;
            start = end + 1;
        }
    }
    size_t same = 0;
    std::string firstDiff;
    for (const auto &t : tokens) {
        const auto now = act::canonicalAction(t);
        const bool ok = now == old_gpio::normalizeSingleAction(t) && now == old_pcf::normalizeSingleAction(t) &&
            now == old_neo::normalizeSingleAction(t);
        same += ok;
        if (!ok && firstDiff.empty()) firstDiff = "'" + t + "' -> '" + now + "' vs '" + old_gpio::normalizeSingleAction(t) + "'";
    }
    check(same == tokens.size(), std::to_string(same) + " of " + std::to_string(tokens.size()) +
          " tokens identical in GpioInput, Pcf8574Input and NeoRotary4Input" + (firstDiff.empty() ? "" : " first diff " + firstDiff));
    check(old_gpio::normalizeSingleAction("photo_mode") == "still_mode" && act::canonicalAction("photo_mode") == "still_mode",
          "photo_mode is still_mode in both (and photo is a different action)");

    std::printf("2. classify: what Core's dispatcher does with a token\n");
    auto c = act::classify(act::canonicalAction("iso200"));
    check(c.known && c.id == "iso_value" && c.value == "200", "iso200 = Set ISO 200");
    c = act::classify(hardware::actionToken("fps23.976"));
    check(c.known && c.id == "fps_value" && c.value == "23.976", "fps23.976 (written fps23_976 by actionToken) = Set FPS 23.976");
    c = act::classify(hardware::actionToken("ev-1"));
    check(c.known && c.id == "ev_value" && c.value == "-1", "ev-1 (evm1) = EV -1");
    c = act::classify("wb5k");
    check(c.known && c.value == "2500" && has(c.note, "clamps 5 K to 2500 K"), "wb5k is 5 K, clamped to 2500 K (R2 §3.3 row 13)");
    c = act::classify(hardware::actionToken("shutter1/48"));
    check(c.known && c.id == "shutter_speed_value" && c.value == "48", "shutter1/48 = 1/48 s");
    c = act::classify("shutter180");
    check(c.known && c.id == "shutter_angle_value" && has(c.note, "photo mode"), "shutter180 = 180 degrees in video, 1/180 s in photo");
    c = act::classify("shutter2s");
    check(c.known && c.id == "shutter_seconds_value" && c.value == "2", "shutter2s = 2 s");
    c = act::classify("resolution4056x2280");
    check(c.known && c.value == "4056x2280", "resolution4056x2280");
    check(act::classify("fps_up").id == "fps_up" && act::classify("iso").id == "iso", "cycles are table entries, not numbers");
    check(!act::classify("isoo_up").known && act::suggestion("isoo_up") == "iso_up", "isoo_up is unknown; suggestion iso_up");
    check(!act::classify("iso_auto").known, "iso_auto has no dispatcher branch today (R2 §3.3)");
    check(act::findSpec("zoom_toggle")->ui && !(act::findSpec("standby")->sources & act::Rotation), "zoom is a UI action; standby is button only");
    check(has(act::catalogJson(), "\"id\":\"iso_value\"") && has(act::catalogJson(), "\"max_per_mapping\":6"), "list_actions JSON");


    std::printf("11. one vocabulary for analog targets, trigger events and numbers\n");
    {
        std::vector<std::string> targets = {"", " ", "none", "OFF", "disabled", "unknown", "Res", "res"};
        for (const auto &t : act::kAnalogTargets) targets.push_back(std::string(t));
        for (const std::string t : {"white_balance", "WhiteBalance", "focus", "focus-peaking", "focus_peaking_value", "zebra",
                                     "zebras", "volume", "input gain", "headphone", "headphones", "opacity", "controls.opacity"})
            targets.push_back(t), targets.push_back(" " + t + " ");
        size_t grove = 0, app = 0, appExpected = 0;
        for (const auto &t : targets) {
            grove += act::canonicalAnalogTarget(t) == old_grove::normalizeTarget(t);
            const std::string n = old_grove::normalizeToken(t);
            const bool off = n == "none" || n == "off" || n == "disabled";
            appExpected += !off;
            app += !off && act::canonicalAnalogTarget(t) == old_app::normalizeHardwareAnalogTarget(t);
        }
        check(grove == targets.size(), "analog targets: identical to Grove's normalizeTarget on " + std::to_string(targets.size()) + " tokens");
        check(app == appExpected, "analog targets: identical to App's copy except none/off/disabled, which App never receives");

        size_t events = 0, eventTokens = 0;
        const char *names[] = {"recording_start", "still", "timelapse_start", "timelapse_frame"};
        for (const auto &spec : act::kTriggerEvents) {
            std::string aliases(spec.aliases);
            for (size_t start = 0; start <= aliases.size();) {
                const auto end = aliases.find(',', start);
                const std::string alias = aliases.substr(start, end == std::string::npos ? std::string::npos : end - start);
                for (const std::string &token : {alias, " " + alias + " ", std::string("x") + alias}) {
                    ++eventTokens;
                    const auto old = old_trigger::eventFromToken(token);
                    const std::string want = old ? names[static_cast<int>(*old)] : "";
                    events += act::canonicalTriggerEvent(token) == want;
                }
                if (end == std::string::npos) break;
                start = end + 1;
            }
        }
        check(events == eventTokens, "trigger events: identical to TriggerOutput's eventFromToken on " + std::to_string(eventTokens) + " tokens");

        std::vector<std::string> numbers = {"iso800", "iso_800", "iso", "iso_", "isoabc", "iso0x10", "iso1e3", "fps23_976", "fps24p",
            "fps-1", "fps1/48", "wb5600k", "wb5k", "white_balance3200", "ev_1", "evm1", "isoinf", "isonan", "iso1e999", "iso1e-999"};
        std::string differ;
        bool onlyNonFinite = true;
        for (const auto &t : numbers) {
            for (const auto &prefixes : {std::vector<std::string>{"iso"}, std::vector<std::string>{"fps"},
                                        std::vector<std::string>{"wb", "white_balance", "whitebalance"}, std::vector<std::string>{"evm", "ev"}}) {
                const auto old = old_app::parseHardwareActionNumber(t, prefixes);
                std::optional<double> now;
                if (prefixes.size() == 1) now = act::numberAfter(t, {prefixes[0]});
                else if (prefixes.size() == 2) now = act::numberAfter(t, {prefixes[0], prefixes[1]});
                else now = act::numberAfter(t, {prefixes[0], prefixes[1], prefixes[2]});
                if (old == now) continue;
                differ += t + " ";
                if (!(old && !std::isfinite(*old) && !now)) onlyNonFinite = false;
            }
        }
        check(onlyNonFinite, "numbers: the header parses like App on " + std::to_string(numbers.size()) +
              " tokens except non-finite ones, which it refuses (" + differ + ")");

        std::ifstream appFile(coreTree + "/src/ApertarCoreApp.cpp");
        std::stringstream buffer;
        buffer << appFile.rdbuf();
        const std::string app_src = buffer.str();
        const auto from = app_src.find("void ApertarCoreApp::handleSingleHardwareInputAction(");
        const auto to = app_src.find("Hardware input action ignored: unknown action", from);
        const std::string body = from != std::string::npos && to != std::string::npos ? app_src.substr(from, to - from) : "";
        std::string missing;
        for (const auto &spec : act::kSpecs) {
            const std::string id(spec.id);
            bool covered = has(body, "\"" + id + "\"");
            for (const std::string family : {"iso", "shutter", "fps", "wb", "resolution"})
                if (id == family || id == family + "_up" || id == family + "_down")
                    covered = covered || has(body, "pcfSettingStepMode(action, \"" + family + "\")");
            if (id.rfind("run_script", 0) == 0) covered = has(body, "hardware::scriptActionSlot(action)");
            if (id == "iso_value") covered = has(body, "parseHardwareActionNumber(action, { \"iso\" })");
            if (id == "fps_value") covered = has(body, "parseHardwareActionNumber(action, { \"fps\" })");
            if (id == "wb_value") covered = has(body, "parseHardwareActionNumber(action, { \"wb\"");
            if (id == "ev_value") covered = has(body, "{\"evm\", \"ev\"") || has(body, "{ \"evm\", \"ev\"");
            if (id == "shutter_angle_value") covered = has(body, "\"shutter_angle\"");
            if (id == "shutter_speed_value") covered = has(body, "\"shutter_speed\"");
            if (id == "shutter_seconds_value") covered = has(body, "\"shutter\"");
            if (id == "resolution_value") covered = has(body, "parseHardwareActionResolution(action)");
            if (!covered) missing += id + " ";
        }
        std::string extra;
        for (size_t at = body.find("action == \""); at != std::string::npos; at = body.find("action == \"", at + 1)) {
            const auto start = at + 11;
            const std::string literal = body.substr(start, body.find('"', start) - start);
            if (!act::findSpec(literal) && literal != "standby_toggle") extra += literal + " ";
        }
        check(!body.empty() && missing.empty() && extra.empty(),
              "dispatcher coverage: every catalog id has a branch in handleSingleHardwareInputAction, and every literal there is a catalog id" +
              (missing.empty() ? std::string() : " missing: " + missing) + (extra.empty() ? std::string() : " extra: " + extra));
    }

    std::printf("%s: %d of %d checks\n", failures ? "FAILED" : "all ok", checks - failures, checks);
    return failures ? 1 : 0;
}