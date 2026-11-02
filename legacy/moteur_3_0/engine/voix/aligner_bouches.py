"""Aligne les bustes de bouche sur une référence, pour que la tête ne saute pas.

Méthode : DWPose (engine/rig2d/pose.py) donne les points du visage (68 points, indices 23 à 90
du modèle 133). Les centres des yeux (points 36-41 et 42-47 du 68 points, soit 59-64 et 65-70)
donnent le milieu des yeux et l'écart inter-oculaire. Chaque buste est ramené par une
similitude (translation + échelle) sur ces repères de la référence.
Le fond blanc connecté au bord devient le gris de la scène, pour éviter les rectangles.

Sortie : out/voix/bouches_alignees/bouche_<V>.png (408 px de haut) et un contrôle des yeux.
"""
import os
import sys

import cv2
import numpy as np
import onnxruntime as ort

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "rig2d"))
import pose  # noqa: E402

RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DESSINS = os.path.join(RACINE, "universes", "eclipse_royale", "characters", "kael", "dessins")
SORTIE = os.path.join(RACINE, "out", "voix", "bouches_alignees")
FORMES = "AEIMOU"
REF = "A"
FOND = (236, 236, 236)
OEIL_D = slice(59, 65)   # 68 points 36-41
OEIL_G = slice(65, 71)   # 68 points 42-47


def milieu_yeux(pts):
    c1, c2 = pts[OEIL_D].mean(axis=0), pts[OEIL_G].mean(axis=0)
    return (c1 + c2) / 2.0, float(np.linalg.norm(c2 - c1))


def fond_vers_gris(img):
    """Remplace le blanc relié au bord de l'image par le gris de la scène."""
    h, w = img.shape[:2]
    blanc = (img > 235).all(axis=2).astype(np.uint8)
    masque = np.zeros((h + 2, w + 2), np.uint8)
    fond = blanc.copy()
    for x in range(w):
        for y in (0, h - 1):
            if fond[y, x]:
                cv2.floodFill(fond, masque, (x, y), 2)
    for y in range(h):
        for x in (0, w - 1):
            if fond[y, x]:
                cv2.floodFill(fond, masque, (x, y), 2)
    zone = (fond == 2)
    out = img.copy()
    out[zone] = FOND
    return out


def aligner(dossier_entree=DESSINS, dossier_sortie=SORTIE):
    """Renvoie {forme: image BGR alignée} et écrit bouche_<V>.png dans dossier_sortie.

    dossier_entree doit contenir bouche_A.png ... bouche_U.png ; la référence est bouche_A.
    """
    os.makedirs(dossier_sortie, exist_ok=True)
    session = ort.InferenceSession(pose.MODELE, providers=["CPUExecutionProvider"])
    brutes, repères = {}, {}
    for v in FORMES:
        img = cv2.imread(os.path.join(dossier_entree, "bouche_%s.png" % v), cv2.IMREAD_COLOR)
        assert img is not None, v
        pts, score = pose.detecter(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), session)
        assert score[OEIL_D].min() > 0.3 and score[OEIL_G].min() > 0.3, "yeux non détectés : %s" % v
        brutes[v] = img
        repères[v] = milieu_yeux(pts)
    centre_ref, ecart_ref = repères[REF]
    sortie = {}
    for v in FORMES:
        centre, ecart = repères[v]
        s = ecart_ref / ecart
        t = centre_ref - s * centre
        M = np.array([[s, 0, t[0]], [0, s, t[1]]], np.float32)
        h, w = brutes[REF].shape[:2]
        aligne = cv2.warpAffine(brutes[v], M, (w, h), flags=cv2.INTER_CUBIC,
                                borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
        aligne = fond_vers_gris(aligne)
        cv2.imwrite(os.path.join(dossier_sortie, "bouche_%s.png" % v), aligne)
        sortie[v] = aligne
    return sortie, {v: (round(float(repères[v][1]), 1), round(float(ecart_ref / repères[v][1]), 3))
                    for v in FORMES}


if __name__ == "__main__":
    _, infos = aligner()
    print("écart inter-oculaire et facteur d'échelle par forme :", infos)
    print("sortie :", SORTIE)
