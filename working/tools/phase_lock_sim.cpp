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

// The qbc libcamera fork's IMX585 getBlanking (4cff971): when one rate is pinned
// it searches the integer (VMAX even, HMAX) lattice for the product nearest the
// requested period in 74.25 MHz ticks, snapping an integer-microsecond request
// to the exact nominal rate when that is a whole even tick count. Modelled from
// libcamera-qbc/src/ipa/rpi/cam_helper/cam_helper_imx585.cpp:95-225@7e9fef0.
struct LatticeSensor {
    double ppm;
    int64_t requestUs;
    long minHmax = 550;        // ticks; the 4K modes' HMAX per the Cinemate hardware log
    long capHmax = 825;        // minHmax + minHmax/2
    long long minFrameLength = 2200, maxFrameLength = (1LL << 20) - 1;
    static constexpr double kClock = 74250000.0;
    long lastH = 0; long long lastV = 0;

    double realised(int64_t request)
    {
        long long target = std::llround(static_cast<double>(request) * 1e-6 * kClock);
        const long nominalFps = std::lround(kClock / static_cast<double>(target));
        if (nominalFps > 0 && std::fabs(1.0e6 / nominalFps - static_cast<double>(request)) < 1.0) {
            const double exact = kClock / static_cast<double>(nominalFps);
            const long long exactTicks = std::llround(exact);
            if (exact == std::floor(exact) && (exactTicks & 1LL) == 0)
                target = exactTicks;
        }
        long bestH = minHmax;
        long long bestV = (target / minHmax) & ~1LL;      // default helper: floor to lines, driver rounds even
        long long bestErr = std::llabs(bestV * bestH - target);
        const long long halfUs = std::llround(kClock / 2.0e6);
        long lowH = -1; long long lowV = 0;
        for (long h = minHmax; h <= capHmax && bestErr; ++h) {
            const long long vIdeal = (target + h / 2) / h;
            const long long vEven = vIdeal & ~1LL;
            for (long long v : { vEven, vEven + 2 }) {
                if (v < minFrameLength || v > maxFrameLength) continue;
                const long long err = std::llabs(v * h - target);
                if (err < bestErr) { bestErr = err; bestV = v; bestH = h; }
                if (lowH < 0 && err <= halfUs) { lowH = h; lowV = v; }
            }
        }
        if (bestErr != 0 && lowH >= 0 && lowH < bestH) { bestH = lowH; bestV = lowV; }
        lastH = bestH; lastV = bestV;
        return static_cast<double>(bestV) * static_cast<double>(bestH) / kClock * 1e6 * (1.0 - ppm * 1e-6);
    }
};

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
        // Settling time from a cold arm (no preview pre-convergence): the frame
        // after which |err| stays under 20 us for the rest of the run.
        {
            FramePhaseLock cold;
            Sensor coldSensor{11.0, +1066.0, 40000};
            int64_t t = 2'000'000'000LL;
            uint64_t lastBad = 0;
            for (uint64_t i = 0; i < 6000; ++i) {
                t += static_cast<int64_t>(std::llround(coldSensor.realised(coldSensor.requestUs) * 1000.0));
                const auto d = cold.step(true, true, 25.0, t);
                if (d.pushDuration) coldSensor.requestUs = d.durationUs;
                if (d.servoRan && std::fabs(d.phaseErrorUs) > 20.0) lastBad = i;
            }
            std::printf("    cold arm: |err| stays < 20 us after frame %llu (%.1f s at 25 fps)\n",
                        (unsigned long long)lastBad + 1, (lastBad + 1) / 25.0);
            check(lastBad < 2500, "settles within 2500 frames from a cold arm at +1066 ppm");
        }
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

    // 6. The qbc lattice: what do the servo's +/-1..2 us requests become, and does
    //    the lock still hold? (critic P1/P2). Table first, then a locked run.
    {
        std::printf("6. qbc getBlanking lattice (HMAX 550..825, VMAX even), realised period per request\n");
        LatticeSensor table{0.0, 40000};
        for (int64_t req : { 39998, 39999, 40000, 40001, 40002, 41665, 41666, 41667, 41668, 33332, 33333, 33334 }) {
            const double r = table.realised(req);
            std::printf("    req %6lld us -> HMAX %4ld x VMAX %5lld = %10.3f us (%+.2f us)\n",
                        (long long)req, table.lastH, table.lastV, r, r - req);
        }
        for (double fps : { 25.0, 24.0 }) {
            FramePhaseLock lock;
            LatticeSensor sensor{+300.0, static_cast<int64_t>(1e6 / fps)};
            int64_t now = 3'000'000'000LL;
            std::set<long> hmaxSeen;
            uint64_t pushes = 0; double maxErr = 0.0; double spanStart = 0; uint64_t frames = 0;
            for (uint64_t i = 0; i < 12000; ++i) {
                now += static_cast<int64_t>(std::llround(sensor.realised(sensor.requestUs) * 1000.0));
                const auto d = lock.step(true, i >= 2000, fps, now);
                if (d.pushDuration) sensor.requestUs = d.durationUs;
                if (i == 4000) spanStart = static_cast<double>(now);
                if (i >= 4000) { hmaxSeen.insert(sensor.lastH); ++frames; if (d.servoRan) maxErr = std::max(maxErr, std::fabs(d.phaseErrorUs)); }
                if (i >= 4000 && d.pushDuration) ++pushes;
            }
            const double meanPpm = (((static_cast<double>(now) - spanStart) * 1e-3) / ((frames - 1) * 1e6 / fps) - 1.0) * 1e6;
            std::printf("    %.0f fps, +300 ppm sensor under the lattice: mean %.2f ppm, max |err| %.1f us, pushes %llu / %llu frames, distinct HMAX %zu\n",
                        fps, meanPpm, maxErr, (unsigned long long)pushes, (unsigned long long)frames, hmaxSeen.size());
            check(std::fabs(meanPpm) < 10.0, "lattice: cadence still within 10 ppm");
            check(maxErr < 150.0, "lattice: phase error bounded by the clamp");
        }
    }

    std::printf("%s (%d failure%s)\n", failures ? "FAILED" : "ALL CHECKS PASSED", failures, failures == 1 ? "" : "s");
    return failures ? 1 : 0;
}
