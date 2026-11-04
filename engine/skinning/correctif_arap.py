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

def _rotations(x, p, ij, N):
    """Rotation polaire par sommet : R_i = argmin sum_j ||(p_i-p_j) - R (x_i-x_j)||^2."""
    i, j = ij[:, 0], ij[:, 1]
    dx = x[i] - x[j]; dp = p[i] - p[j]
    S = np.zeros((N, 3, 3))
    np.add.at(S, i, dx[:, :, None] * dp[:, None, :])
    U, _, Vt = np.linalg.svd(S)
    V = np.transpose(Vt, (0, 2, 1)).copy()
    R = V @ np.transpose(U, (0, 2, 1))
    det = np.linalg.det(R)
    V[det < 0, :, 2] *= -1          # interdit les réflexions
    return V @ np.transpose(U, (0, 2, 1))

def arap_cible(rest, W, M, aretes, ancre, iters=12):
    """Positions ARAP pour une pose. ancre : masque booléen des sommets fixés (à P0)."""
    N = len(rest)
    P0 = _lbs(rest, W, M)
    i, j = aretes[:, 0], aretes[:, 1]
    ij = np.vstack([aretes, aretes[:, ::-1]])
    p = P0.copy()
    free = ~ancre
    idx = -np.ones(N, dtype=int); idx[free] = np.arange(free.sum())
    # matrice laplacienne réduite (poids uniformes)
    deg = np.bincount(ij[:, 0], minlength=N).astype(float)
    mask = free[ij[:, 0]] & free[ij[:, 1]]
    rows = idx[ij[mask, 0]]; cols = idx[ij[mask, 1]]
    L = sp.diags(deg[free]) - sp.coo_matrix((np.ones(mask.sum()), (rows, cols)), shape=(free.sum(),) * 2).tocsr()
    L = L.tocsc()
    solveur = spl.factorized(L)
    for _ in range(iters):
        R = _rotations(rest, p, ij, N)
        # second membre : sum_j (R_i + R_j)/2 (x_i - x_j) pour chaque arête orientée i->j
        dx = rest[ij[:, 0]] - rest[ij[:, 1]]
        Rm = 0.5 * (R[ij[:, 0]] + R[ij[:, 1]])
        contrib = np.einsum("eij,ej->ei", Rm, dx)
        b = np.zeros((N, 3))
        np.add.at(b, ij[:, 0], contrib)
        # termes des ancres fixés : retirer la contribution des voisins fixés
        bf = b[free].copy()
        fixed_nb = ~free[ij[:, 1]]
        fb = np.zeros((N, 3))
        np.add.at(fb, ij[fixed_nb, 0], P0[ij[fixed_nb, 1]])
        rhs = bf + fb[free]
        p_new = np.zeros((N, 3))
        for c in range(3):
            p_new[free, c] = solveur(rhs[:, c])
        p_new[ancre] = P0[ancre]
        p = p_new
    return P0, p
