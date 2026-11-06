"""Audit topologique des trois maillages (Maria, HBM masculin, HBM féminin) et analyse du système linéaire de SQ.

Phase 1 (audit) : composantes connexes de la graphe d'arêtes, sommets/arêtes/faces par composante, sommets non
   référencés, faces dégénérées ou dupliquées, boucles de frontière et leur taille, composantes isolées, distance
   entre composantes, étiquette anatomique dominante de chaque composante, poids nuls.
Phase 2 (solveur) : la matrice de SQ est M = diag(deg + λ) − Adj (fonction solve_fixe) : aucune condition de
   frontière explicite ; ancre λ uniforme vers LBS. On vérifie la structure par blocs, le rang et le conditionnement
   par composante, et l'indépendance des solutions entre composantes.
Phase 5 (comparaison) : mêmes mesures sur les trois morphologies ; connexions pelvis–cuisses ; frontières près des
   articulations.
Aucun maillage n'est modifié ici.
"""
import importlib.util
import json
import os
from collections import Counter

import numpy as np
import scipy.sparse as sp
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import eigsh, spsolve
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SORTIE = os.path.join(RACINE, "docs", "rapports", "skinning", "topologie")


def charger(nom):
    spec = importlib.util.spec_from_file_location(nom, os.path.join(HERE, nom + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


CMP = charger("investigation_comparaison")
MORPHS = ["masculin", "feminin", "maria"]


def boucles_de_bord(tris, N):
    """Arêtes de frontière et leurs boucles (composantes du graphe des arêtes de frontière)."""
    e = np.sort(np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]]), axis=1)
    u, cnt = np.unique(e, axis=0, return_counts=True)
    fr = u[cnt == 1]
    surf = u[cnt >= 2]
    nonvar = int((cnt > 2).sum())
    if len(fr) == 0:
        return fr, np.zeros(N, int), 0, nonvar, surf
    G = sp.coo_matrix((np.ones(len(fr)), (fr[:, 0], fr[:, 1])), shape=(N, N))
    nb, lab = connected_components(G, directed=False)
    vus = np.unique(fr)
    nb_boucles = len(np.unique(lab[vus]))
    return fr, lab, nb_boucles, nonvar, surf


def audit(M, nom):
    rest, tris, A, W, N = M["rest"], M["tris"], M["A"], M["W"], M["N"]
    labs = CMP.regions(M)
    hip = [M["cG"], M["cD"]]
    knee = [M["kG"], M["kD"]]
    hd = M["hipd"]
    res = {"morphologie": nom, "N_sommets": int(N), "N_faces": int(len(tris)), "N_aretes": int(len(A))}

    # sommets non référencés
    ref = np.zeros(N, bool)
    ref[tris.ravel()] = True
    res["sommets_non_references"] = int((~ref).sum())

    # faces dégénérées / dupliquées
    aire = 0.5 * np.linalg.norm(np.cross(rest[tris[:, 1]] - rest[tris[:, 0]], rest[tris[:, 2]] - rest[tris[:, 0]]), axis=1)
    res["faces_repetition_indice"] = int(((tris[:, 0] == tris[:, 1]) | (tris[:, 1] == tris[:, 2]) | (tris[:, 0] == tris[:, 2])).sum())
    res["faces_aire_nulle_1e-12"] = int((aire < 1e-12).sum())
    res["faces_dupliquees"] = int(len(tris) - len({tuple(sorted(t)) for t in tris}))

    # composantes connexes (graphe des arêtes A, sommets référencés et non référencés)
    G = sp.coo_matrix((np.ones(len(A)), (A[:, 0], A[:, 1])), shape=(N, N))
    ncomp, comp = connected_components(G, directed=False)
    res["composantes_graphe_aretes"] = int(ncomp)
    tailles = np.bincount(comp)
    res["composantes_top10_tailles_sommets"] = sorted(tailles.tolist(), reverse=True)[:10]

    fr, blab, nb_boucles, nonvar, surf = boucles_de_bord(tris, N)
    res["aretes_frontiere"] = int(len(fr))
    res["aretes_non_variete"] = nonvar
    res["boucles_de_frontiere"] = int(nb_boucles)
    bord = np.zeros(N, bool)
    if len(fr):
        bord[fr.ravel()] = True
    res["sommets_frontiere"] = int(bord.sum())

    # par composante
    comps = []
    arbre_cache = {}
    for c in range(ncomp):
        vs = np.where(comp == c)[0]
        if len(vs) < 1:
            continue
        vref = vs[ref[vs]]
        mask_e = np.isin(A[:, 0], vs)
        ne = int(mask_e.sum())
        tr = tris[np.isin(tris[:, 0], vs)] if len(vref) else np.zeros((0, 3), int)
        nf = int(len(tr))
        bfr = fr[np.isin(fr[:, 0], vs)] if len(fr) else np.zeros((0, 2), int)
        boucles_c = int(len(np.unique(blab[bfr.ravel()]))) if len(bfr) else 0
        p = rest[vs]
        centre = p.mean(0)
        lab_c = Counter(labs[vs]).most_common(3)
        dhip = float(min(np.linalg.norm(centre - h) for h in hip) / hd)
        comps.append({"id": int(c), "sommets": int(len(vs)), "sommets_references": int(len(vref)),
                      "aretes": ne, "faces": nf, "aretes_frontiere": int(len(bfr)), "boucles": boucles_c,
                      "euler_V_E_F": int(len(vs) - ne + nf),
                      "bbox_min_m": p.min(0).round(4).tolist(), "bbox_max_m": p.max(0).round(4).tolist(),
                      "etendue_m": float(np.linalg.norm(p.max(0) - p.min(0))),
                      "centre_m": centre.round(4).tolist(), "distance_hanche_sur_hipd": dhip,
                      "labels_dominants": [[k, int(v)] for k, v in lab_c],
                      "poids_nuls_sommets": int((W[vs].sum(1) < 1e-9).sum())})
    res["composantes"] = comps
    res["composantes_sans_face"] = int(sum(1 for c in comps if c["faces"] == 0))
    res["composantes_avec_frontiere"] = int(sum(1 for c in comps if c["aretes_frontiere"] > 0))
    res["composantes_fermees"] = int(sum(1 for c in comps if c["aretes_frontiere"] == 0 and c["faces"] > 0))
    res["poids_nuls_total"] = int((W.sum(1) < 1e-9).sum())

    # distance entre composantes (plus proche sommet d'une autre composante)
    if ncomp > 1:
        arbre = cKDTree(rest)
        dmin = []
        grandes = [c["id"] for c in sorted(comps, key=lambda c: -c["faces"])[:8] if c["faces"] > 0]
        for c in grandes:
            vs = np.where(comp == c)[0]
            autres = np.where(comp != c)[0]
            d, _ = cKDTree(rest[autres]).query(rest[vs])
            dmin.append({"composante": int(c), "distance_min_autre_composante_hipd": float(d.min() / hd)})
        res["separation_composantes_principales"] = dmin

    # poids : sommets non référencés ou sans poids
    res["sommets_non_references_avec_poids"] = int(((~ref) & (W.sum(1) > 1e-9)).sum())
    return res, comp, ref, fr, blab, bord


