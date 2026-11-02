"""Rendu NPR d'un maillage 3D skinné : LBS sur le CPU, puis le chemin maillage de rendu.py.

Chaîne : pose (squelette 3D) -> skinning linéaire -> transformation modèle-vue (yaw autour de y, puis
recul de la caméra) -> VBO -> G-buffer (géométrie) -> ombrage NPR (rampes, rim, spéculaire) -> contour.
Le même ombrage et le même contour que les calques 2.5D : seule la géométrie change.

Texture : une texture RGBA et des UV fournis par le maillage. Les UV planaires sont justes de face ;
sur les côtés la texture s'étire (limite connue, voir maillage3d).
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from npr import maillage3d as M  # noqa: E402
from npr import tete_test as T  # noqa: E402
from npr.parametres import ParamsOmbrage  # noqa: E402
from npr.rendu import Maillage, RenduNPR  # noqa: E402

DISTANCE_CAMERA = 1.6          # recul de la caméra, unités modèle (cadrage d'un buste de ~0,5 de haut)
CENTRE_TETE = np.array([0.0, 0.31, 0.0])   # centre de la tête au repos, espace modèle
AVANT_MODELE = np.array([0.0, 0.0, 1.0])   # direction de face du personnage, espace modèle


class Avatar3D:
    """Un maillage skinné, rendu en NPR. Un seul RenduNPR (et un seul VBO) par instance."""

    def __init__(self, ctx, modele, squelette, largeur, hauteur, *, texture_rgba=None,
                 ombrage=None, encre=None, distance=DISTANCE_CAMERA):
        if modele.poids is None:
            raise ValueError("le modèle n'a pas de poids d'os : appeler maillage3d.poids_proximite")
        self.modele = modele
        self.squelette = squelette
        self.largeur, self.hauteur = largeur, hauteur
        self.distance = float(distance)
        self.rendu = RenduNPR(ctx, largeur, hauteur,
                              ombrage=ombrage or ParamsOmbrage(poids_sphere=0.0))
        if encre is not None:
            self.rendu.definir_encre(encre)
        self.albedo = self.rendu.texture_rgba(texture_rgba) if texture_rgba is not None else None
        # Le maillage GPU est créé à la première pose ; sa topologie et ses UV ne changent plus.
        self._maillage = None
        # Cadrage : la caméra vise le centre de la boîte englobante de la pose de repos.
        mn, mx = modele.sommets.min(axis=0), modele.sommets.max(axis=0)
        self.centre_cadrage = 0.5 * (mn + mx)

    def matrice_vue(self, yaw):
        """Modèle -> vue : rotation de `yaw` autour de l'axe vertical, puis recul de la caméra."""
        ry = M.rotation_axe((0.0, 1.0, 0.0), float(yaw))
        decale = M.transformation(translation=-self.centre_cadrage)
        recul = M.transformation(translation=(0.0, 0.0, -self.distance))
        m = recul @ M.transformation(rotation3=ry) @ decale
        return m, ry

    def rendre(self, pose=None, yaw=0.0, *, lumiere_vue=T.LUMIERE_VUE):
        """Image RGB uint8 (H, W, 3) du maillage à la pose et à l'angle donnés."""
        s, n, t = M.skinner(self.modele, self.squelette, pose)
        m4, ry = self.matrice_vue(yaw)
        sv, nv, tv = M.vers_vue(s, n, t, m4)
        centre_vue = (m4 @ np.append(CENTRE_TETE, 1.0))[:3]
        avant_vue = ry @ AVANT_MODELE
        avant_vue = avant_vue / np.linalg.norm(avant_vue)
        if self._maillage is None:
            self._maillage = Maillage(self.rendu.ctx, self.rendu.prog_geo, sv, nv,
                                      self.modele.uv, tv, self.modele.triangles)
        else:
            self._maillage.mettre_a_jour(sommets=sv, normales=nv, tangentes=tv)
        self.rendu.dessiner(self._maillage, modele_vue=np.eye(4, dtype=np.float32),
                            projection=T.projection(self.largeur, self.hauteur),
                            centre_tete_vue=centre_vue.astype(np.float32),
                            lumiere_vue=lumiere_vue, avant_tete_vue=avant_vue.astype(np.float32),
                            tan_fov=T.tan_fov(self.largeur, self.hauteur), albedo=self.albedo)
        img = self.rendu.image_finale()[..., :3]
        if img.dtype != np.uint8:
            img = (np.clip(img, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
        return img.copy()

    def liberer(self):
        self.rendu.liberer()
