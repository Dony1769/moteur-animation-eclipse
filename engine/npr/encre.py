"""Encre fine : contours minces, épaissis du côté ombré, à partir du G-buffer relu.

Remplace le Sobel 3x3 épais de la passe contour par trois étapes :
1. détection : Sobel sur les normales et sur log(profondeur), comme la passe GPU ;
2. amincissement : on ne garde que le maximum local d'intensité le long du gradient
   (suppression des non-maxima), ce qui donne un trait d'un pixel à la crête de l'arête ;
3. épaisseur variable selon l'éclairage : trait de 1 px sur la face éclairée, de 3 px
   (dilatation 3x3) sur la face ombrée, et de 2 px entre les deux (le trait de 1 px
   élargi d'un seul côté par décalage). Les plages sont réglées par ParamsEncre.

Fonctionne sur des tableaux numpy (ligne 0 en haut). Pas de GPU : testable sans contexte.
"""
from dataclasses import dataclass
import math

import cv2
import numpy as np


@dataclass
class ParamsEncre:
    seuil_normale: float = 1.5         # arêtes internes ; plus haut que ParamsContour (0,4) pour éviter les hachures
    seuil_profondeur: float = 0.6      # arêtes internes ; plus haut que ParamsContour (0,25)
    couleur_trait: tuple = (0.06, 0.05, 0.08)
    couleur_fond: tuple = (0.93, 0.93, 0.93)
    lum_claire: float = 0.6            # au-dessus : trait de 1 px
    lum_ombre: float = 0.3             # en dessous : trait de 3 px ; entre les deux : 2 px
    profondeur_fond: float = 100.0     # substitut log pour le fond (profondeur nulle)
    seuil_faible: float = 0.5          # hystérésis : un trait faible n'est gardé que s'il touche un trait fort (1.0)
    longueur_min: int = 20             # composantes d'arêtes internes plus petites (pixels) : supprimées


def _sobel_vecteur(a):
    """Norme |Gx| + |Gy| d'un champ (H, W, C) ; bord répliqué comme CLAMP_TO_EDGE."""
    total = np.zeros(a.shape[:2], np.float64)
    gx_tot = np.zeros(a.shape, np.float64)
    gy_tot = np.zeros(a.shape, np.float64)
    for c in range(a.shape[2]):
        gx_tot[..., c] = cv2.Sobel(a[..., c].astype(np.float64), cv2.CV_64F, 1, 0, ksize=3,
                                   borderType=cv2.BORDER_REPLICATE)
        gy_tot[..., c] = cv2.Sobel(a[..., c].astype(np.float64), cv2.CV_64F, 0, 1, ksize=3,
                                   borderType=cv2.BORDER_REPLICATE)
    total = np.linalg.norm(gx_tot, axis=2) + np.linalg.norm(gy_tot, axis=2)
    return total


def _sobel_scalaire(a):
    gx = cv2.Sobel(a, cv2.CV_64F, 1, 0, ksize=3, borderType=cv2.BORDER_REPLICATE)
    gy = cv2.Sobel(a, cv2.CV_64F, 0, 1, ksize=3, borderType=cv2.BORDER_REPLICATE)
    return gx, gy


def aretes(normale, profondeur, p):
    """Intensité d'arête m (H, W) : 1 = au seuil. Fond (profondeur <= 0) = 0.

    normale : (H, W, 3) vecteurs (zéro au fond) ; profondeur : (H, W) distance positive.
    """
    N = np.asarray(normale, np.float64)
    d = np.asarray(profondeur, np.float64)
    valide = d > 0.0
    log_d = np.where(valide, np.log(np.maximum(d, 1e-12)), math.log(p.profondeur_fond))
    edN = _sobel_vecteur(N)
    gx, gy = _sobel_scalaire(log_d)
    edD = np.abs(gx) + np.abs(gy)
    m = np.maximum(edN / p.seuil_normale, edD / p.seuil_profondeur)
    m[~valide] = 0.0
    return m


