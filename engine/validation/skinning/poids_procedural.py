"""Poids procéduraux à partir des longueurs réelles des os (phase 4, étape 2).

Principe (aucune forme sculptée, aucun réglage par personnage) :
- chaque os k est un segment réel [tête_k, queue_k] extrait de l'armature (squelette_*.json, étape 1) ;
- sa largeur d'influence est σ_k = ALPHA × L_k, où L_k est la longueur réelle de l'os ;
- pour un os terminal (longueur non fiable, entrée 169), σ_k = ALPHA × L_parent (longueur du parent, réelle) ;
  l'influence est mesurée depuis le point de tête ;
- w_k(v) = exp(-(d_k(v) / σ_k)²), on garde les 4 plus fortes influences (comme les poids Blender), normalisées ;
- un sommet sans influence reçoit l'os le plus proche (jamais de poids nul).

ALPHA est UN coefficient global, identique pour les trois morphologies ; il n'est pas réglé sur un personnage.
"""
import json

import numpy as np


def segments_depuis_squelette(json_squelette, noms_os):
    """Retourne (tete, queue, σ_base, fiable) par os de noms_os, dans l'ordre des poids."""
    d = json.load(open(json_squelette, encoding="utf-8"))
    par = {o["nom"]: o for o in d["os"]}
    tetes, queues, longueurs, est_point = [], [], [], []
    for n in noms_os:
        if n not in par:
            raise KeyError(f"os {n} absent du squelette extrait ({json_squelette})")
        o = par[n]
        tetes.append(o["tete"])
        if o["longueur_fiable"]:
            queues.append(o["queue"])
            longueurs.append(o["longueur"])
            est_point.append(False)
        else:
            # Os terminal : pas de segment réel ; on utilise la longueur du parent (réelle, fiable).
            queues.append(o["tete"])
            p = par.get(o["parent"]) if o["parent"] else None
            if p is None or not p["longueur_fiable"]:
                raise ValueError(f"os terminal {n} sans parent à longueur fiable")
            longueurs.append(p["longueur"])
            est_point.append(True)
    return (np.array(tetes, float), np.array(queues, float), np.array(longueurs, float), np.array(est_point))


def distance_segments(P, A, B, point):
    """Distance de chaque sommet P (N,3) à chaque segment [A_k, B_k] (J,3). Si point[k], distance à A_k."""
    AB = B - A
    nn = (AB * AB).sum(axis=1)
    nn = np.where(nn < 1e-12, 1.0, nn)
    d = np.empty((P.shape[0], A.shape[0]))
    for k in range(A.shape[0]):
        if point[k]:
            d[:, k] = np.linalg.norm(P - A[k], axis=1)
            continue
        tk = np.clip(((P - A[k]) @ AB[k]) / nn[k], 0.0, 1.0)
        proj = A[k] + tk[:, None] * AB[k]
        d[:, k] = np.linalg.norm(P - proj, axis=1)
    return d


def poids_procedural(rest, tetes_queues, alpha, max_influences=4):
    """Retourne (W_idx, W_w) de forme (N, 4). tetes_queues = (tete, queue, longueur, est_point)."""
    A, B, L, point = tetes_queues
    sigma = alpha * L
    d = distance_segments(rest, A, B, point)
    w = np.exp(-(d / sigma[None, :]) ** 2)
    idx = np.argsort(-w, axis=1)[:, :max_influences]
    W_w = np.take_along_axis(w, idx, axis=1)
    somme = W_w.sum(axis=1, keepdims=True)
    # Sommet sans influence numérique : os le plus proche.
    vide = (somme[:, 0] <= 1e-300)
    if vide.any():
        proche = np.argmin(d[vide], axis=1)
        idx[vide] = 0
        idx[vide, 0] = proche
        W_w[vide] = 0.0
        W_w[vide, 0] = 1.0
        somme = W_w.sum(axis=1, keepdims=True)
    W_w = W_w / somme
    return idx.astype(np.int64), W_w


if __name__ == "__main__":
    import sys
    rest = np.load(sys.argv[1])["rest_monde"]
    print("N", rest.shape)


def melange_pres_articulation(rest, W_idx_ref, W_w_ref, tetes_queues, noms_os, alpha, max_influences=4):
    """Variante BORNÉE : les poids procéduraux ne remplacent la référence que près des articulations.

    β(v) = max_j exp(-(d(v, tête_j) / (ALPHA × L_j))²) : influence d'une articulation j (tête d'un os de longueur
    réelle L_j, os non terminal). Résultat : W = (1 − β) W_ref + β W_proc, puis top-N normalisé.
    Loin de toute articulation β ≈ 0 : la référence Bone Heat est conservée à l'identique.
    """
    A, B, L, point = tetes_queues
    N, J = rest.shape[0], len(noms_os)
    # référence en matrice dense
    ref = np.zeros((N, J))
    np.add.at(ref, (np.arange(N)[:, None], W_idx_ref), W_w_ref)
    # procédural dense
    idx_p, w_p = poids_procedural(rest, tetes_queues, alpha, max_influences=J)
    proc = np.zeros((N, J))
    np.add.at(proc, (np.arange(N)[:, None], idx_p), w_p)
    # β : distance aux têtes des os non terminaux (articulations réelles)
    beta = np.zeros(N)
    for j in range(J):
        if point[j]:
            continue
        dj = np.linalg.norm(rest - A[j], axis=1)
        beta = np.maximum(beta, np.exp(-(dj / (alpha * L[j])) ** 2))
    mix = (1 - beta)[:, None] * ref + beta[:, None] * proc
    idx = np.argsort(-mix, axis=1)[:, :max_influences]
    w = np.take_along_axis(mix, idx, axis=1)
    s = w.sum(axis=1, keepdims=True)
    s = np.where(s <= 1e-300, 1.0, s)
    return idx.astype(np.int64), (w / s)
