"""Détection de pose locale (DWPose, 133 points COCO-WholeBody) sur les vues d'un personnage.

Usage : python3 engine/rig2d/pose.py <dossier_vues> <dossier_sortie>
Chaque vue est recadrée autour du personnage (fond blanc supposé), puis les points sont
ramenés aux coordonnées de l'image d'origine. Sortie : keypoints_<vue>.json et superposition PNG.
"""
import json
import os
import sys

import cv2
import numpy as np
import onnxruntime as ort

HERE = os.path.dirname(os.path.abspath(__file__))
MODELE = os.path.join(HERE, "..", "..", "models", "dw-ll_ucoco_384.onnx")
ENTREE_W, ENTREE_H = 288, 384
MOY = np.array([123.675, 116.28, 103.53], np.float32)
ECART = np.array([58.395, 57.12, 57.375], np.float32)

# Squelette lisible : nom -> indice COCO-WholeBody
CORPS = {
    "nez": 0, "oeil_g": 1, "oeil_d": 2, "oreille_g": 3, "oreille_d": 4,
    "epaule_g": 5, "epaule_d": 6, "coude_g": 7, "coude_d": 8, "poignet_g": 9, "poignet_d": 10,
    "hanche_g": 11, "hanche_d": 12, "genou_g": 13, "genou_d": 14, "cheville_g": 15, "cheville_d": 16,
    "pied_g_gros": 17, "pied_g_petit": 18, "talon_g": 19,
    "pied_d_gros": 20, "pied_d_petit": 21, "talon_d": 22,
}
LIENS = [
    ("epaule_g", "epaule_d"), ("hanche_g", "hanche_d"), ("epaule_g", "hanche_g"), ("epaule_d", "hanche_d"),
    ("epaule_g", "coude_g"), ("coude_g", "poignet_g"), ("epaule_d", "coude_d"), ("coude_d", "poignet_d"),
    ("hanche_g", "genou_g"), ("genou_g", "cheville_g"), ("hanche_d", "genou_d"), ("genou_d", "cheville_d"),
    ("cheville_g", "pied_g_gros"), ("cheville_d", "pied_d_gros"), ("nez", "oeil_g"), ("nez", "oeil_d"),
]


def recadrer(img):
    """Recadre autour du personnage (pixels non blancs) au ratio 3:4 de l'entrée du modèle."""
    h, w = img.shape[:2]
    masque = (img < 240).any(axis=2)
    ys, xs = np.where(masque)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hauteur = (y1 - y0) * 1.12
    largeur = hauteur * ENTREE_W / ENTREE_H
    if (x1 - x0) * 1.12 > largeur:
        largeur = (x1 - x0) * 1.12
        hauteur = largeur * ENTREE_H / ENTREE_W
    bx0, by0 = int(round(cx - largeur / 2)), int(round(cy - hauteur / 2))
    bw, bh = int(round(largeur)), int(round(hauteur))
    fond = np.full((bh, bw, 3), 255, np.uint8)
    sx0, sy0 = max(bx0, 0), max(by0, 0)
    sx1, sy1 = min(bx0 + bw, w), min(by0 + bh, h)
    fond[sy0 - by0:sy1 - by0, sx0 - bx0:sx1 - bx0] = img[sy0:sy1, sx0:sx1]
    return fond, (bx0, by0, bw / ENTREE_W)


def detecter(img_rgb, session):
    recadree, (ox, oy, echelle) = recadrer(img_rgb)
    entree = cv2.resize(recadree, (ENTREE_W, ENTREE_H), interpolation=cv2.INTER_LINEAR).astype(np.float32)
    entree = ((entree - MOY) / ECART).transpose(2, 0, 1)[None]
    simcc_x, simcc_y = session.run(None, {session.get_inputs()[0].name: entree})
    kx = simcc_x[0].argmax(axis=1) / 2.0
    ky = simcc_y[0].argmax(axis=1) / 2.0
    score = np.minimum(simcc_x[0].max(axis=1), simcc_y[0].max(axis=1))
    pts = np.stack([ox + kx * echelle, oy + ky * echelle], axis=1)
    return pts, score


def main():
    dossier, sortie = sys.argv[1], sys.argv[2]
    os.makedirs(sortie, exist_ok=True)
    session = ort.InferenceSession(MODELE, providers=["CPUExecutionProvider"])
    for nom in sorted(os.listdir(dossier)):
        if not nom.endswith(".png"):
            continue
        vue = os.path.splitext(nom)[0]
        bgr = cv2.imread(os.path.join(dossier, nom))
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        pts, score = detecter(rgb, session)
        resultat = {k: {"x": round(float(pts[i][0]), 1), "y": round(float(pts[i][1]), 1),
                        "score": round(float(score[i]), 3)} for k, i in CORPS.items()}
        with open(os.path.join(sortie, "keypoints_%s.json" % vue), "w", encoding="utf-8") as f:
            json.dump(resultat, f, ensure_ascii=False, indent=1)
        dessin = bgr.copy()
        for a, b in LIENS:
            if score[CORPS[a]] > 0.3 and score[CORPS[b]] > 0.3:
                cv2.line(dessin, tuple(map(int, pts[CORPS[a]])), tuple(map(int, pts[CORPS[b]])), (0, 0, 255), 2)
        for k, i in CORPS.items():
            couleur = (0, 200, 0) if score[i] > 0.3 else (0, 0, 255)
            cv2.circle(dessin, tuple(map(int, pts[i])), 5, couleur, -1)
        cv2.imwrite(os.path.join(sortie, "superposition_%s.png" % vue), dessin)
        print(vue, "score moyen corps : %.2f" % float(score[:23].mean()))


if __name__ == "__main__":
    main()
