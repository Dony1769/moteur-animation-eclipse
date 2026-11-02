"""Rigging 2D : squelette rigide, poids d'influence, grille FFD, animation par clés.

Pur numpy, sans GPU. Repère : coordonnées image en pixels, x vers la droite, y vers le bas
(comme les calques de relief.py). Un angle positif tourne dans le sens horaire à l'écran.

- Squelette : des os reliés à un parent ; chaque os tourne autour de son pivot.
  La pose est un dict {nom_os: angle en radians} ; les absents valent 0 (repos).
- Skinning linéaire : p' = somme_k w_k · G_k(pose) · p, avec G_k(repos) = identité.
  Les normales et tangentes ne reçoivent que la partie rotation de G_k.
- FFD (Sederberg-Parry) : une grille de points de contrôle en Bernstein ; un déplacement
  des points de contrôle déforme tout point de la boîte. Un champ linéaire est reproduit exactement.
- Animation : Piste (clés (temps, valeur), interpolation linéaire ou cubique de Hermite
  avec tangentes de Catmull-Rom) et Timeline (plusieurs pistes nommées).
"""
from dataclasses import dataclass, field
from math import comb
from typing import Optional

import numpy as np


def _rotation(theta):
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def _translation(x, y):
    m = np.eye(3)
    m[0, 2] = x
    m[1, 2] = y
    return m


# ---- squelette ----------------------------------------------------------------

@dataclass
class Os:
    nom: str
    pivot: tuple                        # (x, y) au repos, pixels
    parent: Optional[int] = None        # index de l'os parent, plus petit que le sien
    bout: Optional[tuple] = None        # extrémité au repos (poids par distance au segment)
    sigma: float = 40.0                 # étalement de l'influence autour de l'os, pixels


class Squelette:
    def __init__(self, os):
        self.os = list(os)
        self.index = {}
        for k, o in enumerate(self.os):
            if o.nom in self.index:
                raise ValueError(f"nom d'os en double : {o.nom}")
            if o.parent is not None and not (0 <= o.parent < k):
                raise ValueError(f"l'os {o.nom} doit avoir un parent d'index inférieur au sien")
            if o.sigma <= 0:
                raise ValueError(f"étalement non positif pour {o.nom}")
            self.index[o.nom] = k

    def matrices(self, pose=None):
        """Transformations (K, 3, 3) de chaque os, en coordonnées image. G_k(repos) = identité."""
        pose = pose or {}
        G = np.zeros((len(self.os), 3, 3))
        for k, o in enumerate(self.os):
            px, py = o.pivot
            local = _translation(px, py) @ _rotation(float(pose.get(o.nom, 0.0))) @ _translation(-px, -py)
            G[k] = local if o.parent is None else G[o.parent] @ local
        return G

    def skinner(self, points, poids, pose=None):
        """Positions (N, 2) déformées par skinning linéaire. poids : (N, K), lignes sommant à 1."""
        P = np.asarray(points, np.float64)
        G = self.matrices(pose)
        ph = np.concatenate([P, np.ones((len(P), 1))], axis=1)
        transformes = np.einsum("kab,nb->kna", G, ph)[..., :2]
        return np.einsum("nk,knc->nc", poids, transformes)

    def tourner_vecteurs(self, vecteurs, poids, pose=None):
        """Rotation pondérée de vecteurs 2D (N, 2) : seule la partie rotation de chaque os compte."""
        V = np.asarray(vecteurs, np.float64)
        R = self.matrices(pose)[:, :2, :2]
        return np.einsum("nk,kab,nb->na", poids, R, V)


def poids_par_distance(points, squelette, actifs=None):
    """Poids (N, K) : influence gaussienne de la distance au segment de chaque os, normalisée.

    actifs : noms des os autorisés à influencer ce groupe de points (None = tous). Les autres
    os ont un poids nul : un calque ne suit que les os qui le concernent (ex. un corps ne suit
    pas la tête).
    Calculé en log-domaine (softmax) : jamais de ligne nulle, même loin de tous les os.
    """
    P = np.asarray(points, np.float64)
    cols = []
    masque = np.ones(len(squelette.os), bool)
    if actifs is not None:
        inconnus = set(actifs) - set(squelette.index)
        if inconnus:
            raise ValueError(f"os inconnus : {sorted(inconnus)}")
        masque = np.array([o.nom in actifs for o in squelette.os], bool)
        if not masque.any():
            raise ValueError("aucun os actif")
    for k, o in enumerate(squelette.os):
        if not masque[k]:
            cols.append(np.full(len(P), -np.inf))
            continue
        a = np.asarray(o.pivot, np.float64)
        b = np.asarray(o.bout if o.bout is not None else o.pivot, np.float64)
        ab = b - a
        n2 = float(ab @ ab)
        if n2 < 1e-12:
            proj = np.broadcast_to(a, P.shape)
        else:
            t = np.clip((P - a) @ ab / n2, 0.0, 1.0)
            proj = a + t[:, None] * ab
        d2 = np.sum((P - proj) ** 2, axis=1)
        cols.append(-d2 / (2.0 * o.sigma ** 2))
    log_w = np.stack(cols, axis=1)
    log_w -= log_w.max(axis=1, keepdims=True)      # le max porte sur un os actif : jamais -inf partout
    w = np.exp(log_w)                               # exp(-inf) = 0 pour les os exclus
    return w / w.sum(axis=1, keepdims=True)


