"""Maillages 3D : import OBJ, UV, tangentes, squelette 3D et skinning linéaire (LBS).

Conventions :
- espace modèle : y vers le haut, +z vers l'avant du personnage, unités arbitraires (≈ mètres) ;
- la caméra est à l'origine de l'espace vue, regarde vers -z (comme le reste du moteur) ;
- un maillage est un objet `Modele` : positions, normales, UV, tangentes, triangles, poids d'os.

Ce module ne contient ni OpenGL ni rendu : il est testable sur CPU. Le rendu est dans rendu3d.py.

Limites, à lire avant utilisation :
- OBJ seulement (pas de glTF) ; pas de matériaux ni de textures lus depuis le fichier ;
- les UV, s'ils manquent, sont une projection planaire depuis la face (+z). Elle est juste de face et
  s'étire sur les côtés : une texture peinte ou dépliée est nécessaire pour les grands angles ;
- les poids d'os viennent d'une proximité aux segments d'os (gaussienne, top-k), pas d'une peinture de poids.
"""
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class Modele:
    sommets: np.ndarray            # (N, 3) positions, espace modèle
    normales: np.ndarray           # (N, 3) unitaires
    uv: np.ndarray                 # (N, 2) dans [0, 1]
    triangles: np.ndarray          # (M, 3) uint32
    tangentes: np.ndarray          # (N, 3) unitaires, orthogonales aux normales
    poids: np.ndarray = None       # (N, B) poids d'os (lignes sommant à 1), ou None
    uv_origine: str = "fichier"    # "fichier" ou "projection" (UV planaires calculées)
    origine: str = ""              # chemin ou nom de la source
    extras: dict = field(default_factory=dict)


# ---------------------------------------------------------------- normales, tangentes, UV

def calculer_normales(sommets, triangles):
    """Normales de sommets : moyenne des normales de faces, pondérée par l'aire. Unitaires."""
    s = np.asarray(sommets, np.float64)
    t = np.asarray(triangles, np.int64)
    a, b, c = s[t[:, 0]], s[t[:, 1]], s[t[:, 2]]
    fn = np.cross(b - a, c - a)                       # norme = 2 × aire
    n = np.zeros_like(s)
    for k in range(3):
        np.add.at(n, t[:, k], fn)
    norme = np.linalg.norm(n, axis=1, keepdims=True)
    defaut = np.array([0.0, 0.0, 1.0])
    return np.where(norme > 1e-12, n / np.maximum(norme, 1e-12), defaut)


def calculer_tangentes(sommets, uv, triangles, normales):
    """Tangentes de sommets d'après les dérivées des UV, orthogonalisées à la normale."""
    s = np.asarray(sommets, np.float64)
    uv = np.asarray(uv, np.float64)
    t = np.asarray(triangles, np.int64)
    n = np.asarray(normales, np.float64)
    tan = np.zeros_like(s)
    for i0, i1, i2 in t:
        e1, e2 = s[i1] - s[i0], s[i2] - s[i0]
        d1, d2 = uv[i1] - uv[i0], uv[i2] - uv[i0]
        det = d1[0] * d2[1] - d2[0] * d1[1]
        if abs(det) < 1e-14:
            continue
        r = 1.0 / det
        tf = (e1 * d2[1] - e2 * d1[1]) * r
        for i in (i0, i1, i2):
            tan[i] += tf
    tan = tan - n * np.sum(tan * n, axis=1, keepdims=True)
    norme = np.linalg.norm(tan, axis=1, keepdims=True)
    # Repli : sommet sans UV exploitable -> direction arbitraire perpendiculaire à la normale.
    repli = np.cross(n, np.array([0.0, 1.0, 0.0]))
    repli = np.where(np.linalg.norm(repli, axis=1, keepdims=True) > 1e-6, repli,
                     np.cross(n, np.array([1.0, 0.0, 0.0])))
    tan = np.where(norme > 1e-12, tan / np.maximum(norme, 1e-12), repli)
    tan = tan / np.maximum(np.linalg.norm(tan, axis=1, keepdims=True), 1e-12)
    return tan


