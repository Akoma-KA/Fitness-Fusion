"""Lyla Villa — montage vertical 1080x1920 (Reels / TikTok / Shorts), sans musique."""
import os, sys, math, subprocess, glob
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(__file__))
import sfx

FMT = os.environ.get("FMT", "9x16")          # 9x16 (Reels/Stories/TikTok) | 4x5 (Facebook fil d'actualité)
CTA = os.environ.get("CTA", "1") == "1"
VILLA = os.environ.get("VILLA", "lyla")      # lyla | palmarin
WITH_CLIPS = os.environ.get("CLIPS", "0") == "1"   # Lyla : insère les clips vidéo retouchés (prep_clips.py)
CLIP_FRAMES = os.environ.get("CLIP_FRAMES", "clipframes")
NEW_TAG = os.environ.get("NEW_TAG", "1") == "1"   # pastille « NOUVELLE VILLA » dans l'intro (0 = version réutilisable)      # mention "Réservation directe..." + lien sur le dernier plan
W, H, FPS = (1080, 1350, 30) if FMT == "4x5" else (1080, 1920, 30)
if H == 1920:
    P = dict(i_logo_w=520, i_logo_y=520, i_tag=1060, i_title=1190, i_title_s=176, i_sub=1340, wm_y=1775,
             chip1_y=1440, chip_y=440, label_y=1470, o_logo_w=540, o_logo_y=480, o_title=790, o_title_s=132,
             rows_y0=935, rows_dy=138, rows_extra=24, cta_y=1478, url_y=1538, shift=90)
else:
    P = dict(i_logo_w=440, i_logo_y=300, i_tag=820, i_title=930, i_title_s=150, i_sub=1045, wm_y=1240,
             chip1_y=1090, chip_y=160, label_y=1085, o_logo_w=400, o_logo_y=250, o_title=505, o_title_s=112,
             rows_y0=650, rows_dy=122, rows_extra=18, cta_y=1160, url_y=1215, shift=50)
