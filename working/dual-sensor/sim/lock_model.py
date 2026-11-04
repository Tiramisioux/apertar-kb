# Host model of Core's FramePhaseLock (FramePhaseLock.hpp:79-140@31d5418: kp 0.06, ki 0.0015, deadband 6,
# clamp 150, windup clampUs/ki, llround) driving three actuator models at IMX585 HMAX 550 (H = 550/74.25 us):
#   ideal      : realised period = integer-us request (what the qbc lattice approximates, +-0.5 us)
#   floor      : option A, pin {d,d+1}: base getBlanking floors d/H, driver forces VMAX even
#   sigmadelta : option A + Q, error-feedback quantiser onto even-VMAX periods, pushed as {ceil(V*H), +1}
# Plant: error vs grid, sensor crystal offset ppm, fixed loop delay; no timestamp jitter, no holes.
import math, sys

H = 550 / 74.25

def run(e0, ppm, mode, P=40000.0, delay=2, N=6000):
    kp, ki, db, cl = 0.06, 0.0015, 6.0, 150.0
    wind = cl / ki
    I, r, carry, e = 0.0, P, 0.0, float(e0)
    hist = [P] * (delay + 2)
    es = []
    for _ in range(1, N):
        e += hist[-1 - delay] * (1 + ppm * 1e-6) - P
        if abs(e) > db:
            I = max(-wind, min(wind, I + e))
            r = max(P - cl, min(P + cl, P - (kp * e + ki * I)))
        d = round(r)
        if mode == 'ideal':
            real = float(d)
        elif mode == 'floor':
            real = 2 * int(int(d / H) / 2) * H
        else:
            q = r + carry
            V = 2 * round(q / (2 * H))
            carry = q - V * H
            dd = math.ceil(V * H)
            assert 2 * int(int(dd / H) / 2) == V
            real = V * H
        hist.append(real)
        es.append(e)
    return es

def tail_stats(es, n=3000):
    t = es[-n:]
    return max(abs(x) for x in t), math.sqrt(sum(x * x for x in t) / len(t))

def entered(es, th):
    last = None
    for i, x in enumerate(es):
        if abs(x) >= th:
            last = i
    return 0 if last is None else last + 2

if __name__ == '__main__':
    ppms = (0.5, 1.5, 5, -5, -30, 300, 1066)
    print('steady state (e0=0), max/rms phase error over the last 3000 frames, us')
    for delay, lab in ((2, '3-frame'), (6, '7-frame')):
        for mode in ('ideal', 'floor', 'sigmadelta'):
            res = [tail_stats(run(0, p, mode, delay=delay, N=8000)) for p in ppms]
            print('  %s %-10s max %4.0f..%4.0f  rms %4.1f..%4.1f' % (
                lab, mode, min(x[0] for x in res), max(x[0] for x in res),
                min(x[1] for x in res), max(x[1] for x in res)))
    print('pull-in from a shared grid (3-frame delay): frame from which |e| stays < 50 us, overshoot us')
    for mode in ('ideal', 'floor', 'sigmadelta'):
        for e0 in (20000, -20000, 2000):
            es = run(e0, 1.5, mode)
            over = max((abs(x) for x in es[5:] if math.copysign(1, x) != math.copysign(1, e0)), default=0)
            print('  %-10s e0 %+6d  in<50 from %4d  overshoot %5.0f' % (mode, e0, entered(es, 50), over))
