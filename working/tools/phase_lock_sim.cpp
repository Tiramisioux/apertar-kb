// Host-side simulation of apertar::FramePhaseLock (src/camera/FramePhaseLock.hpp).
//
// Build:  g++ -std=c++20 -O2 -I<apertar-core>/src/camera phase_lock_sim.cpp -o phase_lock_sim
// Run:    ./phase_lock_sim
//
// The sensor model: a requested duration d (us) is realised as whole lines of
// `lineUs`, rounded up (libcamera picks the VBLANK that makes the duration >=
// the request). The sensor crystal runs `ppm` fast (+) or slow (-) against the
// reference clock, so the observed arrival spacing is lines*lineUs*(1 - ppm/1e6).
// Exit code 0 when every check passes.

#include "FramePhaseLock.hpp"

#include <cmath>
#include <cstdio>
#include <set>
#include <vector>

namespace {

struct Sensor {
    double lineUs;      // realisable quantum (IMX585 4K at 25 fps is ~11 us per line)
    double ppm;         // sensor crystal error, + = sensor runs fast (frames early)
    int64_t requestUs;  // current FrameDurationLimits request
    double realised(int64_t request) const
    {
        const double lines = std::ceil(static_cast<double>(request) / lineUs - 1e-9);
        return lines * lineUs * (1.0 - ppm * 1e-6);
    }
};

struct RunStats {
    double meanPpm = 0.0;        // cadence error of the window vs nominal, ppm
    double maxAbsErrUs = 0.0;    // largest |phase error| the servo reported in the window
    uint64_t pushes = 0;
    std::set<int64_t> durations; // distinct requests seen in the window
    uint64_t rearms = 0;
};

// Runs `frames` frames, returns stats over the last `window` frames.
RunStats run(apertar::FramePhaseLock &lock, Sensor &sensor, bool enabled, bool recording, double fps,
             int64_t &nowNs, uint64_t frames, uint64_t window)
{
    RunStats stats;
    const double nominalUs = 1e6 / fps;
    double windowStartNs = 0;
    uint64_t windowFrames = 0;
    const uint64_t pushesBefore = lock.pushes;
    for (uint64_t i = 0; i < frames; ++i) {
        nowNs += static_cast<int64_t>(std::llround(sensor.realised(sensor.requestUs) * 1000.0));
        const auto d = lock.step(enabled, recording, fps, nowNs);
        if (d.rearmed) ++stats.rearms;
        if (d.pushDuration) sensor.requestUs = d.durationUs;
        if (i + window == frames) windowStartNs = static_cast<double>(nowNs);
        if (i + window < frames) continue;
        ++windowFrames;
        if (d.servoRan) {
            stats.maxAbsErrUs = std::max(stats.maxAbsErrUs, std::fabs(d.phaseErrorUs));
            stats.durations.insert(d.durationUs);
        }
    }
    const double spanUs = (static_cast<double>(nowNs) - windowStartNs) * 1e-3;
    const double idealUs = static_cast<double>(windowFrames - 1) * nominalUs;
    stats.meanPpm = (spanUs / idealUs - 1.0) * 1e6;
    stats.pushes = lock.pushes - pushesBefore;
    return stats;
}

int failures = 0;
void check(bool ok, const char *what)
{
    std::printf("  [%s] %s\n", ok ? "ok" : "FAIL", what);
    if (!ok) ++failures;
}

} // namespace

