"""Rendu d'une frame par déformation 2D : seuls les pixels des dessins sont composés.

1. Tête : fondu contrôlé entre le dessin de face et le dessin 3/4 recalé sur le cou, dans la zone de tête
   (poids doux). Le fondu est une interpolation entre deux dessins réels : il ne dessine rien.
2. Grille de déformation : compression de la tête vers l'axe (rotation simulée), respiration autour de
   l'articulation du bassin, cape et cheveux déplacés horizontalement (ressorts). Les nœuds portent le
   déplacement, interpolé sur l'image. cv2.remap déplace les pixels, sans fond ni contour ajouté.
3. Composition sur fond blanc (fond du dessin).
"""
import cv2
import numpy as np

from .grille import Grille
from .segmentation import zone_tete


def _rampe(x, a, b):
    """0 avant a, 1 après b (ou l'inverse si b < a), linéaire entre les deux."""
    return np.clip((x - a) / (b - a), 0.0, 1.0)


class Rendu:
    def __init__(self, personnage, pas=24, compression_tete=0.06):
        self.p = personnage
        face = personnage.vues["face"]
        H, W = face.fg.shape
        self.H, self.W = H, W
        tx, ty = personnage.translation_34
        M = np.float32([[1, 0, tx], [0, 1, ty]])
        self.F = face.premultiplie
        self.R = cv2.warpAffine(personnage.vues["trois_quarts"].premultiplie, M, (W, H),
                                flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        sq = face.points
        xc, yc = face.pivot_tete
        xb, yb = sq["bassin"]
        self.cx = 0.5 * (sq["tete_haut"][0] + sq["cou"][0])
        self.compression = float(compression_tete)
        X, Y = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
        self.wt = zone_tete(sq, (H, W))                                   # tête
        self.wb = _rampe(Y, yc + 30, yc + 90) * (1.0 - _rampe(Y, yb, yb + 30))   # respiration : haut du torse
        self.wc = _rampe(Y, yb - 20, 600)                                  # cape : bas, sous le bassin
        self.wh = (1.0 - _rampe(Y, yc - 60, yc - 20)) * self.wt            # cheveux : haut de la tête
        self.yb = float(yb)
        self.grille = Grille(H, W, pas)
        self.noeuds = (self.grille.XN, self.grille.YN)
        self.X, self.Y = X, Y
        self.wt_n, self.wb_n, self.wc_n, self.wh_n = (self._noeuds(a) for a in (self.wt, self.wb, self.wc, self.wh))

    def _noeuds(self, carte):
        """Valeurs de la carte aux nœuds de la grille (ny, nx)."""
        XN, YN = self.noeuds
        return carte[np.round(YN).astype(int), np.round(XN).astype(int)]

    def image(self, t, respiration=0.0, cape_px=0.0, cheveux_px=0.0):
        """Image RGB uint8 (H, W, 3). t : 0 = face, 1 = trois-quarts (fondu de la tête). Déplacements en px."""
        t = float(np.clip(t, 0.0, 1.0))
        comp = self.F + self.wt[..., None] * t * (self.R - self.F)
        XN, YN = self.noeuds
        dx_n = ((XN - self.cx) * self.compression * t * self.wt_n
                - cape_px * self.wc_n - cheveux_px * self.wh_n)
        dy_n = -(YN - self.yb) * respiration * self.wb_n
        dx = self.grille.champ_dense(dx_n)
        dy = self.grille.champ_dense(dy_n)
        out = self.grille.deformer(comp, self.X + dx, self.Y + dy)
        rgb = out[..., :3] + (1.0 - out[..., 3:4])        # fond blanc
        return (np.clip(rgb, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)

    def fantome(self, t=0.5):
        """Recouvrement des têtes des deux dessins (IoU des masques dans la zone de tête) après recalage.

        1.0 = les deux têtes se superposent parfaitement ; plus bas = deux silhouettes visibles pendant le fondu.
        """
        a = self.F[..., 3] * self.wt
        b = self.R[..., 3] * self.wt
        return float(np.minimum(a, b).sum() / max(np.maximum(a, b).sum(), 1e-9))
