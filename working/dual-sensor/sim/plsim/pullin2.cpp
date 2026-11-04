// Scratch: pull-in variants for a nearest-slot grid lock (includes dual_model.cpp pieces).
#define main dual_main
#include "dual_model.cpp"
#undef main

// one-shot acquisition: if |e| > 1 ms, lengthen ONE request by (-e mod P), hold the servo D+2 frames, reset I.
static void run(double off, int D, int mode /*0 PI, 1 PI+antiwindup, 2 stretch+PI(aw)*/)
{
    Cam c(-1.5, D, false, 2.0, 1e12 + off * 1e6, 11);
    GridLock g; g.antiWindup = (mode >= 1); g.originNs = 0;
    int firstBelow1ms = -1, lastAbove250 = -1, hold = 0; double overshoot = 0, firstSign = 0; bool crossed = false;
    for (int i = 0; i < 6000; ++i) {
        const int64_t ts = c.frame();
        bool stretched = false;
        if (hold > 0) { --hold; c.queue(); continue; }
        auto o = g.step(ts, 25.0);
        if (o.servo && mode == 2 && std::fabs(o.err) > 1000.0) {
            const double P = 40000.0;
            const double stretch = std::fmod(-o.err + 2 * P, P);           // 0..P, always lengthen
            c.pipe.push_back(std::llround(40000.0 + stretch));
            stretched = true; hold = D + 2; g.integralUs = 0; g.requestedUs = g.nominalUs; g.lastPushedUs = -1; c.pin = 40000;
        }
        if (o.servo) {
            if (firstSign == 0) firstSign = (o.err > 0) ? 1 : -1;
            if (std::fabs(o.err) < 1000.0 && firstBelow1ms < 0) firstBelow1ms = i;
            if (!crossed && o.err * firstSign < 0) crossed = true;
            if (crossed && !stretched) overshoot = std::max(overshoot, -o.err * firstSign);
            if (std::fabs(o.err) > 250.0) lastAbove250 = i;
        }
        if (!stretched) { if (o.push) c.pin = o.dur; c.queue(); }
    }
    const char *name[] = { "PI (as shipped law)", "PI + anti-windup", "1-frame stretch + PI(aw)" };
    std::printf("   %+6.1f  %3d  %-26s | first |e|<1ms at frame %5d (%5.1f s) | |e|<250us for good after %5d (%5.1f s) | overshoot %5.0f us\n",
                off, D, name[mode], firstBelow1ms, firstBelow1ms / 25.0, lastAbove250 + 1, (lastAbove250 + 1) / 25.0, overshoot);
}

int main()
{
    std::printf("E2' grid-lock pull-in, VBLANK model, sensor -1.5 ppm, jitter 2 us, 25 fps (P = 40 ms)\n");
    for (double off : { +19.0, -19.0, +5.0 })
        for (int D : { 7, 11 })
            for (int m : { 0, 1, 2 }) run(off, D, m);
    return 0;
}