int main()
{
    using apertar::FramePhaseLock;

    // 1. Convergence from a +1066 ppm sensor (Cinemate's measured imx585 mode0 case),
    //    25 fps, 11 us lines: preview pre-converge, then a 20 000-frame recording.
    {
        std::printf("1. +1066 ppm sensor, 25 fps, 11 us lines\n");
        FramePhaseLock lock;
        Sensor sensor{11.0, +1066.0, 40000};
        int64_t now = 1'000'000'000'000LL;
        const auto open = run(lock, sensor, false, false, 25.0, now, 500, 500);
        std::printf("    open loop: %.1f ppm\n", open.meanPpm);
        check(std::fabs(open.meanPpm + 1066.0) < 400.0, "open loop shows the sensor error (line rounding included)");
        run(lock, sensor, true, false, 25.0, now, 2000, 1);          // preview pre-converge
        lock.resetTelemetry();
        const auto rec = run(lock, sensor, true, true, 25.0, now, 20000, 20000);
        std::printf("    locked: mean %.2f ppm, max |err| %.1f us, pushes %llu, distinct requests %zu, rearms %llu\n",
                    rec.meanPpm, rec.maxAbsErrUs, (unsigned long long)rec.pushes, rec.durations.size(),
                    (unsigned long long)rec.rearms);
        check(std::fabs(rec.meanPpm) < 10.0, "recorded cadence within 10 ppm of nominal");
        check(rec.maxAbsErrUs < 200.0, "phase error stays bounded (< 200 us)");
        check(rec.rearms == 0, "no re-arm while recording");
        check(rec.durations.size() <= 6, "requests dither over a few adjacent values only");
    }

    // 2. A sensor already exact: the deadband must hold (no control churn). Note a
//    period that is not a whole number of microseconds (24 fps = 41666.667 us)
//    *must* dither between 41666 and 41667, so exactness is tested at 25 fps.
    {
        std::printf("2. exact sensor, 25 fps, 10 us lines (4000 lines = 40000 us exactly)\n");
        FramePhaseLock lock;
        Sensor sensor{10.0, 0.0, 40000};
        int64_t now = 5'000'000'000LL;
        run(lock, sensor, true, false, 25.0, now, 200, 1);
        lock.resetTelemetry();
        const auto rec = run(lock, sensor, true, true, 25.0, now, 5000, 5000);
        std::printf("    pushes %llu, max |err| %.1f us, mean %.2f ppm\n", (unsigned long long)rec.pushes,
                    rec.maxAbsErrUs, rec.meanPpm);
        check(rec.pushes <= 3, "deadband holds: at most a few pushes over 5000 frames");
        check(std::fabs(rec.meanPpm) < 2.0, "cadence stays exact");
    }

    // 3. Gap policy: preview gap re-arms, recording gap is absorbed and the lock survives.
    {
        std::printf("3. gaps\n");
        FramePhaseLock lock;
        Sensor sensor{11.0, +300.0, 40000};
        int64_t now = 7'000'000'000LL;
        run(lock, sensor, true, false, 25.0, now, 3000, 1);
        now += 186'000'000; // a 186 ms reconfigure stall in preview (Cinemate e74e3e4)
        auto d = lock.step(true, false, 25.0, now);
        check(d.rearmed, "preview gap > 1.5 frames re-arms");
        run(lock, sensor, true, false, 25.0, now, 3000, 1);
        run(lock, sensor, true, true, 25.0, now, 1000, 1);
        const uint64_t framesBefore = lock.frames;
        now += 3 * 40'000'000; // a 3-period gap while recording: two frames never arrived
        d = lock.step(true, true, 25.0, now);
        check(!d.rearmed && d.servoRan, "recording gap does not re-arm");
        check(lock.frames == framesBefore + 3, "missing frames are counted (2 missed + 1 arrived)");
        check(std::fabs(d.phaseErrorUs) < 500.0, "phase stays continuous across the recorded gap");
        lock.resetTelemetry();
        const auto rec = run(lock, sensor, true, true, 25.0, now, 5000, 5000);
        check(std::fabs(rec.meanPpm) < 10.0, "lock still holds after the gap");
    }

    // 4. fps change re-arms; disabling releases; half-frame leak in preview re-arms.
    {
        std::printf("4. re-arm and release\n");
        FramePhaseLock lock;
        Sensor sensor{11.0, +300.0, 40000};
        int64_t now = 9'000'000'000LL;
        run(lock, sensor, true, true, 25.0, now, 500, 1);
        auto d = lock.step(true, true, 24.0, now + 41'667'000);
        check(d.rearmed && lock.targetFps == 24.0, "fps change re-arms on the new rate");
        d = lock.step(false, true, 24.0, now + 2 * 41'667'000);
        check(!d.active && !lock.active, "disable releases the lock");
        run(lock, sensor, true, false, 25.0, now, 500, 1);
        // Inject a phase leak of 25 ms (> half a 40 ms frame) as a burst of sub-1.5-frame gaps.
        for (int i = 0; i < 10; ++i) {
            now += 42'500'000; // 1.0625 frames each: slips under the gap detector
            d = lock.step(true, false, 25.0, now);
        }
        check(d.rearmed || std::fabs(d.phaseErrorUs) < 20'000.0, "preview half-frame backstop re-arms");
    }

    // 5. Reference-magnitude invariance: an epoch-scale clock gives the same requests.
    {
        std::printf("5. reference magnitude\n");
        FramePhaseLock a, b;
        Sensor sa{11.0, +500.0, 40000}, sb{11.0, +500.0, 40000};
        int64_t ta = 1'000'000'000LL, tb = 1'700'000'000'000'000'000LL; // 2023 in ns since epoch
        std::vector<int64_t> reqA, reqB;
        for (int i = 0; i < 4000; ++i) {
            ta += static_cast<int64_t>(std::llround(sa.realised(sa.requestUs) * 1000.0));
            tb += static_cast<int64_t>(std::llround(sb.realised(sb.requestUs) * 1000.0));
            const auto da = a.step(true, true, 25.0, ta);
            const auto db = b.step(true, true, 25.0, tb);
            if (da.pushDuration) sa.requestUs = da.durationUs;
            if (db.pushDuration) sb.requestUs = db.durationUs;
            reqA.push_back(sa.requestUs);
            reqB.push_back(sb.requestUs);
        }
        check(reqA == reqB, "boot-relative and epoch-scale references produce identical requests");
    }

    std::printf("%s (%d failure%s)\n", failures ? "FAILED" : "ALL CHECKS PASSED", failures, failures == 1 ? "" : "s");
    return failures ? 1 : 0;
}
