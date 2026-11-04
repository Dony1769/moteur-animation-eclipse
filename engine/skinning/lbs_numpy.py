"""Skinning linéaire (LBS) et mesures d'étirement en numpy, à partir des données exportées (exporter_poids.py).

x'_i = Σ_b W_ib · (M_ab · x_i)   où M_ab = matrice de pose de l'os b à l'angle a (repère armature).
Mesures : étirement des arêtes (longueur pose / longueur repos) : max, min, écart p99.
Témoin : à 0° la déformation est l'identité (étirement = 1).
"""
import numpy as np


def deformer(rest, W, M):
    """Sommets déformés en LBS pour une matrice par os M (B,4,4)."""
    R = M[:, :3, :3]; t = M[:, :3, 3]
    # pour chaque sommet : Σ_b W_ib (R_b x_i + t_b)
    tr = np.einsum("bij,nj->nbi", R, rest) + t[None]
    return np.einsum("nb,nbi->ni", W, tr)


def etirements(pts, rest, aretes):
    lr = np.linalg.norm(rest[aretes[:, 0]] - rest[aretes[:, 1]], axis=1)
    lp = np.linalg.norm(pts[aretes[:, 0]] - pts[aretes[:, 1]], axis=1)
    ok = lr > 0
    r = lp[ok] / lr[ok]
    return {"max": float(r.max()), "min": float(r.min()), "p99_ecart": float(np.quantile(np.abs(r - 1), 0.99))}


def mesurer(data, ia, W=None):
    W = data["W"] if W is None else W
    pts = deformer(data["rest"], W, data["M"][ia])
    return etirements(pts, data["rest"], data["aretes"])