def minces(m, valide, seuil=1.0):
    """Suppression des non-maxima le long du gradient de m : bool (H, W), trait d'un pixel."""
    gx, gy = _sobel_scalaire(m)
    H, W = m.shape
    norme = np.hypot(gx, gy)
    sx = np.where(norme > 1e-12, np.rint(gx / np.maximum(norme, 1e-12)), 0.0).astype(int)
    sy = np.where(norme > 1e-12, np.rint(gy / np.maximum(norme, 1e-12)), 0.0).astype(int)
    yy, xx = np.mgrid[0:H, 0:W]

    def voisin(dx, dy):
        return m[np.clip(yy + dy, 0, H - 1), np.clip(xx + dx, 0, W - 1)]

    # Égalités (crête plate, arête symétrique) : on garde le pixel dont le décalage le long du
    # gradient est positif ou nul. Sans cela, deux pixels voisins restent à égalité et le trait
    # fait deux pixels.
    a = voisin(sx, sy)
    b = voisin(-sx, -sy)
    egal = np.isclose(m, a, rtol=1e-9, atol=1e-12)
    cote = (sx + sy) >= 0
    crete = ((m > a) | (egal & cote)) & (m >= b) & (norme > 1e-12)
    return crete & valide & (m > seuil)


def _etiquettes_relies(trait):
    """Étiquettes de composantes du trait, reliées à travers les trous d'un pixel.

    La suppression des non-maxima laisse de petits trous le long d'une arête courbe. Les composantes
    se calculent donc sur le masque dilaté d'un pixel, puis le résultat est restreint au trait.
    Renvoie (n, étiquettes) ; étiquette 0 = hors trait.
    """
    dilate = cv2.dilate(trait.astype(np.uint8), np.ones((3, 3), np.uint8))
    n, etiquettes = cv2.connectedComponents(dilate, connectivity=8)
    return n, np.where(trait, etiquettes, 0)


def hysteresis(faible, forte):
    """Garde les composantes de `faible` qui contiennent au moins un pixel de `forte`."""
    n, etiquettes = _etiquettes_relies(faible)
    presence = np.zeros(n, bool)
    presence[etiquettes[forte & faible]] = True
    presence[0] = False
    return presence[etiquettes] & faible


def retirer_petits(trait, longueur_min):
    """Supprime les composantes de moins de longueur_min pixels (points de bruit)."""
    if longueur_min <= 1:
        return trait
    n, etiquettes = _etiquettes_relies(trait)
    aire = np.bincount(etiquettes.ravel(), minlength=n)
    garder = aire >= longueur_min
    garder[0] = False                    # hors trait
    return garder[etiquettes] & trait


def silhouette(valide):
    """Frontière intérieure de la silhouette : 1 px, continue par construction (pas de seuil)."""
    v8 = valide.astype(np.uint8)
    interieur = cv2.erode(v8, np.ones((3, 3), np.uint8), borderType=cv2.BORDER_CONSTANT,
                          borderValue=0).astype(bool)
    return valide & ~interieur


def appliquer(rgb, normale, profondeur, p=None):
    """Image RGB (H, W, 3) 0..1 avec encre. Renvoie (H, W, 3) float64.

    - Silhouette (bord du masque de profondeur) : continue, 1 px sur la face éclairée, 2 px au
      milieu, 3 px sur la face ombrée (dilatation restreinte au personnage).
    - Arêtes internes (normales, profondeur) : Sobel, suppression des non-maxima, hystérésis,
      composantes courtes retirées. Elles restent fragmentaires sur les surfaces courbes.
    """
    p = p or ParamsEncre()
    rgb = np.asarray(rgb, np.float64)
    valide = np.asarray(profondeur) > 0.0
    m = aretes(normale, profondeur, p)
    faible = minces(m, valide, seuil=p.seuil_faible)
    interne = hysteresis(faible, minces(m, valide, seuil=1.0))
    interne = retirer_petits(interne, p.longueur_min)

    bord = silhouette(valide)
    noyau = np.ones((3, 3), np.uint8)
    bord8 = bord.astype(np.uint8)
    bord_large = cv2.dilate(bord8, noyau).astype(bool) & valide
    decale = np.zeros_like(bord8)
    decale[:, 1:] = bord8[:, :-1]
    bord_moyen = (bord8 | decale).astype(bool) & valide

    lum = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    ombre = lum < p.lum_ombre
    milieu = (lum >= p.lum_ombre) & (lum < p.lum_claire)
    contour = bord | (ombre & bord_large) | (milieu & bord_moyen)
    # Une arête interne collée à la silhouette doublerait le trait : on la retire près du bord.
    pres_bord = cv2.dilate(bord8, noyau).astype(bool)
    ink = (interne & valide & ~pres_bord) | contour

    out = rgb.copy()
    out[~valide] = np.asarray(p.couleur_fond, np.float64)
    out[ink] = np.asarray(p.couleur_trait, np.float64)
    return out
