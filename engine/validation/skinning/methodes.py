"""Méthodes de skinning comparées sur des entrées identiques (phase 4).

  LBS     : somme pondérée des transformations (référence : c'est la formule du skinning de Blender et de Puppeteer,
            engine animation/model.py, _linear_blend_skinning).
  DQS     : Dual Quaternion Skinning (Kavan, Collins, Žára, O'Sullivan, « Geometric Skinning with Approximate Dual
            Quaternion Blending », ACM TOG 2008). Hémisphère alignée sur l'os dominant, normalisation du dual.
  HYBRIDE : mélange par sommet p = (1 - a) LBS + a DQS. Deux règles de a, toutes deux fixées avant la mesure :
            « global » (a = 0,5 partout) et « angle » (a = min(1, angle relatif maximal entre les os du sommet / 45°)).

Entrées communes : pos (N,3) positions au repos en mètres monde ; W_idx (N,K) indices d'os (-1 = vide) ;
W_w (N,K) poids bruts ; T (J,4,4) = matrice de pose monde @ inverse(matrice de repos monde de l'os).
Aucune méthode n'est choisie par un seuil : les comparaisons sont des mesures.
"""
import numpy as np


def decomposer(T):
    """Retourne (R, t, erreur_orthonormalité, det) pour chaque transformation d'os. Une échelle non unitaire
    serait signalée : les méthodes par quaternions supposent des transformations rigides."""
    R = T[:, :3, :3]
    t = T[:, :3, 3]
    orth = float(np.abs(np.einsum("jab,jcb->jac", R, R) - np.eye(3)).max())
    det = np.linalg.det(R)
    return R, t, orth, det


