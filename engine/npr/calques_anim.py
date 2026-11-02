"""Calques articulés 2.5D : grille de sommets déformable, prête pour des VBO dynamiques.

Un CalqueArticule est un Calque (relief.py) découpé en grille de sommets au repos, en
coordonnées image. À chaque pose :
  1. la grille FFD déforme les positions au repos (ex. clignement des yeux) ;
  2. le squelette déforme les positions, les normales et les tangentes (skinning linéaire) ;
  3. chaque sommet reçoit une profondeur issue du relief au repos, et on passe en coordonnées vue.
Le résultat (sommets, normales, UV, tangentes) est écrit dans le VBO du calque à chaque image
(voir rendu.RenduNPR.dessiner_calques). La topologie (triangles) ne change jamais.

Profondeur : la profondeur de chaque sommet suit son relief au repos. Le tri par profondeur
moyenne (trier_par_profondeur) fixe l'ordre de dessin ; le z-buffer matériel tranche ensuite
pixel par pixel, donc un ordre de dessin faux ne change pas l'image finale.
"""
from dataclasses import dataclass
from typing import Optional

import numpy as np

from . import relief as RL
from .rig import GrilleFFD, Squelette, decalage_clignement, poids_par_distance


def _axe(longueur, pas):
    """Coordonnées de grille de 0 à longueur, pas constant, bord final inclus."""
    axe = np.arange(0.0, float(longueur), float(pas))
    if axe[-1] != longueur:
        axe = np.append(axe, float(longueur))
    return axe


def vers_vue(points, profondeurs, largeur, hauteur, tan_fov):
    """Points image (N, 2) + profondeur d (N,) -> sommets vue (N, 3), même convention que l'ombrage.

    L'ombrage reconstruit x = ndc_x · tan_x · d, y = ndc_y · tan_y · d, z = -d. Ici ndc_x = 2x/W - 1
    et ndc_y = 1 - 2y/H (y image vers le bas). Les deux chemins restent cohérents.
    """
    P = np.asarray(points, np.float64)
    d = np.asarray(profondeurs, np.float64)
    tx, ty = tan_fov
    ndc_x = 2.0 * P[:, 0] / largeur - 1.0
    ndc_y = 1.0 - 2.0 * P[:, 1] / hauteur
    return np.stack([ndc_x * tx * d, ndc_y * ty * d, -d], axis=1)


def _tourner_3d(vecteurs, squelette, poids, pose):
    """Rotation pondérée de vecteurs vue (N, 3). Passage dans le repère image (y vers le bas)."""
    v = np.asarray(vecteurs, np.float64)
    img = np.stack([v[:, 0], -v[:, 1]], axis=1)
    tourne = squelette.tourner_vecteurs(img, poids, pose)
    out = np.stack([tourne[:, 0], -tourne[:, 1], v[:, 2]], axis=1)
    norme = np.linalg.norm(out, axis=1, keepdims=True)
    return np.where(norme > 1e-9, out / np.maximum(norme, 1e-12), 0.0)


@dataclass
class CalqueArticule:
    nom: str
    calque: RL.Calque
    ordre: int                      # départage à profondeur moyenne égale (plus grand = plus devant)
    squelette: Optional[Squelette]
    ffd: Optional[GrilleFFD]
    cle_ffd: Optional[str]          # nom de la piste de pose qui pilote la grille FFD (ex. "cligne")
    P: np.ndarray                   # (N, 2) positions au repos, pixels image
    uv: np.ndarray                  # (N, 2) coordonnées de texture = P / (W, H)
    triangles: np.ndarray           # (T, 3) uint32, topologie fixe
    d_repos: np.ndarray             # (N,) profondeur de chaque sommet au repos
    n_repos: np.ndarray             # (N, 3) normales au repos, vue
    t_repos: np.ndarray             # (N, 3) tangentes au repos, vue (zéro = pas de cheveux)
    poids: Optional[np.ndarray]     # (N, K) poids du squelette, None sans squelette
    largeur: int
    hauteur: int

    def sommets(self, pose, tan_fov):
        """Sommets à la pose donnée : dict {vue (N,3), normales (N,3), tangentes (N,3), uv (N,2), px (N,2)}."""
        pose = pose or {}
        P = self.P
        if self.ffd is not None:
            dec = decalage_clignement(self.ffd, pose.get(self.cle_ffd, 0.0)) if self.cle_ffd else None
            P = self.ffd.appliquer(P, dec)
        n = self.n_repos
        t = self.t_repos
        if self.squelette is not None:
            P = self.squelette.skinner(P, self.poids, pose)
            n = _tourner_3d(n, self.squelette, self.poids, pose)
            t = _tourner_3d(t, self.squelette, self.poids, pose)
        vue = vers_vue(P, self.d_repos, self.largeur, self.hauteur, tan_fov)
        return {"vue": vue, "normales": n, "tangentes": t, "uv": self.uv, "px": P}