# ---- grille FFD ---------------------------------------------------------------

def _bernstein(s, n):
    """Base de Bernstein de degré n-1 aux paramètres s (N,) -> (N, n). Somme à 1 partout."""
    deg = n - 1
    s = np.asarray(s, np.float64)[:, None]
    i = np.arange(n)[None, :]
    coef = np.array([comb(deg, k) for k in range(n)], np.float64)[None, :]
    return coef * s ** i * (1.0 - s) ** (deg - i)


class GrilleFFD:
    """Grille de contrôle nx x ny sur la boîte (x0, y0, x1, y1), déformation de Sederberg-Parry."""

    def __init__(self, boite, nx, ny):
        if nx < 2 or ny < 2:
            raise ValueError("une grille FFD a au moins 2 x 2 points de contrôle")
        x0, y0, x1, y1 = boite
        if x1 <= x0 or y1 <= y0:
            raise ValueError("boîte FFD vide")
        self.boite = (float(x0), float(y0), float(x1), float(y1))
        self.nx, self.ny = nx, ny
        self.repos = np.stack(np.meshgrid(np.linspace(x0, x1, nx), np.linspace(y0, y1, ny)), axis=-1)
        self.decalages = np.zeros((ny, nx, 2))

    def appliquer(self, points, decalages=None):
        """Positions (N, 2) déformées. decalages : (ny, nx, 2) ; None = self.decalages."""
        dec = self.decalages if decalages is None else np.asarray(decalages, np.float64)
        P = np.asarray(points, np.float64)
        x0, y0, x1, y1 = self.boite
        s = (P[:, 0] - x0) / (x1 - x0)
        t = (P[:, 1] - y0) / (y1 - y0)
        Bx = _bernstein(s, self.nx)     # (N, nx)
        By = _bernstein(t, self.ny)     # (N, ny)
        deplacement = np.einsum("nj,ni,jic->nc", By, Bx, dec)
        return P + deplacement


def decalage_clignement(grille, cligne):
    """Décalages qui écrasent la boîte vers sa ligne médiane : cligne = 0 ouvert, 1 fermé.

    Champ linéaire en y : la déformation est exacte, p'_y = (1 - c) y + c y_milieu.
    """
    x0, y0, x1, y1 = grille.boite
    milieu = 0.5 * (y0 + y1)
    dec = np.zeros((grille.ny, grille.nx, 2))
    dec[..., 1] = -float(cligne) * (grille.repos[..., 1] - milieu)
    return dec


# ---- animation par clés -------------------------------------------------------

@dataclass
class Piste:
    cles: list                          # [(temps, valeur), ...]
    mode: str = "lineaire"              # "lineaire" ou "cubique"
    _t: np.ndarray = field(init=False, repr=False)
    _v: np.ndarray = field(init=False, repr=False)

    def __post_init__(self):
        if self.mode not in ("lineaire", "cubique"):
            raise ValueError(f"interpolation inconnue : {self.mode}")
        cles = sorted((float(t), float(v)) for t, v in self.cles)
        if not cles:
            raise ValueError("une piste a au moins une clé")
        ts = [t for t, _ in cles]
        if len(set(ts)) != len(ts):
            raise ValueError("deux clés au même instant")
        self.cles = cles
        self._t = np.array(ts)
        self._v = np.array([v for _, v in cles])

    def _tangente(self, k):
        """Pente dv/dt au nœud k (Catmull-Rom non uniforme, bords en différence simple)."""
        t, v, n = self._t, self._v, len(self._t)
        if n == 1:
            return 0.0
        if k == 0:
            return (v[1] - v[0]) / (t[1] - t[0])
        if k == n - 1:
            return (v[-1] - v[-2]) / (t[-1] - t[-2])
        return (v[k + 1] - v[k - 1]) / (t[k + 1] - t[k - 1])

    def valeur(self, temps):
        t, v = self._t, self._v
        if len(t) == 1 or temps <= t[0]:
            return float(v[0])
        if temps >= t[-1]:
            return float(v[-1])
        i = int(np.searchsorted(t, temps, side="right") - 1)
        i = min(max(i, 0), len(t) - 2)
        h = t[i + 1] - t[i]
        s = (temps - t[i]) / h
        if self.mode == "lineaire":
            return float(v[i] + s * (v[i + 1] - v[i]))
        m0 = self._tangente(i) * h
        m1 = self._tangente(i + 1) * h
        h00 = 2 * s ** 3 - 3 * s ** 2 + 1
        h10 = s ** 3 - 2 * s ** 2 + s
        h01 = -2 * s ** 3 + 3 * s ** 2
        h11 = s ** 3 - s ** 2
        return float(h00 * v[i] + h10 * m0 + h01 * v[i + 1] + h11 * m1)


class Timeline:
    """Ensemble de pistes nommées ; pose(t) renvoie {nom: valeur} à l'instant t."""

    def __init__(self):
        self.pistes = {}

    def ajouter(self, nom, cles, mode="lineaire"):
        self.pistes[nom] = Piste(cles, mode)

    def pose(self, temps):
        return {nom: p.valeur(temps) for nom, p in self.pistes.items()}

    def duree(self):
        return max((p.cles[-1][0] for p in self.pistes.values()), default=0.0)
