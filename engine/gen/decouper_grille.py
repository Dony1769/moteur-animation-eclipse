"""Découpe les planches de personnage en cellules explicites (fond blanc, repères magenta retirés).

Configuration explicite par planche (pas de détection automatique : elle fusionnait des figures).
- corps : N colonnes égales sur toute la hauteur (4 pas de marche).
- tête  : 6 colonnes égales, rangées données par leurs bornes en y (ex. lettres hors cellule exclues).

Sortie : assets/personnages/<id>/poses/marche_N.png et assets/personnages/<id>/tete/*.png
"""
import os
import sys

import cv2
import numpy as np

RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SOURCES = "/mnt/user-data/attachments/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c"
ASSETS = os.path.join(RACINE, "assets", "personnages")
TETE_ORDRE = ["bouche_A", "bouche_E", "bouche_I", "bouche_M", "bouche_O", "bouche_U",
              "expr_neutre", "expr_joie", "expr_tristesse", "expr_colere", "expr_surprise"]

# id : (fichier source, type, paramètres)
PLANCHES = {
    "aiko_soryu": [
        ("8dd68650", "corps", {"n": 4}),
        ("e152c51d", "tete", {"rangees": [(0, 336), (336, 672)]}),
    ],
    "darius_valen": [
        ("c659bb0b", "corps", {"n": 4}),
        ("2fde27f0", "tete", {"rangees": [(0, 340), (390, 768)]}),
    ],
    "alaric": [
        ("5d4bcfd7", "corps", {"n": 4}),
        ("bcc1f17e", "tete", {"rangees": [(0, 256), (256, 512)]}),
    ],
    "vorthaz": [
        ("37bc4e97", "corps", {"n": 4}),
        ("2b38a0d2", "tete", {"rangees": [(0, 296), (296, 592)]}),
    ],
}


def trouver(prefixe):
    for f in os.listdir(SOURCES):
        if f.startswith(prefixe):
            return os.path.join(SOURCES, f)
    raise FileNotFoundError(prefixe)


def nettoyer(img):
    """Retire les repères magenta : seulement les pixels magenta situés sur de vraies lignes-guides.

    Une colonne (ou une rangée) est un guide si la couleur magenta y couvre au moins 15 % de
    la hauteur (ou 10 % de la largeur). Les pixels magenta hors de ces lignes ne sont pas touchés,
    donc la peau et les cheveux restent intacts.
    """
    b, g, r = [img[:, :, i].astype(int) for i in range(3)]
    lache = (r > 200) & (b > 200) & ((r - g) > 60) & ((b - g) > 60)
    h, w = lache.shape
    colonnes = np.where(lache.sum(axis=0) >= max(40, 0.15 * h))[0]
    rangees = np.where(lache.sum(axis=1) >= max(40, 0.10 * w))[0]
    guide = np.zeros_like(lache)
    for x in colonnes:
        guide[:, max(0, x - 2):x + 3] = True
    for y in rangees:
        guide[max(0, y - 2):y + 3, :] = True
    masque = (lache & (guide | True)).astype(np.uint8)  # couleur magenta franche seulement : pas de restriction aux lignes
    masque = cv2.dilate(masque, np.ones((3, 3), np.uint8), iterations=1)
    propre = cv2.inpaint(img, masque * 255, 3, cv2.INPAINT_TELEA)
    # seconde passe sur les bords d'anti-aliasing restants
    b2, g2, r2 = [propre[:, :, i].astype(int) for i in range(3)]
    reste = ((r2 > 200) & (b2 > 200) & ((r2 - g2) > 60) & ((b2 - g2) > 60)).astype(np.uint8)
    reste = cv2.dilate(reste, np.ones((3, 3), np.uint8), iterations=1)
    return cv2.inpaint(propre, reste * 255, 3, cv2.INPAINT_TELEA)


def decouper(prefixe, type_, params, id_perso):
    img = nettoyer(cv2.imread(trouver(prefixe), cv2.IMREAD_COLOR))
    h, w = img.shape[:2]
    sortie = []
    marge = 6
    if type_ == "corps":
        n = params["n"]
        dossier = os.path.join(ASSETS, id_perso, "poses")
        os.makedirs(dossier, exist_ok=True)
        for i in range(n):
            x0, x1 = int(i * w / n), int((i + 1) * w / n)
            cel = img[marge:h - marge, x0 + marge:x1 - marge]
            nom = os.path.join(dossier, "marche_%d.png" % (i + 1))
            cv2.imwrite(nom, cel)
            sortie.append(nom)
    else:
        dossier = os.path.join(ASSETS, id_perso, "tete")
        os.makedirs(dossier, exist_ok=True)
        cibles = list(TETE_ORDRE)
        k = 0
        for (y0, y1) in params["rangees"]:
            for c in range(6):
                if k >= len(cibles):
                    break
                x0, x1 = int(c * w / 6), int((c + 1) * w / 6)
                cel = img[y0 + marge:y1 - marge, x0 + marge:x1 - marge]
                nom = os.path.join(dossier, cibles[k] + ".png")
                cv2.imwrite(nom, cel)
                sortie.append(nom)
                k += 1
    return sortie


def main():
    total = 0
    for id_perso, lots in PLANCHES.items():
        for prefixe, type_, params in lots:
            fichiers = decouper(prefixe, type_, params, id_perso)
            total += len(fichiers)
            print("%-14s %-6s %2d fichiers" % (id_perso, type_, len(fichiers)))
    print("total :", total)


if __name__ == "__main__":
    sys.exit(main())
