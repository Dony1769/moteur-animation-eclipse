"""Rampes de toon (1 x n texels) pour l'ombrage en bandes nettes.

Convention : la coordonnée u = N·L demi-lambert (dans [0, 1]) sélectionne le texel
floor(u * n) avec GL_NEAREST. Le texel le plus clair (u = 1) est la couleur « éclairée »
de l'albédo ; les bandes sont donc alignées sur des multiples de 1/n.
"""
import numpy as np

# Trois bandes : ombre profonde, demi-teinte, lumière. Valeurs sRGB 0..1.
COULEURS_TOON = ((0.31, 0.27, 0.43), (0.59, 0.49, 0.63), (0.98, 0.92, 0.86))
SEUILS_TOON = (0.35, 0.70)


def rampe(seuils, couleurs, n=256):
    """Rampe en bandes nettes, renvoyée en uint8 de forme (n, 3).

    seuils : positions u croissantes, multiples de 1/n de préférence.
    couleurs : len(seuils) + 1 couleurs RGB 0..1.
    """
    if len(couleurs) != len(seuils) + 1:
        raise ValueError("il faut len(seuils) + 1 couleurs")
    bords = np.arange(n, dtype=np.float64) / n          # u du bord gauche de chaque texel
    bande = np.searchsorted(np.asarray(seuils, dtype=np.float64), bords, side="right")
    c = np.asarray(couleurs, dtype=np.float64)[bande]
    return np.round(c * 255.0).astype(np.uint8)


def rampe_par_defaut(n=256):
    return rampe(SEUILS_TOON, COULEURS_TOON, n)


def vers_flottant(rampe_u8):
    """Conversion identique à celle de OpenGL pour une texture uint8 normalisée."""
    return rampe_u8.astype(np.float32) / 255.0
