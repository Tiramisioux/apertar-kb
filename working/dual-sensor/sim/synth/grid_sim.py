# Synthesizer cross-check: grid lock on an absolute BOOTTIME grid, VBLANK-only actuator.
# Plant: frame k lasts V_k*H*(1+eps); V_k is realised D frames after the request.
# Law: shipped FramePhaseLock (kp, ki, deadband, clamp, hold inside deadband) with the error
# taken to the nearest slot of k*T. Actuators: A (llround us -> floor lines -> even),
# A+Q (even-VMAX error-feedback quantiser), A+Q+S (Q plus Smith predictor over in-flight frames).
import math, random, sys
H = 550/74.25          # us per line at 891 MHz, HMAX 550
def run(fps=25.0, eps_ppm=1.5, D=11, sigma=3.0, mode="AQ", N=30000, seed=1, phase0=None,
        kp=0.06, ki=0.0015, db=6.0, clamp=150.0, slew_ppm=0.0):
    rnd = random.Random(seed)
    T = 1e6/fps
    nominalV = T/H
    # start at random phase within +-T/2 unless given; we look at steady state after acquisition
    t = (phase0 if phase0 is not None else rnd.uniform(-T/2, T/2))
    inflight = [None]*D   # V for upcoming frames (index 0 = next frame)
    vnom_even = 2*round(nominalV/2)
    for i in range(D): inflight[i] = vnom_even
    integ = 0.0; req = T; carry = 0.0; lastV = None
    errs = []; true_errs = []; pushes = 0; prevV = vnom_even
    for k in range(N):
        # frame k starts at t (true), measured with jitter, quantised to 1 us
        meas = round(t + rnd.gauss(0, sigma))
        slot = round(meas / T)
        e = meas - slot*T
        tslot = round(t / T); te = t - tslot*T
        if mode.endswith("S"):
            # predicted error at the frame this request will drive: add in-flight deviations
            pred = e + sum(v*H - T for v in inflight[:-1]) if D > 1 else e
            # wrap to nearest slot
            pred = pred - round(pred/T)*T
            ectl = pred
        else:
            ectl = e
        if abs(ectl) > db:
            w = clamp/max(ki, 1e-9)
            integ = max(-w, min(w, integ + ectl))
            req = T - (kp*ectl + ki*integ)
            req = max(T-clamp, min(T+clamp, req))
        if mode == "A":
            d = int(round(req))
            V = int(math.floor((d)/H)) & ~1
        else:
            q = req + carry
            V = 2*int(round(q/(2*H)))
            carry = q - V*H
        # this request drives frame k+D: shift the pipeline
        Vnow = inflight.pop(0); inflight.append(V)
        if Vnow != prevV: pushes += 1
        prevV = Vnow
        eps = (eps_ppm + slew_ppm)*1e-6
        t = t + Vnow*H*(1+eps)
        if k > N//3:
            errs.append(e); true_errs.append(te)
    return true_errs, pushes

def stats(x):
    a = sorted(abs(v) for v in x)
    return a[-1], a[int(0.99*len(a))], math.sqrt(sum(v*v for v in x)/len(x))

if __name__ == "__main__":
    print("single sensor, steady state (last 2/3 of 30000 frames), |true phase err| max/p99/rms us, pushes/1000 frames")
    for fps in (25.0, 24.0):
        for D in (3, 7, 11):
            for sigma in (0.0, 3.0):
                for eps in (1.5, 45.0):
                    row = []
                    for mode in ("A", "AQ", "AQS"):
                        e, p = run(fps=fps, eps_ppm=eps, D=D, sigma=sigma, mode=mode, phase0=0.0)
                        mx, p99, rms = stats(e)
                        row.append(f"{mode}: {mx:6.1f}/{p99:6.1f}/{rms:5.1f} p{1000*p/30000:5.1f}")
                    print(f"fps {fps:4.0f} D {D:2d} sig {sigma:3.1f} eps {eps:5.1f} | " + " | ".join(row))