def uv_planaires(sommets):
    """UV planaires depuis la face (+z) : u selon x, v selon y (v = 1 en haut), dans [0, 1]."""
    s = np.asarray(sommets, np.float64)
    mn, mx = s.min(axis=0), s.max(axis=0)
    etendue = np.maximum(mx - mn, 1e-12)
    u = (s[:, 0] - mn[0]) / etendue[0]
    v = 1.0 - (s[:, 1] - mn[1]) / etendue[1]
    return np.stack([u, v], axis=1)


# ---------------------------------------------------------------- OBJ

def _indice(texte, n):
    """Indice OBJ (1-based, négatif = depuis la fin) vers indice 0-based."""
    i = int(texte)
    if i == 0:
        raise ValueError("indice OBJ nul")
    return i - 1 if i > 0 else n + i


def lire_obj(texte, origine="<texte>"):
    """Modele depuis le texte d'un fichier OBJ (v, vt, vn, f ; polygones triangulés en éventail)."""
    pos, uvs, nrm = [], [], []
    clefs = {}                       # (iv, ivt, ivn) -> indice de sommet final
    sommets, uv_fin, nrm_fin = [], [], []
    triangles = []
    for ligne in texte.splitlines():
        morceaux = ligne.split("#", 1)[0].split()
        if not morceaux:
            continue
        mot, args = morceaux[0], morceaux[1:]
        if mot == "v":
            if len(args) < 3:
                raise ValueError(f"{origine} : sommet incomplet : {ligne!r}")
            pos.append([float(x) for x in args[:3]])
        elif mot == "vt":
            uvs.append([float(x) for x in args[:2]] if len(args) >= 2 else [0.0, 0.0])
        elif mot == "vn":
            if len(args) < 3:
                raise ValueError(f"{origine} : normale incomplète : {ligne!r}")
            nrm.append([float(x) for x in args[:3]])
        elif mot == "f":
            if len(args) < 3:
                raise ValueError(f"{origine} : face à moins de 3 sommets : {ligne!r}")
            idx = []
            for a in args:
                parts = a.split("/")
                iv = _indice(parts[0], len(pos))
                ivt = _indice(parts[1], len(uvs)) if len(parts) > 1 and parts[1] else None
                ivn = _indice(parts[2], len(nrm)) if len(parts) > 2 and parts[2] else None
                if not 0 <= iv < len(pos):
                    raise ValueError(f"{origine} : indice de sommet hors plage : {a}")
                if ivt is not None and not 0 <= ivt < len(uvs):
                    raise ValueError(f"{origine} : indice UV hors plage : {a}")
                if ivn is not None and not 0 <= ivn < len(nrm):
                    raise ValueError(f"{origine} : indice de normale hors plage : {a}")
                cle = (iv, ivt, ivn)
                if cle not in clefs:
                    clefs[cle] = len(sommets)
                    sommets.append(pos[iv])
                    uv_fin.append(uvs[ivt] if ivt is not None else None)
                    nrm_fin.append(nrm[ivn] if ivn is not None else None)
                idx.append(clefs[cle])
            for k in range(1, len(idx) - 1):          # éventail : (0, k, k+1)
                triangles.append((idx[0], idx[k], idx[k + 1]))
    if not triangles:
        raise ValueError(f"{origine} : aucune face")
    s = np.asarray(sommets, np.float64)
    t = np.asarray(triangles, np.uint32)
    if all(u is not None for u in uv_fin):
        uv = np.asarray(uv_fin, np.float64)
        origine_uv = "fichier"
    else:
        uv = uv_planaires(s)
        origine_uv = "projection"
    if all(n is not None for n in nrm_fin):
        normales = np.asarray(nrm_fin, np.float64)
        normales = normales / np.maximum(np.linalg.norm(normales, axis=1, keepdims=True), 1e-12)
    else:
        normales = calculer_normales(s, t)
    tangentes = calculer_tangentes(s, uv, t, normales)
    return Modele(sommets=s, normales=normales, uv=uv, triangles=t, tangentes=tangentes,
                  uv_origine=origine_uv, origine=origine)


