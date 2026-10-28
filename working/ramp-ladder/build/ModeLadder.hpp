// Mode Ladder (T34): pure logic, no libcamera, so it compiles and is tested on any host.
// CameraController owns the sanitiser, so it supplies each resolution's state (valid, usable,
// ceiling, crop) as plain values; this file parses, validates, chooses and prints.
// In messages a rung is a "Resolution", numbered from 1 down the list.
#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <sstream>
#include <string>
#include <vector>

namespace apertar::ladder {

// The four raw compressions of the WebUI's Compression select: cDNG uncompressed or lossless JPEG,
// lossy DNG 3:1 or 5:1. Keys are the select's values.
enum class Compression { None, LosslessJpeg, Lossy3, Lossy5 };
constexpr std::array<Compression, 4> kCompressions{ Compression::None, Compression::LosslessJpeg,
                                                    Compression::Lossy3, Compression::Lossy5 };
constexpr size_t kMaxRungs = 8;
constexpr double kFpsEpsilon = 0.0005;

inline const char *compressionKey(Compression c)
{
    switch (c) {
    case Compression::LosslessJpeg: return "lossless_jpeg";
    case Compression::Lossy3: return "lossy_3to1";
    case Compression::Lossy5: return "lossy_5to1";
    case Compression::None: break;
    }
    return "none";
}

inline const char *compressionLabel(Compression c)
{
    switch (c) {
    case Compression::LosslessJpeg: return "Lossless JPEG";
    case Compression::Lossy3: return "Lossy 3:1";
    case Compression::Lossy5: return "Lossy 5:1";
    case Compression::None: break;
    }
    return "Uncompressed";
}

inline bool compressionFromKey(const std::string &key, Compression &out)
{
    for (const Compression c : kCompressions)
        if (key == compressionKey(c)) {
            out = c;
            return true;
        }
    return false;
}

struct Rung {
    uint32_t width = 3840;
    uint32_t height = 2160;
    uint32_t bits = 12;       // 10, 12 or 16
    bool clearHdr = false;
    Compression compression = Compression::None;  // applies in cDNG and lossy DNG; MLV records uncompressed
    double threshold = 0.0;   // "Up to (fps)": highest FPS this resolution serves; 0 = the mode's own ceiling
};

struct Ladder {
    bool enabled = false;     // "Activate ladder": Core picks the resolution from the FPS
    std::vector<Rung> rungs;  // first = preferred mode, serves the lowest FPS; tops rise down the list
};

// A sensor window in sensor pixels (libcamera's ScalerCropMaximum for the mode). width 0 = unknown.
struct Crop {
    uint32_t x = 0, y = 0, width = 0, height = 0;
};

// What CameraController knows about one resolution right now.
struct RungState {
    bool valid = false;        // a mode of this sensor (the sanitiser keeps it in uncompressed cDNG)
    bool usable = false;       // the sanitiser keeps it in its compression (or in the current format)
    double modeCeiling = 0.0;  // the sanitiser's FPS ceiling (table, probe, lossless cap, build maximum)
    std::string reason;        // why not valid or not usable; empty otherwise
    Crop crop;                 // from the sensor probe; width 0 when unknown
    uint32_t binning = 0;      // 0 = unknown
};

inline bool sameMode(const Rung &a, const Rung &b)
{
    return a.width == b.width && a.height == b.height && a.bits == b.bits && a.clearHdr == b.clearHdr;
}

inline std::string classLabel(const Rung &r)  // "ClearHDR16", "SDR12"
{
    return (r.clearHdr ? "ClearHDR" : "SDR") + std::to_string(r.bits);
}

inline std::string label(const Rung &r)       // "4K Clear HDR 16-bit", "3840x2076 SDR 12-bit"
{
    const std::string size = (r.width == 3840 && r.height == 2160)
        ? std::string("4K") : std::to_string(r.width) + "x" + std::to_string(r.height);
    return size + (r.clearHdr ? " Clear HDR " : " SDR ") + std::to_string(r.bits) + "-bit";
}

inline std::string sizeText(const Rung &r)    // "3840×2160"
{
    return std::to_string(r.width) + "×" + std::to_string(r.height);
}

inline std::string aspectText(const Rung &r)  // "" for 16:9, else "2.39:1"
{
    if (r.height == 0)
        return "";
    const double ratio = double(r.width) / double(r.height);
    if (std::abs(ratio - 16.0 / 9.0) < 0.01)
        return "";
    char text[16];
    std::snprintf(text, sizeof text, "%.2f:1", ratio);
    return text;
}

inline std::string number(double v)
{
    std::ostringstream o;
    o << v;
    return o.str();
}

// One number per resolution, in and out of takes.
inline double rungCeiling(const Rung &r, const RungState &s)
{
    if (!s.usable || s.modeCeiling <= 0.0)
        return 0.0;
    return r.threshold > 0.0 ? std::min(r.threshold, s.modeCeiling) : s.modeCeiling;
}

inline double ladderCeiling(const Ladder &l, const std::vector<RungState> &s)
{
    double top = 0.0;
    for (size_t i = 0; i < l.rungs.size() && i < s.size(); ++i)
        top = std::max(top, rungCeiling(l.rungs[i], s[i]));
    return top;
}

// The first usable resolution that reaches targetFps (upper bound inclusive). If none does,
// the usable one with the highest ceiling. -1 when none is usable.
inline int chooseRung(const Ladder &l, const std::vector<RungState> &s, double targetFps)
{
    int best = -1;
    double bestCeiling = 0.0;
    for (size_t i = 0; i < l.rungs.size() && i < s.size(); ++i) {
        const double ceiling = rungCeiling(l.rungs[i], s[i]);
        if (ceiling <= 0.0)
            continue;
        if (ceiling >= targetFps - kFpsEpsilon)
            return static_cast<int>(i);
        if (ceiling > bestCeiling) {
            bestCeiling = ceiling;
            best = static_cast<int>(i);
        }
    }
    return best;
}

// The resolution the camera runs: same mode, and same compression when compressionApplies
// (cDNG and lossy DNG; MLV records uncompressed). -1 = off the ladder.
inline int findRung(const Ladder &l, const Rung &running, bool compressionApplies)
{
    for (size_t i = 0; i < l.rungs.size(); ++i)
        if (sameMode(l.rungs[i], running) && (!compressionApplies || l.rungs[i].compression == running.compression))
            return static_cast<int>(i);
    return -1;
}

// Rung text: WIDTHxHEIGHT:BITS:hdr|sdr[:COMPRESSION][:FPS], resolutions joined by ",".
// COMPRESSION is a key of compressionKey() (none when left out); FPS empty or left out = the mode's ceiling.
// Example: 3840x2160:16:hdr:none:25,3840x2160:12:sdr:none
inline bool parseRungs(const std::string &text, std::vector<Rung> &out, std::string &error)
{
    out.clear();
    std::stringstream list(text);
    std::string item;
    while (std::getline(list, item, ',')) {
        std::vector<std::string> f;
        std::stringstream fields(item);
        std::string part;
        while (std::getline(fields, part, ':'))
            f.push_back(part);
        std::string shown;  // the item as typed, without control characters (the error goes into JSON replies)
        for (const char c : item)
            if (static_cast<unsigned char>(c) >= 0x20)
                shown += c;
        const std::string bad = "\"" + shown + "\": expected WIDTHxHEIGHT:BITS:hdr|sdr[:COMPRESSION][:FPS], "
                                "with BITS 10, 12 or 16 and COMPRESSION none, lossless_jpeg, lossy_3to1 or lossy_5to1.";
        const auto x = f.empty() ? std::string::npos : f[0].find('x');
        if (f.size() < 3 || f.size() > 5 || x == std::string::npos) {
            error = bad;
            return false;
        }
        Rung r;
        char *end = nullptr;
        r.width = static_cast<uint32_t>(std::strtoul(f[0].c_str(), &end, 10));
        const bool widthOk = end == f[0].c_str() + x;
        r.height = static_cast<uint32_t>(std::strtoul(f[0].c_str() + x + 1, &end, 10));
        const bool heightOk = end && *end == '\0';
        r.bits = static_cast<uint32_t>(std::strtoul(f[1].c_str(), &end, 10));
        const bool bitsOk = end && *end == '\0';
        if (!widthOk || !heightOk || !bitsOk || r.width == 0 || r.height == 0 ||
            (r.bits != 10 && r.bits != 12 && r.bits != 16) || (f[2] != "hdr" && f[2] != "sdr")) {
            error = bad;
            return false;
        }
        r.clearHdr = f[2] == "hdr";
        bool haveFps = false, haveCompression = false;
        for (size_t k = 3; k < f.size(); ++k) {
            if (f[k].empty())
                continue;
            Compression c;
            if (!haveCompression && compressionFromKey(f[k], c)) {
                r.compression = c;
                haveCompression = true;
                continue;
            }
            const double fps = std::strtod(f[k].c_str(), &end);
            if (haveFps || !end || *end != '\0' || !(fps > 0.0 && fps <= 280.0)) {
                error = bad + " The FPS must be above 0 and at most 280, or empty.";
                return false;
            }
            r.threshold = fps;
            haveFps = true;
        }
        out.push_back(r);
    }
    if (out.empty()) {
        error = "Add at least one resolution.";
        return false;
    }
    return true;
}

inline std::string rungsText(const std::vector<Rung> &rungs)
{
    std::string text;
    for (const auto &r : rungs) {
        if (!text.empty())
            text += ",";
        text += std::to_string(r.width) + "x" + std::to_string(r.height) + ":" + std::to_string(r.bits) + ":" +
                (r.clearHdr ? "hdr" : "sdr") + ":" + compressionKey(r.compression) +
                (r.threshold > 0.0 ? ":" + number(r.threshold) : "");
    }
    return text;
}

inline std::string resolutionName(size_t i)
{
    return "Resolution " + std::to_string(i + 1);
}

// Errors refuse a save; warnings are shown and saved. `s` is each resolution in its own compression
// (cDNG or lossy DNG), so the result does not depend on the format the camera is in now.
inline void validate(const Ladder &l, const std::vector<RungState> &s,
                     std::vector<std::string> &errors, std::vector<std::string> &warnings)
{
    if (l.rungs.empty())
        errors.push_back("Add at least one resolution.");
    if (l.rungs.size() > kMaxRungs)
        errors.push_back("At most " + std::to_string(kMaxRungs) + " resolutions.");
    double reached = 0.0;       // the top of the resolutions above
    int previous = -1;          // the last resolution that is used
    for (size_t i = 0; i < l.rungs.size(); ++i) {
        const Rung &r = l.rungs[i];
        bool repeat = false;
        for (size_t j = 0; j < i && !repeat; ++j)
            if (sameMode(r, l.rungs[j])) {
                errors.push_back(resolutionName(i) + " repeats resolution " + std::to_string(j + 1) + " (" +
                                 label(r) + ").");
                repeat = true;
            }
        if (repeat || i >= s.size())
            continue;
        if (!s[i].valid) {
            errors.push_back(resolutionName(i) + ": " + label(r) + " is not a mode of this sensor.");
            continue;
        }
        if (!s[i].usable) {
            errors.push_back(resolutionName(i) + " (" + label(r) + ", " + compressionLabel(r.compression) +
                             ") cannot record: " + (s[i].reason.empty() ? std::string("not in this format.") : s[i].reason));
            continue;
        }
        if (r.threshold > s[i].modeCeiling + kFpsEpsilon) {
            errors.push_back(resolutionName(i) + ": " + number(r.threshold) + " fps is above this mode's ceiling of " +
                             number(s[i].modeCeiling) + " fps.");
            continue;
        }
        const double ceiling = rungCeiling(r, s[i]);
        if (ceiling <= reached + kFpsEpsilon) {
            errors.push_back(r.threshold > 0.0 && s[i].modeCeiling > reached + kFpsEpsilon
                ? resolutionName(i) + " must go above " + number(reached) + " fps, where the resolutions above stop."
                : resolutionName(i) + " would never be used: the ones above already reach " + number(reached) + " fps.");
            continue;
        }
        if (previous >= 0) {
            const Rung &p = l.rungs[static_cast<size_t>(previous)];
            std::vector<std::string> parts;
            if (p.clearHdr != r.clearHdr || p.bits != r.bits)
                parts.push_back(std::string(p.clearHdr ? "Clear HDR " : "SDR ") + std::to_string(p.bits) + "-bit → " +
                                (r.clearHdr ? "Clear HDR " : "SDR ") + std::to_string(r.bits) + "-bit");
            if (p.width != r.width || p.height != r.height)
                parts.push_back("picture " + sizeText(p) + " → " + sizeText(r));
            if (p.compression != r.compression)
                parts.push_back(std::string(compressionLabel(p.compression)) + " → " + compressionLabel(r.compression));
            std::string text;
            for (size_t k = 0; k < parts.size(); ++k)
                text += (k ? ", " : "") + parts[k];
            warnings.push_back("Above " + number(reached) + " fps: " + text + ". Switches between takes only; in a take FPS stops at " +
                               number(reached) + ".");
        }
        reached = ceiling;
        previous = static_cast<int>(i);
    }
}

// "Resolution 1 · 3840×2160 · ClearHDR16 · ≤25 · Uncompressed". compressionText: the compression's
// label, or "MLV" where the compression does not apply.
inline std::string runningText(size_t index, const Rung &r, double ceiling, bool cropIn, const std::string &compressionText)
{
    const std::string aspect = aspectText(r);
    return resolutionName(index) + " · " + sizeText(r) + (cropIn ? " crop in" : "") + " · " + classLabel(r) +
           (aspect.empty() ? "" : " " + aspect) + " · ≤" + number(ceiling) + " · " + compressionText;
}

// libcamera's Rectangle::toString(): "(x, y)/WIDTHxHEIGHT".
inline bool parseCrop(const std::string &text, Crop &out)
{
    long x = 0, y = 0;
    unsigned long w = 0, h = 0;
    if (std::sscanf(text.c_str(), " (%ld, %ld)/%lux%lu", &x, &y, &w, &h) != 4 || x < 0 || y < 0 || w == 0 || h == 0)
        return false;
    out = Crop{ static_cast<uint32_t>(x), static_cast<uint32_t>(y), static_cast<uint32_t>(w), static_cast<uint32_t>(h) };
    return true;
}

// The whole readout area: the extent of every known crop. width 0 when none is known.
inline Crop sensorArea(const std::vector<Crop> &crops)
{
    Crop area;
    for (const auto &c : crops)
        if (c.width > 0) {
            area.width = std::max(area.width, c.x + c.width);
            area.height = std::max(area.height, c.y + c.height);
        }
    return area;
}

// A real crop-in: the sensor window is narrower than the readout area. Same width with less
// height is a different aspect ratio, not a crop-in.
inline bool cropIn(const Crop &c, const Crop &area)
{
    return c.width > 0 && area.width > 0 && c.width < area.width;
}

// A sensor mode the editor may add (from the probe): its ceiling in each compression, 0 where it
// cannot record, and why.
struct PoolEntry {
    Rung mode;
    bool valid = false;
    std::array<double, 4> ceilings{};      // indexed like kCompressions
    std::array<std::string, 4> reasons{};
    Crop crop;
    uint32_t binning = 0;
};

// Everything the get_mode_ladder / set_mode_ladder reply carries.
struct Reply {
    Ladder ladder;
    std::vector<RungState> states;   // each resolution as the camera would run it now
    bool active = false;             // ladder_active
    int running = -1;                // 0-based, -1 = off the ladder
    std::string runningText;
    std::string format;              // the current recording format's key (cdng, lossydng, mlv, h264, prores)
    bool compressionApplies = true;  // false in MLV
    double buildMax = 0.0;           // T33 [camera] max_fps, 0 = none
    Crop area;
    std::vector<PoolEntry> pool;
    std::vector<std::string> errors;
    std::vector<std::string> warnings;
};

inline std::string quote(const std::string &t)  // JSON string; UTF-8 passes through
{
    std::string out = "\"";
    for (const char c : t) {
        if (c == '"' || c == '\\') {
            out += '\\';
            out += c;
        } else if (static_cast<unsigned char>(c) < 0x20) {
            char escaped[8];
            std::snprintf(escaped, sizeof escaped, "\\u%04x", static_cast<unsigned>(static_cast<unsigned char>(c)));
            out += escaped;
        } else {
            out += c;
        }
    }
    return out + "\"";
}

inline std::string cropJson(const Crop &c)
{
    if (c.width == 0)
        return "null";
    return "{\"x\":" + std::to_string(c.x) + ",\"y\":" + std::to_string(c.y) + ",\"width\":" + std::to_string(c.width) +
           ",\"height\":" + std::to_string(c.height) + "}";
}

inline std::string toJson(const Reply &reply)
{
    const auto list = [](const std::vector<std::string> &v) {
        std::string out = "[";
        for (size_t i = 0; i < v.size(); ++i)
            out += (i ? "," : "") + quote(v[i]);
        return out + "]";
    };
    const auto mode = [](const Rung &r) {
        return "\"width\":" + std::to_string(r.width) + ",\"height\":" + std::to_string(r.height) +
               ",\"bits\":" + std::to_string(r.bits) + ",\"clear_hdr\":" + (r.clearHdr ? "true" : "false") +
               ",\"label\":" + quote(label(r)) + ",\"class\":" + quote(classLabel(r)) + ",\"size\":" + quote(sizeText(r));
    };
    const Ladder &l = reply.ladder;
    std::string out = "{\"enabled\":" + std::string(l.enabled ? "true" : "false") +
        ",\"active\":" + (reply.active ? "true" : "false") + ",\"rungs_text\":" + quote(rungsText(l.rungs)) +
        ",\"format\":" + quote(reply.format) + ",\"compression_applies\":" + (reply.compressionApplies ? "true" : "false") +
        ",\"build_max\":" + number(reply.buildMax) + ",\"ceiling\":" + number(ladderCeiling(l, reply.states)) +
        ",\"running_rung\":" + std::to_string(reply.running + 1) + ",\"running_text\":" + quote(reply.runningText) +
        ",\"sensor_area\":{\"width\":" + std::to_string(reply.area.width) + ",\"height\":" + std::to_string(reply.area.height) +
        "},\"rungs\":[";
    double from = 0.0;  // a resolution serves (from, ceiling]
    for (size_t i = 0; i < l.rungs.size() && i < reply.states.size(); ++i) {
        const Rung &r = l.rungs[i];
        const RungState &st = reply.states[i];
        const double ceiling = rungCeiling(r, st);
        out += std::string(i ? "," : "") + "{" + mode(r) + ",\"compression\":" + quote(compressionKey(r.compression)) +
               ",\"compression_label\":" + quote(compressionLabel(r.compression)) +
               ",\"valid\":" + (st.valid ? "true" : "false") + ",\"usable\":" + (st.usable ? "true" : "false") +
               ",\"reason\":" + quote(st.reason) + ",\"mode_ceiling\":" + number(st.modeCeiling) +
               ",\"threshold\":" + number(r.threshold) + ",\"ceiling\":" + number(ceiling) + ",\"from\":" + number(from) +
               ",\"crop\":" + cropJson(st.crop) + ",\"crop_in\":" + (cropIn(st.crop, reply.area) ? "true" : "false") +
               ",\"binning\":" + std::to_string(st.binning) + "}";
        from = std::max(from, ceiling);
    }
    out += "],\"pool\":[";
    for (size_t i = 0; i < reply.pool.size(); ++i) {
        const PoolEntry &p = reply.pool[i];
        std::string ceilings, reasons;
        for (size_t k = 0; k < kCompressions.size(); ++k) {
            ceilings += std::string(k ? "," : "") + quote(compressionKey(kCompressions[k])) + ":" + number(p.ceilings[k]);
            if (!p.reasons[k].empty())
                reasons += std::string(reasons.empty() ? "" : ",") + quote(compressionKey(kCompressions[k])) + ":" + quote(p.reasons[k]);
        }
        out += std::string(i ? "," : "") + "{" + mode(p.mode) + ",\"valid\":" + (p.valid ? "true" : "false") +
               ",\"ceilings\":{" + ceilings + "},\"reasons\":{" + reasons + "},\"crop\":" + cropJson(p.crop) +
               ",\"crop_in\":" + (cropIn(p.crop, reply.area) ? "true" : "false") + ",\"binning\":" + std::to_string(p.binning) + "}";
    }
    return out + "],\"errors\":" + list(reply.errors) + ",\"warnings\":" + list(reply.warnings) + "}";
}

// mode_ladder.conf: one key per line, so a person can read it. Core rewrites it whole.
inline std::string fileText(const Ladder &l)
{
    return "# Apertar Mode Ladder (T34). Core writes this file; edit it in the WebUI (Settings > Record > Mode Ladder).\n"
           "enabled=" + std::string(l.enabled ? "true" : "false") + "\n"
           "rungs=" + rungsText(l.rungs) + "\n";
}

inline Ladder parseFile(const std::string &text)
{
    Ladder l;
    std::stringstream in(text);
    std::string line, error;
    while (std::getline(in, line)) {
        if (!line.empty() && line.back() == '\r')
            line.pop_back();
        const auto eq = line.find('=');
        if (line.empty() || line[0] == '#' || eq == std::string::npos)
            continue;
        const std::string key = line.substr(0, eq), value = line.substr(eq + 1);
        if (key == "enabled") l.enabled = value == "true";
        else if (key == "rungs" && !parseRungs(value, l.rungs, error)) l.rungs.clear();
    }
    if (l.rungs.empty())
        l.enabled = false;  // a broken file never switches the camera
    return l;
}

} // namespace apertar::ladder