SHIFT = 0 if CTA else P["shift"]            # sans mention finale : on recentre le bloc
OUTRO_D = 7.2 if CTA else 6.0
PHOTOS = sys.argv[1]
OUT = sys.argv[2]
MODE = sys.argv[3] if len(sys.argv) > 3 else "full"      # full | stills
BRAND = os.environ.get("BRAND_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "brand")) + "/"
F_TITLE = BRAND + "AbrilFatface-400.ttf"                      # titres  (police du site Mau-rent Houses)
F_LIGHT, F_MED, F_SEMI = BRAND + "Epilogue-400.ttf", BRAND + "Epilogue-500.ttf", BRAND + "Epilogue-600.ttf"
NAVY, NAVY_D = (18, 34, 103), (9, 18, 60)                     # bleu marine du logo / du site
CORAL, PEACH = (255, 95, 109), (255, 195, 113)                # dégradé du logo
SAND = PEACH                                                  # accent texte
TEAL = NAVY                                                   # traits des icônes
WHITE = (255, 255, 255)

# ------------------------------------------------------------------ utilitaires
clamp = lambda x, a=0.0, b=1.0: max(a, min(b, x))
ease_out = lambda p: 1 - (1 - clamp(p)) ** 3
ease_io = lambda p: (lambda q: 4 * q ** 3 if q < .5 else 1 - (-2 * q + 2) ** 3 / 2)(clamp(p))
def ease_back(p, s=1.6):
    p = clamp(p) - 1
    return 1 + (s + 1) * p ** 3 + s * p ** 2


def text_layer(text, path, size, tracking=0, fill=WHITE, max_w=None, shadow=0.55, pad=44):
    f = ImageFont.truetype(path, size)
    def width(fn): return sum(fn.getlength(c) for c in text) + tracking * (len(text) - 1)
    if max_w:
        while width(f) > max_w and size > 12:
            size -= 2
            f = ImageFont.truetype(path, size)
    w = int(width(f)) + pad * 2
    asc, desc = f.getmetrics()
    h = asc + desc + pad * 2
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d, ds = ImageDraw.Draw(lay), ImageDraw.Draw(sh)
    x = pad
    for c in text:
        d.text((x, pad), c, font=f, fill=fill + (255,))
        ds.text((x, pad + 3), c, font=f, fill=(0, 0, 0, int(255 * shadow)))
        x += f.getlength(c) + tracking
    sh = sh.filter(ImageFilter.GaussianBlur(9))
    return Image.alpha_composite(sh, lay)


def rounded_shadow(w, h, r, fill, border=None, blur=18, off=8, sh_a=90):
    pad = blur * 2
    lay = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", lay.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((pad, pad + off, pad + w, pad + h + off), r, fill=(0, 0, 0, sh_a))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle((pad, pad, pad + w, pad + h), r, fill=fill, outline=border, width=2 if border else 0)
    return Image.alpha_composite(sh, lay), pad


def grad_disc(d):
    S = 4; n = d * S
    g = np.linspace(0, 1, n, dtype=np.float32)[None, :, None]
    arr = (np.array(CORAL, np.float32) * (1 - g) + np.array(PEACH, np.float32) * g)
    arr = np.broadcast_to(arr, (n, n, 3)).astype(np.uint8)
    m = Image.new("L", (n, n), 0); ImageDraw.Draw(m).ellipse((0, 0, n - 1, n - 1), fill=255)
    im = Image.fromarray(arr).convert("RGBA"); im.putalpha(m)
    return im.resize((d, d), Image.LANCZOS)


def grad_bar(w, h):
    g = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    arr = np.broadcast_to(np.array(CORAL, np.float32) * (1 - g) + np.array(PEACH, np.float32) * g, (h, w, 3)).astype(np.uint8)
    return Image.fromarray(arr).convert("RGBA")


_LOGO = Image.open(BRAND + "maurent-logo-badge.png").convert("RGBA")
def logo_layer(width, glow=True):
    h = int(_LOGO.height * width / _LOGO.width)
    lg = _LOGO.resize((width, h), Image.LANCZOS)
    pad = 50
    lay = Image.new("RGBA", (width + pad * 2, h + pad * 2), (0, 0, 0, 0))
    if glow:
        sh = Image.new("RGBA", lay.size, (0, 0, 0, 0))
        sh.paste((0, 0, 0, 120), (pad, pad + 8), lg.split()[3])
        lay = Image.alpha_composite(lay, sh.filter(ImageFilter.GaussianBlur(14)))
    lay.alpha_composite(lg, (pad, pad))
    return lay


# ---- icônes dessinées en vectoriel (suréchantillonnées)
def icon(kind, size=64):
    S = 512; k = S / 128
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    c = TEAL + (255,); sw = int(9 * k)
    P = lambda *v: [x * k for x in v]
    if kind == "bed":
        d.rounded_rectangle(P(16, 68, 114, 88), 4 * k, fill=c)
        d.rectangle(P(16, 40, 28, 100), fill=c); d.rectangle(P(104, 88, 114, 100), fill=c)
        d.rounded_rectangle(P(34, 50, 62, 66), 6 * k, fill=c)
        d.rounded_rectangle(P(66, 52, 106, 66), 5 * k, fill=c)
    elif kind == "shower":
        d.line(P(36, 104, 36, 36), fill=c, width=sw); d.line(P(36, 36, 76, 36), fill=c, width=sw)
        d.polygon(P(66, 40, 108, 40, 116, 54, 58, 54), fill=c)
        for x in (70, 87, 104):
            d.line(P(x, 66, x, 74), fill=c, width=int(6 * k)); d.line(P(x - 3, 82, x - 3, 90), fill=c, width=int(6 * k))
    elif kind == "pool":
        for x in (42, 66):
            d.line(P(x, 26, x, 66), fill=c, width=int(7 * k))
        d.arc(P(42, 12, 66, 40), 180, 360, fill=c, width=int(7 * k))
        d.line(P(42, 42, 66, 42), fill=c, width=int(6 * k)); d.line(P(42, 56, 66, 56), fill=c, width=int(6 * k))
        for y in (78, 98):
            pts = [(x * k, (y + 5 * math.sin((x - 16) / 8.0)) * k) for x in range(16, 113, 2)]
            d.line(pts, fill=c, width=int(8 * k), joint="curve")
    elif kind == "pin":
        d.ellipse(P(38, 22, 90, 74), fill=c)
        d.polygon(P(42, 62, 86, 62, 64, 108), fill=c)
        d.ellipse(P(55, 39, 73, 57), fill=(255, 140, 110, 255))
    return im.resize((size, size), Image.LANCZOS)


def chip(kind, text, sub=None, min_w=0):
    f = ImageFont.truetype(F_SEMI, 40); fs = ImageFont.truetype(F_MED, 30)
    tw = sum(f.getlength(c) for c in text) + 3 * (len(text) - 1)
    sw_ = (sum(fs.getlength(c) for c in sub) + 1.5 * (len(sub) - 1)) if sub else 0
    h = 124 if sub else 100
    w = int(max(min_w, 40 + 70 + 22 + max(tw, sw_) + 44))
    base, pad = rounded_shadow(w, h, h // 2, NAVY + (228,), border=PEACH + (110,))
    d = ImageDraw.Draw(base)
    cx, cy = pad + 40 + 35, pad + h // 2
    base.alpha_composite(grad_disc(70), (cx - 35, cy - 35))
    base.alpha_composite(icon(kind, 46), (cx - 23, cy - 23))
    x = pad + 40 + 70 + 22
    y = pad + (h - 40) // 2 - (14 if sub else 0) - 4
    for c in text:
        d.text((x, y), c, font=f, fill=WHITE + (255,)); x += f.getlength(c) + 3
    if sub:
        x = pad + 40 + 70 + 22; y2 = y + 54
        for c in sub:
            d.text((x, y2), c, font=fs, fill=SAND + (255,)); x += fs.getlength(c) + 1.5
    return base


def tag(text):
    f = ImageFont.truetype(F_SEMI, 32)
    tw = sum(f.getlength(c) for c in text) + 5 * (len(text) - 1)
    w, h = int(tw + 80), 76
    base, pad = rounded_shadow(w, h, h // 2, NAVY + (232,), border=PEACH + (110,))
    d = ImageDraw.Draw(base); x = pad + 40
    for c in text:
        d.text((x, pad + 17), c, font=f, fill=SAND + (255,)); x += f.getlength(c) + 5
    return base


def label(text, sub=None):
    t = text_layer(text, F_SEMI, 54, tracking=1)
    parts = [t]
    if sub:
        parts.append(text_layer(sub, F_MED, 36, tracking=2, fill=SAND, shadow=.8))
    h = sum(p.height - 60 for p in parts) + 60
    w = max(p.width for p in parts) + 40
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    y = 0
    for p in parts:
        lay.alpha_composite(p, (30, y)); y -= 0; y += p.height - 60
    bar = grad_bar(8, 70)
    lay.alpha_composite(bar, (14, 44))
    return lay


# ------------------------------------------------------------------ plan de montage
SHOTS_LYLA = [  # nom du fichier, durée, mode, (z0,z1,fx0,fx1,fy0,fy1)
    ("01_facade", 3.9, "fill", (1.00, 1.10, .5, .5, .54, .46)),
    ("02_facade-piscine-vue-large", 2.7, "fit", (1.0, 1.07, .5, .5, .5, .5)),
    ("03_salon", 2.7, "fill", (1.12, 1.0, .56, .44, .5, .5)),
    ("04_salon-et-cuisine", 2.7, "fill", (1.0, 1.10, .45, .56, .5, .5)),
    ("05_salon-vue-piscine", 2.7, "fill", (1.10, 1.0, .62, .5, .5, .5)),
    ("06_salle-a-manger", 2.7, "fill", (1.0, 1.10, .5, .4, .5, .5)),
    ("07_cuisine-equipee", 2.7, "fill", (1.10, 1.0, .4, .6, .5, .5)),
    ("08_chambre-1", 2.8, "fill", (1.0, 1.12, .5, .5, .5, .5)),
    ("09_chambre-2-vue-piscine", 2.6, "fill", (1.08, 1.0, .36, .56, .5, .5)),
    ("10_chambre-3", 2.6, "fill", (1.0, 1.10, .5, .4, .5, .5)),
    ("11_chambre-4", 2.6, "fill", (1.10, 1.0, .45, .55, .5, .5)),
    ("12_salle-de-bain-1", 2.7, "fill", (1.0, 1.10, .52, .58, .5, .5)),
    ("13_salle-de-bain-2", 2.6, "fill", (1.10, 1.0, .6, .52, .5, .5)),
    ("14_piscine-privee", 3.0, "fill", (1.0, 1.12, .5, .5, .58, .52)),
    ("15_piscine-et-terrasse", 2.8, "fill", (1.12, 1.0, .55, .45, .5, .5)),
    ("16_piscine-pierre-volcanique", OUTRO_D, "outro", (1.0, 1.08, .5, .5, .5, .5)),
]
SHOTS_PAL = [
    ("01_facade-couverture", 3.9, "fill", (1.00, 1.10, .5, .5, .56, .48)),
    ("02_facade-palmier", 2.7, "fill", (1.10, 1.0, .45, .55, .5, .5)),
    ("03_salon", 2.7, "fill", (1.12, 1.0, .56, .44, .5, .5)),
    ("04_salon-tv", 2.7, "fill", (1.0, 1.10, .45, .56, .5, .5)),
    ("05_sejour-terrasse", 2.7, "fill", (1.10, 1.0, .62, .5, .5, .5)),
    ("06_salle-a-manger-cuisine", 2.7, "fill", (1.0, 1.10, .5, .4, .5, .5)),
    ("07_cuisine-equipee", 2.7, "fill", (1.10, 1.0, .4, .6, .5, .5)),
    ("08_chambre-1", 2.8, "fill", (1.0, 1.12, .5, .5, .5, .5)),
    ("09_chambre-2-vue-piscine", 2.6, "fill", (1.08, 1.0, .36, .56, .5, .5)),
    ("10_chambre-3", 2.6, "fill", (1.0, 1.10, .5, .4, .5, .5)),
    ("11_chambre-4", 2.6, "fill", (1.10, 1.0, .45, .55, .5, .5)),
    ("12_salle-de-bain-1", 2.7, "fill", (1.0, 1.10, .52, .58, .5, .5)),
    ("13_salle-de-bain-2", 2.6, "fill", (1.10, 1.0, .6, .52, .5, .5)),
    ("14_salle-de-bain-3", 2.6, "fill", (1.0, 1.10, .45, .55, .5, .5)),
    ("15_piscine-jardin", 3.0, "fill", (1.0, 1.12, .5, .5, .58, .52)),
    ("16_terrasse-piscine", 2.8, "fill", (1.12, 1.0, .55, .45, .5, .5)),
    ("17_facade-fin", OUTRO_D, "outro", (1.0, 1.08, .5, .5, .5, .5)),
]
SHOTS_LYLA_CLIPS = SHOTS_LYLA[:8] + [
    ("clip-08a-chambre-1", 3.2, "clip", ()), ("clip-08b-chambre-1", 2.4, "clip", ()), ("clip-08c-chambre-1", 2.4, "clip", ()),
    SHOTS_LYLA[8], ("clip-09-chambre-2", 2.8, "clip", ()),
    SHOTS_LYLA[9], ("clip-10-chambre-3", 2.8, "clip", ()),
    SHOTS_LYLA[10], ("clip-11-chambre-4", 2.8, "clip", ()),
    SHOTS_LYLA[11], ("clip-12-salle-de-bain", 3.0, "clip", ()),
] + SHOTS_LYLA[12:]
SHOTS = SHOTS_PAL if VILLA == "palmarin" else (SHOTS_LYLA_CLIPS if WITH_CLIPS else SHOTS_LYLA)
if VILLA == "palmarin":
    TITLE, LOC_SUB = "Villa Palmarin", "à quelques minutes de toutes commodités"
    LAB = {2: ("Salon", None), 3: ("Salon & télévision", None), 4: ("Séjour ouvert sur la terrasse", None),
           5: ("Salle à manger & cuisine", None), 6: ("Cuisine entièrement équipée", None)}
    POOL_SUB, LAST_LABEL = "Jardin & terrasse", "Terrasse en bois & piscine"
else:
    TITLE, LOC_SUB = "Lyla Villa", "à quelques minutes de la plage et du centre-ville"
    LAB = {2: ("Salon", None), 3: ("Salon & cuisine ouverte", None), 4: ("Ouvert sur la piscine", None),
           5: ("Salle à manger", None), 6: ("Cuisine entièrement équipée", None)}
    POOL_SUB, LAST_LABEL = "Terrasse en bois", "Détente au bord de l'eau"

# transition à la fin de chaque plan i -> i+1 : (type, durée)
TRANS = [("zoom", .55), ("push_left", .5), ("fade", .55), ("wipe", .55), ("push_up", .5), ("fade", .55),
         ("flash", .5), ("push_left", .5), ("wipe", .5), ("push_left", .5), ("flash", .5), ("fade", .5),
         ("flash", .5), ("zoom", .55), ("fade", .9)]
if WITH_CLIPS and VILLA != "palmarin":
    TRANS = [("zoom", .55), ("push_left", .5), ("fade", .55), ("wipe", .55), ("push_up", .5), ("fade", .55),
             ("flash", .5), ("fade", .5), ("push_left", .5), ("fade", .5), ("wipe", .5), ("fade", .5),
             ("push_left", .5), ("fade", .5), ("wipe", .5), ("fade", .5), ("flash", .5), ("fade", .5),
             ("push_left", .5), ("flash", .5), ("zoom", .55), ("fade", .9)]
if VILLA == "palmarin":
    TRANS = TRANS[:12] + [("fade", .5)] + TRANS[12:]
starts, t = [], 0.0
for i, s in enumerate(SHOTS):
    starts.append(t)
    if i < len(TRANS):
        t += s[1] - TRANS[i][1]
    else:
        t += s[1]
TOTAL = t
NF = int(round(TOTAL * FPS))

imgs = {}
for s in SHOTS:
    if s[2] != "clip":
        imgs[s[0]] = Image.open(f"{PHOTOS}/{s[0]}.jpg").convert("RGB")

# ------------------------------------------------------------------ rendu d'un plan
def kb_window(iw, ih, p, cfg, aspect):
    z0, z1, fx0, fx1, fy0, fy1 = cfg
    e = ease_io(p) * .6 + p * .4  # presque linéaire, départ/arrivée adoucis
    z = z0 + (z1 - z0) * e
    fx, fy = fx0 + (fx1 - fx0) * e, fy0 + (fy1 - fy0) * e
    if iw / ih > aspect:
        bh = ih; bw = ih * aspect
    else:
        bw = iw; bh = iw / aspect
    w, h = bw / z, bh / z
    x0 = clamp(fx * iw - w / 2, 0, iw - w); y0 = clamp(fy * ih - h / 2, 0, ih - h)
    return (x0, y0, x0 + w, y0 + h)


SHARP = ImageFilter.UnsharpMask(radius=.8, percent=int(os.environ.get("SHARP_PCT", "18")), threshold=3)   # léger : les photos sont déjà nettoyées/affûtées à la retouche
_bg_cache = {}
def fit_bg(name):
    if name not in _bg_cache:
        g = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
        a = np.array(NAVY_D, np.float32) * (1 - g) + np.array(NAVY, np.float32) * g
        _bg_cache[name] = np.broadcast_to(a, (H, W, 3)).astype(np.uint8).copy()
    return _bg_cache[name]


_tint = None
def outro_tint():
    global _tint
    if _tint is None:
        y = np.linspace(0, 1, H, dtype=np.float32)[:, None]
        a = 0.64 + 0.22 * y  # voile teal plus dense en bas
        _tint = (np.broadcast_to(a[..., None], (H, W, 1)).copy(), np.array(NAVY_D, np.float32))
    return _tint


_clip_n = {}
def render_shot(i, lt):
    name, dur, mode, cfg = SHOTS[i]
    p = clamp(lt / dur)
    if mode == "clip":
        if name not in _clip_n:
            _clip_n[name] = len(glob.glob(f"{CLIP_FRAMES}/{name}/*.jpg"))
        k = max(0, min(int(lt * FPS), _clip_n[name] - 1))
        cim = Image.open(f"{CLIP_FRAMES}/{name}/{k:04d}.jpg").convert("RGB")
        if cim.height != H:                       # 4:5 : recadrage centré dans la hauteur 9:16
            y0 = (cim.height - H) // 2
            cim = cim.crop((0, y0, cim.width, y0 + H))
        return np.asarray(cim)
    im = imgs[name]
    if mode == "fit":
        base = fit_bg(name).copy()
        box = kb_window(*im.size, p, cfg, 4 / 3)
        fg = im.resize((W, 810), Image.LANCZOS, box=box).filter(SHARP)
        y0 = (H - 810) // 2 - 70
        base[y0:y0 + 810] = np.asarray(fg)
        return base
    box = kb_window(*im.size, p, cfg, W / H)
    fr = np.asarray(im.resize((W, H), Image.LANCZOS, box=box).filter(SHARP))
    if mode == "outro":
        a, col = outro_tint()
        fr = (fr.astype(np.float32) * (1 - a) + col * a).astype(np.uint8)
    return fr


# ------------------------------------------------------------------ transitions
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
DIAG = (xx / W * .55 + yy / H * .45)


def trans_frame(kind, A, B, p):
    e = ease_io(p)
    if kind == "fade":
        return (A * (1 - e) + B * e).astype(np.uint8) if False else (A.astype(np.float32) * (1 - e) + B.astype(np.float32) * e).astype(np.uint8)
    if kind == "push_left":
        o = int(W * e); out = np.empty_like(A)
        out[:, :W - o] = A[:, o:]; out[:, W - o:] = B[:, :o]
        return out
    if kind == "push_up":
        o = int(H * e); out = np.empty_like(A)
        out[:H - o] = A[o:]; out[H - o:] = B[:o]
        return out
    if kind == "wipe":
        soft = .18
        thr = -soft + e * (1 + 2 * soft)
        m = np.clip((thr - DIAG) / soft, 0, 1)[..., None]
        return (A.astype(np.float32) * (1 - m) + B.astype(np.float32) * m).astype(np.uint8)
    if kind == "zoom":
        def zoomed(fr, s):
            w, h = W / s, H / s
            x0, y0 = (W - w) / 2, (H - h) / 2
            return np.asarray(Image.fromarray(fr).resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + w, y0 + h)))
        za, zb = zoomed(A, 1 + .35 * e), zoomed(B, 1.18 - .18 * e)
        return (za.astype(np.float32) * (1 - e) + zb.astype(np.float32) * e).astype(np.uint8)
    if kind == "flash":
        k = ease_out(p / .5) if p < .5 else ease_out((1 - p) / .5)
        src = A if p < .5 else B
        white = np.array([255, 247, 232], np.float32)
        return (src.astype(np.float32) * (1 - .88 * k) + white * .88 * k).astype(np.uint8)
    raise ValueError(kind)


# ------------------------------------------------------------------ overlays globaux
VIG = (1 - .30 * np.clip(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 1.7)) ** 2, 0, 1.4) ** 1.1).astype(np.float32)[..., None]
GRAD = np.clip((np.linspace(0, 1, H, dtype=np.float32) - .55) / .45, 0, 1) ** 1.4
GRAD_TOP = np.clip((.16 - np.linspace(0, 1, H, dtype=np.float32)) / .16, 0, 1) ** 1.5

