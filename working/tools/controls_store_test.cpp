// Host test for src/hardware/HardwareConfigStore.cpp (T37): the one writer of apertar-hardware.conf, on a temp dir.
// Build: g++ -std=c++20 -Wall -Wextra -Werror -pthread -I<core>/src controls_store_test.cpp <core>/src/hardware/HardwareConfigStore.cpp -o controls_store_test
// Run:   ./controls_store_test
#include "hardware/HardwareConfigStore.hpp"
#include "util/SettingsFile.hpp"

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <thread>

#include <unistd.h>

namespace fs = std::filesystem;
using apertar::hardware::HardwareConfigStore;
using apertar::hardware::StoreFlags;
namespace hc = apertar::hwconf;

static int failures = 0, checks = 0;
static void check(bool ok, const std::string &what)
{
    ++checks;
    std::printf("  [%s] %s\n", ok ? "ok" : "FAIL", what.c_str());
    if (!ok) ++failures;
}
static bool has(const std::string &text, const std::string &part) { return text.find(part) != std::string::npos; }

static std::string slurp(const fs::path &path)
{
    std::ifstream input(path, std::ios::binary);
    std::stringstream buffer;
    buffer << input.rdbuf();
    return buffer.str();
}
static void spit(const fs::path &path, const std::string &text) { std::ofstream(path, std::ios::binary) << text; }
static void age(const fs::path &path) { fs::last_write_time(path, fs::file_time_type::clock::now() - std::chrono::seconds(30)); }
static size_t entries(const fs::path &directory, const std::string &part = "")
{
    size_t n = 0;
    std::error_code error;
    for (const auto &entry : fs::directory_iterator(directory, error))
        if (has(entry.path().filename().string(), part)) ++n;
    return n;
}
static hc::Edit set(const std::string &section, const std::string &key, const std::string &value)
{
    return {hc::Edit::Op::Set, section, key, value};
}

static const std::string base =
    "# Apertar hardware configuration\n"
    "[neorotary4]\n"
    "enabled=true\n"
    "bus=1\n"
    "address=0x49\n"
    "encoder0_cw=iso_up\n"
    "\n"
    "[gpio_buttons]\n"
    "enabled=true\n"
    "d10=capture\n"
    "\n"
    "[imu]\n"
    "enabled=true\n"
    "\n"
    "[run_script]\n"
    "path=\n";

