"""Expérience contrôlée : lissage des poids dans la bande de hanche, MÉTHODE INCHANGÉE (phase 4).

Hypothèse testée (écrite avant la mesure) : les étirements de pointe à l'entrejambe viennent d'une transition de poids
trop brusque entre les os de la cuisse et ceux du bassin. Un lissage des poids sur quelques itérations, limité à la
bande z 0,6-1,15 m, doit réduire l'étirement de pointe sans changer la méthode de déformation.

Protocole : pour chaque méthode (LBS puis DQS), on compare les poids d'origine et les poids lissés, sur les mêmes poses.
Tous les poids restent normalisés (somme 1) ; seuls les sommets de la bande sont modifiés.
Résultat écrit tel quel, favorable ou non.

Usage : python3 engine/validation/skinning/experience_poids_lissage.py POSES.npz SORTIE.json
"""
import json
import os
import sys

import numpy as np
import scipy.sparse as sp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import methodes as M  # noqa: E402
import mesures as Ms  # noqa: E402

BANDE = (0.6, 1.15)
LAMBDA = 0.5
ITERATIONS = 5
POSES = ["L_flex90", "L_flex120", "L_genou90", "L_combo_flex120_genou90", "R_flex120", "R_genou90"]


def densifier(W_idx, W_w, J):
    N = W_idx.shape[0]
    D = np.zeros((N, J))
    for k in range(W_idx.shape[1]):
        m = W_idx[:, k] >= 0
        D[np.where(m)[0], W_idx[m, k]] += W_w[m, k]
    return D


def creuser(D):
    K = int((D > 0).sum(1).max())
    N = D.shape[0]
    idx = -np.ones((N, K), dtype=np.int64)
    w = np.zeros((N, K))
    for i in range(N):
        js = np.where(D[i] > 0)[0]
        idx[i, :len(js)] = js
        w[i, :len(js)] = D[i, js]
    return idx, w


def lisser(D, rest, A):
    N = D.shape[0]
    z = rest[:, 2]
    dans = (z > BANDE[0]) & (z < BANDE[1])
    a, b = A[:, 0], A[:, 1]
    G = sp.coo_matrix((np.ones(2 * len(A)), (np.r_[a, b], np.r_[b, a])), shape=(N, N)).tocsr()
    deg = np.asarray(G.sum(1)).ravel()
    deg[deg == 0] = 1
    P = sp.diags(1.0 / deg) @ G
    X = D.copy()
    for _ in range(ITERATIONS):
        moy = P @ X
        X = np.where(dans[:, None], (1 - LAMBDA) * X + LAMBDA * moy, X)
        X = X / np.maximum(X.sum(1, keepdims=True), 1e-12)
    return X, int(dans.sum())


def main():
    npz, sortie = sys.argv[1], sys.argv[2]
    d = np.load(npz)
    rest, B = d["rest_monde"], d["bones_rest_monde"]
    W_idx, W_w = d["W_idx"], d["W_w"]
    J = B.shape[0]
    A = Ms.aretes(d["b_boucle"], d["b_tot"], len(rest))
    b, tot = d["b_boucle"], d["b_tot"]
    D0 = densifier(W_idx, W_w, J)
    D1, nb = lisser(D0, rest, A)
    i0, w0 = creuser(D0)
    i1, w1 = creuser(D1)
    print("sommets lissés", nb, "poids max par sommet avant/après", i0.shape[1], i1.shape[1])
    resultats = {"bande_z_m": BANDE, "lambda": LAMBDA, "iterations": ITERATIONS, "sommets_lisses": nb, "poses": {}}
    for pose in POSES:
        pm = d[pose + "__os"]
        entree = {}
        for nom, (ii, ww) in {"poids_origine": (i0, w0), "poids_lisses": (i1, w1)}.items():
            Mv = M.repere_rigide(ii, ww, B, pm)
            pos_m, _ = M.calculer_toutes(rest, ii, ww, B, pm)
            for m in ["LBS", "DQS"]:
                mes = Ms.mesurer(pos_m[m], rest, b, tot, A, Mv=Mv)
                entree[f"{m}|{nom}"] = {k: mes[k] for k in ["etirement_max", "etirement_p99", "sommets_aberrants",
                                                          "variation_volume_relative", "polygones_retournes"]}
        resultats["poses"][pose] = entree
        print(pose, {k: (round(v["etirement_max"], 3), v["polygones_retournes"], round(v["variation_volume_relative"], 4))
                     for k, v in entree.items()}, flush=True)
    with open(sortie, "w") as f:
        json.dump(resultats, f, indent=2, ensure_ascii=False)
    print("EXPERIENCE_OK", sortie)


if __name__ == "__main__":
    main()