_rs = np.random.default_rng(3)
BK_H = H + 700
bk = np.zeros((BK_H, W), np.float32)
for _ in range(46):
    cx, cy, r = _rs.uniform(0, W), _rs.uniform(0, BK_H), _rs.uniform(7, 34)
    y0, y1, x0, x1 = int(max(0, cy - 2 * r)), int(min(BK_H, cy + 2 * r)), int(max(0, cx - 2 * r)), int(min(W, cx + 2 * r))
    gy, gx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    d = np.sqrt((gx - cx) ** 2 + (gy - cy) ** 2) / r
    bk[y0:y1, x0:x1] += _rs.uniform(.05, .12) * np.clip(1.15 - d, 0, 1) ** .8 * (1 + .6 * (np.abs(d - .85) < .12))
BOKEH = np.minimum(bk, .22)
WARM = np.array([255, 214, 172], np.float32)


# ------------------------------------------------------------------ évènements texte
EV = []     # dict(layer, x(center), y(center), t_in, t_out, anim)
SX = []     # effets sonores (t, son, gain, pan)

def add_ev(shot, off, dur, layer, cx, cy, anim="rise", left=False):
    t_in = starts[shot] + off
    t_out = t_in + dur
    EV.append(dict(layer=layer, x=cx, y=cy, t_in=t_in, t_out=t_out, anim=anim, left=left, arr=None))
    return t_in


