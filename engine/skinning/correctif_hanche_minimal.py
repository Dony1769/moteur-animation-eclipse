"""Correctif de forme de la hanche, calculé (remplace le sculptage de référence, voir erreur 85).

Pour une pose : on repousse les sommets des faces repliées le long de la normale de repos tournée,
puis on lisse dans la zone, le déplacement étant plafonné (CAP) par rapport à la base LBS.
Objectif : 0 pli avec le déplacement le plus petit possible, zone limitée à RAYON autour de la hanche.
"""
import numpy as np
from scipy.sparse import coo_matrix, diags
from scipy.sparse.linalg import spsolve
from plis_numpy import _newell


def corriger(rest, P0, Ms, dom, faces, aretes, hanche, rayon=0.25, cap=0.03, iters=300, pas=0.002):
    N = len(rest)
    zone = np.linalg.norm(rest - hanche, axis=1) < rayon
    P = P0.copy()
    # Laplacien de la zone (arêtes internes)
    ij = aretes
    m = zone[ij[:, 0]] & zone[ij[:, 1]]
    a, b = ij[m, 0], ij[m, 1]
    L = coo_matrix((np.r_[-np.ones(len(a)), -np.ones(len(a))], (np.r_[a, b], np.r_[b, a])), shape=(N, N)).tocsr()
    deg = np.asarray(-L.sum(1)).ravel()
    L = L + diags(deg)
    idx = np.where(zone)[0]
    for _ in range(iters):
        changed = False
        for f in faces:
            bx = list(f)
            if not zone[bx].any():
                continue
            o = np.bincount(dom[bx], minlength=Ms.shape[0]).argmax()
            R = Ms[o][:3, :3]
            nr = _newell(rest, bx); npz = _newell(P, bx)
            if np.linalg.norm(nr) == 0 or np.linalg.norm(npz) == 0:
                continue
            if npz @ (R @ nr) < 0:
                changed = True
                d = R @ nr / np.linalg.norm(R @ nr)
                for v in bx:
                    if zone[v]:
                        P[v] += pas * d
        if not changed:
            break
        # lissage dans la zone, déplacement plafonné par rapport à la base
        D = P - P0
        Dz = D.copy()
        Dz[zone] = spsolve((L[idx][:, idx] + 1e-6 * diags(np.ones(len(idx)))).tocsc(), D[idx] * 0 + D[idx])
        P = P0 + np.clip(Dz, -cap, cap) if False else P0 + Dz
        n = np.linalg.norm(P - P0, axis=1)
        over = n > cap
        P[over] = P0[over] + (P - P0)[over] * (cap / n[over, None])
    return P
