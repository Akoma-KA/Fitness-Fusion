"""Prépare les clips vidéo (WhatsApp 480x854) pour le montage : retouche « annonce » cohérente + agrandissement 1080x1920.

Usage : python3 -I prep_clips.py <dossier_des_clips_source> <dossier_frames_sortie> [<dossier_mp4_sortie>]
Les paramètres de retouche sont estimés une seule fois par clip (image médiane) puis appliqués à toutes
les images : pas de scintillement. L'audio d'origine est supprimé.
"""
import os, sys, glob, subprocess, shutil, tempfile
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance

FPS = 30
OUT_W, OUT_H = 1080, 1920
# nom de sortie, fichier source (motif), début (s), durée (s)
CLIPS = [
    ("clip-08a-chambre-1", "WA0065", 1.7, 3.2),
    ("clip-08b-chambre-1", "WA0062", 0.2, 2.4),
    ("clip-08c-chambre-1", "WA0063", 0.2, 2.4),
    ("clip-09-chambre-2", "WA0066", 0.2, 2.8),
    ("clip-10-chambre-3", "WA0064", 0.3, 2.8),
    ("clip-11-chambre-4", "WA0067", 0.3, 2.8),
    ("clip-12-salle-de-bain", "WA0068", 0.6, 3.0),
]


def lum(a): return a[..., 0] * .2126 + a[..., 1] * .7152 + a[..., 2] * .0722


def estimate(a, target=.665):
    """Paramètres de retouche à partir d'une image médiane (float 0..1)."""
    L = lum(a); mx, mn = a.max(-1), a.min(-1)
    m = ((mx - mn) < .18) & (L > .35) & (L < .95)
    gain = np.ones(3, np.float32)
    if m.sum() > 1000:
        mean = a[m].mean(0)
        gain = 1 + (np.clip(mean.mean() / mean, .86, 1.14) - 1) * .9
    gain = gain * np.array([1.035, 1.0, .955], np.float32)       # ambiance chaude
    b = np.clip(a * gain, 0, 1); Lb = lum(b)
    lo, hi = .45, 1.0
    for _ in range(18):
        g = (lo + hi) / 2
        if (Lb ** g).mean() > target: lo = g
        else: hi = g
    g = min(1.0, max(.64, (lo + hi) / 2))
    c = np.power(np.clip(b, 1e-4, 1), g)
    c = c + (.22 * (1 - lum(c)) ** 2.4)[..., None] * (.55 + .45 * c)
    p = np.percentile(lum(c), 99.5)
    wscale = float(np.clip(.975 / max(p, .5), .92, 1.22))
    return dict(gain=gain, g=g, wscale=wscale)


def apply(a, P):
    b = np.clip(a * P["gain"], 0, 1)
    c = np.power(np.clip(b, 1e-4, 1), P["g"])
    c = c + (.22 * (1 - lum(c)) ** 2.4)[..., None] * (.55 + .45 * c)
    c = c * P["wscale"]
    c = np.where(c > .86, .86 + (c - .86) * .55, c)
    c = np.clip(c, 0, 1)
    c = c + .24 * (c - .5) * (1 - np.abs(2 * c - 1))
    L = lum(c)
    B = np.asarray(Image.fromarray((np.clip(L, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(12)), np.float32) / 255.
    c = np.clip(c + ((L - B) * .44)[..., None], 0, 1)
    out = Image.fromarray((c * 255 + .5).astype(np.uint8))
    out = ImageEnhance.Color(out).enhance(1.22)
    hsv = np.asarray(out.convert("HSV"), dtype=np.float32); h = hsv[..., 0] * 360 / 255.
    blue = np.exp(-((h - 200) / 42.) ** 2); green = np.exp(-((h - 110) / 35.) ** 2); wood = np.exp(-((h - 28) / 18.) ** 2)
    hsv[..., 1] = np.clip(hsv[..., 1] * (1 + .30 * blue + .14 * green + .12 * wood), 0, 255)
    hsv[..., 1] = np.clip(hsv[..., 1] * (1 + .10 * (1 - hsv[..., 1] / 255.)), 0, 255)
    return Image.fromarray(hsv.astype(np.uint8), "HSV").convert("RGB")


def main(src, out_frames, out_mp4=None, only=None):
    for name, pat, start, length in CLIPS:
        if only and name not in only: continue
        f = [p for p in glob.glob(os.path.join(src, f"*{pat}.mp4"))][0]
        tmp = tempfile.mkdtemp(prefix="clip_")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(start), "-t", str(length), "-i", f,
                        "-vf", f"fps={FPS},hqdn3d=3:2:5:4", "-start_number", "0", os.path.join(tmp, "%04d.png")], check=True)
        pngs = sorted(glob.glob(os.path.join(tmp, "*.png")))
        mid = np.asarray(Image.open(pngs[len(pngs) // 2]).convert("RGB"), np.float32) / 255.
        P = estimate(mid)
        d = os.path.join(out_frames, name); os.makedirs(d, exist_ok=True)
        for i, p in enumerate(pngs):
            a = np.asarray(Image.open(p).convert("RGB"), np.float32) / 255.
            im = apply(a, P).resize((OUT_W, OUT_H), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=1.6, percent=70, threshold=2))
            im.save(os.path.join(d, f"{i:04d}.jpg"), quality=93, subsampling=0)
        shutil.rmtree(tmp)
        if out_mp4:
            os.makedirs(out_mp4, exist_ok=True)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(d, "%04d.jpg"),
                            "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                            os.path.join(out_mp4, name + ".mp4")], check=True)
        print(name, len(pngs), "images", "gamma %.2f" % P["g"], "wscale %.2f" % P["wscale"], flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "-" else None,
         set(sys.argv[4].split(",")) if len(sys.argv) > 4 else None)