# Intro : médaillon de la marque + titre
t = add_ev(0, .25, 3.2, logo_layer(P["i_logo_w"]), 540, P["i_logo_y"], "pop"); SX.append((t, sfx.pop(520), 1, 0))
if NEW_TAG:
    add_ev(0, .70, 2.7, tag("NOUVELLE VILLA"), 540, P["i_tag"])
add_ev(0, .90, 2.5, text_layer(TITLE, F_TITLE, P["i_title_s"], tracking=2, max_w=900, shadow=.75), 540, P["i_title"])
add_ev(0, 1.30, 2.1, text_layer("Grand-Baie  ·  Île Maurice", F_MED, 42, tracking=4, fill=WHITE, max_w=900, shadow=.9), 540, P["i_sub"])
SX.append((starts[0] + .05, sfx.shimmer(.75, .30), 1.0, 0))
SX.append((starts[0] + .92, sfx.ding(1568, 1.8, .3), .8, 0))
SX.append((starts[0] + 1.32, sfx.tick(1200), .9, 0))
# Logo en pied de page sur toutes les photos
add_ev(1, .3, starts[len(SHOTS) - 1] - starts[1] - .1, logo_layer(170, glow=True), 824, P["wm_y"], "rise", left=True)

LY, CY = P["label_y"], P["chip_y"]
_f = lambda sub: next(i for i, sh in enumerate(SHOTS) if sub in sh[0])
if VILLA == "palmarin":
    BEDS, SDB, IPOOL, ILAST = [7, 8, 9, 10], [11, 12, 13], 14, 15
