"""Rendu NPR d'un maillage 3D skinné : LBS sur le CPU, puis le chemin maillage de rendu.py.

Chaîne : pose (squelette 3D) -> skinning linéaire -> transformation modèle-vue (yaw autour de y, puis
recul de la caméra) -> VBO -> G-buffer (géométrie) -> ombrage NPR (rampes, rim, spéculaire) -> contour.
Le même ombrage et le même contour que les calques 2.5D : seule la géométrie change.

Multi-vues (« billboard rig » en 3D) : chaque vue réelle (face, trois-quarts...) apporte sa texture et ses
propres UV, projetés depuis son angle. La vue la plus proche de l'angle de caméra est dessinée (bascule au
point médian), ou fondue avec la suivante sur une fenêtre courte (`fondu_deg`). Un angle sans vue réelle
n'est jamais inventé : la vue la plus proche est répétée et l'écart apparaît dans `ecart_vue`.

Détourage : la texture porte l'alpha du premier plan ; les fragments transparents sont retirés
(`seuil_alpha`), donc le fond blanc de la référence n'apparaît plus en aplat sur les flancs.
Anti-aliasing : mipmaps et filtrage anisotrope sur les albédos.
"""
import dataclasses
import sys
from pathlib import Path

import moderngl
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from npr import maillage3d as M  # noqa: E402
from npr import tete_test as T  # noqa: E402
from npr.parametres import ParamsOmbrage  # noqa: E402
from npr.rendu import Maillage, RenduNPR  # noqa: E402

DISTANCE_CAMERA = 1.6          # recul de la caméra, unités modèle (cadrage d'un buste de ~0,5 de haut)
CENTRE_TETE = np.array([0.0, 0.31, 0.0])   # centre de la tête au repos, espace modèle
AVANT_MODELE = np.array([0.0, 0.0, 1.0])   # direction de face du personnage, espace modèle
SEUIL_ALPHA = 0.5              # alpha de texture en dessous duquel le fragment est retiré
ANISOTROPIE = 8.0              # filtrage anisotrope demandé (plafonné par le pilote)


def _mipmaps(tex):
    """Mipmaps trilinéaires + filtrage anisotrope : réduit le scintillement des textures en rotation."""
    tex.build_mipmaps()
    tex.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
    try:
        tex.anisotropy = ANISOTROPIE
    except (AttributeError, moderngl.Error):
        pass  # pilote sans filtrage anisotrope : les mipmaps restent actifs


