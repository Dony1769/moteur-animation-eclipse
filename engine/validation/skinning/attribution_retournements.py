"""Où sont les polygones retournés ? Attribution par hauteur, os dominant et poids (maillage de base, mètres monde).

Usage : python3 engine/validation/skinning/attribution_retournements.py POSES.npz POSE [METHODE]
Exemple : ... POSES.npz L_flex120 LBS
"""
import collections
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import methodes as M  # noqa: E402
import mesures as Ms  # noqa: E402


def main():
    npz, pose = sys.argv[1], sys.argv[2]
    methode = sys.argv[3] if len(sys.argv) > 3 else "LBS"
    d = np.load(npz)
    rest, W_idx, W_w, B = d["rest_monde"], d["W_idx"], d["W_w"], d["bones_rest_monde"]
    noms = [str(n) for n in d["noms_os"]]
    b, tot = d["b_boucle"], d["b_tot"]
    pos_m, _ = M.calculer_toutes(rest, W_idx, W_w, B, d[pose + "__os"])
    pos = pos_m[methode]
    debut = Ms._debuts(tot)
    Mv = M.repere_rigide(W_idx, W_w, B, d[pose + "__os"])
    masque, _ = Ms.masque_retournes(pos, rest, b, tot, Mv)
    flip = np.where(masque)[0]
    print(f"POSE {pose} {methode} polygones_retournes {len(flip)} / {len(tot)}")
    if len(flip) == 0:
        return
    # centres des polygones retournés (au repos) : hauteur et os dominants
    cent = np.array([rest[b[debut[p]:debut[p] + tot[p]]].mean(axis=0) for p in flip])
    print("HAUTEUR_m min/median/max", np.round([cent[:, 2].min(), np.median(cent[:, 2]), cent[:, 2].max()], 3))
    print("X_m min/median/max", np.round([cent[:, 0].min(), np.median(cent[:, 0]), cent[:, 0].max()], 3))
    # os dominant de chaque sommet du polygone : poids moyen par os
    dom = collections.Counter()
    for p in flip:
        for v in b[debut[p]:debut[p] + tot[p]]:
            k = int(np.argmax(W_w[v]))
            j = W_idx[v, k]
            dom[noms[j] if j >= 0 else "aucun"] += 1
    print("OS_DOMINANT_SOMMETS", dom.most_common(8))
    # répartition par tranches de hauteur
    tranches = [0.6, 0.8, 0.9, 1.0, 1.2, 1.4]
    hist = np.histogram(cent[:, 2], bins=tranches)[0]
    print("TRANCHES_HAUTEUR", list(zip(tranches[:-1], tranches[1:], hist.tolist())))


if __name__ == "__main__":
    main()
