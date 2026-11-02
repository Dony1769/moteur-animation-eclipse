"""Exercice (a) : balle qui rebondit, avec écrasement et étirement.

Principes : gravité, rebond avec perte d'énergie, écrasement à l'impact,
étirement en vol proportionnel à la vitesse, volume conservé (sx * sy ≈ 1),
ombre au sol qui se réduit quand la balle monte. Le bas de la balle reste
calé sur le sol au moment du contact.
"""
import math
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from commun import SORTIE, Video, W, H  # noqa: E402

SOL = 600          # ligne du sol (y)
R = 46             # rayon de la balle au repos (px)
G = 9.0            # gravité (px / image²)
REBOND = 0.80      # fraction de vitesse conservée à chaque rebond
H0 = 420           # hauteur de départ (px)
N = 48             # 4 s à 12 images/s
VMAX = 90.0        # vitesse de référence pour les déformations
FOND = (236, 236, 236)
BALLE = (46, 87, 228)
OMBRE = (190, 190, 190)


def simuler():
    """Renvoie pour chaque image (hauteur, vitesse, écrasement)."""
    y, vy = float(H0), 0.0
    etats = []
    for _ in range(N):
        vy -= G
        y += vy
        ecrasement = 0.0
        if y <= 0:
            y = 0.0
            if vy < 0:
                impact = -vy
                vy = impact * REBOND
                ecrasement = min(0.35, impact / VMAX * 0.35)
        etats.append((y, vy, ecrasement))
    return etats


def echelles(vy, ecrasement):
    if ecrasement > 0:
        sy = 1.0 - ecrasement
    else:
        sy = 1.0 + min(0.2, abs(vy) / VMAX * 0.2)
    return 1.0 / math.sqrt(sy), sy


def dessiner(img, f, y, vy, ecrasement):
    cx = 180 + f * 14
    sx, sy = echelles(vy, ecrasement)
    rx, ry = R * sx, R * sy
    # ombre au sol : plus petite quand la balle est haute
    k = 1.0 - min(y / H0, 1.0) * 0.55
    cv2.ellipse(img, (int(cx), SOL + 3), (int(R * 1.1 * k), int(10 * k)), 0, 0, 360, OMBRE, -1, cv2.LINE_AA)
    # balle : le bas reste sur (SOL - y)
    cy = SOL - y - ry
    cv2.ellipse(img, (int(cx), int(round(cy))), (int(round(rx)), int(round(ry))), 0, 0, 360, BALLE, -1, cv2.LINE_AA)
    # reflet
    cv2.ellipse(img, (int(cx - rx * 0.35), int(round(cy - ry * 0.35))),
                (int(rx * 0.22), int(ry * 0.14)), -30, 0, 360, (250, 250, 250), -1, cv2.LINE_AA)
    return sx, sy


def main():
    chemin = os.path.join(SORTIE, "a_balle.mp4")
    video = Video(chemin)
    etats = simuler()
    rapport = []
    for f, (y, vy, ec) in enumerate(etats):
        img = np.full((H, W, 3), FOND, np.uint8)
        cv2.line(img, (0, SOL), (W, SOL), (120, 120, 120), 2)
        sx, sy = dessiner(img, f, y, vy, ec)
        rapport.append((f, round(y, 1), round(sx, 3), round(sy, 3)))
        video.ajouter(img)
    video.fermer()
    print("balle :", chemin, "images :", video.nb)
    contacts = [r for r in rapport if r[1] == 0.0]
    print("contacts (image, sx, sy) :", [(r[0], r[2], r[3]) for r in contacts])


if __name__ == "__main__":
    main()