class Avatar3D:
    """Un maillage skinné, rendu en NPR, avec une ou plusieurs vues réelles.

    vues : liste de (angle_deg, modele_vue, texture_rgba) ; modele_vue porte les UV de cette vue.
    Sans `vues`, une vue unique à 0° est utilisée (modele, texture_rgba).
    """

    def __init__(self, ctx, modele, squelette, largeur, hauteur, *, texture_rgba=None, vues=None,
                 ombrage=None, encre=None, distance=DISTANCE_CAMERA, seuil_alpha=SEUIL_ALPHA):
        if vues is None:
            vues = [(0.0, modele, texture_rgba)]
        if not vues:
            raise ValueError("aucune vue")
        self.ctx = ctx
        self.squelette = squelette
        self.largeur, self.hauteur = largeur, hauteur
        self.distance = float(distance)
        self.seuil_alpha = float(seuil_alpha)
        self.rendu = RenduNPR(ctx, largeur, hauteur,
                              ombrage=ombrage or ParamsOmbrage(poids_sphere=0.0))
        if encre is not None:
            self.rendu.definir_encre(encre)
        self._vues = []
        for angle, mv, tex in sorted(vues, key=lambda v: float(v[0])):
            if mv.poids is None:
                raise ValueError("le modèle n'a pas de poids d'os : appeler maillage3d.poids_proximite")
            alb = None
            if tex is not None:
                alb = self.rendu.texture_rgba(tex)
                _mipmaps(alb)
            self._vues.append({"angle": float(angle), "modele": mv, "albedo": alb, "maillage": None})
        # Angles de vue stockés en radians (même unité que le yaw passé à rendre).
        self.angles = [float(np.radians(v["angle"])) for v in self._vues]
        # Cadrage : la caméra vise le centre de la boîte englobante de la pose de repos (commune aux vues).
        base = self._vues[0]["modele"].sommets
        mn, mx = base.min(axis=0), base.max(axis=0)
        self.centre_cadrage = 0.5 * (mn + mx)

    def vue_pour(self, yaw):
        """(index, ecart) : vue réelle la plus proche de `yaw` (radians) et écart signé (radians)."""
        ecarts = np.abs(np.asarray(self.angles) - float(yaw))
        i = int(np.argmin(ecarts))
        return i, float(yaw) - self.angles[i]

    def matrice_vue(self, yaw):
        """Modèle -> vue : rotation de `yaw` autour de l'axe vertical, puis recul de la caméra."""
        ry = M.rotation_axe((0.0, 1.0, 0.0), float(yaw))
        decale = M.transformation(translation=-self.centre_cadrage)
        recul = M.transformation(translation=(0.0, 0.0, -self.distance))
        m = recul @ M.transformation(rotation3=ry) @ decale
        return m, ry

    def _dessiner_vue(self, i, pose, yaw, lumiere_vue):
        v = self._vues[i]
        s, n, t = M.skinner(v["modele"], self.squelette, pose)
        m4, ry = self.matrice_vue(yaw)
        sv, nv, tv = M.vers_vue(s, n, t, m4)
        centre_vue = (m4 @ np.append(CENTRE_TETE, 1.0))[:3]
        avant_vue = ry @ AVANT_MODELE
        avant_vue = avant_vue / np.linalg.norm(avant_vue)
        if v["maillage"] is None:
            mv = v["modele"]
            v["maillage"] = Maillage(self.rendu.ctx, self.rendu.prog_geo, sv, nv, mv.uv, tv, mv.triangles)
        else:
            v["maillage"].mettre_a_jour(sommets=sv, normales=nv, tangentes=tv)
        self.rendu.dessiner(v["maillage"], modele_vue=np.eye(4, dtype=np.float32),
                            projection=T.projection(self.largeur, self.hauteur),
                            centre_tete_vue=centre_vue.astype(np.float32),
                            lumiere_vue=lumiere_vue, avant_tete_vue=avant_vue.astype(np.float32),
                            tan_fov=T.tan_fov(self.largeur, self.hauteur), albedo=v["albedo"],
                            seuil_alpha=self.seuil_alpha if v["albedo"] is not None else 0.0)
        img = self.rendu.image_finale()[..., :3]
        if img.dtype != np.uint8:
            img = (np.clip(img, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
        return img.copy()

    def rendre(self, pose=None, yaw=0.0, *, lumiere_vue=T.LUMIERE_VUE, fondu_deg=0.0):
        """Image RGB uint8 (H, W, 3) à la pose et à l'angle donnés.

        Bascule nette par défaut. Avec fondu_deg > 0, près d'un point médian entre deux vues réelles,
        les deux images sont mélangées linéairement sur une fenêtre de fondu_deg degrés (mélange d'images :
        les deux vues ne sont pas recalées, un fondu large montre deux silhouettes superposées).
        """
        yaw = float(yaw)
        i, _ = self.vue_pour(yaw)
        if fondu_deg > 0 and len(self.angles) > 1:
            demi = 0.5 * np.radians(float(fondu_deg))
            for j in range(len(self.angles) - 1):
                mid = 0.5 * (self.angles[j] + self.angles[j + 1])
                if abs(yaw - mid) <= demi:
                    w = float(np.clip((yaw - (mid - demi)) / (2 * demi), 0.0, 1.0))
                    if 0.0 < w < 1.0:
                        a = self._dessiner_vue(j, pose, yaw, lumiere_vue).astype(np.float32)
                        b = self._dessiner_vue(j + 1, pose, yaw, lumiere_vue).astype(np.float32)
                        return np.clip((1.0 - w) * a + w * b + 0.5, 0, 255).astype(np.uint8)
        return self._dessiner_vue(i, pose, yaw, lumiere_vue)

    def liberer(self):
        self.rendu.liberer()
