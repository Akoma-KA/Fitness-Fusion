"""Retouche « annonce » (Airbnb / Booking) : lumineuse, aérée, chaleureuse, naturelle."""
import io, subprocess
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance


def deblock(img):
    """Supprime les blocs de compression JPEG (WhatsApp) AVANT l'éclaircissement, qui les ferait ressortir."""
    buf = io.BytesIO(); img.convert("RGB").save(buf, "PNG")
    r = subprocess.run(["ffmpeg", "-v", "error", "-f", "image2pipe", "-i", "-", "-vf", "pp7=qp=7:mode=medium,hqdn3d=2:2:0:0",
                        "-f", "image2pipe", "-c:v", "png", "-"], input=buf.getvalue(), capture_output=True, check=True)
    out = Image.open(io.BytesIO(r.stdout)).convert("YCbCr")
    y, cb, cr = out.split()                                   # lissage de la chrominance (blocage couleur)
    cb, cr = cb.filter(ImageFilter.GaussianBlur(1.2)), cr.filter(ImageFilter.GaussianBlur(1.2))
    return Image.merge("YCbCr", (y, cb, cr)).convert("RGB")

def lum(a): return a[..., 0] * .2126 + a[..., 1] * .7152 + a[..., 2] * .0722

STYLES = {
    # « listing » : très lumineux et chaleureux (chambres, extérieurs)
    "listing": dict(warm=(1.035, 1.0, .955), target=.71, gmin=.5, lift=.22, s=.13, clar=.30, sat=1.22, vib=True, black=0.0, white=.975),
    # « natural » : proche de ce que l'œil voit (pièces à vivre) — noirs conservés, blancs neutres, éclairage modéré
    "natural": dict(warm=(1.0, 1.0, 1.0), target=.60, gmin=.74, lift=.09, s=.15, clar=.14, sat=1.07, vib=False, black=.8, white=.955),
}


def listing(img, kind, style="listing"):
    P = STYLES[style]
    img = deblock(img)
    a = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.
    # 1. blancs propres : balance des blancs sur les murs / plafonds, puis ambiance chaude légère
    L = lum(a); mx, mn = a.max(-1), a.min(-1)
    m = ((mx - mn) < .18) & (L > .35) & (L < .95)
    if kind == "int" and m.sum() > 2000:
        mean = a[m].mean(0); gain = np.clip(mean.mean() / mean, .86, 1.14)
        a = a * (1 + (gain - 1) * .9)
    a = a * (np.array(P["warm"], np.float32) if kind == "int" else np.array([1.01, 1.0, .995], np.float32))
    if P["black"]:                                              # point noir : garde de vrais noirs (pas de voile)
        bp = min(np.percentile(lum(a), .5), .08) * P["black"]
        a = np.clip((a - bp) / (1 - bp), 0, 1)
    a = np.clip(a, 0, 1)
    # 2. exposition : on éclaircit jusqu'à une luminosité cible (gamma), sans toucher aux couleurs
    L = lum(a)
    target = P["target"] if kind == "int" else .58
    lo, hi = .45, 1.0
    for _ in range(18):
        g = (lo + hi) / 2
        if (L ** g).mean() > target: lo = g
        else: hi = g
    g = min(1.0, max(P["gmin"], (lo + hi) / 2))
    a = np.power(np.clip(a, 1e-4, 1), g)
    # 3. ombres ouvertes (sols sombres, recoins) 
    L = lum(a)
    a = a + ((P["lift"] if kind == "int" else .12) * (1 - L) ** 2.4)[..., None] * (.55 + .45 * a)
    # 3b. les ombres relevées amplifient le bruit : on les lisse légèrement
    soft = np.asarray(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.1)), np.float32) / 255.
    w = (np.clip((.40 - lum(a)) / .40, 0, 1) * .65)[..., None]
    a = a * (1 - w) + soft * w
    # 4. blancs : point blanc à ~0.98 et épaule douce (pas de blanc cramé)
    p = np.percentile(lum(a), 99.5)
    a = a * np.clip(P["white"] / max(p, .5), .92, 1.22)
    a = np.where(a > .86, .86 + (a - .86) * .55, a)
    a = np.clip(a, 0, 1)
    # 5. contraste en S + clarté (relief, matières)
    a = a + P["s"] * (a - .5) * (1 - np.abs(2 * a - 1))
    L = lum(a)
    B = np.asarray(Image.fromarray((np.clip(L, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(30)), np.float32) / 255.
    a = np.clip(a + ((L - B) * P["clar"])[..., None], 0, 1)
    out = Image.fromarray((a * 255 + .5).astype(np.uint8))
    # 6. couleurs qui donnent envie : saturation + vibrance, bleus (ciel/piscine), verts, bois chauds
    out = ImageEnhance.Color(out).enhance(P["sat"])
    hsv = np.asarray(out.convert("HSV"), dtype=np.float32); h = hsv[..., 0] * 360 / 255.
    blue = np.exp(-((h - 200) / 42.) ** 2); green = np.exp(-((h - 110) / 35.) ** 2); wood = np.exp(-((h - 28) / 18.) ** 2)
    hsv[..., 1] = np.clip(hsv[..., 1] * (1 + .30 * blue + .14 * green + .12 * wood), 0, 255)
    low = 1 - hsv[..., 1] / 255.
    if P["vib"]: hsv[..., 1] = np.clip(hsv[..., 1] * (1 + .10 * low), 0, 255)          # vibrance : réveille les teintes ternes
    out = Image.fromarray(hsv.astype(np.uint8), "HSV").convert("RGB")
    # 7. netteté
    return out.filter(ImageFilter.UnsharpMask(radius=1.0, percent=28, threshold=3))
