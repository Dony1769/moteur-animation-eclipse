"""Phase 5 : consolidation de la comparaison régionale (anciennes mesures conservées dans regionale.json).

1. Vérification du BFS : la distance aux zones mixtes calculée par distance_multi (numpy) est comparée à un BFS
   indépendant écrit avec collections.deque sur la liste d'adjacence.
2. Trois classes d'arêtes, séparées : mixte (les deux sommets mixtes), entre sommets purs et mixtes, entièrement
   à poids purs (subdivisée en « propagée » si à 1–3 anneaux d'un sommet mixte, « éloignée » sinon).
3. Pour chaque classe et chaque morphologie : nombre d'arêtes×poses, régressions, % amélioration, % régression,
   % régression pondérée par la longueur, % régression pondérée par l'aire initiale moyenne des triangles adjacents,
   percentiles 50/90/95/99 non pondérés et pondérés par la longueur.
Seuils inchangés : régression > 0,05 ; amélioration < −0,02 ; arêtes ≥ 5 mm au repos.
"""
import json
import os
from collections import deque

import numpy as np
import scipy.sparse as sp

import investigation_regionale as R

SORTIE = os.path.join(R.RACINE, "docs", "rapports", "skinning", "regionale")


def bfs_independant(N, A, sources):
    voisins = [[] for _ in range(N)]
    for a, c in A:
        voisins[a].append(c)
        voisins[c].append(a)
    dist = [-1] * N
    file_ = deque()
    for s in sources:
        dist[s] = 0
        file_.append(s)
    while file_:
        u = file_.popleft()
        for v in voisins[u]:
            if dist[v] < 0:
                dist[v] = dist[u] + 1
                file_.append(v)
    return np.array([d if d >= 0 else np.inf for d in dist], dtype=float)


def pct(x, w=None):
    if len(x) == 0:
        return None
    if w is None:
        return {f"p{p}": float(np.quantile(x, p / 100)) for p in (50, 90, 95, 99)}
    return {f"p{p}": R.quantile_pondere(x, w, p / 100) for p in (50, 90, 95, 99)}


if __name__ == "__main__":
    os.makedirs(SORTIE, exist_ok=True)
    out = {"verification_BFS": {}, "classes": {}, "anciennes_mesures": "regionale.json"}
    for m in R.MORPHS:
        M = R.CMP.charger_morph(m)
        rest, A, tris, W, N = M["rest"], M["A"], M["tris"], M["W"], M["N"]
        a, c = A[:, 0], A[:, 1]
        pur = W.max(1) > 1 - 1e-6
        src = np.where(~pur)[0]
        G = sp.coo_matrix((np.ones(len(A)), (a, c)), shape=(N, N)).tocsr()
        G = G + G.T
        d_num = R.distance_multi(G, src, N)
        d_ind = bfs_independant(N, A, src)
        ecart = float(np.max(np.abs(np.where(np.isinf(d_num) & np.isinf(d_ind), 0, d_num - d_ind))))
        out["verification_BFS"][m] = {"sommets_sources_mixtes": int(len(src)), "ecart_max_numpy_vs_deque": ecart,
                                      "sommets_non_atteints": int(np.isinf(d_ind).sum())}
        print(m, "BFS écart max", ecart, flush=True)

        # aire initiale moyenne des triangles adjacents à chaque arête
        aire0 = 0.5 * np.linalg.norm(np.cross(rest[tris[:, 1]] - rest[tris[:, 0]], rest[tris[:, 2]] - rest[tris[:, 0]]), axis=1)
        cle = {tuple(sorted(e)): i for i, e in enumerate(A)}
        somme = np.zeros(len(A))
        nb = np.zeros(len(A))
        for ti, t in enumerate(tris):
            for i, j in [(0, 1), (1, 2), (2, 0)]:
                k = cle.get(tuple(sorted((t[i], t[j]))))
                if k is not None:
                    somme[k] += aire0[ti]
                    nb[k] += 1
        aire_arete = somme / np.maximum(nb, 1)

        lr = np.linalg.norm(rest[a] - rest[c], axis=1)
        ok5 = lr >= 0.005
        mix_a, mix_c = ~pur[a], ~pur[c]
        dmin = np.minimum(d_ind[a], d_ind[c])
        classe = np.where(mix_a & mix_c, "mixte",
                          np.where(mix_a ^ mix_c, "pur_mixte",
                                   np.where(dmin <= 3, "pure_propagee_1_3", "pure_eloignee")))
        cls_noms = ["mixte", "pur_mixte", "pure_propagee_1_3", "pure_eloignee"]
        acc = {k: {"exc": [], "lr": [], "aire": []} for k in cls_noms}
        for nom in R.CMP.POSES:
            pm = R.CMP.pose_de(M, nom)
            lbs, sq, Mv, Rm, t = R.CMP.evaluer(M, pm)
            exc = (np.linalg.norm(sq[a] - sq[c], axis=1) - np.linalg.norm(lbs[a] - lbs[c], axis=1)) / np.maximum(lr, 1e-12)
            for k in cls_noms:
                sel = (classe == k) & ok5
                acc[k]["exc"].append(exc[sel])
                acc[k]["lr"].append(lr[sel])
                acc[k]["aire"].append(aire_arete[sel])
        res = {}
        for k in cls_noms:
            exc = np.concatenate(acc[k]["exc"]); l_ = np.concatenate(acc[k]["lr"]); ar = np.concatenate(acc[k]["aire"])
            n = len(exc)
            reg = exc > 0.05
            ame = exc < -0.02
            if n == 0:
                res[k] = {"aretes": 0}
                continue
            res[k] = {
                "aretes": int(n), "regressees": int(reg.sum()),
                "pourcentage_amelioration": float(ame.mean()),
                "pourcentage_regression": float(reg.mean()),
                "pourcentage_regression_ponderee_longueur": float((l_ * reg).sum() / l_.sum()),
                "pourcentage_regression_ponderee_aire": float((ar * reg).sum() / max(ar.sum(), 1e-300)),
                "pourcentage_amelioration_ponderee_longueur": float((l_ * ame).sum() / l_.sum()),
                "exc_percentiles": pct(exc),
                "exc_percentiles_ponderes_longueur": pct(exc, l_),
            }
        out["classes"][m] = res
        print(m, {k: (v.get("aretes"), round(v.get("pourcentage_regression", 0) or 0, 4)) for k, v in res.items()}, flush=True)

    with open(os.path.join(SORTIE, "regionale_v2.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print("ECRIT", flush=True)
