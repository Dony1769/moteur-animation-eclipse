"""Exercice (b) : cycle de marche 2D (profil) avec les 4 poses hanche-centrées.

Chaque pose est posée par le bas de son pied le plus bas (pas par sa boîte) et
centrée sur le bassin : le personnage ne saute pas d'une pose à l'autre.
Le sol défile à la vitesse de la marche (effet tapis) pour lire le mouvement.
Cycle = contact gauche, passage, contact droit, passage ; chaque pose tenue 3 images.
"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from commun import SORTIE, Video, W, H  # noqa: E402

RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DOSSIER = os.path.join(RACINE, "out", "cycle", "hanche")
POSES = ["cycle_1_contact_gauche.png", "cycle_2_passage.png",
         "cycle_3_contact_droit.png", "cycle_4_passage.png"]
ECHELLE = 0.7       # taille du personnage à l'écran
SOL = 650           # ligne des pieds
CX = 640            # axe du bassin à l'écran
TENUE = 3           # images par pose
CYCLES = 6          # 6 cycles x 4 poses x 3 images = 72 images (6 s)
VITESSE_SOL = 26    # défilement du sol (px / image)
FOND_HAUT = (246, 240, 232)
FOND_BAS = (200, 214, 226)


def hauteur_figure(im):
    lignes = np.where(im[:, :, 3].max(axis=1) > 0)[0]
    assert len(lignes), "sprite vide"
    return lignes.max() - lignes.min() + 1


def charger():
    """Charge les 4 poses et les ramène à la même taille de personnage.

    Les sprites source n'ont pas la même échelle : le passage 2 fait 537 px
    de haut contre 718 à 725 px pour les autres poses. On normalise chaque
    pose sur la hauteur médiane du cycle, pour que le personnage ne pulse pas.
    """
    bruts = []
    for nom in POSES:
        im = cv2.imread(os.path.join(DOSSIER, nom), cv2.IMREAD_UNCHANGED)
        assert im is not None, nom
        bruts.append(im)
    ref = float(np.median([hauteur_figure(im) for im in bruts]))
    sprites = []
    for im in bruts:
        facteur = ECHELLE * ref / hauteur_figure(im)   # hauteur finale = ECHELLE * ref pour toutes les poses
        sprites.append(cv2.resize(im, None, fx=facteur, fy=facteur, interpolation=cv2.INTER_AREA))
    return sprites


def fond(img, decalage):
    # dégradé de ciel, sol gris avec bandes qui défilent
    haut = np.linspace(0, 1, SOL)[:, None]
    ciel = (np.array(FOND_HAUT) * (1 - haut) + np.array(FOND_BAS) * haut).astype(np.uint8)
    img[:SOL] = ciel[:, None, :]
    img[SOL:] = (150, 150, 150)
    for x in range(-200, W + 200, 140):
        xx = x + (decalage % 140)
        cv2.line(img, (xx, SOL), (xx - 90, H), (125, 125, 125), 3, cv2.LINE_AA)
    cv2.line(img, (0, SOL), (W, SOL), (100, 100, 100), 2)


def coller(img, sprite, x_bassin, y_pied):
    h, w = sprite.shape[:2]
    x0, y0 = int(x_bassin - w // 2), int(y_pied - h)
    xa, ya = max(0, x0), max(0, y0)
    xb, yb = min(W, x0 + w), min(H, y0 + h)
    if xa >= xb or ya >= yb:
        return
    s = sprite[ya - y0:yb - y0, xa - x0:xb - x0]
    a = s[:, :, 3:4].astype(np.float32) / 255.0
    roi = img[ya:yb, xa:xb].astype(np.float32)
    img[ya:yb, xa:xb] = (s[:, :, :3] * a + roi * (1 - a)).astype(np.uint8)


def marge_sous_pieds(sprite):
    """Nombre de lignes transparentes sous le pied le plus bas du sprite."""
    lignes = np.where(sprite[:, :, 3].max(axis=1) > 0)[0]
    return sprite.shape[0] - (lignes.max() + 1)


def main():
    sprites = charger()
    marges = [marge_sous_pieds(s) for s in sprites]
    video = Video(os.path.join(SORTIE, "b_marche.mp4"))
    f = 0
    for _ in range(CYCLES):
        for p in range(4):
            for _ in range(TENUE):
                img = np.zeros((H, W, 3), np.uint8)
                fond(img, f * VITESSE_SOL)
                # le bas du canevas est à SOL + marge : le pied le plus bas touche SOL
                coller(img, sprites[p], CX, SOL + marges[p])
                video.ajouter(img)
                f += 1
    video.fermer()
    print("marche :", video.chemin, "images :", f)


if __name__ == "__main__":
    main()
