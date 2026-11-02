"""Exercice (d) : travelling simple sur un décor (grotte).

La caméra se déplace horizontalement avec une accélération douce (smoothstep)
et un zoom léger (1,20 -> 1,50). Le décor vient de out/scene/grotte_x4.png,
recadré sur un monde de 2560 x 1440. Résolution de sortie : 1280 x 720.
"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from commun import SORTIE, Video, W, H  # noqa: E402

RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DECOR = os.path.join(RACINE, "out", "scene", "grotte_x4.png")
MONDE_W, MONDE_H = 2560, 1440
N = 60              # 5 s
X0, X1 = 150, 1000  # déplacement du centre de vue
CY = 760            # centre vertical de la vue dans le monde
Z0, Z1 = 1.20, 1.50


def monde():
    img = cv2.imread(DECOR, cv2.IMREAD_COLOR)
    assert img is not None, DECOR
    echelle = MONDE_H / img.shape[0]
    largeur = int(round(img.shape[1] * echelle))
    img = cv2.resize(img, (largeur, MONDE_H), interpolation=cv2.INTER_AREA)
    depart = (largeur - MONDE_W) // 2
    return img[:, depart:depart + MONDE_W]


def douceur(t):
    return t * t * (3 - 2 * t)


def main():
    m = monde()
    video = Video(os.path.join(SORTIE, "d_travelling.mp4"))
    for f in range(N):
        t = douceur(f / (N - 1))
        z = Z0 + (Z1 - Z0) * t
        cx = X0 + (X1 - X0) * t
        cw, ch = W / z, H / z
        x0 = int(round(np.clip(cx - cw / 2, 0, MONDE_W - cw)))
        y0 = int(round(np.clip(CY - ch / 2, 0, MONDE_H - ch)))
        vue = m[y0:y0 + int(round(ch)), x0:x0 + int(round(cw))]
        image = cv2.resize(vue, (W, H), interpolation=cv2.INTER_CUBIC)
        video.ajouter(image)
    video.fermer()
    print("travelling :", video.chemin, "images :", N)


if __name__ == "__main__":
    main()
