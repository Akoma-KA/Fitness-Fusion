"""Habille un lit nu : drap blanc tendu « au carré », oreillers, 2 serviettes roulées (bleue + blanche).

Montage 100 % local (aucun envoi externe), en deux temps :
 1. le matelas RÉEL est transformé en drap blanc : on garde sa lumière, ses plis, ses reflets et sa perspective,
    on lisse le quadrillage et le passepoil, on éclaircit vers un blanc propre ;
 2. oreillers et serviettes sont dessinés en volume (ombres, reflets, textures) à partir de la géométrie du lit.
Le dessus du matelas est un quadrilatère A,B,C,D :  A–B = tête de lit, A–D = côté gauche, B–C = côté droit, D–C = pied.
"""
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFilter

BLUE = np.array([.02, .45, .78], np.float32)       # serviette bleue (comme chez Lyla Villa)
WHITE = np.array([.96, .96, .965], np.float32)


def _noise(h, w, scale, rng):
    n = rng.standard_normal((h // scale + 3, w // scale + 3)).astype(np.float32)
    n = cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC)
    return n / (n.std() + 1e-6)


def _poly_mask(shape, pts, ss=3, blur=0.0):
    h, w = shape
    m = np.zeros((h * ss, w * ss), np.uint8)
    cv2.fillPoly(m, [np.round(np.array(pts, np.float32) * ss).astype(np.int32)], 255)
    m = cv2.resize(m, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.
    return cv2.GaussianBlur(m, (0, 0), blur) if blur > 0 else m


def _lerp(P, Q, t): return P + (Q - P) * t


def whiten(base, quad, drop=34, seed=3, level=(.76, .93), smooth=4.5):
    """Transforme matelas (dessus + retombée sur les 2 côtés visibles) en drap blanc en gardant la lumière réelle."""
    A, B, C, D = [np.array(p, np.float32) for p in quad]
    H, W = base.shape[:2]
    top = _poly_mask((H, W), [A, B, C, D], blur=.8)
    sideL = _poly_mask((H, W), [A, D, D + [0, drop], A + [0, drop * .85]], blur=.8)
    sideF = _poly_mask((H, W), [D, C, C + [0, drop * .8], D + [0, drop]], blur=.8)
    sides = np.clip(np.maximum(sideL, sideF) - top, 0, 1)
    allm = np.clip(top + sides, 0, 1)
    g = cv2.cvtColor((base * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.
    # 1. retire le passepoil sombre (fermeture en niveaux de gris) puis le quadrillage (flou)
    gc = cv2.morphologyEx(g, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    gs = cv2.GaussianBlur(gc, (0, 0), smooth)
    keep = np.clip(cv2.GaussianBlur(g, (0, 0), 14), 0, 1)                       # éclairage de grande échelle
    detail = gs - cv2.GaussianBlur(gs, (0, 0), 9)                                # plis moyens (ni quadrillage ni éclairage)
    # 2. niveaux : on remappe l'éclairage du matelas vers des blancs (contraste d'éclairage conservé)
    inside = top > .5
    lo, hi = np.percentile(keep[inside], 3), np.percentile(keep[inside], 97)
    norm = np.clip((keep - lo) / max(hi - lo, 1e-3), 0, 1)
    Lw = level[0] + (level[1] - level[0]) * norm + 1.0 * detail
    rng = np.random.default_rng(seed)
    Lw += .004 * _noise(H, W, 3, rng)                                            # micro-texture du tissu
    col = Lw[..., None] * np.array([.995, 1.0, 1.012], np.float32)              # blanc très légèrement froid (lumière du jour)
    # côtés : un peu plus sombres + dégradé vers le bas + ourlet
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    edge_y = np.where(xx <= D[0], A[1] + (D[1] - A[1]) * np.clip((xx - A[0]) / max(D[0] - A[0], 1), 0, 1),
                      D[1] + (C[1] - D[1]) * np.clip((xx - D[0]) / max(C[0] - D[0], 1), 0, 1))
    dep = np.clip((yy - edge_y) / max(drop, 1), 0, 1)
    sidefac = (.90 - .17 * dep) * np.where(xx <= D[0], .96, 1.0)
    sidefac = sidefac * (1 - .10 * np.exp(-((dep - .93) / .07) ** 2))            # ourlet / ombre de la retombée
    shade = np.where((sides > top)[..., None] | (sides[..., None] > .5), sidefac[..., None], 1.0)
    out = base * (1 - allm[..., None]) + np.clip(col * shade, 0, 1) * allm[..., None]
    return out, top, sides


def _fold_and_creases(img, quad, top, seed):
    """Pli rabattu « au carré » près de la tête + ombre douce : modulations discrètes en perspective."""
    A, B, C, D = [np.array(p, np.float32) for p in quad]
    H, W = img.shape[:2]
    ss = 2
    TW, TH = 960, 1200
    tex = np.ones((TH, TW), np.float32)
    y = np.arange(TH, dtype=np.float32)[:, None] / TH
    tex -= (np.exp(-((y - .31) / .005) ** 2) * .055)                              # ligne d'ombre sous le bord du pli
    tex += (np.exp(-((y - .318) / .010) ** 2) * .018)
    src = np.array([[0, 0], [TW, 0], [TW, TH], [0, TH]], np.float32)
    Hm = cv2.getPerspectiveTransform(src, np.array([A, B, C, D], np.float32))
    w = cv2.warpPerspective(tex, Hm, (W, H), flags=cv2.INTER_CUBIC, borderValue=1.0)
    return img * (1 + (w - 1)[..., None] * top[..., None])


def _plane(quad):
    A, B, C, D = [np.array(p, np.float32) for p in quad]
    src = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], np.float32)       # (v, u)
    Hm = cv2.getPerspectiveTransform(src, np.array([A, B, C, D], np.float32))
    def P(v, u):
        p = Hm @ np.array([v, u, 1.], np.float64)
        return (p[:2] / p[2]).astype(np.float32)
    return P


def _shadow(shape, pts, off=(6, 8), blur=7, amt=.22):
    m = _poly_mask(shape, np.array(pts, np.float32) + np.array(off, np.float32), blur=blur)
    return m * amt


ASSETS = None
def _assets():
    global ASSETS
    if ASSETS is None:
        import os
        d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
        ld = lambda n: cv2.cvtColor(cv2.imread(os.path.join(d, n + ".png"), cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA).astype(np.float32) / 255.
        ASSETS = dict(pg=ld("oreiller_gauche"), pd=ld("oreiller_droit"), tw=ld("serviettes_blanche_bleue"))
        mp = os.environ.get("SR_MODEL")
        if mp and os.path.exists(mp):
            sys_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lyla-villa-montage", "scripts")
            import sys; sys.path.insert(0, sys_path)
            from sr_esrgan import SR
            net = SR(mp)
            for k, a in list(ASSETS.items()):
                rgb = net.x4((a[..., :3] * 255 + .5).astype(np.uint8)).astype(np.float32) / 255.
                al = cv2.resize(a[..., 3], (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_CUBIC)
                ASSETS[k] = np.dstack([rgb, np.clip(al, 0, 1)])
    return ASSETS


def place_asset(img, rgba, center, width, angle, shadow=(5, 7), shadow_amt=.26, gain=1.0, flip=False):
    """Pose une découpe RGBA (oreiller / serviettes) : redimensionnée, tournée, ombrée, posée sur la photo."""
    H, W = img.shape[:2]
    a = rgba[:, ::-1] if flip else rgba
    h0, w0 = a.shape[:2]
    sc = width / w0; nw, nh = max(int(round(w0 * sc)), 2), max(int(round(h0 * sc)), 2)
    a = cv2.resize(a, (nw, nh), interpolation=cv2.INTER_AREA if sc < 1 else cv2.INTER_LANCZOS4)
    pad = 6
    canvas = np.zeros((nh + 2 * pad, nw + 2 * pad, 4), np.float32); canvas[pad:pad + nh, pad:pad + nw] = a
    M = cv2.getRotationMatrix2D((canvas.shape[1] / 2, canvas.shape[0] / 2), angle, 1.0)
    M[:, 2] += np.array(center, np.float32) - np.array([canvas.shape[1] / 2, canvas.shape[0] / 2], np.float32)
    full = cv2.warpAffine(canvas, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    al = np.clip(full[..., 3:4], 0, 1)
    sh = cv2.GaussianBlur(np.roll(np.roll(al[..., 0], shadow[1], 0), shadow[0], 1), (0, 0), 4.0) * shadow_amt
    out = img * (1 - sh[..., None])
    return out * (1 - al) + np.clip(full[..., :3] * gain, 0, 1) * al


def add_pillows(img, quad, seed=3, rise=0, n=2):
    A, B, C, D = [np.array(p, np.float32) for p in quad]
    P = _plane(quad); As = _assets()
    ang = -np.degrees(np.arctan2(B[1] - A[1], B[0] - A[0]))              # inclinaison de la tête de lit
    wlen = float(np.linalg.norm(B - A))
    out = img
    for i, (key, v) in enumerate((("pg", .27), ("pd", .73))):
        c = P(v, .115) + np.array([0, -8], np.float32)
        out = place_asset(out, As[key], c, width=wlen * .44, angle=ang, flip=False, gain=.985, shadow=(4, 6), shadow_amt=.22)
    return out


def add_towels(img, quad, pos=(.50, .56), seed=3):
    A, B, C, D = [np.array(p, np.float32) for p in quad]
    P = _plane(quad); As = _assets()
    ang = -np.degrees(np.arctan2(B[1] - A[1], B[0] - A[0]))
    w = float(np.linalg.norm(B - A)) * .30
    out = place_asset(img, As["tw"], P(pos[0] - .20, pos[1]), width=w, angle=ang - 6, gain=1.0, shadow=(4, 6), shadow_amt=.30)
    return place_asset(out, As["tw"], P(pos[0] + .20, pos[1] + .02), width=w, angle=ang - 3, gain=1.0, flip=True, shadow=(4, 6), shadow_amt=.30)


def dress_bed(img, quad, drop=68, seed=3, pillows=True, towels=True, towel_pos=((.34, .60), (.66, .60)), pillow_rise=34, protect_dark=0.0, protect_polys=()):
    base = np.asarray(img.convert("RGB"), np.float32) / 255.
    out, top, sides = whiten(base, quad, drop=drop, seed=seed)
    out = _fold_and_creases(out, quad, top, seed)
    if pillows: out = add_pillows(out, quad, seed=seed, rise=pillow_rise)
    if towels:
        out = add_towels(out, quad, pos=(.50, .58), seed=seed)
    if protect_dark > 0 or protect_polys:                       # objets devant le lit (lampe...) : on garde l'original
        lum_o = base.mean(-1)
        keep = np.zeros(base.shape[:2], np.float32)
        if protect_dark > 0: keep = np.maximum(keep, (lum_o < protect_dark).astype(np.float32))
        for pp in protect_polys: keep = np.maximum(keep, _poly_mask(base.shape[:2], pp))
        keep = cv2.GaussianBlur(keep, (0, 0), 1.2)[..., None]
        out = out * (1 - keep) + base * keep
    return Image.fromarray((np.clip(out, 0, 1) * 255 + .5).astype(np.uint8))


if __name__ == "__main__":
    import sys
    img = Image.open(sys.argv[1]).convert("RGB")
    out = dress_bed(img, eval(sys.argv[2]), drop=int(sys.argv[4]) if len(sys.argv) > 4 else 34)
    out.save(sys.argv[3], quality=97)