def construire(nom, calque, ordre=0, squelette=None, ffd=None, cle_ffd=None, cellule=4.0, os_actifs=None):
    """Découpe un Calque en grille articulable. Garde les cellules qui touchent un pixel opaque.

    os_actifs : os du squelette qui influencent ce calque (None = tous). Un corps ne doit suivre
    que son propre os ; sinon ses bords se courbent quand la tête bouge.
    """
    H, W = calque.rgba.shape[:2]
    if cellule <= 0:
        raise ValueError("cellule non positive")
    h = RL.relief(calque)
    n_img = RL.normales(h * calque.rayon_biseau, calque.pente)
    if calque.flux is not None:
        t_img = RL.tangente_depuis_flux(calque.flux)
    else:
        t_img = np.zeros((H, W, 3), np.float32)

    xs = _axe(W, cellule)
    ys = _axe(H, cellule)
    gx, gy = np.meshgrid(xs, ys)
    grille = np.stack([gx.ravel(), gy.ravel()], axis=1)
    nx, ny = len(xs) - 1, len(ys) - 1
    index = np.arange((ny + 1) * (nx + 1)).reshape(ny + 1, nx + 1)

    opaque = calque.rgba[..., 3] >= RL.SEUIL_ALPHA
    tris = []
    for j in range(ny):
        y0, y1 = int(ys[j]), int(ys[j + 1])
        for i in range(nx):
            x0, x1 = int(xs[i]), int(xs[i + 1])
            if not opaque[y0:y1, x0:x1].any():
                continue
            a, b = index[j, i], index[j, i + 1]
            c, d = index[j + 1, i], index[j + 1, i + 1]
            tris.append((a, c, b))
            tris.append((b, c, d))
    if not tris:
        raise ValueError(f"le calque {nom} n'a aucun pixel opaque")

    tris = np.array(tris, np.int64)
    utilises = np.unique(tris)
    correspondance = np.full(len(grille), -1, np.int64)
    correspondance[utilises] = np.arange(len(utilises))
    P = grille[utilises]
    triangles = correspondance[tris].astype(np.uint32)

    ix = np.clip(np.floor(P[:, 0]).astype(int), 0, W - 1)
    iy = np.clip(np.floor(P[:, 1]).astype(int), 0, H - 1)
    h_v = h[iy, ix].astype(np.float64)
    d_repos = calque.plan - calque.relief_max * h_v
    poids = poids_par_distance(P, squelette, os_actifs) if squelette is not None else None

    return CalqueArticule(
        nom=nom,
        calque=calque,
        ordre=int(ordre),
        squelette=squelette,
        ffd=ffd,
        cle_ffd=cle_ffd,
        P=P,
        uv=np.stack([P[:, 0] / W, P[:, 1] / H], axis=1),
        triangles=triangles,
        d_repos=d_repos,
        n_repos=n_img[iy, ix].astype(np.float64),
        t_repos=t_img[iy, ix].astype(np.float64),
        poids=poids,
        largeur=W,
        hauteur=H,
    )


def profondeur_moyenne(sommets):
    """Profondeur moyenne (distance caméra) des sommets d'un calque à une pose."""
    return float(np.mean(-sommets["vue"][:, 2]))


def trier_par_profondeur(calques, sommets_par_calque):
    """Ordre de dessin arrière -> avant : profondeur moyenne décroissante, puis ordre croissant.

    sommets_par_calque : {nom: dict renvoyé par CalqueArticule.sommets}. Les noms doivent être uniques.
    """
    noms = [c.nom for c in calques]
    if len(set(noms)) != len(noms):
        raise ValueError("noms de calques en double")
    cle = {c.nom: (-profondeur_moyenne(sommets_par_calque[c.nom]), c.ordre) for c in calques}
    return sorted(calques, key=lambda c: cle[c.nom])
