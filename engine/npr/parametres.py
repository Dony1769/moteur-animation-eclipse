"""Paramètres du rendu NPR, partagés entre les shaders GLSL et la référence numpy.

Les noms de champs suivent les uniforms GLSL correspondants (voir rendu.py).
"""
from dataclasses import dataclass


@dataclass
class ParamsOmbrage:
    """Passe d'ombrage : rampe, rim light, spéculaire, normales sphériques, masque visage."""
    rim_seuil: float = 0.5            # rimThreshold
    rim_douceur: float = 0.05         # rimSmoothness (borné à 1e-4 côté shader)
    rim_couleur: tuple = (0.9, 0.95, 1.0)
    spec_seuil: float = 0.95          # specularThreshold : step() sur N·H
    spec_couleur: tuple = (0.9, 0.9, 0.9)
    poids_sphere: float = 1.0         # sphereWeight, multiplie le masque de normales sphériques
    masque_visage: bool = False       # faceMaskEnabled : active le décalage de lumière + masque d'ombre
    biais_visage: float = 0.3         # faceBias : poids de headForward dans la lumière décalée


@dataclass
class ParamsContour:
    """Passe de contour : Sobel sur normales (vecteurs) et profondeur (log)."""
    seuil_normale: float = 0.4        # normalThreshold : |Gx|+|Gy| sur normales décodées
    seuil_profondeur: float = 0.25    # depthThreshold : |Gx|+|Gy| sur log(profondeur)
    epaisseur: int = 1                # pas d'échantillonnage en texels (entier)
    couleur_trait: tuple = (0.0, 0.0, 0.0)
    couleur_fond: tuple = (0.93, 0.93, 0.93)
    profondeur_fond: float = 100.0    # plan lointain : profondeur substituée au fond
