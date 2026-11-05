# Lyla Villa — montage vidéo (Mau-rent Houses)

- 4 versions (sans musique, bruitages légers) : `Lyla-Villa_Reels-9x16_avec-reservation.mp4`, `Lyla-Villa_Reels-9x16_sans-reservation.mp4` (Reels / Stories / TikTok, 1080x1920), `Lyla-Villa_Facebook-4x5_avec-reservation.mp4`, `Lyla-Villa_Facebook-4x5_sans-reservation.mp4` (fil Facebook, 1080x1350). "sans-reservation" = sans la mention « Réservation directe au meilleur tarif » ni le lien.
- `*_bruitages.wav` : piste de bruitages seule de chaque version (0 s = début de la vidéo)
- `photos-retouchees/` : 16 photos retouchées, numérotées dans l'ordre Airbnb/Booking
- `brand/` : identité reprise de https://maurenthouses.myweb.smoobu.com/
  - logo (médaillon corail → pêche sur bleu marine), polices Abril Fatface (titres) + Epilogue (texte)
  - couleurs : bleu marine #122267 · corail #FF5F6D · pêche #FFC371
- `scripts/` : retouch.py, montage.py, sfx.py (`BRAND_DIR=brand python3 scripts/FMT=9x16|4x5 CTA=1|0 python3 scripts/montage.py photos-retouchees sortie.mp4 full`)
