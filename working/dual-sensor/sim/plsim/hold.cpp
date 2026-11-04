// Scratch: rpi.sync-style sample-and-hold follower on a VBLANK-only actuator (2H = 14.815 us steps).
// A free-runs at VMAX 5400 (exact 25 fps on its crystal); every K frames B measures e = tB - tA (with jitter) and,
// if |e| >= thr, lengthens/shortens ONE of its frames by round(e / 2H) VMAX steps, realised L frames later.
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <random>
#include <vector>
int main()
{
    const double H2 = 2 * 550.0 / 74.25; // 14.815 us
    for (double ppmB : { -1.5, 10.0, -30.0, 100.0 })
        for (int K : { 15, 30 })
            for (double thr : { 8.0, 15.0 }) {
                const int L = 11; const double jit = 3, ppmA = 1.5;
                std::mt19937_64 rng(3); std::normal_distribution<double> n(0, 1);
                std::vector<int> stepAt(400000, 0);
                double tA = 0, tB = 0; std::vector<double> rel; int corrections = 0;
                tB = 7000.0; // start 7 ms off: pull-in included
                for (int j = 0; j < 300000; ++j) {
                    tA += 40000.0 * (1 + ppmA * 1e-6);
                    tB += (40000.0 + stepAt[j] * H2) * (1 + ppmB * 1e-6);
                    if (j % K == 0) {
                        double e = (tB + jit * n(rng)) - (tA + jit * n(rng));
                        if (std::fabs(e) >= thr) {
                            int steps = -static_cast<int>(std::lround(e / H2));
                            steps = std::clamp(steps, -400, 400); // <= ~6 ms shorter per frame (mode minimum)
                            stepAt[j + L] += steps; ++corrections;
                        }
                    }
                    if (j > 20000) rel.push_back(std::fabs(tB - tA));
                }
                std::sort(rel.begin(), rel.end());
                std::printf("B%+6.1fppm K=%2d thr=%4.1f L=%d: |tB-tA| max %5.1f us p99 %5.1f  corrections/1000f %5.1f\n",
                            ppmB, K, thr, L, rel.back(), rel[(size_t)(0.99 * (rel.size() - 1))], 1000.0 * corrections / 300000);
            }
}
