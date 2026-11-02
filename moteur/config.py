"""Configuration pure Python (sans Blender) : valide les paramètres de rendu.

Testable hors Blender. Les valeurs par défaut suivent le cahier des charges :
24 images par seconde, MP4 encodé avec FFmpeg.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Rendu:
    largeur: int = 960
    hauteur: int = 540
    fps: int = 24
    duree_s: float = 4.0
    moteur_rendu: str = "BLENDER_WORKBENCH"   # brouillon ; le jalon 5 choisira le moteur définitif

    def __post_init__(self):
        if self.largeur <= 0 or self.hauteur <= 0:
            raise ValueError("résolution invalide")
        if self.largeur % 2 or self.hauteur % 2:
            raise ValueError("largeur et hauteur doivent être paires (encodage yuv420p)")
        if self.fps not in (12, 24, 25, 30):
            raise ValueError(f"fps non supporté : {self.fps}")
        if self.duree_s <= 0:
            raise ValueError("durée nulle ou négative")

    @property
    def nb_images(self) -> int:
        return round(self.duree_s * self.fps)
