"""Découpe les planches Gemini en dessins séparés, efface les étiquettes, puis détoure
chaque dessin avec isnet-anime (rembg). Sortie : PNG transparents + vérification sur fond coloré.

Usage : python3 engine/gen/detour.py
"""
import os

import cv2
import numpy as np
from PIL import Image
from rembg import new_session, remove

ENTREE = "out/gemini"
SORTIE = "out/gemini/detoure"
os.makedirs(SORTIE, exist_ok=True)

def effacer(img, zones):
    for x0, y0, x1, y1 in zones:
        img[y0:y1, x0:x1] = 255
    return img

def decoupes():
    # Bouches : 6 panneaux de 424 px, étiquettes en haut-gauche et bas-gauche
    m = cv2.imread(os.path.join(ENTREE, "bouches_planche.jpg"))
    noms = ["A", "E", "I", "O", "U", "M"]
    for i, n in enumerate(noms):
        p = m[:, i * 424:(i + 1) * 424].copy()
        p = effacer(p, [(0, 0, 150, 90), (0, 300, 110, 416)])
        yield "bouche_%s" % n, p[0:416, 40:400]
    # Expressions : 4 quadrants de 512 px, étiquette en haut-gauche
    e = cv2.imread(os.path.join(ENTREE, "expressions_planche.jpg"))
    for nom, (y, x) in [("expr_joie", (0, 0)), ("expr_colere", (0, 512)), ("expr_surprise", (512, 0)), ("expr_tristesse", (512, 512))]:
        p = e[y:y + 512, x:x + 512].copy()
        p = effacer(p, [(0, 0, 160, 80)])
        yield nom, p
    # Marches : 4 panneaux de 424 x 632, étiquette « marche_n.png » en haut
    w = cv2.imread(os.path.join(ENTREE, "marches_planche.jpg"))
    for k, (y, x) in enumerate([(0, 0), (0, 424), (632, 0), (632, 424)], start=1):
        p = w[y:y + 632, x:x + 424].copy()
        p = effacer(p, [(0, 0, 424, 34)])
        yield "marche_%d" % k, p

def main():
    session = new_session("isnet-anime")
    fonds = []
    for nom, img in decoupes():
        cv2.imwrite(os.path.join(SORTIE, nom + "_brut.png"), img)
        rgb = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        png = remove(rgb, session=session)
        png.save(os.path.join(SORTIE, nom + ".png"))
        fonds.append((nom, png))
        print("ok", nom, png.size)
    # Vérification : chaque dessin sur fond rose pour voir les bords du détourage
    vignettes = []
    for nom, png in fonds:
        fond = Image.new("RGBA", png.size, (255, 120, 180, 255))
        fond.alpha_composite(png.convert("RGBA"))
        v = np.array(fond.convert("RGB").resize((200, int(200 * png.size[1] / png.size[0]))))
        vignettes.append(cv2.cvtColor(v, cv2.COLOR_RGB2BGR))
    h = max(v.shape[0] for v in vignettes)
    vignettes = [cv2.copyMakeBorder(v, 0, h - v.shape[0], 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255)) for v in vignettes]
    cv2.imwrite(os.path.join(SORTIE, "verification_fond_rose.png"), np.hstack(vignettes))

if __name__ == "__main__":
    main()
