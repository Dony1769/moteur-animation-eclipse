"""Carnet de dessins : enchaîne de vrais dessins (planches), image par image, alignés pixel par pixel.

Principe (animation limitée, comme les séries) :
- chaque dessin est une image réelle, jamais déformée ;
- chaque dessin est recalé sur le sol (bas du pied) et sur l'axe vertical du corps, pour que la tête
  et les pieds restent à la même place d'une image à l'autre ;
- un dessin est tenu plusieurs images (« tenue ») : c'est le rythme des séries (2 ou 3 images par dessin).
- aucun dessin intermédiaire n'est inventé : les transitions sont des coupes entre dessins.

Usage : python3 engine/rig2d/carnet.py <dossier_sortie> <image1> [<image2> ...] [--tenue N] [--points dossier_points133]
"""
import os
import sys

import cv2
import numpy as np

LARGEUR, HAUTEUR = 856, 900
SOL_Y = 880          # ligne du sol dans le cadre
CENTRE_X = 428       # axe vertical du cadre


def longueur_corps(points_json):
    """Distance verticale épaules -> chevilles, mesurée sur les points détectés de la vue."""
    import json
    pts = {p["i"]: (p["x"], p["y"]) for p in json.load(open(points_json, encoding="utf-8"))}
    epaule_y = (pts[5][1] + pts[6][1]) / 2
    cheville_y = (pts[15][1] + pts[16][1]) / 2
    return cheville_y - epaule_y


def recaler(img, longueur=None, longueur_ref=None):
    """Met le dessin à l'échelle du corps de référence (si longueur fournie), puis
    le pose : centre des pieds sur (CENTRE_X, SOL_Y)."""
    echelle = 1.0 if not longueur else longueur_ref / longueur
    fond = (img < 235).any(axis=2)
    ys, xs = np.where(fond)
    bas = ys.max()
    proches = fond[bas - 30:bas + 1]
    ys2, xs2 = np.where(proches)
    cx_pieds = xs2.mean() if len(xs2) else xs.mean()
    # Échelle autour du centre des pieds, puis translation vers (CENTRE_X, SOL_Y)
    m = np.float32([[echelle, 0, cx_pieds * (1 - echelle)], [0, echelle, bas * (1 - echelle)]])
    m[0, 2] += CENTRE_X - cx_pieds
    m[1, 2] += SOL_Y - bas
    return cv2.warpAffine(img, m, (LARGEUR, HAUTEUR), flags=cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))


def construire_carnet(images, tenue=4, points_dir=None):
    """Retourne la liste des images de sortie : chaque dessin est tenu `tenue` images.
    Si points_dir est fourni, chaque vue est mise à l'échelle de la vue de référence (la première)."""
    sortie = []
    ref = None
    for chemin in images:
        longueur = None
        if points_dir:
            nom = os.path.splitext(os.path.basename(chemin))[0]
            longueur = longueur_corps(os.path.join(points_dir, "points133_%s.json" % nom))
            if ref is None:
                ref = longueur
        dessin = recaler(cv2.imread(chemin), longueur, ref)
        sortie.extend([dessin] * tenue)
    return sortie


if __name__ == "__main__":
    dossier = sys.argv[1]
    args = sys.argv[2:]
    tenue = 4
    points = None
    if "--tenue" in args:
        i = args.index("--tenue")
        tenue = int(args[i + 1])
        del args[i:i + 2]
    if "--points" in args:
        i = args.index("--points")
        points = args[i + 1]
        del args[i:i + 2]
    os.makedirs(dossier, exist_ok=True)
    images = construire_carnet(args, tenue, points)
    for i, im in enumerate(images):
        cv2.imwrite(os.path.join(dossier, "f%03d.png" % i), im)
    print(len(images), "images ->", dossier)
