// Host test for src/hardware/ActionCatalog.hpp (T36) and src/hardware/HardwareConfigText.hpp (T37): the catalog gives what
// the old normalizers gave; the text model, the edits and the validator behave on a rig file and on the live file.
// Build: g++ -std=c++20 -Wall -Wextra -Werror -I. -I<core>/src controls_test.cpp -o controls_test
// Run:   ./controls_test <core-tree> [fixture]   (the tree whose ApertarCoreApp.cpp the coverage check reads;
//        fixture = controls_fixture_apertar-hardware.conf, default next to the test)
// The old_* copies are the code T36 deleted, read from the tree before the change (controls_make_old.sh, _old2.sh).
#include "hardware/HardwareConfigText.hpp"
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
static const apertar::hwconf::Issue *find(const std::vector<apertar::hwconf::Issue> &issues, const std::string &part)
{
    for (const auto &issue : issues) if (has(issue.message, part)) return &issue;
    return nullptr;
}

// A file shaped like Patrik's rig, written for the tests. The live file is the fixture, section 12.
static const std::string rig =
    "# Apertar hardware configuration\n"                         // 1
    "# Primary location: /home/pi/apertar-hardware.conf\n"       // 2
    "\n"                                                         // 3
    "[ina219]\n"                                                 // 4
    "enabled=true\n"                                             // 5
    "bus=4\n"                                                    // 6
    "address=0x40\n"                                             // 7
    "\n"                                                         // 8
    "[pcf8574]\n"                                                // 9
    "enabled=false\n"                                            // 10
    "bus=10\n"                                                   // 11
    "address=0x20\n"                                             // 12
    "pin0=none\n"                                                // 13
    "\n"                                                         // 14
    "[trigger_output]\n"                                         // 15
    "enabled=false\n"                                            // 16
    "target=gpio\n"                                              // 17
    "line=17\n"                                                  // 18
    "\n"                                                         // 19
    "[recording_indicator]\n"                                    // 20
    "enabled=true\n"                                             // 21
    "target=gpio\n"                                              // 22
    "line=21\n"                                                  // 23
    "active_high=true\n"                                         // 24
    "\n"                                                         // 25
    "[neorotary4]\n"                                             // 26
    "# Knobs: ISO, shutter, WB, fps\n"                           // 27
    "enabled=true\n"                                             // 28
    "bus=1\n"                                                    // 29
    "address=0x49\n"                                             // 30
    "encoder0_cw=iso_up\n"                                       // 31
    "encoder0_ccw=iso_down\n"                                    // 32
    "encoder3_press=resolution\n"                                // 33
    "\n"                                                         // 34
    "[gpio]\n"                                                   // 35  (an alias of [gpio_buttons])
    "enabled=true\n"                                             // 36
    "active_low=true\n"                                          // 37
    "gpio10=capture\n"                                           // 38  (an alias of d10)
    "d6=eject\n"                                                 // 39
    "\n"                                                         // 40
    "[imu]\n"                                                    // 41
    "enabled=true\n"                                             // 42
    "driver=mpu6050\n"                                           // 43
    "\n"                                                         // 44
    "[mpu6050]\n"                                                // 45
    "bus=10\n"                                                   // 46
    "address=0x68\n"                                             // 47
    "\n"                                                         // 48
    "[cfexpress_hat]\n"                                          // 49
    "enabled=true\n"                                             // 50
    "bus=1\n"                                                    // 51
    "address=0x34\n"                                             // 52
    "\n"                                                         // 53
    "[display]\n"                                                // 54
    "hdmi_external_only=true\n";                                 // 55

