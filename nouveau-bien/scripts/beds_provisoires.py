"""Chambres 2–4 : habillage local provisoire (drap blanc, oreillers, serviettes) + retouche annonce."""
import sys, os
import numpy as np, cv2
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lyla-villa-montage", "scripts"))
from stage_bed import dress_bed
from retouch_listing import listing
U = "/root/.claude/uploads/164dbbcf-d142-5fe7-9f91-fd4f47a4d8f8/"
def clean(im, polys, radius=6, grain=1.6):
    """Retire des objets (inpainting local) : reconstruit le fond puis ajoute un grain léger pour ne pas laisser de zone lisse."""
    a = np.asarray(im.convert("RGB")).copy()
    m = np.zeros(a.shape[:2], np.uint8)
    for p in polys: cv2.fillPoly(m, [np.array(p, np.int32)], 255)
    m = cv2.dilate(m, np.ones((13, 13), np.uint8))
    filled = cv2.inpaint(a, m, radius, cv2.INPAINT_TELEA)
    rng = np.random.default_rng(5)
    g = rng.normal(0, grain, a.shape[:2])[..., None]
    soft = cv2.GaussianBlur(m.astype(np.float32) / 255., (0, 0), 3)[..., None]
    out = a * (1 - soft) + np.clip(filled + g, 0, 255) * soft
    return Image.fromarray(out.astype(np.uint8))


ROOMS = {
    "05_chambre-2": dict(f="5829fd92", quad=((760, 935), (1062, 995), (912, 1195), (530, 1015)), drop=62,
                      clean=[[(0, 636), (324, 636), (324, 721), (0, 699)]]),
    "06_chambre-3": dict(f="ab4568b6", quad=((288, 982), (542, 925), (790, 1010), (505, 1152)), drop=52,
                      clean=[[(0, 1058), (120, 1062), (160, 1090), (150, 1100), (188, 1150), (195, 1215), (175, 1235), (120, 1260), (78, 1300), (66, 1380), (66, 1600), (0, 1600)],
                             [(808, 1050), (905, 1045), (914, 1142), (810, 1146)]]),
    "07_chambre-4": dict(f="983f962b", quad=((39, 1000), (522, 892), (798, 989), (189, 1306)), drop=62, protect_dark=.17),
}
def run(dst, only=None, final=True):
    os.makedirs(dst, exist_ok=True)
    for name, r in ROOMS.items():
        if only and name not in only: continue
        im = Image.open(U + r["f"] + "-image.jpg").convert("RGB")
        if r.get("clean"): im = clean(im, r["clean"])
        d = dress_bed(im, r["quad"], drop=r["drop"], protect_dark=r.get("protect_dark", 0))
        d.save(dst + f"/_{name}_brut.jpg", quality=95)
        (listing(d, "int") if final else d).save(f"{dst}/{name}.jpg", quality=97, subsampling=0)
        print("ok", name, flush=True)
if __name__ == "__main__":
    run(sys.argv[1], set(sys.argv[2].split(",")) if len(sys.argv) > 2 else None)
