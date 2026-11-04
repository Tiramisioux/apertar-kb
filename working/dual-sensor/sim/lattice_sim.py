# Re-implementation of libcamera(apertar@6b0b49f3) CamHelper::getBlanking (base, cam_helper.cpp:82-132),
# CamHelperImx585::getBlanking (cam_helper_imx585.cpp:118-226), IpaBase::applyAGC exposure-line math
# (ipa_base.cpp:1834-1839) and the imx585 driver's VBLANK/HBLANK/EXPOSURE handlers (imx585.c:3478-3544@cd548ef).
# All Durations are double nanoseconds as in libcamera (std::chrono::duration<double, std::nano>).
import math, sys

KCLOCK = 74250000.0
U32MAX = 2**32 - 1

class Mode:
    def __init__(self, name, width, height, min_hmax, min_vmax):
        self.name = name
        self.width = width
        self.height = height
        self.min_hmax = min_hmax
        self.min_vmax = min_vmax
        # driver imx585_set_framing_limits (imx585.c:3382-3399)
        self.pixel_rate = (width * 74250000) // min_hmax
        max_hblank = (65535 * self.pixel_rate) // 74250000 - width
        self.hblank_min, self.hblank_max = 0, max_hblank
        self.vblank_min, self.vblank_max = min_vmax - height, 0xfffff - height
        # libcamera camera_sensor_legacy.cpp:927-932, ipa_base.cpp:612-651
        sec_per_px = 1e9 / self.pixel_rate  # 1.0s / pixelRate, in ns
        self.minLineLength = (width + self.hblank_min) * sec_per_px
        self.maxLineLength = (width + self.hblank_max) * sec_per_px
        self.minFrameLength = height + self.vblank_min
        self.maxFrameLength = height + self.vblank_max

def hblankToLineLength(m, hblank):
    return (m.width + hblank) * (1e9 / m.pixel_rate)

def lineLengthToHblank(m, ll):
    # C++: double (ll*pixelRate/1s) - width, converted to uint32_t (truncation toward zero; negative tiny -> 0)
    v = (ll * m.pixel_rate / 1e9) - m.width
    return max(0, int(v))

def base_getBlanking(m, exposure, minFD, maxFD):
    line = m.minLineLength
    fmin = int(minFD / line)
    fmax = int(maxFD / line)
    expl = min(int(exposure / line), U32MAX - 4)
    fl = min(max(expl + 4, fmin), fmax)
    if fl > m.maxFrameLength:
        adj = line * fl / m.maxFrameLength
        line = min(m.maxLineLength, adj)
        fl = m.maxFrameLength
    hblank = lineLengthToHblank(m, line)
    vblank = fl - m.height
    expl = min(fl - 4, int(exposure / line))
    exposure = expl * line
    return vblank, hblank, exposure