def systeme_SQ(M, comp, ncomp_max=5):
    ncomp_total = int(comp.max()) + 1
    """Structure de M = diag(deg+λ) − Adj : blocs par composante, rang, conditionnement (λ = 0,1)."""
    A, N, rest = M["A"], M["N"], M["rest"]
    lam = CMP.LAM
    deg = np.bincount(A.ravel(), minlength=N).astype(float)
    Mm = sp.coo_matrix((np.concatenate([deg + lam, -np.ones(2 * len(A))]),
                        (np.concatenate([np.arange(N), A[:, 0], A[:, 1]]),
                         np.concatenate([np.arange(N), A[:, 1], A[:, 0]]))), shape=(N, N)).tocsr()
    # couplages entre composantes (entrées hors bloc)
    hors = int(np.sum(comp[A[:, 0]] != comp[A[:, 1]]))
    lmin = float(eigsh(Mm, k=1, sigma=0, which="LM", return_eigenvectors=False)[0])
    lmax = float(eigsh(Mm, k=1, which="LA", return_eigenvectors=False)[0])
    # sans ancre λ : vecteur constant dans le noyau pour chaque composante
    Lap = sp.coo_matrix((np.concatenate([deg, -np.ones(2 * len(A))]),
                         (np.concatenate([np.arange(N), A[:, 0], A[:, 1]]),
                          np.concatenate([np.arange(N), A[:, 1], A[:, 0]]))), shape=(N, N)).tocsr()
    # dimension du noyau du laplacien (= nombre de composantes) : vérification par valeurs propres nulles
    kk = min(ncomp_total + 3, N - 2)
    vals = eigsh(Lap, k=kk, sigma=-1e-9, which="LM", return_eigenvectors=False)
    noyau = int(np.sum(np.abs(vals) < 1e-8))
    # solutions indépendantes : résolution globale vs par composante, avec un second membre aléatoire
    rng = np.random.default_rng(0)
    b = rng.normal(size=N)
    x_glob = spsolve(Mm, b)
    ecart_max = 0.0
    for c in np.unique(comp)[:ncomp_max]:
        vs = np.where(comp == c)[0]
        sub = Mm[vs][:, vs]
        x_c = spsolve(sub.tocsc(), b[vs])
        ecart_max = max(ecart_max, float(np.max(np.abs(x_c - x_glob[vs]))))
    return {"lambda": lam, "entrees_hors_bloc_composante": hors, "lambda_min": lmin, "lambda_max": lmax,
            "conditionnement": lmax / lmin, "dimension_noyau_laplacien_sans_ancre": noyau,
            "ecart_max_solution_globale_vs_bloc": ecart_max,
            "conditions_de_frontiere_explicites": "aucune : ancre λ uniforme sur tous les sommets"}


if __name__ == "__main__":
    os.makedirs(SORTIE, exist_ok=True)
    out = {"convention": "composantes = graphe des arêtes A (sommets référencés et non référencés) ; "
                         "boucles = composantes du graphe des arêtes de frontière"}
    for m in MORPHS:
        M = CMP.charger_morph(m)
        r, comp, ref, fr, blab, bord = audit(M, m)
        r["systeme_SQ"] = systeme_SQ(M, comp)
        out[m] = r
        print(m, {k: r[k] for k in ["N_sommets", "N_faces", "composantes_graphe_aretes", "aretes_frontiere",
                                    "boucles_de_frontiere", "sommets_non_references", "faces_aire_nulle_1e-12",
                                    "faces_dupliquees", "poids_nuls_total"]}, flush=True)
        print("  systeme", r["systeme_SQ"], flush=True)
    with open(os.path.join(SORTIE, "topologie.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print("ECRIT", flush=True)