def quat_depuis_matrice(R):
    """(J,3,3) -> (J,4) quaternions unitaires (w, x, y, z), méthode de Shepperd."""
    Q = np.zeros((R.shape[0], 4))
    for j, m in enumerate(R):
        tr = m[0, 0] + m[1, 1] + m[2, 2]
        if tr > 0:
            s = np.sqrt(tr + 1.0) * 2
            q = [0.25 * s, (m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s]
        elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
            s = np.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
            q = [(m[2, 1] - m[1, 2]) / s, 0.25 * s, (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s]
        elif m[1, 1] > m[2, 2]:
            s = np.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
            q = [(m[0, 2] - m[2, 0]) / s, (m[0, 1] + m[1, 0]) / s, 0.25 * s, (m[1, 2] + m[2, 1]) / s]
        else:
            s = np.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
            q = [(m[1, 0] - m[0, 1]) / s, (m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s, 0.25 * s]
        q = np.array(q)
        if q[0] < 0:
            q = -q
        Q[j] = q / np.linalg.norm(q)
    return Q


def qmul(a, b):
    """Produit de quaternions (w, x, y, z) vectorisé sur les premières dimensions."""
    w1, x1, y1, z1 = np.moveaxis(a, -1, 0)
    w2, x2, y2, z2 = np.moveaxis(b, -1, 0)
    return np.stack([
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
    ], axis=-1)


def _valides(W_idx, W_w):
    valide = W_idx >= 0
    ids = np.where(valide, W_idx, 0)
    w = np.where(valide, W_w, 0.0)
    return ids, w


def lbs(pos, W_idx, W_w, R, t):
    """Skinning linéaire : somme_k w_k (R_k p + t_k). Identique à Blender ARMATURE (poids non renormalisés)."""
    ids, w = _valides(W_idx, W_w)
    out = np.zeros_like(pos)
    for k in range(ids.shape[1]):
        Rk = R[ids[:, k]]
        tk = t[ids[:, k]]
        out += w[:, k, None] * (np.einsum("nab,nb->na", Rk, pos) + tk)
    return out


def dqs(pos, W_idx, W_w, Q, t):
    """Dual Quaternion Skinning (Kavan 2008). Q (J,4) quaternions de rotation, t (J,3) translations."""
    ids, w = _valides(W_idx, W_w)
    N, K = ids.shape
    # quaternion dual de chaque os : D = 1/2 (0, t) Q
    tq = np.concatenate([np.zeros((t.shape[0], 1)), t], axis=1)
    D = 0.5 * qmul(tq, Q)
    Qn = Q[ids]                       # (N,K,4)
    Dn = D[ids]
    piv = np.argmax(w, axis=1)
    qp = Qn[np.arange(N), piv]        # quaternion de l'os dominant
    dot = np.einsum("nkc,nc->nk", Qn, qp)
    sg = np.where(dot < 0, -1.0, 1.0)  # même hémisphère que l'os dominant
    Qn = Qn * sg[..., None]
    Dn = Dn * sg[..., None]
    qr = np.einsum("nk,nkc->nc", w, Qn)
    qd = np.einsum("nk,nkc->nc", w, Dn)
    n = np.linalg.norm(qr, axis=1, keepdims=True)
    qrn = qr / n
    # normalisation du dual : retirer la composante parallèle à qr (condition de quaternion dual unitaire)
    qd2 = qd / n - (np.sum(qr * qd, axis=1, keepdims=True) / n ** 2) * qrn
    u = qrn[:, 1:]
    wq = qrn[:, :1]
    uxp = np.cross(u, pos)
    rot = pos + 2.0 * wq * uxp + 2.0 * np.cross(u, uxp)
    qc = qrn * np.array([1.0, -1.0, -1.0, -1.0])
    trans = 2.0 * qmul(qd2, qc)[:, 1:]
    return rot + trans


def angle_relatif_max(W_idx, W_w, Q):
    """Par sommet : angle maximal (radians) entre le quaternion de l'os dominant et ceux des autres os influents."""
    ids, w = _valides(W_idx, W_w)
    N = ids.shape[0]
    piv = np.argmax(w, axis=1)
    qp = Q[ids[np.arange(N), piv]]
    Qn = Q[ids]
    d = np.clip(np.abs(np.einsum("nkc,nc->nk", Qn, qp)), 0.0, 1.0)
    theta = 2.0 * np.arccos(d)
    theta = np.where(w > 1e-6, theta, 0.0)
    return theta.max(axis=1)


def repere_rigide(W_idx, W_w, bones_rest_monde, pose_monde):
    """Rotation locale mélangée par sommet, Mv (N,3,3) = somme_k w_k R_k. Elle sert de repère commun à toutes les
    méthodes pour dire « la surface a suivi son mouvement rigide » : un polygone tourné de 120° change de signe de
    produit scalaire avec sa normale de repos sans être retourné (entrée 147)."""
    T = pose_monde @ np.linalg.inv(bones_rest_monde)
    R = T[:, :3, :3]
    ids, w = _valides(W_idx, W_w)
    return np.einsum("nk,nkab->nab", w, R[ids])


def hybride(pos_lbs, pos_dqs, a):
    """Mélange par sommet ; a est un scalaire ou un tableau (N,)."""
    a = np.asarray(a, dtype=np.float64)
    if a.ndim == 1:
        a = a[:, None]
    return (1.0 - a) * pos_lbs + a * pos_dqs


def calculer_toutes(pos, W_idx, W_w, bones_rest_monde, pose_monde, angle_ref=np.radians(45.0)):
    """Calcule LBS, DQS et les deux hybrides pour une pose. Retourne (dict de positions, diagnostics)."""
    rest_inv = np.linalg.inv(bones_rest_monde)
    T = pose_monde @ rest_inv
    R, t, orth, det = decomposer(T)
    Q = quat_depuis_matrice(R)
    theta = angle_relatif_max(W_idx, W_w, Q)
    a_angle = np.clip(theta / angle_ref, 0.0, 1.0)
    p_lbs = lbs(pos, W_idx, W_w, R, t)
    p_dqs = dqs(pos, W_idx, W_w, Q, t)
    sortie = {
        "LBS": p_lbs,
        "DQS": p_dqs,
        "HYBRIDE_global": hybride(p_lbs, p_dqs, 0.5),
        "HYBRIDE_angle": hybride(p_lbs, p_dqs, a_angle),
    }
    diag = {"erreur_orthonormalite": orth, "det_min": float(det.min()), "det_max": float(det.max()),
            "part_sommets_angle_gt_0": float(np.mean(a_angle > 0))}
    return sortie, diag