elif WITH_CLIPS:      # les plans « clip » s'intercalent : on repère les photos par leur nom
    BEDS = [_f("08_chambre-1"), _f("09_chambre-2"), _f("10_chambre-3"), _f("11_chambre-4")]
    SDB = [_f("12_salle-de-bain-1"), _f("13_salle-de-bain-2")]
    IPOOL, ILAST = _f("14_piscine-privee"), _f("15_piscine-et-terrasse")
else:
    BEDS, SDB, IPOOL, ILAST = [7, 8, 9, 10], [11, 12], 13, 14
# Plan 2 : piscine privée
t = add_ev(1, .45, 2.0, chip("pool", "PISCINE PRIVÉE"), *((500, P["chip1_y"]) if SHOTS[1][2] == "fit" else (540, CY)), "pop"); SX.append((t, sfx.pop(640), 1, 0))
# Plans 3-7 : espaces de vie
for i, (tx, sb) in LAB.items():
    t = add_ev(i, .35, 2.0, label(tx, sb), 60, LY, "rise", left=True); SX.append((t, sfx.tick(1500 + 90 * i), .8, -.2))
# Chambres
t = add_ev(BEDS[0], .35, 2.2, chip("bed", "4 CHAMBRES"), 540, CY, "pop"); SX.append((t, sfx.pop(700), 1, 0))
for n, i in enumerate(BEDS, 1):
    sub = "Vue piscine" if n == 2 else None
    t = add_ev(i, .45 if n == 1 else .3, 2.0, label(f"Chambre {n}", sub), 60, LY, "rise", left=True)
    SX.append((t, sfx.tick(1400 + 110 * n), .8, -.2))
