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


def jacobiennes(P_repos, P_deforme, triangles):
    """Jacobienne 2x2 (N, 2, 2) de la déformation rest -> déformé, par sommet.

    Pour chaque triangle, application affine J_t = [b1-b0, b2-b0] · [a1-a0, a2-a0]^-1 ; on moyenne
    par sommet, pondéré par l'aire au repos. Un triangle dégénéré au repos ne compte pas. Un sommet
    sans triangle valable reçoit l'identité.
    """
    A = np.asarray(P_repos, np.float64)
    B = np.asarray(P_deforme, np.float64)
    T = np.asarray(triangles, np.int64)
    a = [A[T[:, k]] for k in range(3)]
    b = [B[T[:, k]] for k in range(3)]
    E = np.stack([a[1] - a[0], a[2] - a[0]], axis=-1)          # (T, 2, 2), colonnes = arêtes
    F = np.stack([b[1] - b[0], b[2] - b[0]], axis=-1)
    det = np.linalg.det(E)
    valable = np.abs(det) > 1e-9
    Jt = np.zeros((len(T), 2, 2))
    Jt[valable] = F[valable] @ np.linalg.inv(E[valable])
    aire = np.abs(det) * 0.5 * valable
    J = np.zeros((len(A), 2, 2))
    poids = np.zeros(len(A))
    for k in range(3):
        np.add.at(J, T[:, k], Jt * aire[:, None, None])
        np.add.at(poids, T[:, k], aire)
    ok = poids > 0
    J[ok] /= poids[ok, None, None]
    J[~ok] = np.eye(2)
    return J


def pousser_normales(n_vue, t_vue, J):
    """Normales et tangentes vue poussées par la jacobienne J (N, 2, 2), calcul exact et à la volée.

    Hauteur implicite h : n_img = (-∂h/∂x, -∂h/∂y, 1) avec n_img = (nx, -ny, nz). Donc
    g = ∇h = (-nx/nz, ny/nz) dans le repère image. Sous une déformation F de jacobienne J, le
    gradient se transforme en g' = J^-T g (règle de la chaîne inverse), d'où la normale
    n' ∝ (-g'x, +g'y, 1) en repère vue. La tangente (flux) se transforme par J : t' = J t.
    Pour une rotation rigide J = R, g' = R g : on retrouve la rotation de la normale. Au repos J = I.
    Une jacobienne dégénérée (det <= 1e-6, repli sur l'identité) laisse la normale inchangée.
    """
    n = np.asarray(n_vue, np.float64)
    t = np.asarray(t_vue, np.float64)
    J = np.asarray(J, np.float64)
    det = np.linalg.det(J)
    sain = det > 1e-6
    J = np.where(sain[:, None, None], J, np.eye(2))
    g = np.stack([-n[:, 0] / n[:, 2], n[:, 1] / n[:, 2]], axis=1)
    JT = np.transpose(J, (0, 2, 1))
    gp = np.linalg.solve(JT, g[..., None])[..., 0]
    out = np.stack([-gp[:, 0], gp[:, 1], np.ones(len(n))], axis=1)
    out /= np.linalg.norm(out, axis=1, keepdims=True)
    # Tangente : repère image (x, -y), puis retour vue. z reste nul.
    ti = np.stack([t[:, 0], -t[:, 1]], axis=1)
    tp = np.einsum("nab,nb->na", J, ti)
    tv = np.stack([tp[:, 0], -tp[:, 1], np.zeros(len(t))], axis=1)
    nt = np.linalg.norm(tv, axis=1, keepdims=True)
    tv = np.where(nt > 1e-9, tv / np.maximum(nt, 1e-12), 0.0)
    return out.astype(np.float32), tv.astype(np.float32)


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
    texture: Optional[np.ndarray] = None   # (A_H, A_W, 4) : atlas partagé ; None = calque.rgba

    def sommets(self, pose, tan_fov):
        """Sommets à la pose donnée : dict {vue, normales, tangentes, uv, px}.

        Ordre : FFD (positions au repos), puis skinning (positions). Les normales et tangentes
        sont recalculées à partir de la jacobienne de la déformation totale (jacobiennes,
        pousser_normales), donc elles suivent le volume déformé, FFD comprise.
        """
        pose = pose or {}
        P = self.P
        if self.ffd is not None:
            dec = decalage_clignement(self.ffd, pose.get(self.cle_ffd, 0.0)) if self.cle_ffd else None
            P = self.ffd.appliquer(P, dec)
        if self.squelette is not None:
            P = self.squelette.skinner(P, self.poids, pose)
        if np.array_equal(P, self.P):
            n, t = self.n_repos.astype(np.float32), self.t_repos.astype(np.float32)
        else:
            J = jacobiennes(self.P, P, self.triangles)
            n, t = pousser_normales(self.n_repos, self.t_repos, J)
        vue = vers_vue(P, self.d_repos, self.largeur, self.hauteur, tan_fov)
        return {"vue": vue, "normales": n, "tangentes": t, "uv": self.uv, "px": P}


def construire(nom, calque, ordre=0, squelette=None, ffd=None, cle_ffd=None, cellule=4.0, os_actifs=None,
               texture=None, uv_de=None):
    """Découpe un Calque en grille articulable. Garde les cellules qui touchent un pixel opaque.

    os_actifs : os du squelette qui influencent ce calque (None = tous). Un corps ne doit suivre
    que son propre os ; sinon ses bords se courbent quand la tête bouge.
    texture : atlas RGBA partagé (A_H, A_W, 4) ; uv_de(P) -> UV (N, 2) dans cet atlas (ex. chargeur.Atlas.uv).
    Sans ces deux arguments, la texture est le calque plein cadre et uv = P / (W, H).
    """
    if (texture is None) != (uv_de is None):
        raise ValueError("texture et uv_de vont ensemble")
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
    uv = uv_de(P) if uv_de is not None else np.stack([P[:, 0] / W, P[:, 1] / H], axis=1)

    return CalqueArticule(
        nom=nom,
        calque=calque,
        ordre=int(ordre),
        squelette=squelette,
        ffd=ffd,
        cle_ffd=cle_ffd,
        P=P,
        uv=np.asarray(uv, np.float64),
        triangles=triangles,
        d_repos=d_repos,
        n_repos=n_img[iy, ix].astype(np.float64),
        t_repos=t_img[iy, ix].astype(np.float64),
        poids=poids,
        largeur=W,
        hauteur=H,
        texture=texture,
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
