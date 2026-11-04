import math, random, sys
sys.path.insert(0, '.')
from grid_sim import run, stats
# Dual: two independent grid locks on the same BOOTTIME grid; skew = true phase error A - true phase error B per slot.
print("dual skew |tA-tB| max/p99/rms us (steady state), AQ actuator, per (fps, D, sigma, epsA, epsB, slew)")
for fps in (25.0, 24.0):
    for D in (7, 11):
        for (ea, eb, slew) in ((1.5, -1.5, 0.0), (1.5, 30.0, 0.0), (1.5, -1.5, 45.0), (1.5, 50.0, 45.0)):
            for db in (6.0, 15.0):
                eA, pA = run(fps=fps, eps_ppm=ea, D=D, sigma=3.0, mode="AQ", phase0=0.0, seed=11, db=db, slew_ppm=slew)
                eB, pB = run(fps=fps, eps_ppm=eb, D=D, sigma=3.0, mode="AQ", phase0=0.0, seed=29, db=db, slew_ppm=slew)
                sk = [a-b for a, b in zip(eA, eB)]
                mx, p99, rms = stats(sk)
                sa = stats(eA); sb = stats(eB)
                print(f"fps {fps:3.0f} D {D:2d} eps {ea:+5.1f}/{eb:+5.1f} slew {slew:4.1f} db {db:4.1f} | skew {mx:6.1f}/{p99:6.1f}/{rms:5.1f} | A max {sa[0]:5.1f} B max {sb[0]:5.1f} | pushes/1000 A {1000*pA/30000:5.1f} B {1000*pB/30000:5.1f}")