# Salles de bain
t = add_ev(SDB[0], .35, 2.2, chip("shower", "3 SALLES DE BAIN"), 540, CY, "pop"); SX.append((t, sfx.pop(760), 1, 0))
t = add_ev(SDB[0], .55, 1.9, label("Salle de bain"), 60, LY, "rise", left=True); SX.append((t, sfx.tick(1700), .8, -.2))
t = add_ev(SDB[1], .30, 2.0, label("Salle de bain"), 60, LY, "rise", left=True); SX.append((t, sfx.tick(1800), .8, -.2))
if len(SDB) > 2:        # 3e salle de bain
    t = add_ev(SDB[2], .30, 2.0, label("Salle de bain"), 60, LY, "rise", left=True); SX.append((t, sfx.tick(1900), .8, -.2))
# Piscine
t = add_ev(IPOOL, .35, 2.5, chip("pool", "PISCINE PRIVÉE", POOL_SUB), 540, CY, "pop"); SX.append((t, sfx.pop(660), 1, 0))
SX.append((starts[IPOOL] + .1, sfx.water(2.2, .32), 1, 0))
t = add_ev(ILAST, .3, 2.2, label(LAST_LABEL), 60, LY, "rise", left=True); SX.append((t, sfx.tick(1500), .8, -.2))
SX.append((starts[ILAST] + .2, sfx.water(1.8, .22), 1, .1))

