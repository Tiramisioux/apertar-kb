#define main dual_main
#include "dual_model.cpp"
#undef main
static int64_t predicted(const Cam &c, int64_t ts)
{
    double adj = 0; for (int64_t p : c.pipe) { long h; adj += vblankRealised(p, h) - 40000.0; }
    return ts + std::llround(adj) * 1000;
}
int main()
{
    std::printf("E5 two sensors, grid lock + anti-windup + quantization-aware dead-time compensation, VBLANK model\n");
    struct Case { double pa; int da; double pb; int db; double j; };
    for (const Case cs : { Case{-1.5, 11, +20.0, 11, 2}, Case{-1.5, 11, -50.0, 7, 2}, Case{+30.0, 11, -30.0, 11, 2}, Case{-1.5, 11, +20.0, 11, 10} }) {
        Cam a(cs.pa, cs.da, false, cs.j, 1e12 + 3.1e6, 21), b(cs.pb, cs.db, false, cs.j, 1e12 + 27.9e6, 22);
        GridLock ga, gb; ga.antiWindup = gb.antiWindup = true;
        std::vector<double> skew; std::map<int64_t, double> bySlotB; const int64_t P = 40'000'000; int unmatched = 0;
        int holdA = 0, holdB = 0;
        for (int i = 0; i < 30000; ++i) {
            const int64_t ta = a.frame(), tb = b.frame();
            auto doCam = [&](Cam &c, GridLock &g, int64_t ts, int &hold) {
                if (hold > 0) { --hold; c.queue(); return; }
                const auto o = g.step(predicted(c, ts), 25.0);
                if (o.servo && std::fabs(o.err) > 1000.0) {              // acquisition: one long frame, then hold
                    const double stretch = std::fmod(-o.err + 80000.0, 40000.0);
                    c.pipe.push_back(std::llround(40000.0 + stretch));
                    hold = c.D + 2; g.integralUs = 0; g.requestedUs = g.nominalUs; g.lastPushedUs = -1; c.pin = 40000;
                    return;
                }
                if (o.push) c.pin = o.dur;
                c.queue();
            };
            doCam(a, ga, ta, holdA); doCam(b, gb, tb, holdB);
            if (i >= 2000) {
                bySlotB[((int64_t)b.tTrueNs + P / 2) / P] = b.tTrueNs;
                const int64_t ka = ((int64_t)a.tTrueNs + P / 2) / P;
                if (auto it = bySlotB.find(ka); it != bySlotB.end()) skew.push_back(std::fabs(a.tTrueNs - it->second) * 1e-3); else ++unmatched;
                while (bySlotB.size() > 8) bySlotB.erase(bySlotB.begin());
            }
        }
        std::sort(skew.begin(), skew.end());
        std::printf("   A %+5.1f ppm D%-2d  B %+5.1f ppm D%-2d jitter %2.0f us | skew max %6.1f us  p99 %6.1f us  (unmatched %d)\n",
                    cs.pa, cs.da, cs.pb, cs.db, cs.j, skew.back(), skew[size_t(skew.size() * 0.99)], unmatched);
    }
    return 0;
}
