"""Segmentation tirée du dessin : premier plan par couleur (fond blanc exclu), composante connexe, zone de tête.

Aucun polygone : les masques viennent uniquement des pixels du dessin et des points du squelette.
"""
import cv2
import numpy as np

SEUIL_FOND = 245   # canal minimal au-delà duquel un pixel est du fond blanc (0..255)


def premier_plan(rgb):
    """Masque bool (H, W) : vrai là où le pixel n'est pas blanc. rgb : float 0..1, (H, W, 3)."""
    return (rgb.min(axis=2) * 255.0) < SEUIL_FOND


def garder_composante(masque, point):
    """Garde la composante connexe qui contient `point` (x, y). Si le point est hors masque, garde la plus grande.

    Sert à écarter les fragments étrangers au personnage (ex. bord de la vue 3/4 : une partie de cape d'une autre vue).
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


def zone_tete(points, forme):
    """Poids doux (H, W) float 0..1 de la tête : 1 dans la tête, 0 hors, transition sur ~20 px.

    Bornes tirées du squelette : sommet de la tête ('tete_haut') et articulation du cou ('cou').
    Le centre horizontal est la moyenne des abscisses de ces deux points.
    """
    H, W = forme
    xh, yh = points["tete_haut"]
    xc, yc = points["cou"]
    cx = 0.5 * (xh + xc)
    demi = 95.0
    haut, bas = yh - 12.0, yc + 8.0
    X = np.arange(W, dtype=np.float32)[None, :]
    Y = np.arange(H, dtype=np.float32)[:, None]
    fx = np.clip((demi + 20.0 - np.abs(X - cx)) / 40.0, 0.0, 1.0)
    fy = np.clip((Y - (haut - 10.0)) / 20.0, 0.0, 1.0) * np.clip(((bas + 25.0) - Y) / 25.0, 0.0, 1.0)
    return (fx * fy).astype(np.float32)
