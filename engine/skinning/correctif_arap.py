"""Correctifs déterministes par pose, cible ARAP (Sorkine & Alexa 2007, méthode locale-globale).

Pour une pose donnée :
  1. départ : positions LBS P0 ;
  2. étape locale : rotation optimale R_i par sommet (décomposition polaire de la covariance des arêtes) ;
  3. étape globale : positions p qui minimisent sum_arêtes ||(p_i - p_j) - (R_i + R_j)/2 (x_i - x_j)||^2,
     les sommets d'ancrage (os racine) restant fixés à P0 ;
  4. répéter ; le correctif est delta = p - P0.

Aucune donnée d'artiste : la cible est géométrique. Déterministe, CPU uniquement.
"""
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spl

def _lbs(rest, W, M):
    R4 = np.concatenate([rest, np.ones((len(rest), 1))], 1)
    return np.einsum("ib,bjk,ik->ij", W, M, R4)[:, :3]

def _rotations(x, p, ij, N, wij=None):
    """Rotation polaire par sommet : R_i = argmin sum_j ||(p_i-p_j) - R (x_i-x_j)||^2."""
    i, j = ij[:, 0], ij[:, 1]
    dx = x[i] - x[j]; dp = p[i] - p[j]
    S = np.zeros((N, 3, 3))
    ww = np.ones(len(i)) if wij is None else wij
    np.add.at(S, i, ww[:, None, None] * dx[:, :, None] * dp[:, None, :])
    U, _, Vt = np.linalg.svd(S)
    V = np.transpose(Vt, (0, 2, 1)).copy()
    R = V @ np.transpose(U, (0, 2, 1))
    det = np.linalg.det(R)
    V[det < 0, :, 2] *= -1          # interdit les réflexions
    return V @ np.transpose(U, (0, 2, 1))

def arap_cible(rest, W, M, aretes, ancre, iters=12, poids=None, faces=None, alpha=0.5, debut_limite=0):
    """Positions ARAP pour une pose. ancre : masque booléen des sommets fixés (à P0)."""
    N = len(rest)
    P0 = _lbs(rest, W, M)
    if poids is None:
        poids = np.ones(len(aretes))
    ij = np.vstack([aretes, aretes[:, ::-1]])
    wij = np.concatenate([poids, poids])
    p = P0.copy()
    free = ~ancre
    idx = -np.ones(N, dtype=int); idx[free] = np.arange(free.sum())
    # matrice laplacienne réduite (poids uniformes)
    deg = np.bincount(ij[:, 0], weights=wij, minlength=N)
    mask = free[ij[:, 0]] & free[ij[:, 1]]
    rows = idx[ij[mask, 0]]; cols = idx[ij[mask, 1]]
    L = sp.diags(deg[free]) - sp.coo_matrix((wij[mask], (rows, cols)), shape=(free.sum(),) * 2).tocsr()
    L = L.tocsc()
    solveur = spl.factorized(L)
    for _ in range(iters):
        R = _rotations(rest, p, ij, N, wij)
        if faces is not None and _ >= debut_limite:
            # limitation de rotation : sommets des faces repliées ramenés vers l'identité (erreur 58)
            from plis_numpy import plis_masque
            masque = plis_masque(rest, p, W, M, faces)
            if masque.any():
                touches = np.unique(np.concatenate([np.array(list(faces[k]), dtype=int) for k in np.where(masque)[0]]))
                melange = alpha * R[touches] + (1 - alpha) * np.eye(3)
                U2, _, Vt2 = np.linalg.svd(melange)
                R2 = Vt2.transpose(0, 2, 1) @ U2.transpose(0, 2, 1)
                R[touches] = R2
        # second membre : sum_j (R_i + R_j)/2 (x_i - x_j) pour chaque arête orientée i->j
        dx = rest[ij[:, 0]] - rest[ij[:, 1]]
        Rm = 0.5 * (R[ij[:, 0]] + R[ij[:, 1]])
        contrib = wij[:, None] * np.einsum("eij,ej->ei", Rm, dx)
        b = np.zeros((N, 3))
        np.add.at(b, ij[:, 0], contrib)
        # termes des ancres fixés : retirer la contribution des voisins fixés
        bf = b[free].copy()
        fixed_nb = ~free[ij[:, 1]]
        fb = np.zeros((N, 3))
        np.add.at(fb, ij[fixed_nb, 0], wij[fixed_nb, None] * P0[ij[fixed_nb, 1]])
        rhs = bf + fb[free]
        p_new = np.zeros((N, 3))
        for c in range(3):
            p_new[free, c] = solveur(rhs[:, c])
        p_new[ancre] = P0[ancre]
        p = p_new
    return P0, p


def poids_cotangents(rest, faces, aretes):
    """Poids cotangents par arête (Pinkall-Polthier), faces triangulées en éventail.

    Poids négatifs ramenés à 0 (cas obtus) pour garder une Laplacienne semi-définie positive.
    Retourne un tableau aligné sur `aretes`.
    """
    index = {(min(a, b), max(a, b)): k for k, (a, b) in enumerate(aretes)}
    w = np.zeros(len(aretes))
    for f in faces:
        f = list(f)
        for k in range(1, len(f) - 1):
            tri = (f[0], f[k], f[k + 1])
            for c in range(3):
                o, a, b = tri[c], tri[(c + 1) % 3], tri[(c + 2) % 3]
                u = rest[a] - rest[o]; v = rest[b] - rest[o]
                cross = np.linalg.norm(np.cross(u, v))
                cot = np.dot(u, v) / cross if cross > 0 else 0.0
                key = (min(a, b), max(a, b))
                if key in index:
                    w[index[key]] += 0.5 * cot
    return np.maximum(w, 0.0)
