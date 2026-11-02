"""Passage 2D -> 2.5D : relief estimé depuis l'alpha (et, en option, la luminance), normales
dérivées de ce relief, puis composition des calques par profondeur en un G-buffer.

Ce relief est une estimation artistique, pas une profondeur mesurée. Il donne un volume
en biseau à chaque aplat (le bord s'arrondit vers la caméra). L'intérieur d'un aplat
reste plat : pour du volume interne, il faut une profondeur estimée (hors de ce module).

Conventions :
- les calques sont en ordre image : ligne 0 en haut, x vers la droite, y vers le bas ;
- les normales sont en coordonnées vue : x vers la droite, y vers le haut, z vers la caméra ;
- composer() renvoie un G-buffer en ordre OpenGL (ligne 0 en bas), prêt pour
  rendu.RenduNPR.dessiner_gbuffer().
"""
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

SEUIL_ALPHA = 0.1          # équivalent du discard GLSL (alpha < 0.1)


@dataclass
class Calque:
    rgba: np.ndarray                       # (H, W, 4) float 0..1, ordre image
    plan: float = 5.0                      # distance caméra du plan de base
    relief_max: float = 0.25               # amplitude du relief, en unités de profondeur
    rayon_biseau: float = 20.0             # largeur du biseau depuis le bord de l'alpha, en px
    pente: float = 1.0                     # facteur de pente des normales (réglage artistique)
    poids_luminance: float = 0.0           # 0 = relief pur depuis l'alpha ; 1 = pur depuis la luminance
    flou: float = 3.0                      # écart-type (px) du flou appliqué à la hauteur avant les pentes
    flux: Optional[np.ndarray] = None      # (H, W, 2) direction dans le plan (dx, dy_image), ordre image
    masque_cheveux: Optional[np.ndarray] = None   # (H, W) 0..1, ordre image


def relief(calque):
    """Hauteur 0..1, ordre image. Biseau circulaire depuis le bord de l'alpha, mélangé à la luminance."""
    alpha = calque.rgba[..., 3]
    binaire = (alpha >= SEUIL_ALPHA).astype(np.uint8)
    dist = cv2.distanceTransform(binaire, cv2.DIST_L2, 5)   # distance au bord, dans l'aplat
    t = np.clip(dist / max(calque.rayon_biseau, 1e-6), 0.0, 1.0)
    h_alpha = np.sqrt(1.0 - (1.0 - t) ** 2) * binaire          # quart de cercle : 0 au bord, 1 à l'intérieur
    w = float(np.clip(calque.poids_luminance, 0.0, 1.0))
    if w > 0.0:
        rgb = calque.rgba[..., :3]
        lum = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
        h = (1.0 - w) * h_alpha + w * lum * binaire
    else:
        h = h_alpha
    if calque.flou > 0.0:
        # Le bord d'un alpha binaire est en escalier : sans flou, les pentes créent des dents.
        h = cv2.GaussianBlur(h.astype(np.float32), (0, 0), calque.flou)
    return h.astype(np.float32)


def normales(h, pente=1.0):
    """Normales vue (H, W, 3) à partir de la hauteur (ordre image). z vers la caméra, y vers le haut.

    Surface z = h(x, y_vue) : n = normalize(-pente·∂h/∂x, -pente·∂h/∂y_vue, 1).
    Comme y_vue = -y_image, on a -∂h/∂y_vue = +∂h/∂y_image.
    """
    hf = h.astype(np.float64)
    dx = cv2.Sobel(hf, cv2.CV_64F, 1, 0, ksize=3) / 8.0
    dy_image = cv2.Sobel(hf, cv2.CV_64F, 0, 1, ksize=3) / 8.0
    n = np.stack([-pente * dx, pente * dy_image, np.ones_like(hf)], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n.astype(np.float32)


def tangente_depuis_flux(flux):
    """Tangente vue unitaire (H, W, 3) depuis un flux (dx, dy_image) ; zéro où le flux est nul."""
    fl = flux.astype(np.float32)
    H, W = fl.shape[:2]
    t = np.stack([fl[..., 0], -fl[..., 1], np.zeros((H, W), np.float32)], axis=-1)
    nt = np.linalg.norm(t, axis=-1, keepdims=True)
    return np.where(nt > 1e-6, t / np.maximum(nt, 1e-12), 0.0).astype(np.float32)


def composer(calques, largeur, hauteur):
    """Composition par profondeur (z-buffer CPU). Renvoie le G-buffer en ordre OpenGL.

    Pour chaque pixel, le calque opaque le plus proche l'emporte. Les pixels sans calque
    opaque ont une profondeur nulle (fond). Clés du dictionnaire : albedo, normale,
    profondeur, uv, tangente, masque_cheveux.
    """
    H, W = hauteur, largeur
    albedo = np.zeros((H, W, 3), np.float32)
    normale = np.zeros((H, W, 3), np.float32)
    prof = np.zeros((H, W), np.float32)
    tang = np.zeros((H, W, 3), np.float32)
    cheveux = np.zeros((H, W), np.float32)
    meilleure = np.full((H, W), np.inf, np.float32)

    for c in calques:
        if c.rgba.shape[:2] != (H, W):
            raise ValueError("tous les calques doivent avoir la taille de l'écran")
        h = relief(c)
        # Pentes en pixels : le biseau (rayon en px) donne ainsi une pente de l'ordre de 45°.
        n = normales(h * c.rayon_biseau, c.pente)
        d = (c.plan - c.relief_max * h).astype(np.float32)
        opaque = c.rgba[..., 3] >= SEUIL_ALPHA
        ecrit = opaque & (d < meilleure)
        meilleure[ecrit] = d[ecrit]
        albedo[ecrit] = c.rgba[..., :3][ecrit]
        normale[ecrit] = n[ecrit]
        prof[ecrit] = d[ecrit]
        if c.flux is not None:
            tang[ecrit] = tangente_depuis_flux(c.flux)[ecrit]
        else:
            tang[ecrit] = 0.0
        if c.masque_cheveux is not None:
            cheveux[ecrit] = c.masque_cheveux[ecrit]
        else:
            cheveux[ecrit] = 0.0

    def bas(a):
        return np.ascontiguousarray(a[::-1])

    ys, xs = np.mgrid[0:H, 0:W]
    uv = np.stack([(xs + 0.5) / W, (ys + 0.5) / H], axis=-1).astype(np.float32)
    return {
        "albedo": bas(albedo),
        "normale": bas(normale),
        "profondeur": bas(prof),
        "uv": uv,
        "tangente": bas(tang),
        "masque_cheveux": bas(cheveux),
    }
