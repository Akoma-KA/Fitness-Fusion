"""Bruitages légers synthétisés (aucune musique) — 48 kHz stéréo."""
import numpy as np, wave

SR = 48000
rng = np.random.default_rng(7)


def _t(d):
    return np.arange(int(d * SR)) / SR


def _svf_bandpass(x, f_curve, q=1.6):
    """Filtre passe-bande à fréquence variable (state-variable filter)."""
    y = np.zeros_like(x)
    low = band = 0.0
    qq = 1.0 / q
    for n in range(len(x)):
        f = 2 * np.sin(np.pi * f_curve[n] / SR)
        low += f * band
        high = x[n] - low - qq * band
        band += f * high
        y[n] = band
    return y


def _norm(x, peak):
    m = np.max(np.abs(x)) + 1e-9
    return x * (peak / m)


def stereo(mono, pan=0.0):
    """pan: scalaire ou tableau [-1..1]"""
    pan = np.broadcast_to(np.asarray(pan, dtype=np.float64), mono.shape)
    l = mono * np.sqrt((1 - pan) / 2)
    r = mono * np.sqrt((1 + pan) / 2)
    return np.stack([l, r], 1)


def whoosh(d=0.6, direction=1, f0=300, f1=3800, peak=0.5):
    t = _t(d)
    n = rng.standard_normal(len(t))
    if direction >= 0:
        f = f0 * (f1 / f0) ** (t / d)
    else:
        f = f1 * (f0 / f1) ** (t / d)
    y = _svf_bandpass(n, f, q=1.4)
    env = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2.2
    y = _norm(y * env, peak)
    return y


def pop(freq=620, d=0.28, peak=0.4):
    t = _t(d)
    fr = freq * (1 + 0.55 * np.exp(-t / 0.025))
    ph = 2 * np.pi * np.cumsum(fr) / SR
    y = np.sin(ph) * np.exp(-t / 0.075) + 0.25 * np.sin(2 * ph) * np.exp(-t / 0.04)
    click = rng.standard_normal(len(t)) * np.exp(-t / 0.003) * 0.15
    return _norm(y + click, peak)


def tick(freq=1500, d=0.12, peak=0.22):
    t = _t(d)
    y = np.sin(2 * np.pi * freq * t) * np.exp(-t / 0.018) + 0.3 * np.sin(2 * np.pi * freq * 2.01 * t) * np.exp(-t / 0.01)
    return _norm(y, peak)


def ding(freq=1568, d=1.6, peak=0.35):
    t = _t(d)
    y = (np.sin(2 * np.pi * freq * t) * np.exp(-t / 0.55)
         + 0.45 * np.sin(2 * np.pi * freq * 1.5 * t) * np.exp(-t / 0.4)
         + 0.25 * np.sin(2 * np.pi * freq * 2.0 * t) * np.exp(-t / 0.3)
         + 0.12 * np.sin(2 * np.pi * freq * 3.01 * t) * np.exp(-t / 0.15))
    y *= np.minimum(1, t / 0.004)
    # petite réverb (échos)
    out = y.copy()
    for dl, g in ((0.09, 0.30), (0.19, 0.18), (0.31, 0.10)):
        k = int(dl * SR)
        out[k:] += g * y[:-k]
    return _norm(out, peak)


def shimmer(d=0.9, peak=0.3):
    """Montée aiguë scintillante (intro, flashs)."""
    t = _t(d)
    n = rng.standard_normal(len(t))
    f = 2500 * (9000 / 2500) ** (t / d)
    y = _svf_bandpass(n, f, q=2.5)
    env = (t / d) ** 2.0 * np.exp(-((t / d - 1) ** 2) * 0)  # croissante
    env *= np.minimum(1, (d - t) / 0.06 + 0.0)
    sp = (rng.random(len(t)) > 0.9985).astype(float)
    sp = np.convolve(sp, np.exp(-np.arange(900) / 140.0))[: len(t)]
    y = _norm(y * env, 1.0) * 0.8 + sp * 0.25 * np.sin(2 * np.pi * 5200 * t)
    return _norm(y, peak)


def water(d=1.8, peak=0.28):
    """Clapotis léger + bulles."""
    t = _t(d)
    n = rng.standard_normal(len(t))
    f = 900 + 500 * np.sin(2 * np.pi * 0.7 * t)
    y = _svf_bandpass(n, f, q=0.9)
    lap = 0.55 + 0.45 * np.sin(2 * np.pi * 3.2 * t + 1.1 * np.sin(2 * np.pi * 0.9 * t)) ** 2
    y = y * lap
    # bulles
    for _ in range(9):
        s0 = rng.uniform(0.1, d - 0.2)
        L = int(0.05 * SR)
        i0 = int(s0 * SR)
        tt = np.arange(L) / SR
        f0 = rng.uniform(500, 900)
        chirp = np.sin(2 * np.pi * (f0 * tt + 9000 * tt ** 2))
        y[i0:i0 + L] += chirp * np.exp(-tt / 0.012) * rng.uniform(0.4, 0.9) * np.max(np.abs(y)) * 0.6
    env = np.minimum(1, t / 0.35) * np.minimum(1, (d - t) / 0.6)
    return _norm(y * env, peak)


def mix(events, total, bus_peak=0.6):
    """events: liste (t, mono_ou_stereo, gain, pan)"""
    n = int((total + 1.5) * SR)
    out = np.zeros((n, 2))
    for t0, snd, g, pan in events:
        s = stereo(snd, pan) if snd.ndim == 1 else snd
        i = int(t0 * SR)
        if i < 0:
            continue
        j = min(n, i + len(s))
        out[i:j] += s[: j - i] * g
    m = np.max(np.abs(out)) + 1e-9
    out *= min(1.0, bus_peak / m) if m > bus_peak else 1.0
    return out[: int(total * SR)]


def write_wav(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