# Outro : médaillon, critères, (appel à réserver si CTA) — reste affiché jusqu'à la fin
o = len(SHOTS) - 1; HOLD = 30
t = add_ev(o, .30, HOLD, logo_layer(P["o_logo_w"]), 540, P["o_logo_y"] + SHIFT, "pop"); SX.append((t, sfx.pop(480), 1, 0))
add_ev(o, .70, HOLD, text_layer(TITLE, F_TITLE, P["o_title_s"], tracking=2, max_w=900, shadow=.75), 540, P["o_title"] + SHIFT)
rows = [("bed", "4 CHAMBRES", None), ("shower", "3 SALLES DE BAIN", None), ("pool", "PISCINE PRIVÉE", None),
        ("pin", "GRAND-BAIE", LOC_SUB)]
for k, (ic, tx, sb) in enumerate(rows):
    off = 1.2 + .5 * k
    t = add_ev(o, off, HOLD, chip(ic, tx, sb, min_w=900), 540,
               P["rows_y0"] + SHIFT + P["rows_dy"] * k + (P["rows_extra"] if k == 3 else 0), "pop")
    SX.append((t, sfx.pop(560 + 70 * k, .3, .42), 1, 0))
if CTA:
    add_ev(o, 3.7, HOLD, text_layer("Réservation directe au meilleur tarif", F_SEMI, 40, tracking=1, max_w=940, shadow=.8), 540, P["cta_y"])
    add_ev(o, 4.0, HOLD, text_layer("maurenthouses.myweb.smoobu.com", F_MED, 34, tracking=1, fill=PEACH, max_w=940, shadow=.8), 540, P["url_y"])
    SX.append((starts[o] + 3.72, sfx.ding(1760, 2.0, .34), .9, 0))
    SX.append((starts[o] + 3.8, sfx.shimmer(.8, .2), .6, 0))
else:
    SX.append((starts[o] + 2.95, sfx.ding(1760, 2.0, .34), .9, 0))
    SX.append((starts[o] + 3.0, sfx.shimmer(.8, .2), .6, 0))

# Transitions -> sons
for i, (kind, d) in enumerate(TRANS):
    ts = starts[i + 1]
    if kind == "push_left":
        SX.append((ts - .06, sfx.whoosh(.6, 1, 250, 3600, .55), 1, np.linspace(.6, -.6, int(.6 * sfx.SR))))
    elif kind == "push_up":
        SX.append((ts - .06, sfx.whoosh(.6, 1, 200, 3000, .55), 1, 0))
    elif kind == "wipe":
        SX.append((ts - .06, sfx.whoosh(.62, -1, 400, 4500, .5), 1, np.linspace(-.5, .5, int(.62 * sfx.SR))))
    elif kind == "zoom":
        SX.append((ts - .08, sfx.whoosh(.7, 1, 150, 2600, .55), 1, 0))
    elif kind == "fade":
        SX.append((ts - .05, sfx.whoosh(.8 if d > .6 else .65, 1, 180, 1300, .28), 1, 0))
    elif kind == "flash":
        SX.append((ts - .03, sfx.shimmer(.55, .26), 1, 0))
        SX.append((ts + .12, sfx.ding(1318, 1.2, .18), 1, 0))


def draw_events(fr, t):
    for ev in EV:
        if not (ev["t_in"] - .01 <= t <= ev["t_out"] + .01):
            continue
        pin = clamp((t - ev["t_in"]) / .5); pout = clamp((ev["t_out"] - t) / .35)
        a = ease_out(pin) * pout
        if a <= 0.003:
            continue
        lay = ev["layer"]
        if ev["anim"] == "pop":
            s = .82 + .18 * ease_back(pin)
            lay = lay.resize((max(2, int(lay.width * s)), max(2, int(lay.height * s))), Image.BICUBIC)
            dy = 0
        else:
            dy = (1 - ease_out(pin)) * 46
        arr = np.asarray(lay, dtype=np.float32)
        h, w = arr.shape[:2]
        x = int(ev["x"]) if ev["left"] else int(ev["x"] - w / 2)
        y = int(ev["y"] - h / 2 + dy)
        x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
        if x1 <= x0 or y1 <= y0:
            continue
        sub = arr[y0 - y:y1 - y, x0 - x:x1 - x]
        al = (sub[..., 3:4] / 255.) * a
        reg = fr[y0:y1, x0:x1]
        fr[y0:y1, x0:x1] = reg * (1 - al) + sub[..., :3] * al


