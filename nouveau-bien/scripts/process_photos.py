"""Retouche « annonce » (Airbnb / Booking) des photos du nouveau bien — salon, salle à manger, cuisine, salle de bain."""
import sys, os
from PIL import Image
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lyla-villa-montage", "scripts"))
from retouch_listing import listing

U = "/root/.claude/uploads/164dbbcf-d142-5fe7-9f91-fd4f47a4d8f8/"
# nom de sortie -> (fichier source, nettoyage optionnel)
JOBS = {
    "01_salon": "bcf893db",
    "02_salon-salle-a-manger": "8e1eea08",
    "03_cuisine-salle-a-manger": "ef1b02ef",
    "08_salle-de-bain": "6eebdf43",
}

# pièces à vivre : rendu naturel ; salle de bain : rendu annonce
STYLE = {"01_salon": "natural", "02_salon-salle-a-manger": "natural", "03_cuisine-salle-a-manger": "natural"}


def run(dst, only=None, pre=None):
    os.makedirs(dst, exist_ok=True)
    for name, f in JOBS.items():
        if only and name not in only: continue
        im = Image.open(f"{U}{f}-image.jpg").convert("RGB")
        if pre and name in pre: im = pre[name](im)
        listing(im, "int", style=STYLE.get(name, "listing")).save(f"{dst}/{name}.jpg", quality=97, subsampling=0)
        print("ok", name, flush=True)

def crop_person(im):
    """Cuisine : la personne est au bord droit (x >= 1145). On recadre ce bord (vrai recadrage, aucun pixel inventé),
    en gardant le haut (suspensions) ; format 3:4 conservé, puis retour à 1200x1600."""
    w = 1135; h = round(w * 4 / 3)
    return im.crop((0, 0, w, h)).resize((1200, 1600), Image.LANCZOS)


if __name__ == "__main__":
    run(sys.argv[1], set(sys.argv[2].split(",")) if len(sys.argv) > 2 else None, pre={"03_cuisine-salle-a-manger": crop_person})
