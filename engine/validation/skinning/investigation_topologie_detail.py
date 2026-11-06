"""Détail topologique de Maria : sommets dupliqués à la même position, composantes en double, effet d'une soudure
(fusion des sommets de position identique), boucles de frontière et distance aux sept triangles.

Ce script ne modifie pas le moteur. La soudure est une expérience de diagnostic : elle sert à savoir si les
frontières proviennent de coutures non soudées, et non à produire un maillage corrigé.
"""
import importlib.util
import json
import os
from collections import Counter

import numpy as np
import scipy.sparse as sp
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SORTIE = os.path.join(RACINE, "docs", "rapports", "skinning", "topologie")
MECA = os.path.join(RACINE, "docs", "rapports", "skinning", "maria_retournements", "mecanisme_retournements.json")


def charger(nom):
    spec = importlib.util.spec_from_file_location(nom, os.path.join(HERE, nom + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


CMP = charger("investigation_comparaison")


def composantes(N, A):
    G = sp.coo_matrix((np.ones(len(A)), (A[:, 0], A[:, 1])), shape=(N, N))
    return connected_components(G, directed=False)


def frontieres(tris):
    e = np.sort(np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]]), axis=1)
    u, cnt = np.unique(e, axis=0, return_counts=True)
    return u, cnt