int main()
{
    char pattern[] = "/tmp/controls_store_test.XXXXXX";
    const fs::path root = mkdtemp(pattern);
    const fs::path file = root / "home" / "apertar-hardware.conf";
    const fs::path notes = root / "notes";
    fs::create_directories(file.parent_path());
    HardwareConfigStore store(file, notes);

    std::printf("1. no file yet\n");
    check(store.currentText().empty() && store.currentRevision() == hc::kAbsentRevision && !store.info().exists,
          "absent: empty text, the absent revision");
    auto r = store.replace(std::string(hc::kAbsentRevision), base, "webui");
    check(r.ok && r.written && fs::exists(file) && slurp(file) == base, "the first save creates the file");
    check(r.code.empty(), "a new file with an empty [run_script] is not a script-path change");
    check(!fs::exists(notes / "hardware-history") || entries(notes / "hardware-history") == 0, "nothing to keep in the history yet");
    check(store.currentRevision() == hc::revision(base) && r.revision == hc::revision(base), "the revision is the file's");
    check(store.info().writtenBy == "webui" && store.info().writtenRevision == hc::revision(base) &&
          has(slurp(notes / "hardware-state.conf"), "written_by=webui"), "hardware-state.conf says who wrote it");

    std::printf("2. key edits, history, backup\n");
    r = store.edit(store.currentRevision(), {set("neorotary4", "encoder0_ccw", "iso_down")}, "webui");
    check(r.ok && r.written && has(slurp(file), "encoder0_ccw=iso_down") && has(r.diff, "+encoder0_ccw=iso_down"), "a key edit adds that line");
    check(entries(notes / "hardware-history", "-webui.conf") == 1, "the replaced version is in the history");
    check(!fs::exists(file.string() + ".bak"), "no .bak without the backup flag");
    StoreFlags backup;
    backup.backup = true;
    const std::string before = store.currentText();
    r = store.edit(store.currentRevision(), {set("gpio_buttons", "d6", "eject")}, "webui", backup);
    check(r.ok && slurp(file.string() + ".bak") == before, ".bak holds the version before a WebUI save");
    r = store.edit(store.currentRevision(), {set("gpio_buttons", "d6", "eject")}, "webui");
    check(r.ok && !r.written && r.diff.empty(), "the same value again changes nothing and writes nothing");

    std::printf("3. stale bases\n");
    const std::string rev0 = store.currentRevision();
    r = store.edit(rev0, {set("gpio_buttons", "d10", "record_toggle")}, "webui");
    check(r.ok && r.written, "the first of two saves from one revision");
    r = store.edit(rev0, {set("neorotary4", "poll_ms", "20")}, "core.py");
    check(r.ok && r.written && has(slurp(file), "d10=record_toggle") && has(slurp(file), "poll_ms=20"),
          "the second, on another key, merges: no lost update");
    r = store.edit(rev0, {set("gpio_buttons", "d10", "photo")}, "core.py");
    check(!r.ok && r.code == "conflict" && r.conflicts.size() == 1 && r.conflicts[0].key == "d10", "the same key is a conflict");
    r = store.edit("h1234567890abcdef", {set("neorotary4", "poll_ms", "30")}, "core.py");
    check(!r.ok && r.code == "stale", "a revision Core never saw: reload");

    std::printf("4. a stale text save\n");
    const std::string textBase = store.currentText();
    const std::string textBaseRevision = store.currentRevision();
    r = store.edit(textBaseRevision, {set("imu", "driver", "mpu6050")}, "imu");
    check(r.ok && r.written, "the IMU page changes the file meanwhile");
    std::string mine = textBase;
    mine.replace(mine.find("poll_ms=20"), 10, "poll_ms=25");
    r = store.replace(textBaseRevision, mine, "webui");
    check(r.ok && r.merged && r.needsReview && !r.written && has(r.text, "poll_ms=25") && has(r.text, "driver=mpu6050"),
          "values-only text save merges and waits for a review");
    check(!has(slurp(file), "poll_ms=25"), "nothing was written before the review");
    StoreFlags confirm;
    confirm.confirmMerge = true;
    r = store.replace(textBaseRevision, mine, "webui", confirm);
    check(r.ok && r.written && has(slurp(file), "poll_ms=25") && has(slurp(file), "driver=mpu6050"), "confirmed: both changes are in");
    std::string comment = textBase;
    comment.insert(0, "# a new comment line\n");
    r = store.replace(textBaseRevision, comment, "webui");
    check(!r.ok && r.code == "stale", "a text save that adds a line is refused when stale");

    std::printf("5. validation and script paths\n");
    r = store.edit(store.currentRevision(), {set("neorotary4", "bus", "999")}, "webui");
    check(!r.ok && r.code == "errors" && !r.newErrors.empty() && has(r.error, "Not saved"), "a new error blocks the save");
    StoreFlags force;
    force.force = true;
    r = store.edit(store.currentRevision(), {set("neorotary4", "bus", "999")}, "webui", force);
    check(r.ok && r.written && has(slurp(file), "bus=999"), "force saves it");
    r = store.edit(store.currentRevision(), {set("neorotary4", "bus", "1")}, "webui");
    check(r.ok && r.written, "fixing it works: an old error does not lock the editor");
    std::string withScript = store.currentText();
    withScript.replace(withScript.find("path=\n"), 6, "path=/home/pi/run.sh\n");
    r = store.replace(store.currentRevision(), withScript, "webui");
    check(!r.ok && r.code == "script_paths", "a script path is not set from the browser");
    r = store.edit(store.currentRevision(), {set("run_script", "path", "/home/pi/run.sh")}, "webui");
    check(!r.ok && (r.code == "edits" || r.code == "script_paths"), "nor by a key edit");

    std::printf("6. a file someone else is writing\n");
    spit(file, store.currentText() + "# edited by hand\n");   // revision Core did not write, mtime now
    r = store.edit(store.currentRevision(), {set("neorotary4", "poll_ms", "30")}, "webui");
    check(!r.ok && r.code == "being_written", "a fresh hand edit is not merged into");
    age(file);
    r = store.edit(store.currentRevision(), {set("neorotary4", "poll_ms", "30")}, "webui");
    check(r.ok && r.written && has(slurp(file), "# edited by hand"), "settled: the save keeps the hand edit");
    r = store.edit(store.currentRevision(), {set("neorotary4", "poll_ms", "40")}, "webui");
    check(r.ok && r.written, "a file Core wrote itself needs no wait");

    std::printf("7. the IMU: one history entry for a session\n");
    const size_t imuBefore = entries(notes / "hardware-history", "-imu.conf");
    StoreFlags trusted;
    trusted.trusted = true;
    r = store.edit(store.currentRevision(), {set("mpu6050", "gyro_bias_x", "9")}, "webui");
    check(!r.ok && r.code == "edits", "a calibration key is not an easy-mode key");
    for (int i = 1; i <= 3; ++i)
        store.edit(store.currentRevision(), {set("mpu6050", "gyro_bias_x", std::to_string(i))}, "imu", trusted);
    check(entries(notes / "hardware-history", "-imu.conf") == imuBefore + 1, "three IMU writes, one new entry");
    check(has(slurp(file), "gyro_bias_x=3"), "the last value is in the file");

    std::printf("8. the history keeps 20, and the adopted file\n");
    check(store.adopt() && !store.adopt(), "adopt pins the file once");
    check(entries(notes / "hardware-history", "adopted-") == 1, "adopted-<revision>.conf is there");
    for (int i = 0; i < 30; ++i)
        store.edit(store.currentRevision(), {set("neorotary4", "debounce_ms", std::to_string(60 + i))}, "webui");
    check(entries(notes / "hardware-history", "-webui.conf") + entries(notes / "hardware-history", "-imu.conf") +
          entries(notes / "hardware-history", "-core_py.conf") <= 20, "at most 20 versions");
    check(entries(notes / "hardware-history", "adopted-") == 1, "the adopted version is never pruned");

    std::printf("9. another program holds the lock\n");
    {
        std::thread holder([&] {
            apertar::settingsFile::QtIniLock lock(file);
            std::this_thread::sleep_for(std::chrono::milliseconds(3000));
        });
        std::this_thread::sleep_for(std::chrono::milliseconds(300));
        const auto start = std::chrono::steady_clock::now();
        r = store.edit(store.currentRevision(), {set("neorotary4", "poll_ms", "50")}, "webui");
        const auto waited = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - start).count();
        check(!r.ok && r.code == "locked" && waited >= 1500 && waited < 2800, "refused after about 2 s: " + std::to_string(waited) + " ms");
        holder.join();
        r = store.edit(store.currentRevision(), {set("neorotary4", "poll_ms", "50")}, "webui");
        check(r.ok && r.written, "the lock released: the save works");
    }

    std::printf("10. four writers at once lose nothing\n");
    {
        std::vector<std::thread> writers;
        for (int t = 0; t < 4; ++t)
            writers.emplace_back([&, t] {
                for (int i = 0; i < 8; ++i) {
                    const std::string name = "d" + std::to_string(20 + t * 8 + i);
                    for (int attempt = 0; attempt < 20; ++attempt) {
                        const auto saved = store.edit(store.currentRevision(), {set("gpio_buttons", name, "photo")}, "webui");
                        if (saved.ok) break;
                    }
                }
            });
        for (auto &w : writers) w.join();
        int found = 0;
        const std::string finalText = store.currentText();
        for (int n = 20; n < 52; ++n)
            if (has(finalText, "d" + std::to_string(n) + "=photo\n")) ++found;
        check(found == 32, "all 32 keys are in the file (" + std::to_string(found) + ")");
        check(hc::join(hc::parse(finalText)) == finalText, "and the file parses back byte for byte");
    }

    fs::remove_all(root);
    std::printf("%s: %d of %d checks\n", failures ? "FAILED" : "all ok", checks - failures, checks);
    return failures ? 1 : 0;
}
