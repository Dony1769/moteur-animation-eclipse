"""Découpe une planche (plusieurs figures sur fond blanc) en figures alignées sur un canevas 856x900.

Chaque figure : détourage (rembg isnet-anime), mise à l'échelle sur la hauteur de référence
(tête -> pieds = 840 px), pieds posés sur y=876, centre horizontal sur x=428.

Usage : python3 engine/gen/decouper_planche.py <planche.png> <dossier_sortie> <prefixe> <lignes> <colonnes_par_ligne,...>
  ex. tour :  ... tour.png out/sheets tour 2 4,4
      marche : ... marche.png out/sheets marche 3 3,2,3
"""
import os
import sys

import cv2
import numpy as np
from rembg import new_session, remove

W, H = 856, 900
HAUTEUR_REF = 840   # haut des cheveux y=36 -> pieds y=876 (référence face_g)
SOL_Y = 876
CENTRE_X = 428


def composantes(img_bgr):
    masque = (img_bgr < 235).any(axis=2).astype(np.uint8) * 255
    masque = cv2.dilate(masque, np.ones((25, 25), np.uint8))
    n, labels, stats, cent = cv2.connectedComponentsWithStats(masque)
    boites = []
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        if a < 5000:
            continue
        boites.append((x, y, w, h, cent[i][1]))
    return boites


def regrouper(boites, lignes):
    """Répartit les figures en lignes (selon la coordonnée y du centre)."""
    boites = sorted(boites, key=lambda b: b[4])
    groupes, courant = [], [boites[0]]
    for b in boites[1:]:
        if b[4] - courant[-1][4] > 200:
            groupes.append(courant)
            courant = [b]
        else:
            courant.append(b)
    groupes.append(courant)
    return groupes


def figure(img_bgr, box, session):
    x, y, w, h, _ = box
    m = 20
    x0, y0 = max(x - m, 0), max(y - m, 0)
    x1, y1 = min(x + w + m, img_bgr.shape[1]), min(y + h + m, img_bgr.shape[0])
    crop = img_bgr[y0:y1, x0:x1]
    rgba = remove(cv2.cvtColor(crop, cv2.COLOR_BGR2RGBA), session=session)
    a = rgba[..., 3]
    ys, xs = np.where(a > 20)
    if len(xs) == 0:
        return None
    rgba = rgba[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return rgba


def placer(rgba, echelle):
    hh, ww = rgba.shape[:2]
    nh, nw = max(1, int(round(hh * echelle))), max(1, int(round(ww * echelle)))
    r = cv2.resize(rgba, (nw, nh), interpolation=cv2.INTER_AREA)
    canevas = np.zeros((H, W, 4), np.uint8)
    x0 = int(round(CENTRE_X - nw / 2))
    y0 = SOL_Y - nh
    xa, ya = max(x0, 0), max(y0, 0)
    xb, yb = min(x0 + nw, W), min(y0 + nh, H)
    canevas[ya:yb, xa:xb] = r[ya - y0:yb - y0, xa - x0:xb - x0]
    return canevas


def sur_blanc(rgba):
    a = rgba[..., 3:4] / 255.0
    return (rgba[..., :3] * a + 255 * (1 - a)).astype(np.uint8)


if __name__ == "__main__":
    # Usage : decouper_planche.py <planche> <dossier_sortie> <prefixe> "x0,y0,x1,y1;x0,y0,x1,y1;..."
    planche, sortie, prefixe, cellules = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    os.makedirs(sortie, exist_ok=True)
    img = cv2.imread(planche)
    session = new_session("isnet-anime")
    rapport = []
    for k, c in enumerate(cellules.split(";")):
        x0, y0, x1, y1 = [int(v) for v in c.split(",")]
        crop = img[y0:y1, x0:x1]
        rgba = np.array(remove(cv2.cvtColor(crop, cv2.COLOR_BGR2RGBA), session=session))
        # Ne garder que la plus grande zone détourée (supprime les résidus des cellules voisines)
        binaire = (rgba[..., 3] > 20).astype(np.uint8)
        n, lab, stats, _ = cv2.connectedComponentsWithStats(binaire)
        if n <= 1:
            print("cellule", k, "vide"); continue
        grande = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        rgba[..., 3] = np.where(lab == grande, rgba[..., 3], 0)
        ys, xs = np.where(rgba[..., 3] > 20)
        rgba = rgba[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        echelle = HAUTEUR_REF / rgba.shape[0]
        canevas = placer(rgba, echelle)
        nom = f"{prefixe}_{k:02d}"
        cv2.imwrite(os.path.join(sortie, nom + ".png"), cv2.cvtColor(canevas, cv2.COLOR_RGBA2BGRA))
        cv2.imwrite(os.path.join(sortie, nom + "_blanc.png"), cv2.cvtColor(sur_blanc(canevas), cv2.COLOR_RGB2BGR))
        rapport.append({"nom": nom, "hauteur_brute": int(rgba.shape[0]), "echelle": round(echelle, 3)})
    print(rapport)