if __name__ == "__main__":
    os.makedirs(SORTIE, exist_ok=True)
    M = CMP.charger_morph("maria")
    rest, tris, A, W, N = M["rest"], M["tris"], M["A"], M["W"], M["N"]
    res = {}

    # 1. sommets à position identique
    arbre = cKDTree(rest)
    paires = arbre.query_pairs(1e-9)
    res["paires_sommets_position_identique_1e-9"] = len(paires)
    nc, comp = composantes(N, A)
    inter = sum(1 for i, j in paires if comp[i] != comp[j])
    res["paires_identiques_entre_composantes_differentes"] = int(inter)
    # poids identiques pour les paires dupliquées ?
    if paires:
        pa = np.array(list(paires))
        dW = np.abs(W[pa[:, 0]] - W[pa[:, 1]]).max()
        res["ecart_max_poids_entre_paires_identiques"] = float(dW)
        res["sommets_impliques"] = int(len(np.unique(pa)))

    # 2. composantes dupliquées : même nombre de sommets, arêtes et faces, et même position
    tailles = {}
    for c in range(nc):
        vs = np.where(comp == c)[0]
        tailles.setdefault((len(vs), int((np.isin(A[:, 0], vs)).sum()), int(np.isin(tris[:, 0], vs).sum())), []).append(c)
    dup = {str(k): v for k, v in tailles.items() if len(v) > 1}
    res["groupes_composantes_identiques_V_E_F"] = {str(k): v for k, v in dup.items()}
    res["composantes_dans_groupes_identiques"] = int(sum(len(v) for v in dup.values()))
    # vérification : positions identiques entre deux composantes d'un même groupe
    verif = []
    for k, cs in list(dup.items())[:6]:
        a_, b_ = cs[0], cs[1]
        pa_ = rest[np.where(comp == a_)[0]]
        pb_ = rest[np.where(comp == b_)[0]]
        # distance symétrique : chaque sommet de a a un sommet de b à moins de 1e-9 ?
        d, _ = cKDTree(pb_).query(pa_)
        verif.append({"groupe": k, "composantes": [int(a_), int(b_)], "distance_max_positions": float(d.max()),
                      "distance_moyenne_positions": float(d.mean())})
    res["verification_positions_groupes"] = verif

    # 3. soudure diagnostique : fusion des sommets à position identique
    parent = np.arange(N)

    def trouver(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for i, j in paires:
        ri, rj = trouver(i), trouver(j)
        if ri != rj:
            parent[rj] = ri
    racines = np.array([trouver(i) for i in range(N)])
    uniq, inv = np.unique(racines, return_inverse=True)
    tris_s = inv[tris]
    # supprimer faces dégénérées après fusion
    ok = (tris_s[:, 0] != tris_s[:, 1]) & (tris_s[:, 1] != tris_s[:, 2]) & (tris_s[:, 0] != tris_s[:, 2])
    tris_s = tris_s[ok]
    # arêtes et frontières après soudure
    e_s = np.sort(np.concatenate([tris_s[:, [0, 1]], tris_s[:, [1, 2]], tris_s[:, [2, 0]]]), axis=1)
    u, cnt = np.unique(e_s, axis=0, return_counts=True)
    Ns = len(uniq)
    G2 = sp.coo_matrix((np.ones(len(u)), (u[:, 0], u[:, 1])), shape=(Ns, Ns))
    nc2, _ = connected_components(G2, directed=False)
    res["soudure_diagnostique"] = {
        "sommets_avant": int(N), "sommets_apres": int(Ns), "faces_avant": int(len(tris)), "faces_apres": int(len(tris_s)),
        "aretes_frontiere_avant": int((frontieres(tris)[1] == 1).sum()),
        "aretes_frontiere_apres": int((cnt == 1).sum()), "aretes_non_variete_apres": int((cnt > 2).sum()),
        "composantes_apres": int(nc2),
        "surface_fermee_apres": bool((cnt == 1).sum() == 0 and (cnt > 2).sum() == 0),
    }
    print("soudure", res["soudure_diagnostique"], flush=True)

    # 4. frontières : position par rapport aux articulations et aux sept triangles
    u0, c0 = frontieres(tris)
    fr = u0[c0 == 1]
    bord_v = np.unique(fr)
    hd = M["hipd"]
    centres = {"hanche_G": M["cG"], "hanche_D": M["cD"], "genou_G": M["kG"], "genou_D": M["kD"]}
    dist_art = {k: np.linalg.norm(rest[bord_v] - c, axis=1) / hd for k, c in centres.items()}
    res["frontieres_distance_articulations_hipd"] = {
        k: {"min": float(v.min()), "mediane": float(np.median(v)), "n_sous_0_5": int((v < 0.5).sum())}
        for k, v in dist_art.items()}
    sept = sorted({tuple(s) for s in json.load(open(MECA, encoding="utf-8"))["sept_triangles"]} if False else
                  {tuple(o["triangle"]) for o in json.load(open(MECA, encoding="utf-8"))["triangles"]})
    sommets7 = sorted({v for s in sept for v in s})
    res["sept_triangles"] = [list(s) for s in sept]
    # distance en anneaux (graphe) des sept triangles à la frontière
    from collections import deque
    voisins = [[] for _ in range(N)]
    for a_, c_ in A:
        voisins[a_].append(c_)
        voisins[c_].append(a_)
    dist = np.full(N, -1)
    fil = deque(bord_v.tolist())
    for v in bord_v:
        dist[v] = 0
    while fil:
        u_ = fil.popleft()
        for v in voisins[u_]:
            if dist[v] < 0:
                dist[v] = dist[u_] + 1
                fil.append(v)
    res["sept_triangles_anneaux_jusqu_frontiere"] = {str(v): int(dist[v]) for v in sommets7}
    res["sept_triangles_composante"] = sorted({int(comp[v]) for v in sommets7})
    res["sept_triangles_composantes_en_double"] = {int(c): [int(x) for x in cs] for k, cs in dup.items()
                                                  for c in cs if any(comp[v] == c for v in sommets7)}
    res["sept_triangles_distance_frontiere_hipd"] = {str(v): float(np.min(np.linalg.norm(rest[bord_v] - rest[v], axis=1)) / hd)
                                                    for v in sommets7}
    # 5. connexions pelvis–cuisses (arêtes entre régions)
    labs = CMP.regions(M)
    rel = Counter()
    for a_, c_ in A:
        la, lc = labs[a_], labs[c_]
        if la != lc:
            rel[tuple(sorted((la, lc)))] += 1
    res["connexions_entre_regions_aretes"] = {"|".join(k): int(v) for k, v in rel.most_common()}

    with open(os.path.join(SORTIE, "topologie_maria_detail.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print({k: res[k] for k in ["paires_sommets_position_identique_1e-9", "paires_identiques_entre_composantes_differentes",
                              "composantes_dans_groupes_identiques", "sept_triangles_composante",
                              "sept_triangles_anneaux_jusqu_frontiere"]}, flush=True)
    print("ECRIT", flush=True)
