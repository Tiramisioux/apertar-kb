import sys
sys.path.insert(0, '.')
import grid_sim_m as g
g.MEAS = True
for fps, D in ((25.0, 11), (25.0, 7), (24.0, 11)):
    for eps in (1.5, 45.0):
        e, p = g.run(fps=fps, eps_ppm=eps, D=D, sigma=3.0, mode="AQ", phase0=0.0, seed=3)
        print(f"MEASURED err fps {fps:3.0f} D {D:2d} eps {eps:4.1f}: max/p99/rms {g.stats(e)[0]:5.1f}/{g.stats(e)[1]:5.1f}/{g.stats(e)[2]:4.1f}  pushes/1000 {1000*p/30000:4.0f}")
# acquisition by one-frame stretch: start at a random phase, stretch one frame by (-e mod T) quantised to even lines, hold servo D+2 frames
import random, math
H = 550/74.25
def acquire(fps=25.0, D=11, sigma=3.0, seed=0):
    rnd = random.Random(seed); T = 1e6/fps
    t = rnd.uniform(-T/2, T/2) + 1000*T
    inflight = [2*round(T/H/2)]*D
    frames_to_lock = None; stretched = False; hold = 0; carry = 0.0; integ = 0.0; req = T
    for k in range(400):
        meas = round(t + rnd.gauss(0, sigma)); slot = round(meas/T); e = meas - slot*T
        if not stretched:
            ext = (-e) % T                     # lengthen one frame so the next frame lands on a slot
            # account for frames already in flight at nominal: they keep the phase
            V = 2*round((T + ext)/H/2); stretched = True; hold = D + 2
        elif hold > 0:
            hold -= 1; q = T + carry; V = 2*round(q/(2*H)); carry = q - V*H
        else:
            if abs(e) > 6.0:
                integ += e; req = max(T-150, min(T+150, T - (0.06*e + 0.0015*integ)))
            q = req + carry; V = 2*round(q/(2*H)); carry = q - V*H
        Vnow = inflight.pop(0); inflight.append(V)
        t += Vnow*H*(1+1.5e-6)
        te = t - round(t/T)*T
        if frames_to_lock is None and stretched and hold == 0 and abs(e) < 50: frames_to_lock = k
    return frames_to_lock, abs(te)
res = [acquire(seed=s) for s in range(200)]
fl = sorted(r[0] for r in res if r[0] is not None); last = sorted(r[1] for r in res)
print(f"acquisition by stretch, 25 fps D 11: frames until |e|<50us: median {fl[len(fl)//2]} max {fl[-1]} (n={len(fl)}/200); |true err| at frame 400: max {last[-1]:.1f} us")