# ------------------------------------------------------------------ rendu d'une image du film
def which(t):
    for i in range(len(SHOTS)):
        if i == len(SHOTS) - 1:
            return i, None
        te = starts[i + 1]            # début de la transition i -> i+1
        if t < te:
            return i, None
        if t < te + TRANS[i][1]:
            return i, (t - te) / TRANS[i][1]
    return len(SHOTS) - 1, None


GRAIN = float(os.environ.get("GRAIN", "0"))
_rng = np.random.default_rng(11)


def frame_at(t):
    i, tp = which(t)
    A = render_shot(i, t - starts[i])
    sweep = 0.0
    if tp is not None:
        kind = TRANS[i][0]
        B = render_shot(i + 1, t - starts[i + 1])
        fr = trans_frame(kind, A, B, tp)
        if kind in ("push_left", "push_up", "wipe", "zoom", "fade"):
            sweep = math.sin(math.pi * tp)
    else:
        fr = A
    fr = fr.astype(np.float32)
    # poussière lumineuse (bokeh) qui dérive vers le haut
    off = int((t * 16) % 700)
    # reflet lumineux pendant les transitions
    if sweep > 0:
        pos = -.25 + 1.5 * (tp if tp is not None else 0)
        band = np.exp(-((DIAG - pos) / .12) ** 2)[..., None]
        fr += band * WARM * .30 * sweep
    # voiles de lisibilité + vignette
    k = .34 + .30 * clamp((3.9 - t) / .9)
    if i >= len(SHOTS) - 1:
        k = 0.0
    fr *= (1 - k * GRAD)[:, None, None]
    np.clip(fr, 0, 255, out=fr)
    draw_events(fr, t)
    if GRAIN > 0:
        fr += _rng.normal(0, GRAIN, fr.shape[:2]).astype(np.float32)[..., None]
        np.clip(fr, 0, 255, out=fr)
    return fr.astype(np.uint8)


# ------------------------------------------------------------------ main
if __name__ == "__main__":
    print(f"durée {TOTAL:.2f}s  ({NF} images)  départs:", [round(s, 2) for s in starts])
    audio = sfx.mix(SX, TOTAL + .1, bus_peak=.62)
    wav = OUT.replace(".mp4", "_bruitages.wav")
    sfx.write_wav(wav, audio)
    if MODE == "stills":
        outd = os.path.dirname(OUT)
        for tt in [float(x) for x in sys.argv[4].split(",")]:
            Image.fromarray(frame_at(tt)).save(f"{outd}/still_{tt:05.2f}.jpg", quality=90)
        sys.exit()
    # Encodage : conversion RGB -> YUV BT.709 explicite (sinon BT.601 par défaut = couleurs/contours faussés),
    # x264 « slow », CRF bas, AQ pour les aplats (murs blancs), débit plafonné pour rester < 100 Mo.
    ENC = os.environ.get("ENC", "new")
    seg = os.environ.get("SEG")            # "début,fin" en s : rend seulement un extrait (tests), sans audio
    n0, n1 = (int(float(x) * FPS) for x in seg.split(",")) if seg else (0, NF)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
    if not seg: cmd += ["-i", wav, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k", "-t", f"{TOTAL:.3f}"]
    if ENC == "old":
        cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-maxrate", "14M", "-bufsize", "28M", "-pix_fmt", "yuv420p", "-profile:v", "high"]
    else:
        cmd += ["-vf", "scale=out_color_matrix=bt709:out_range=tv:flags=lanczos+accurate_rnd+full_chroma_int,format=yuv420p",
                "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
                "-c:v", "libx264", "-preset", os.environ.get("X264_PRESET", "slow"), "-crf", os.environ.get("X264_CRF", "15"),
                "-profile:v", "high", "-x264-params", "aq-mode=3:psy-rd=1.0,0.0:deblock=-1,-1",
                "-maxrate", os.environ.get("MAXRATE", "20M"), "-bufsize", "40M", "-g", "60"]
    cmd += ["-r", str(FPS), "-movflags", "+faststart", OUT]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for n in range(n0, n1):
        pr.stdin.write(frame_at(n / FPS).tobytes())
        if n % 100 == 0:
            print(n, "/", NF, flush=True)
    pr.stdin.close(); pr.wait()
    print("terminé", OUT)
