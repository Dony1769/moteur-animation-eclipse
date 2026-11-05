"""Skinning à quaternions duaux (Kavan, Collins, Žára, O'Sullivan, « Geometric Skinning with
Approximate Dual Quaternion Blending », ACM TOG 2008 ; source officielle : https://users.cs.utah.edu/~ladislav/dq/).

Convention : quaternions au format scalaire en dernier (x, y, z, w), comme scipy.

Entrées :
- rest (N,3) : sommets au repos ;
- W (N,B) : poids de peau (lignes de somme 1) ;
- parent (B,) : indice du parent de chaque os, -1 pour la racine ;
- h (B,3) : tête de chaque os au repos (pivot de l'os) ;
- R (B,3,3) : rotation locale de chaque os autour de sa tête (identité au repos).

Transformation globale : G_b = G_p · R_b ; t_b = G_p (h_b − h_p) + t_p (repos : G = I, t_b = h_b).
Transformation de peau : x ↦ G_b x + d_b, avec d_b = t_b − G_b h_b.
"""
import numpy as np
from scipy.spatial.transform import Rotation as Rot


def qmul(a, b):
    """Produit de quaternions (x,y,z,w), broadcastable."""
    ax, ay, az, aw = np.moveaxis(a, -1, 0)
    bx, by, bz, bw = np.moveaxis(b, -1, 0)
    return np.stack([
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    ], axis=-1)


def conj(q):
    return q * np.array([-1.0, -1.0, -1.0, 1.0])


def rotation_fk(parent, h, R):
    """Transformations globales G (B,3,3) et t (B,3) par parcours dans l'ordre (parent avant enfant)."""
    B = len(parent)
    G = np.zeros((B, 3, 3)); t = np.zeros((B, 3))
    for b in range(B):
        p = parent[b]
        if p < 0:
            G[b] = R[b]; t[b] = h[b]
        else:
            G[b] = G[p] @ R[b]
            t[b] = G[p] @ (h[b] - h[p]) + t[p]
    return G, t


def skin_transforms(parent, h, R):
    """Pour chaque os : rotation G_b et translation d_b de la transformation de peau."""
    G, t = rotation_fk(parent, h, R)
    d = np.zeros_like(t)
    for b in range(len(parent)):
        d[b] = t[b] - G[b] @ h[b]
    return G, d


def dqs(rest, W, G, d):
    """Skinning à quaternions duaux. Renvoie (N,3) sommets posés."""
    q = Rot.from_matrix(G).as_quat()                       # (B,4) réel
    # dual : 0.5 * (t, 0) ⊗ q, où t = d (translation de la transformation de peau)
    tq = np.concatenate([d, np.zeros((len(d), 1))], axis=1)
    dual_b = 0.5 * qmul(tq, q)                             # (B,4)
    N, B = W.shape
    # référence de signe : os de poids maximal par sommet
    ref = np.argmax(W, axis=1)
    qref = q[ref]                                          # (N,4)
    real = np.zeros((N, 4)); dual = np.zeros((N, 4))
    for b in range(B):
        w = W[:, b]
        if not np.any(w > 0):
            continue
        s = np.sign(np.einsum("ij,ij->i", q[b][None, :].repeat(N, 0), qref))
        s[s == 0] = 1.0
        real += (w * s)[:, None] * q[b][None, :]
        dual += (w * s)[:, None] * dual_b[b][None, :]
    n = np.linalg.norm(real, axis=1, keepdims=True)
    real /= n; dual /= n
    # translation = 2 * (dual ⊗ conj(real)) vecteur
    tr = 2.0 * qmul(dual, conj(real))[:, :3]
    v = Rot.from_quat(real).apply(rest)
    return v + tr


def coude_rigide(rest, W, parent, h, indice_bras, R_avant):
    """Utilitaire : R (B,3,3) identité sauf l'os avant-bras (indice_bras) tourné de R_avant."""
    B = len(parent)
    R = np.tile(np.eye(3), (B, 1, 1))
    R[indice_bras] = R_avant
    return R
