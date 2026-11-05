import sys, os, shutil
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from retouch import retouch
U = "/root/.claude/uploads/164dbbcf-d142-5fe7-9f91-fd4f47a4d8f8/"
SRC = dict(enumerate("9a9b7997 b08f75f7 8a4d7ff9 a2948f23 4f008ab5 bfa19ad2 aba3666c 8a1cc3e2 8696cf58 005c5103 6f7d28ef 0cff18a1 fd8322bf e656f60a f0a85bbb ed770c54 351dd2b2 440ab523 c01a8e64 e25e60f0 d0577831".split(), 1))
# (n° photo, nom, type) — couverture = photo 1, puis ordre logique réseaux/Airbnb/Booking
ORDER = [(1, "facade-couverture", "ext"), (19, "facade-palmier", "ext"), (4, "salon", "int"), (5, "salon-tv", "int"),
         (3, "sejour-terrasse", "int"), (2, "salle-a-manger-cuisine", "int"), (8, "cuisine-equipee", "int"),
         (10, "chambre-1", "int"), (11, "chambre-2-vue-piscine", "int"), (12, "chambre-3", "int"), (13, "chambre-4", "int"),
         (14, "salle-de-bain-1", "int"), (15, "salle-de-bain-2", "int"), (21, "salle-de-bain-3", "int"),
         (6, "piscine-jardin", "ext"), (9, "terrasse-piscine", "ext")]
dst = sys.argv[1]; os.makedirs(dst, exist_ok=True)
for i, (n, name, kind) in enumerate(ORDER, 1):
    retouch(Image.open(f"{U}{SRC[n]}-image.jpg").convert("RGB"), kind).save(f"{dst}/{i:02d}_{name}.jpg", quality=95, subsampling=0)
# fond de l'écran final : la façade de couverture (même photo)
shutil.copy(f"{dst}/01_facade-couverture.jpg", f"{dst}/17_facade-fin.jpg")
print("ok", len(ORDER) + 1)
