"""Segmentation tirée du dessin : premier plan par couleur (fond blanc exclu) et composante connexe.

Aucun polygone : le masque vient uniquement des pixels du dessin.
"""
import cv2
import numpy as np

SEUIL_FOND = 245   # canal minimal au-delà duquel un pixel est du fond blanc (0..255)


def premier_plan(rgb):
    """Masque bool (H, W) : vrai là où le pixel n'est pas blanc. rgb : float 0..1, (H, W, 3)."""
    return (rgb.min(axis=2) * 255.0) < SEUIL_FOND


def garder_composante(masque, point):
    """Garde la composante connexe qui contient `point` (x, y) ; hors masque, garde la plus grande.

    Écarte les fragments étrangers au personnage (ex. bord d'un dessin qui contient une partie d'une autre vue).
    """
    n, etiquettes = cv2.connectedComponents(masque.astype(np.uint8), connectivity=8)
    if n <= 1:
        raise ValueError("aucun premier plan dans le dessin")
    x, y = int(round(point[0])), int(round(point[1]))
    k = etiquettes[y, x]
    if k == 0:
        tailles = np.bincount(etiquettes.ravel())[1:]
        k = int(np.argmax(tailles)) + 1
    return etiquettes == k