def imx585_getBlanking(m, exposure, minFD, maxFD):
    vblank, hblank, exposure = base_getBlanking(m, exposure, minFD, maxFD)
    if minFD != maxFD or m.maxLineLength <= m.minLineLength:
        return vblank, hblank, exposure
    toTicks = lambda d: d * (KCLOCK * 1e-9)
    width, height = m.width, m.height
    minH = round_half_away(toTicks(m.minLineLength))
    capH = min(round_half_away(toTicks(m.maxLineLength)), minH + minH // 2)
    target = round_half_away(toTicks(minFD))
    reqUs = minFD / 1000.0
    nominalFps = round_half_away(KCLOCK / float(target))
    if nominalFps > 0 and abs(1.0e6 / nominalFps - reqUs) < 1.0:
        exact = KCLOCK / float(nominalFps)
        exactTicks = round_half_away(exact)
        if exact == math.floor(exact) and (exactTicks & 1) == 0:
            target = exactTicks
    bestH = minH
    bestV = (vblank + height) & ~1
    bestErr = abs(bestV * bestH - target)
    halfUs = round_half_away(KCLOCK / 2.0e6)
    lowH, lowV = -1, 0
    h = minH
    while h <= capH and bestErr:
        vIdeal = (target + h // 2) // h
        vEven = vIdeal & ~1
        for v in (vEven, vEven + 2):
            if v < m.minFrameLength or v > m.maxFrameLength:
                continue
            err = abs(v * h - target)
            if err < bestErr:
                bestErr, bestV, bestH = err, v, h
            if lowH < 0 and err <= halfUs:
                lowH, lowV = h, v
        h += 1
    if bestErr != 0 and lowH >= 0 and lowH < bestH:
        bestH, bestV = lowH, lowV
    lineLengthPck = (bestH * width + minH - 1) // minH
    newHblank = max(0, lineLengthPck - width)
    newVblank = max(0, bestV - height)
    ll = hblankToLineLength(m, newHblank)
    expl = min(int(exposure / ll), bestV - 4)
    exposure = expl * ll
    return newVblank, newHblank, exposure

def round_half_away(x):
    return int(math.floor(x + 0.5)) if x >= 0 else -int(math.floor(-x + 0.5))

def realise(m, helper, d_us, exp_us):
    """FrameDurationLimits {d,d} (or {d,d+1} when helper is 'range'), manual exposure exp_us."""
    if helper == 'range':
        vb, hb, e = imx585_getBlanking(m, exp_us * 1000.0, d_us * 1000.0, (d_us + 1) * 1000.0)
    elif helper == 'base':
        vb, hb, e = base_getBlanking(m, exp_us * 1000.0, d_us * 1000.0, d_us * 1000.0)
    else:
        vb, hb, e = imx585_getBlanking(m, exp_us * 1000.0, d_us * 1000.0, d_us * 1000.0)
    expl = int(e / hblankToLineLength(m, hb))        # ipa_base.cpp:1838-1839
    vmax = (m.height + vb) & ~1                         # imx585.c:3510
    hmax = (m.min_hmax * (m.width + hb)) // m.width     # imx585.c:3531-3532
    shr = (vmax - expl) & ~1                            # imx585.c:3479
    true_period_us = vmax * hmax / KCLOCK * 1e6
    model_fd_us = (m.height + vb) * hblankToLineLength(m, hb) / 1000.0   # FrameDuration metadata model
    true_exp_us = (vmax - shr) * hmax / KCLOCK * 1e6
    return dict(d=d_us, vb=vb, hb=hb, vmax=vmax, hmax=hmax, expl=expl, shr=shr,
                period=true_period_us, model=model_fd_us, texp=true_exp_us)

MODES = {
    'hdr16': Mode('4K Clear HDR 16-bit 3840x2200', 3840, 2200, 550, 4500),
    'sdr12': Mode('4K SDR 12-bit 3840x2160', 3840, 2160, 550, 2250),
    'bin1080': Mode('1080p 2x2 binned 12-bit 1920x1080', 1920, 1080, 550, 2250),
}

if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'table'
    if what == 'modes':
        for k, m in MODES.items():
            print(k, m.name, 'pixel_rate', m.pixel_rate, 'hblank_max', m.hblank_max,
                  'vblank_min', m.vblank_min, 'line_us %.6f' % (m.minLineLength / 1000),
                  'minFL', m.minFrameLength, 'maxFps %.4f' % (KCLOCK / (m.min_vmax * m.min_hmax)))
    elif what == 'check':
        m = MODES['hdr16']
        for d in (40000, 40001, 40016, 39999):
            r = realise(m, 'lattice', d, 20000)
            print(r)
    elif what == 'sweep':
        key, nominal, span, exp_us = sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5])
        m = MODES[key]
        for helper in ('lattice', 'range'):
            rows = [realise(m, helper, d, exp_us) for d in range(nominal - span, nominal + span + 1)]
            hs = sorted(set(r['hmax'] for r in rows))
            print('==', key, helper, 'requests %d..%d' % (nominal - span, nominal + span),
                  'distinct HMAX', len(hs), 'min', hs[0], 'max', hs[-1],
                  'distinct VMAX', len(set(r['vmax'] for r in rows)))
            base = realise(m, helper, nominal, exp_us)
            maxjump = max(abs(r['hmax'] - base['hmax']) for r in rows)
            print('   nominal', base, 'max |dHMAX| vs nominal', maxjump, '(%.2f %%)' % (100.0 * maxjump / base['hmax']))
            # adjacent-request HMAX jumps
            adj = [abs(rows[i + 1]['hmax'] - rows[i]['hmax']) for i in range(len(rows) - 1)]
            print('   adjacent 1us steps: HMAX unchanged in %d of %d, median |dH| %s, max |dH| %d' % (
                sum(1 for a in adj if a == 0), len(adj), sorted(adj)[len(adj) // 2], max(adj)))
            mm = [r['model'] - r['period'] for r in rows]
            print('   FrameDuration model - true period: min %.2f max %.2f us' % (min(mm), max(mm)))
            ee = [r['texp'] - exp_us for r in rows]
            print('   steady-state exposure error (true - requested): min %.2f max %.2f us' % (min(ee), max(ee)))
    elif what == 'list':
        key, lo, hi, exp_us, helper = sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5]), sys.argv[6]
        m = MODES[key]
        for d in range(lo, hi + 1):
            r = realise(m, helper, d, exp_us)
            print('%d  hb=%d vb=%d  HMAX=%d VMAX=%d  period=%.3f  model_FD=%.3f  expl=%d shr=%d  texp=%.2f' % (
                d, r['hb'], r['vb'], r['hmax'], r['vmax'], r['period'], r['model'], r['expl'], r['shr'], r['texp']))