def charger_obj(chemin):
    """Modele depuis un fichier .obj."""
    chemin = Path(chemin)
    return lire_obj(chemin.read_text(encoding="utf-8"), origine=str(chemin))


def ecrire_obj(modele, chemin):
    """Écrit un Modele en OBJ (sommets, UV, normales par sommet, faces triangulaires)."""
    lignes = ["# maillage écrit par maillage3d.ecrire_obj"]
    lignes += [f"v {x:.6f} {y:.6f} {z:.6f}" for x, y, z in modele.sommets]
    lignes += [f"vt {u:.6f} {v:.6f}" for u, v in modele.uv]
    lignes += [f"vn {x:.6f} {y:.6f} {z:.6f}" for x, y, z in modele.normales]
    for a, b, c in np.asarray(modele.triangles, np.int64) + 1:
        lignes.append(f"f {a}/{a}/{a} {b}/{b}/{b} {c}/{c}/{c}")
    Path(chemin).write_text("\n".join(lignes) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- transformations

def rotation_axe(axe, angle):
    """Matrice 3x3 de rotation autour d'un axe unitaire (formule de Rodrigues)."""
    a = np.asarray(axe, np.float64)
    nrm = np.linalg.norm(a)
    if nrm < 1e-12:
        raise ValueError("axe de rotation nul")
    x, y, z = a / nrm
    c, s = np.cos(angle), np.sin(angle)
    k = np.array([[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]])
    return np.eye(3) + s * k + (1.0 - c) * (k @ k)


def transformation(rotation3=None, translation=(0.0, 0.0, 0.0)):
    """Matrice 4x4 : rotation 3x3 puis translation."""
    m = np.eye(4)
    if rotation3 is not None:
        m[:3, :3] = rotation3
    m[:3, 3] = translation
    return m


# ---------------------------------------------------------------- squelette 3D

@dataclass(frozen=True)
class Os3D:
    nom: str
    parent: int                    # indice de l'os parent dans le squelette, -1 pour la racine
    joint: tuple                   # articulation au repos, espace modèle
    extremite: tuple               # bout de l'os au repos (sert aux poids par proximité)


class Squelette3D:
    """Hiérarchie d'os 3D. Pose : {nom: (axe, angle)} ; rotation autour de l'articulation de l'os.

    Matrice monde : G_k = G_parent · T(joint_k − joint_parent) · R_k ;
    matrice de skinning : S_k = G_k · T(−joint_k), égale à l'identité au repos.
    Les os doivent être listés après leur parent (parent < enfant).
    """

    def __init__(self, os):
        self.os = list(os)
        self.index = {}
        for k, o in enumerate(self.os):
            if o.nom in self.index:
                raise ValueError(f"os en double : {o.nom}")
            if o.parent >= k:
                raise ValueError(f"l'os {o.nom} doit suivre son parent")
            if o.parent < -1:
                raise ValueError(f"parent invalide pour {o.nom}")
            self.index[o.nom] = k
        self.joints = np.array([o.joint for o in self.os], np.float64)
        self.extremites = np.array([o.extremite for o in self.os], np.float64)

    def __len__(self):
        return len(self.os)

    def matrices_monde(self, pose=None):
        """Liste des G_k (4x4) pour une pose {nom: (axe, angle)} (os absents = repos)."""
        pose = pose or {}
        for nom in pose:
            if nom not in self.index:
                raise ValueError(f"os inconnu dans la pose : {nom}")
        g = []
        for k, o in enumerate(self.os):
            if o.parent < 0:
                base = transformation(translation=self.joints[k])
            else:
                base = g[o.parent] @ transformation(translation=self.joints[k] - self.joints[o.parent])
            if o.nom in pose:
                axe, angle = pose[o.nom]
                base = base @ transformation(rotation3=rotation_axe(axe, angle))
            g.append(base)
        return g

    def matrices_skinning(self, pose=None):
        """(B, 4, 4) : S_k = G_k · T(−joint_k)."""
        g = self.matrices_monde(pose)
        return np.stack([g[k] @ transformation(translation=-self.joints[k]) for k in range(len(self.os))])


def poids_proximite(sommets, squelette, sigma=0.08, k=2):
    """Poids d'os (N, B) : gaussienne de la distance de chaque sommet au segment (joint, extrémité) de l'os.

    Seuls les k os les plus proches gardent un poids ; les poids sont normalisés à 1. Si un sommet est
    loin de tous les segments, le plus proche reçoit tout le poids (pas de sommet sans os).
    """
    s = np.asarray(sommets, np.float64)
    a = squelette.joints                        # (B, 3)
    b = squelette.extremites                    # (B, 3)
    ab = b - a
    longueur2 = np.sum(ab * ab, axis=1)
    # distance point -> segment, pour tous les (sommet, os)
    ap = s[:, None, :] - a[None, :, :]          # (N, B, 3)
    t = np.where(longueur2 > 1e-12, np.sum(ap * ab[None], axis=2) / np.maximum(longueur2, 1e-12)[None], 0.0)
    t = np.clip(t, 0.0, 1.0)
    proj = a[None] + t[..., None] * ab[None]
    d = np.linalg.norm(s[:, None, :] - proj, axis=2)     # (N, B)
    gauss = np.exp(-(d * d) / (2.0 * sigma * sigma))
    rang = np.argsort(-gauss, axis=1)
    masque = np.zeros_like(gauss, bool)
    np.put_along_axis(masque, rang[:, :k], True, axis=1)
    w = np.where(masque, gauss, 0.0)
    somme = w.sum(axis=1, keepdims=True)
    proche = np.argmin(d, axis=1)
    w_repli = np.zeros_like(w)
    w_repli[np.arange(len(s)), proche] = 1.0
    return np.where(somme > 1e-300, w / np.maximum(somme, 1e-300), w_repli)


def skinner(modele, squelette, pose=None):
    """Positions et normales posées (LBS). Renvoie (sommets (N,3), normales (N,3), tangentes (N,3)).

    v' = Σ_k w_k · S_k · v ; n' = normalize(Σ_k w_k · R_k · n) avec R_k la partie linéaire de S_k.
    Sans poids d'os, le maillage est renvoyé tel quel (pose de repos).
    """
    if modele.poids is None:
        return modele.sommets.copy(), modele.normales.copy(), modele.tangentes.copy()
    S = squelette.matrices_skinning(pose)                      # (B, 4, 4)
    w = np.asarray(modele.poids, np.float64)                   # (N, B)
    if w.shape[1] != len(squelette):
        raise ValueError("poids et squelette de tailles différentes")
    vh = np.concatenate([modele.sommets, np.ones((len(modele.sommets), 1))], axis=1)
    pos = np.einsum("nb,bij,nj->ni", w, S, vh)[:, :3]
    lin = S[:, :3, :3]
    nrm = np.einsum("nb,bij,nj->ni", w, lin, modele.normales)
    tan = np.einsum("nb,bij,nj->ni", w, lin, modele.tangentes)
    nrm = nrm / np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
    tan = tan / np.maximum(np.linalg.norm(tan, axis=1, keepdims=True), 1e-12)
    return pos, nrm, tan


def vers_vue(sommets, normales, tangentes, m4):
    """Applique une transformation 4x4 (modèle -> vue) aux positions et à la partie linéaire aux vecteurs."""
    s = np.asarray(sommets, np.float64)
    vh = np.concatenate([s, np.ones((len(s), 1))], axis=1)
    pos = (vh @ np.asarray(m4, np.float64).T)[:, :3]
    lin = np.asarray(m4, np.float64)[:3, :3]
    nrm = np.asarray(normales, np.float64) @ lin.T
    tan = np.asarray(tangentes, np.float64) @ lin.T
    nrm = nrm / np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
    tan = tan / np.maximum(np.linalg.norm(tan, axis=1, keepdims=True), 1e-12)
    return pos, nrm, tan
