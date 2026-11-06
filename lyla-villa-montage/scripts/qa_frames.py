"""Banc d'essai qualité : compare des images d'un MP4 encodé à l'image de référence non compressée (frame_at).

Usage (mêmes variables d'environnement que montage.py : VILLA, FMT, CTA, CLIPS, CLIP_FRAMES, BRAND_DIR) :
  python3 -I qa_frames.py <photos_dir> <video.mp4> <t1,t2,...> <dossier_sortie> [<video_B.mp4>]
Écrit pour chaque instant un PNG « référence | A [| B] » en recadrage 1:1 (360x360 au centre-haut des détails)
et affiche SSIM / PSNR / netteté (variance du Laplacien).
"""
import os, sys, subprocess
import numpy as np
from PIL import Image

photos, vid, times, outd = sys.argv[1], sys.argv[2], [float(x) for x in sys.argv[3].split(",")], sys.argv[4]
vid_b = sys.argv[5] if len(sys.argv) > 5 else None
os.makedirs(outd, exist_ok=True)
sys.argv = ["montage.py", photos, "/dev/null", "none"]       # importe le module sans rendre
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import montage as M


def ssim(a, b):
    a = np.asarray(Image.fromarray(a).convert("L"), np.float32); b = np.asarray(Image.fromarray(b).convert("L"), np.float32)
    k = 7
    def mean(x):
        c = np.cumsum(np.cumsum(np.pad(x, ((1, 0), (1, 0))), 0), 1)
        return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)
    mu_a, mu_b = mean(a), mean(b)
    va, vb, cov = mean(a * a) - mu_a ** 2, mean(b * b) - mu_b ** 2, mean(a * b) - mu_a * mu_b
    C1, C2 = (.01 * 255) ** 2, (.03 * 255) ** 2
    return float((((2 * mu_a * mu_b + C1) * (2 * cov + C2)) / ((mu_a ** 2 + mu_b ** 2 + C1) * (va + vb + C2))).mean())


def psnr(a, b):
    mse = ((a.astype(np.float32) - b.astype(np.float32)) ** 2).mean()
    return 99.0 if mse == 0 else float(10 * np.log10(255 ** 2 / mse))


def lap_var(a):
    g = np.asarray(Image.fromarray(a).convert("L"), np.float32)
    l = g[1:-1, 1:-1] * 4 - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:]
    return float(l.var())


def decode(path, t):
    t = t - float(os.environ.get("QA_OFFSET", "0"))        # extrait rendu avec SEG=début,fin
    tmp = os.path.join(outd, "_dec.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1", tmp], check=True)
    return np.asarray(Image.open(tmp).convert("RGB"))


for t in times:
    # la vidéo est à FPS fixe : on prend l'image exacte n/FPS pour que référence et décodage coïncident
    t = round(t * M.FPS) / M.FPS
    ref = M.frame_at(t)
    outs = [("réf", ref)]
    for label, path in (("A", vid), ("B", vid_b)):
        if path:
            d = decode(path, t)
            outs.append((label, d))
            print(f"t={t:6.2f}  {label}: SSIM {ssim(ref, d):.4f}  PSNR {psnr(ref, d):5.2f} dB  netteté(lap.var) {lap_var(d):7.1f}   (réf {lap_var(ref):7.1f})")
    h, w = ref.shape[:2]
    # recadrage 1:1 sur une zone riche en détails (autour de 40 % de la hauteur)
    y0, x0 = int(h * .40), w // 2 - 180
    tiles = [Image.fromarray(o[y0:y0 + 360, x0:x0 + 360]) for _, o in outs]
    sheet = Image.new("RGB", (370 * len(tiles), 360), "white")
    for i, im in enumerate(tiles): sheet.paste(im, (i * 370, 0))
    sheet.save(os.path.join(outd, f"crop_{t:05.2f}.png"))
