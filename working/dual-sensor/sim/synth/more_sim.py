import sys
sys.path.insert(0, '.')
from grid_sim import run, stats
for fps, D in ((50.0, 7), (30.0, 7), (25.0, 11), (24.0, 11)):
    for sigma in (3.0, 10.0):
        eA, pA = run(fps=fps, eps_ppm=1.5, D=D, sigma=sigma, mode="AQ", phase0=0.0, seed=5)
        eB, pB = run(fps=fps, eps_ppm=-20.0, D=D, sigma=sigma, mode="AQ", phase0=0.0, seed=7)
        sk = [a-b for a, b in zip(eA, eB)]
        print(f"fps {fps:3.0f} D {D:2d} sigma {sigma:4.1f} | single A max/p99/rms {stats(eA)[0]:5.1f}/{stats(eA)[1]:5.1f}/{stats(eA)[2]:4.1f} | dual skew {stats(sk)[0]:5.1f}/{stats(sk)[1]:5.1f}/{stats(sk)[2]:4.1f} | pushes/1000 {1000*pA/30000:5.0f}")
