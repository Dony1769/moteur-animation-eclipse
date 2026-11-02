"""Grille de déformation : des nœuds réguliers portent un déplacement, interpolé sur tout le dessin.

La grille ne dessine rien : cv2.remap déplace les pixels du dessin. Le champ est calculé aux nœuds
puis interpolé bilinéairement, donc il est continu (c'est la grille de contrôle, pas une forme).
"""
import cv2
import numpy as np


class Grille:
    def __init__(self, hauteur, largeur, pas=24):
        self.h, self.w, self.pas = int(hauteur), int(largeur), int(pas)
        self.nx = int(np.ceil((self.w - 1) / self.pas)) + 1
        self.ny = int(np.ceil((self.h - 1) / self.pas)) + 1
        # positions pixel des nœuds
        self.xn = np.linspace(0, self.w - 1, self.nx, dtype=np.float32)
        self.yn = np.linspace(0, self.h - 1, self.ny, dtype=np.float32)
        XN, YN = np.meshgrid(self.xn, self.yn)
        self.XN, self.YN = XN, YN

    def champ_dense(self, valeurs_nodes):
        """Champ aux nœuds (ny, nx) -> carte pleine (H, W) par interpolation bilinéaire."""
        return cv2.resize(np.asarray(valeurs_nodes, np.float32), (self.w, self.h),
                          interpolation=cv2.INTER_LINEAR)

    def deformer(self, image, src_x, src_y):
        """Échantillonne `image` (H, W, C float32) aux positions source (src_x, src_y) : déplacement des pixels."""
        return cv2.remap(image, src_x, src_y, interpolation=cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=0)

    def positions_identite(self):
        """Cartes (H, W) des coordonnées pixel : point de départ de tout déplacement."""
        X, Y = np.meshgrid(np.arange(self.w, dtype=np.float32), np.arange(self.h, dtype=np.float32))
        return X, Y