int main(int argc, char **argv)
{
    const std::string coreTree = argc > 1 ? argv[1] : "../core-tip";
    using namespace apertar;
    namespace act = hardware::actions;
    namespace hc = hwconf;

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


    std::printf("3. the text model: round trip and revision\n");
    const std::string crlf = "# x\r\n[cfexpress_hat]\r\nbus=1\r\nno newline at the end";
    check(hc::join(hc::parse(rig)) == rig && hc::join(hc::parse(crlf)) == crlf, "parse/join is byte-identical (CRLF, no final newline)");
    check(hc::revision(rig) != hc::revision(rig + "\n") && hc::revision(rig)[0] == 'h' && hc::revision(rig).size() == 17,
          "revision: h + 16 hex, changes with any byte");
    const auto doc = hc::parse(rig);
    check(hc::valueOf(doc, "gpio_buttons", "d10") == std::optional<std::string>("capture"), "[gpio] gpio10= is read as gpio_buttons.d10");
    check(hc::canonicalKey("neorotary4", "enc2_click") == "encoder2_press" && hc::canonicalKey("neorotary4", "encoder2_hold") == "encoder2_hold",
          "encoder aliases; encoder2_hold is the knob push's hold (T42)");
    check(hc::canonicalKey("grove_analog", "channel") == "bus" && hc::canonicalKey("grove_analog", "channel3") == "a3",
          "[grove_analog]: channel= is the bus, channel3= is input a3 (R3 §4.4)");
    check(hc::canonicalKey("pcf8574", "p3_action") == "pin3" && hc::canonicalKey("gpio_buttons", "bcm_21_hold") == "d21_hold",
          "pin and gesture spellings");

    std::printf("4. key edits keep every other byte\n");
    std::vector<hc::Edit> edits;
    std::map<std::string, std::string> fields = {{"cmd", "set_controls"}, {"base", hc::revision(rig)},
        {"set.neorotary4.encoder1_cw", "shutter_up"}, {"set.gpio_buttons.d10", "record_toggle"}, {"set.neorotary4.poll_ms", "50"}};
    check(hc::parseEdits(fields, edits).empty() && edits.size() == 3, "set.<section>.<key> fields parse (cmd, base ignored)");
    std::string after = hc::applyEdits(rig, edits);
    auto d = hc::diff(rig, after);
    check(has(after, "[gpio]\nenabled=true\nactive_low=true\nd10=record_toggle\nd6=eject\n"),
          "gpio10=capture rewritten in place as d10=record_toggle, in the [gpio] section (no second spelling)");
    check(has(after, "encoder3_press=resolution\nencoder1_cw=shutter_up\npoll_ms=50\n\n[gpio]"), "new keys after the section's last line");
    check(has(after, "# Knobs: ISO, shutter, WB, fps\n"), "comments kept");
    check(hc::splitLines(after).size() == hc::splitLines(rig).size() + 2, "two lines added, none lost");
    check(has(d, "-gpio10=capture\n+d10=record_toggle\n") && has(d, "+encoder1_cw=shutter_up\n"), "diff shows the three changes");

    std::printf("5. sections: new ones go to their canonical place; unset removes\n");
    edits.clear();
    hc::parseEdits({{"set.grove_analog.enabled", "true"}, {"set.grove_analog.a0", "wb"}}, edits);
    after = hc::applyEdits(rig, edits);
    check(has(after, "\n[grove_analog]\nenabled=true\na0=wb\n\n[imu]\n"), "[grove_analog] lands between [gpio] and [imu]");
    edits.clear();
    hc::parseEdits({{"unset.gpio_buttons.d6", "true"}, {"unset.pcf8574", "true"}}, edits);
    after = hc::applyEdits(rig, edits);
    check(!has(after, "d6=eject") && !has(after, "[pcf8574]") && has(after, "\n[trigger_output]\n"), "unset a key, unset a section");
    edits.clear();
    check(!hc::parseEdits({{"set.neorotary4.bus", "1 # header"}}, edits).empty() &&
          !hc::parseEdits({{"set.neorotory4.bus", "1"}}, edits).empty() &&
          !hc::parseEdits({{"set.neorotary4.bus", ""}}, edits).empty(), "refused: inline comment, unknown section, empty value");

    std::printf("6. an inline comment is moved to its own line when Core edits that key\n");
    const std::string commented = "[cfexpress_hat]\nenabled=true\nbus=1  # header (Patrik 2026-10-23)\naddress=0x34\n";
    edits.clear();
    hc::parseEdits({{"set.cfexpress_hat.bus", "10"}}, edits);
    check(hc::applyEdits(commented, edits) == "[cfexpress_hat]\nenabled=true\n# header (Patrik 2026-10-23)\nbus=10\naddress=0x34\n",
          "comment kept above, value line clean");

    std::printf("7. two editors, one file: per-key merge against the revision the page loaded\n");
    const std::string outside = [&] {   // Patrik edits over ssh after the page loaded `rig`: hat back to bus 10
        std::string t = rig;
        t.replace(t.find("[cfexpress_hat]\nenabled=true\nbus=1"), 34, "[cfexpress_hat]\nenabled=true\nbus=10");
        return t;
    }();
    edits.clear();
    hc::parseEdits({{"set.neorotary4.encoder2_cw", "wb_up"}}, edits);
    check(hc::conflicts(rig, outside, edits).empty(), "page edits a knob, ssh edited the hat: no conflict");
    after = hc::applyEdits(outside, edits);
    check(has(after, "encoder2_cw=wb_up") && has(after, "[cfexpress_hat]\nenabled=true\nbus=10"), "both changes survive");
    edits.clear();
    hc::parseEdits({{"set.cfexpress_hat.bus", "1"}}, edits);
    const auto conflict = hc::conflicts(rig, outside, edits);
    check(conflict.size() == 1 && conflict[0].base == "1" && conflict[0].current == "10", "page and ssh both touched cfexpress_hat.bus: conflict 1 vs 10");

    std::printf("8. the validator, on Patrik's rig and on broken variants\n");
    const hc::Facts pi{true, {1, 10, 13, 14}, {}};
    auto issues = hc::validate(rig, pi);
    const auto ina = find(issues, "[ina219] bus 4 does not exist");
    check(ina && !ina->error && ina->line == 6, "INA219 on bus 4: warning at line 6, names the buses 1, 10, 13, 14");
    size_t errors = 0;
    for (const auto &i : issues) errors += i.error;
    check(errors == 0, "Patrik's rig has no errors (" + std::to_string(issues.size()) + " warning(s))");
    const hc::Facts dpi{true, {10, 13, 14, 15}, {76, 77, 78}};
    issues = hc::validate(rig, dpi);
    const auto neo = find(issues, "[neorotary4] bus 1 does not exist");
    check(neo && neo->line == 29 && has(neo->message, "DPI overlay on config.txt line 76"), "before the fix: bus 1 missing, DPI line 76 named");
    check(find(issues, "GPIO 10 is held by the DPI overlay") && find(issues, "GPIO 21 is held by the DPI overlay"),
          "before the fix: the buttons and the tally sit on DPI pins");
    std::string bad = commented + "[trigger_output]\nenabled=true\nline=21\n[gpio_buttons]\nenabled=true\nd2=capture\nd5=isoo_up\n"
        "d7=iso_up,iso_down,wb_up,wb_down,fps_up,fps_down,capture\nd8=recindicatorled\n[neorotary4]\nencoder0_cw=standby\n"
        "[neorotary4]\nbus=1\n[recording_indicator]\nenabled=true\nline=21\n[neorotory4]\n";
    issues = hc::validate(bad, pi);
    auto e = find(issues, "Comment after the value on line 3");
    check(e && e->error && has(e->message, "keeps its default"), "hat bus with an inline comment: error, Core keeps 10");
    e = find(issues, "GPIO 2 is the SDA line of I2C bus 1");
    check(e && e->error && e->line == 10, "d2 while bus 1 exists: error at line 10");
    e = find(issues, "Unknown action 'isoo_up'");
    check(e && e->error && has(e->message, "Did you mean iso_up?"), "unknown action with a suggestion");
    check(find(issues, "at most six actions") != nullptr, "seven actions: error");
    check(find(issues, "tally shorthand") != nullptr, "d8=recindicatorled: warning, use the section (T17)");
    check(find(issues, "standby on a turn") != nullptr, "standby on a knob turn: warning");
    check(find(issues, "[neorotary4] appears twice") != nullptr, "duplicate section: error");
    e = find(issues, "GPIO 21 is used by Trigger output");
    check(e && e->error && has(e->message, "Tally"), "trigger and tally on GPIO 21: error naming both");
    check(find(issues, "Did you mean [neorotary4]?") != nullptr, "[neorotory4]: unknown section, suggestion");
    issues = hc::validate("bus=1\n[storage]\nmount_path=/media/RAW\nstray words\n  pcie_controller=x\n", pi);
    check(find(issues, "Line 1 is a key above the first") && find(issues, "Line 4 is not a section") && find(issues, "Line 5 is indented"),
          "what kills Core's Python reinsert helper: a key above the first section, a junk line; indent warned");
    edits.clear();
    hc::parseEdits({{"set.neorotary4.encoder1_cw", "shutter_up"}}, edits);
    check(hc::newErrors(hc::validate(bad, pi), hc::validate(hc::applyEdits(bad, edits), pi)).empty(),
          "an edit elsewhere adds no new errors, although lines moved (old errors do not block it)");
    edits.clear();
    hc::parseEdits({{"set.gpio_buttons.d3", "photo"}}, edits);
    check(hc::newErrors(hc::validate(bad, pi), hc::validate(hc::applyEdits(bad, edits), pi)).size() == 1,
          "a new button on GPIO 3 adds exactly one new error");

    std::printf("9. config.txt, read only\n");
    const std::string config =
        "dtparam=i2c_arm=on\n[pi4]\ndtoverlay=vc4-kms-DPI-4inch\n[all]\ndtoverlay=imx585,cam0\n"
        "dtoverlay=vc4-kms-DPI-4inch\ndtoverlay=waveshare-4dpi\n#dtoverlay=waveshare-touch-4dpi\n";
    const auto boot = hc::parseConfigTxt(config);
    check(boot.i2cArm && boot.dpiLines == std::vector<size_t>({6, 7}), "i2c_arm on; DPI lines 6 and 7 (not [pi4] line 3, not the comment)");

    std::printf("10. the cases found in review: comment rules, duplicates, tricky edits, merges\n");
    {
        const hc::Facts none{};
        auto t = std::string("[trigger_output]\nenabled=true\nevents=recording_start;still\n");
        check(hc::valueOf(hc::parse(t), "trigger_output", "events") == std::optional<std::string>("recording_start;still") &&
              !find(hc::validate(t, none), "Comment after"), "D1: events=recording_start;still keeps both (the trigger cuts only after a space)");
        t = "[run_script]\npath='/home/pi/a;b.sh'\n";
        check(hc::valueOf(hc::parse(t), "run_script", "path") == std::optional<std::string>("'/home/pi/a;b.sh'") &&
              !find(hc::validate(t, none), "Comment after"), "D1: a quoted script path may hold ;");
        t = "[mpu6050]\norientation=xyz;x\n";
        auto e = find(hc::validate(t, none), "Comment after");
        check(hc::valueOf(hc::parse(t), "mpu6050", "orientation") == std::optional<std::string>("xyz") && e && !e->error,
              "D1: the IMU reader cuts at the first ; (Mpu6050RecordingSession.cpp:209): value xyz, a warning");
        t = "[cfexpress_hat]\nenabled=true # on\nbus=1\n";
        e = find(hc::validate(t, none), "Comment after");
        check(e && !e->error && hc::effectiveValue(hc::parse(t), "cfexpress_hat", "enabled") == std::optional<std::string>("true"),
              "D1: a comment after enabled= in [cfexpress_hat] is read (the bool parser cuts it): warning only");
        t = "[cfexpress_hat]\nenabled=true\nbus=1  # header\n";
        const hc::Facts busOne{true, {1}, {}};
        e = find(hc::validate(t, busOne), "has no usable bus=, so Core uses bus 10");
        check(!hc::effectiveValue(hc::parse(t), "cfexpress_hat", "bus") && e != nullptr,
              "operator 11: bus=1 # header is shown as what Core uses: bus 10, and bus 10 is missing here");

        const std::string dup = "[gpio]\nenabled=true\nd10=capture\n\n[gpio_buttons]\nd10=eject\n";
        std::vector<hc::Edit> ed;
        hc::parseEdits({{"set.gpio_buttons.d10", "photo"}}, ed);
        check(hc::valueOf(hc::parse(dup), "gpio_buttons", "d10") == std::optional<std::string>("eject") &&
              has(hc::checkEdits(hc::parse(dup), ed), "Merge the copies"),
              "D2: duplicate sections: the model shows the later value (eject, as GpioInput), key edits are refused");

        const std::string junk = "[pcf8574]\nenabled=false\n\n[gpio_buttons]\nenabled=true\nstray words\n"
            "d7=iso_up,iso_down,wb_up,wb_down,fps_up,fps_down,capture\n";
        ed.clear();
        hc::parseEdits({{"set.pcf8574.pin1", "photo"}}, ed);
        const hc::Facts pi{true, {1, 10, 13, 14}, {}};
        check(hc::newErrors(hc::validate(junk, pi), hc::validate(hc::applyEdits(junk, ed), pi)).empty(),
              "D3: a key added above an old junk line and an old 7-action line adds no new error (ids from rule/section/key)");

        const hc::Facts tenOnly{true, {1, 10}, {}};
        e = find(hc::validate("[ina219]\nenabled=true\n", tenOnly), "has no usable bus=, so Core uses bus 4");
        check(e && !e->error, "D4: [ina219] on with no bus= runs on bus 4 (App:4284): warned");
        e = find(hc::validate("[neorotary4]\nencoder0_cw=iso_up\n", tenOnly), "[ina219] is not in this file, so Core looks on bus 4");
        check(e && !e->error, "D4: no [ina219] at all: Core still polls bus 4 (on by default): warned");

        auto boot = hc::parseConfigTxt("dtparam=i2c_arm=on,i2c_arm_baudrate=400000\n");
        const bool commaList = boot.i2cArm;
        boot = hc::parseConfigTxt("dtparam=i2c_arm=1 # header bus\n");
        const bool one = boot.i2cArm;
        boot = hc::parseConfigTxt("dtparam=i2c_arm=on\ndtparam=i2c_arm=off\n");
        check(commaList && one && !boot.i2cArm, "D5: dtparam is a comma list; =1 and a trailing comment count; a later =off wins");

        const std::string config = "dtparam=i2c_arm=on\n[pi4]\ndtoverlay=vc4-kms-DPI-4inch\n[all]\ndtoverlay=imx585,cam0\n"
            "dtoverlay=vc4-kms-DPI-4inch\ndtoverlay=waveshare-4dpi\ndtoverlay=waveshare-touch-4dpi,rotate=90\n#dtoverlay=hyperpixel4\n";
        boot = hc::parseConfigTxt(config);
        const auto cmds = hc::dpiCommands(boot);
        check(boot.dpiOverlays == std::vector<std::string>({"vc4-kms-DPI-4inch", "waveshare-4dpi", "waveshare-touch-4dpi"}) &&
              cmds.size() == 3 && has(cmds[0], "config.txt.$(date +%Y%m%d-%H%M%S)"),
              "D5: the commands name the three overlays and back up to a timestamped copy");
        {   // run the generated sed (without sudo, on a copy) twice: the second run changes nothing
            const std::string dir = "/tmp/claude-0/-home-user-apertar-kb/17fc979d-f346-53ac-97ad-c8caa225a57d/scratchpad/controls/sketch/tmp";
            std::system(("mkdir -p " + dir).c_str());
            { std::ofstream(dir + "/config.txt") << config; }
            std::string sed = cmds[1].substr(5);   // drop "sudo "
            sed.replace(sed.find("/boot/firmware/config.txt"), 25, dir + "/config.txt");
            const int r1 = std::system(sed.c_str());
            std::stringstream once; once << std::ifstream(dir + "/config.txt").rdbuf();
            const int r2 = std::system(sed.c_str());
            std::stringstream twice; twice << std::ifstream(dir + "/config.txt").rdbuf();
            const std::string want = "dtparam=i2c_arm=on\n[pi4]\n#dtoverlay=vc4-kms-DPI-4inch\n[all]\ndtoverlay=imx585,cam0\n"
                "#dtoverlay=vc4-kms-DPI-4inch\n#dtoverlay=waveshare-4dpi\n#dtoverlay=waveshare-touch-4dpi,rotate=90\n#dtoverlay=hyperpixel4\n";
            check(r1 == 0 && r2 == 0 && once.str() == want && twice.str() == want,
                  "D5: GNU sed run of the command: the 3 overlays (and the [pi4] copy) commented, imx585 kept, second run a no-op");
        }

        ed.clear();
        hc::parseEdits({{"set.neorotary4.bogus", "1"}}, ed);
        const auto rigDoc = hc::parse(rig);
        const std::string unknownKey = hc::checkEdits(rigDoc, ed);
        ed.clear();
        hc::parseEdits({{"set.display.ui_width", "1920"}}, ed);
        const std::string textOnly = hc::checkEdits(rigDoc, ed);
        ed.clear();
        hc::parseEdits({{"set.neorotary4.encoder3_press", "zebra"}, {"set.gpio_buttons.d10_hold", "standby"}}, ed);
        check(has(unknownKey, "not a key of [neorotary4]") && has(textOnly, "Settings > Config") && hc::checkEdits(rigDoc, ed).empty(),
              "D6: unknown keys and text-only sections are refused in key edits; known ones pass");
        ed.clear();
        hc::parseEdits({{"set.grove_analog.enabled", "true"}}, ed);
        const std::string withComment = "[gpio_buttons]\nd6=eject\n\n# IMU on bus 10\n[imu]\nenabled=true\n";
        check(hc::applyEdits(withComment, ed) == "[gpio_buttons]\nd6=eject\n\n[grove_analog]\nenabled=true\n\n# IMU on bus 10\n[imu]\nenabled=true\n",
              "D6: a new section goes above the comment block of the next header, not between them");
        ed.clear();
        check(!hc::parseEdits({{"set.neorotary4.bus", "null"}}, ed).empty(), "critic C: a JSON null (the text 'null') is refused");

        auto issues = hc::validate("[neorotary4]\nencoder0_cw=capture\nencoder1_cw=iso_up,iso_up\n", none);
        check(find(issues, "'capture' on a turn") && find(issues, "'iso_up' appears twice"),
              "operator 9: Record on a turn warned; a duplicate in one mapping warned (Core keeps one, ButtonActionList.hpp:103)");
        issues = hc::validate("[recording_indicator]\nenabled=true\ntarget=gpio\nline=21\nactive_high=true\nopen_drain=true\n", none);
        check(find(issues, "open drain with active high") != nullptr, "operator 14: open drain + active high warned");
        issues = hc::validate("[pcf8574]\nbus=1\naddress=0x20\npin0=photo\n[recording_indicator]\nenabled=true\ntarget=pcf8574\npcf_pin=7\n", none);
        check(find(issues, "share the chip at bus 1 0x20") != nullptr, "critic A / operator 14: buttons and the tally on one PCF8574 warned");
        check(find(hc::validate("[gpio_buttons]\r\nd6=eject\r\n", none), "Windows line ends") != nullptr, "critic G3: CRLF warned");
        check(act::isStepping("iso_up") && !act::isStepping("iso") && !act::isStepping("capture") &&
              has(act::catalogJson(), "\"stepping\":true") && has(act::catalogJson(), "\"trigger_events\":[{\"id\":\"recording_start\""),
              "list_actions marks stepping actions and carries the trigger events and analog targets");

        const std::string mine = [&] { std::string m = rig; m.replace(m.find("encoder0_cw=iso_up"), 18, "encoder0_cw=shutter_up"); return m; }();
        const std::string current = [&] { std::string c = rig; c.replace(c.find("address=0x68\n"), 13, "address=0x68\nsync_offset_ms=3\n"); return c; }();
        const auto stale = hc::textToEdits(rig, mine);
        const bool merges = stale && stale->size() == 1 && hc::conflicts(rig, current, *stale).empty();
        const std::string merged = merges ? hc::applyEdits(current, *stale) : "";
        const std::string commentEdit = [&] { std::string m = mine; m.replace(m.find("# Knobs"), 7, "# The knobs"); return m; }();
        check(merges && has(merged, "encoder0_cw=shutter_up") && has(merged, "sync_offset_ms=3") && !hc::textToEdits(rig, commentEdit),
              "operator 10: a stale text save that only changed values merges with an IMU write; a comment edit does not");
        check(hc::revision("") != std::string(hc::kAbsentRevision), "critic F2: the absent-file revision is not the empty file's");
    }

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

    std::printf("12. the live file (Patrik's apertar-hardware.conf, 2026-10-25), M7\n");
    {
        const std::string fixturePath = argc > 2 ? argv[2] : "controls_fixture_apertar-hardware.conf";
        std::ifstream fixtureFile(fixturePath, std::ios::binary);
        std::stringstream fixtureBuffer;
        fixtureBuffer << fixtureFile.rdbuf();
        const std::string live = fixtureBuffer.str();
        check(live.size() == 10106, "the fixture is the 10,106 bytes read from the Pi (" + std::to_string(live.size()) + ")");
        check(hc::join(hc::parse(live)) == live, "parse/join is byte-identical on the live file");
        hc::Facts facts;
        facts.known = true;
        facts.buses = {0, 1, 10, 13, 14};   // M3: the I2C buses on this Pi
        const auto issues = hc::validate(live, facts);
        size_t errors = 0;
        for (const auto &issue : issues) {
            errors += issue.error;
            std::printf("    %s line %zu: %s\n", issue.error ? "error" : "warning", issue.line, issue.message.c_str());
        }
        check(errors == 0, "M7: no errors on the live file (" + std::to_string(issues.size()) + " issues in all)");
        check(hc::effectiveValue(hc::parse(live), "neorotary4", "bus") == std::optional<std::string>("1") &&
              hc::effectiveValue(hc::parse(live), "mpu6050", "bus") == std::optional<std::string>("10") &&
              hc::effectiveValue(hc::parse(live), "gpio_buttons", "d10") == std::optional<std::string>("capture"),
              "neorotary4 bus 1, mpu6050 bus 10, d10=capture");
        check(hc::applyEdit(live, {hc::Edit::Op::Set, "neorotary4", "bus", "1"}) == live &&
              hc::applyEdit(live, {hc::Edit::Op::Set, "gpio_buttons", "d6", "eject"}) == live,
              "setting a key to the value it has changes no byte");
        const std::string flipped = hc::applyEdit(live, {hc::Edit::Op::Set, "ina219", "enabled", "true"});
        const std::string flippedDiff = hc::diff(live, flipped);
        check(has(flippedDiff, "-enabled=false") && has(flippedDiff, "+enabled=true") && flipped.size() + 1 == live.size() &&
              flipped != live, "one key edit changes exactly that line");
    }

    std::printf("%s: %d of %d checks\n", failures ? "FAILED" : "all ok", checks - failures, checks);
    return failures ? 1 : 0;
}