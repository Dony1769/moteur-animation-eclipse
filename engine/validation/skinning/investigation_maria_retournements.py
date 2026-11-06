"""Phase 1 et 2 : diagnostic triangle par triangle des retournements nouveaux de Maria (SQ retourné, LBS non retourné),
et vérification indépendante du solveur SQ.

Convention identique au reste du dossier : SQ résout M p = b avec R_ab = 0,5 (R_a + R_b) (moyenne arithmétique,
configuration actuelle de ARAP.solve_fixe), λ = 0,1. Le référentiel d'orientation est la normale de repos tournée par la
polaire de la moyenne des Mv du triangle. Aucun seuil n'est modifié.

Vérification indépendante : assemblage explicite arête par arête (pas de code partagé avec ARAP.solve_fixe), trois
solveurs (LU creux, gradient conjugué, moindres carrés LSQR sur le système empilé), raffinement itératif avec résidu en
précision étendue (np.longdouble), contrôle de topologie (arêtes, indices, connexions).
"""
import importlib.util
import json
import os

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve, cg, lsqr, eigsh

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SORTIE = os.path.join(RACINE, "docs", "rapports", "skinning", "maria_retournements")
LAM = 0.1


def charger(nom):
    spec = importlib.util.spec_from_file_location(nom, os.path.join(HERE, nom + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


DEC = charger("investigation_decomposition")
CMP = charger("investigation_comparaison")
DR = charger("investigation_defaut_reel")
ARAP = CMP.ARAP


def assembler_independant(A, rest, lbs, Rab, lam):
    """M = (deg + λ) I − Adj ; b_a = Σ_b R_ab (r_a − r_b) + λ lbs_a, par boucle explicite sur les arêtes."""
    N = len(rest)
    rows, cols, vals = [], [], []
    deg = np.zeros(N)
    b = np.zeros((N, 3))
    for e in range(len(A)):
        i, j = int(A[e, 0]), int(A[e, 1])
        deg[i] += 1.0
        deg[j] += 1.0
        rows += [i, j]
        cols += [j, i]
        vals += [-1.0, -1.0]
        d = rest[i] - rest[j]
        rd = Rab[e] @ d
        b[i] += rd
        b[j] -= rd
    for i in range(N):
        rows.append(i)
        cols.append(i)
        vals.append(deg[i] + lam)
    Mm = sp.csr_matrix((np.array(vals), (np.array(rows), np.array(cols))), shape=(N, N))
    b += lam * lbs
    return Mm, b


def rab_arith(Rsq, A):
    a, c = A[:, 0], A[:, 1]
    return 0.5 * (Rsq[a] + Rsq[c])


def residu(Mm, x, b):
    """Résidu en précision étendue (np.longdouble) : r = b − M x."""
    coo = Mm.tocoo()
    r = b.astype(np.longdouble).copy()
    xl = x.astype(np.longdouble)
    for k in range(3):
        contrib = coo.data.astype(np.longdouble) * xl[coo.col, k]
        acc = np.zeros(Mm.shape[0], dtype=np.longdouble)
        np.add.at(acc, coo.row, contrib)
        r[:, k] -= acc
    return r


def solveurs(Mm, b, lbs, rest, A, Rab):
    """Trois solveurs indépendants et raffinement en précision étendue."""
    out = {}
    x_lu = np.column_stack([spsolve(Mm.tocsc(), b[:, k]) for k in range(3)])
    out["LU_creux"] = x_lu
    x_cg = np.zeros_like(b)
    info_cg = []
    for k in range(3):
        xk, inf = cg(Mm, b[:, k], rtol=1e-13, atol=0.0, maxiter=50000)
        x_cg[:, k] = xk
        info_cg.append(int(inf))
    out["gradient_conjugue"] = x_cg
    # moindres carrés : (p_i − p_j) = R_ab (r_i − r_j) pondéré, et sqrt(λ)(p − lbs) = 0
    E = len(A)
    N = len(rest)
    lam = LAM
    rr, cc, vv = [], [], []
    for e in range(E):
        i, j = int(A[e, 0]), int(A[e, 1])
        rr += [e, e]
        cc += [i, j]
        vv += [1.0, -1.0]
    for i in range(N):
        rr.append(E + i)
        cc.append(i)
        vv.append(np.sqrt(lam))
    Bst = sp.csr_matrix((np.array(vv), (np.array(rr), np.array(cc))), shape=(E + N, N))
    x_ls = np.zeros_like(b)
    info_ls = []
    for k in range(3):
        rhs = np.zeros(E + N)
        d = rest[A[:, 0]] - rest[A[:, 1]]
        rhs[:E] = np.einsum("eij,ej->ei", Rab, d)[:, k]
        rhs[E:] = np.sqrt(lam) * lbs[:, k]
        sol = lsqr(Bst, rhs, atol=1e-15, btol=1e-15, iter_lim=200000)
        x_ls[:, k] = sol[0]
        info_ls.append(int(sol[1]))
    out["moindres_carres_LSQR"] = x_ls
    # raffinement : une itération avec résidu étendu, correction en float64
    x_ref = x_lu.copy()
    r = residu(Mm, x_ref, b)
    corr = np.column_stack([spsolve(Mm.tocsc(), r[:, k].astype(np.float64)) for k in range(3)])
    out["LU_raffine_residu_etendu"] = x_ref + corr
    return out, {"cg_info": info_cg, "lsqr_info": info_ls}


def controle_topologie(tris, A, b, tot, N):
    """Arêtes, indices, connexions des triangles, orientation, composantes."""
    e_tri = set()
    for t in tris:
        for k in range(3):
            e_tri.add(tuple(sorted((int(t[k]), int(t[(k + 1) % 3])))))
    e_A = set(tuple(sorted((int(i), int(j)))) for i, j in A)
    res = {"aretes_depuis_triangles": len(e_tri), "aretes_depuis_A": len(e_A),
           "identiques": e_tri == e_A, "sommets_degeneres_triangles": int(sum(len(set(t)) < 3 for t in tris)),
           "indices_hors_bornes": int(((tris < 0) | (tris >= N)).sum())}
    from scipy.sparse.csgraph import connected_components
    G = sp.coo_matrix((np.ones(len(A)), (A[:, 0], A[:, 1])), shape=(N, N))
    ncomp, _ = connected_components(G, directed=False)
    res["composantes_connexes"] = int(ncomp)
    return res


if __name__ == "__main__":
    os.makedirs(SORTIE, exist_ok=True)
    M = CMP.charger_morph("maria")
    rest, A, tris, W, noms = M["rest"], M["A"], M["tris"], M["W"], M["noms"]
    N = M["N"]
    a, c = A[:, 0], A[:, 1]
    aire0 = 0.5 * np.linalg.norm(np.cross(rest[tris[:, 1]] - rest[tris[:, 0]], rest[tris[:, 2]] - rest[tris[:, 0]]), axis=1)
    n0 = np.cross(rest[tris[:, 1]] - rest[tris[:, 0]], rest[tris[:, 2]] - rest[tris[:, 0]])
    n0u = n0 / np.maximum(np.linalg.norm(n0, axis=1, keepdims=True), 1e-300)

    sortie = {"convention": "R_ab arithmétique, λ=0,1, référence = polaire(moyenne Mv) ; 29 poses",
              "topologie": controle_topologie(tris, A, None, M["tot"], N),
              "poses": {}, "retournements_nouveaux": [], "classes": {}}
    print("topologie", sortie["topologie"], flush=True)

    # conditionnement global de M (λ = 0,1), mesuré une fois (la matrice ne dépend pas de la pose pour les poids
    # de l'arête, seulement de λ et de la topologie)
    deg = np.bincount(np.concatenate([a, c]), minlength=N).astype(float)
    Mglob = sp.csr_matrix((np.concatenate([deg + LAM, -np.ones(2 * len(a))]),
                           (np.concatenate([np.arange(N), a, c]), np.concatenate([np.arange(N), c, a]))), shape=(N, N))
    lmax = float(eigsh(Mglob, k=1, which="LA", return_eigenvectors=False)[0])
    lmin = float(eigsh(Mglob, k=1, which="SA", return_eigenvectors=False)[0])
    sortie["conditionnement_M"] = {"lambda_min": lmin, "lambda_max": lmax, "cond": lmax / lmin}
    print("cond M", sortie["conditionnement_M"], flush=True)

    for nom in CMP.POSES:
        pm = CMP.pose_de(M, nom)
        lbs, sq, Mv, R, t = CMP.evaluer(M, pm)
        Rsq = DEC.polaire_gen(Mv)
        Rab = rab_arith(Rsq, A)
        Mm, b = assembler_independant(A, rest, lbs, Rab, LAM)
        # 1. solutions indépendantes et écarts avec le solveur d'origine
        sols, infos = solveurs(Mm, b, lbs, rest, A, Rab)
        ecarts = {k: float(np.abs(v - sq).max()) for k, v in sols.items()}
        res_LU = residu(Mm, sols["LU_creux"], b)
        res_abs = float(np.abs(res_LU).max())
        b_max = float(np.abs(b).max())
        res_rel = res_abs / max(b_max, 1e-300)
        # 2. flips par solveur
        flips = {}
        # définition identique à investigation_retournements.retournements
        Mt = Mv[tris].mean(1)
        ref = np.einsum("tij,tj->ti", DEC.polaire_gen(Mt), n0u)

        def flips_de(p):
            nL = np.cross(lbs[tris[:, 1]] - lbs[tris[:, 0]], lbs[tris[:, 2]] - lbs[tris[:, 0]])
            nS = np.cross(p[tris[:, 1]] - p[tris[:, 0]], p[tris[:, 2]] - p[tris[:, 0]])
            return np.einsum("ti,ti->t", nL, ref) < 0, np.einsum("ti,ti->t", nS, ref) < 0

        fL, fS = flips_de(sq)
        nv = fS & ~fL
        flips["origine_ARAP"] = int(nv.sum())
        for k, v in sols.items():
            _, fSk = flips_de(v)
            flips[k] = int((fSk & ~fL).sum())
        # 3. classes sur tous les triangles
        cls = np.zeros(len(tris), int)
        cls[(~fL) & (~fS)] = 1
        cls[fL & (~fS)] = 2
        cls[(~fL) & fS] = 3
        cls[fL & fS] = 4
        comptes = {str(k): int((cls == k).sum()) for k in (1, 2, 3, 4)}
        sortie["classes"][nom] = comptes
        sortie["poses"][nom] = {"ecarts_solveurs_vs_origine_m": ecarts, "residu_absolu_LU_etendu": res_abs,
                                "max_abs_b": b_max, "residu_relatif_LU_etendu": res_rel,
                                "retournements_nouveaux_par_solveur": flips, "infos": infos,
                                "classes": comptes}
        print(nom, comptes, "nouveaux", flips, "résidu", res_rel, flush=True)

        # 4. détail des triangles de catégorie 3 (retournement SQ seulement)
        for ti in np.where(cls == 3)[0]:
            i, j, k = (int(v) for v in tris[ti])
            vert = [i, j, k]
            poids = []
            for v in vert:
                idx = np.argsort(-W[v])[:3]
                poids.append([[noms[q], round(float(W[v, q]), 4)] for q in idx if W[v, q] > 1e-9])
            dom = [noms[int(np.argmax(W[v]))] for v in vert]
            Rdom = [R[int(np.argmax(W[v]))] for v in vert]
            angles_os = [round(float(np.degrees(np.arccos(np.clip((np.trace(Rk) - 1) / 2, -1, 1)))), 2) for Rk in Rdom]
            rel = [round(float(np.degrees(np.arccos(np.clip((np.trace(Rdom[p].T @ Rdom[q]) - 1) / 2, -1, 1)))), 2)
                   for p, q in [(0, 1), (1, 2), (0, 2)]]
            nS = np.cross(sq[j] - sq[i], sq[k] - sq[i])
            nL = np.cross(lbs[j] - lbs[i], lbs[k] - lbs[i])
            aL = 0.5 * np.linalg.norm(nL)
            aS = 0.5 * np.linalg.norm(nS)
            sv = np.linalg.svd(Mt[ti], compute_uv=False)
            Dm = np.column_stack([rest[j] - rest[i], rest[k] - rest[i]])
            sv_Dm = np.linalg.svd(Dm, compute_uv=False)
            resv = np.abs(res_LU[vert]).max() / max(np.abs(b[vert]).max(), 1e-300)
            sortie["retournements_nouveaux"].append({
                "pose": nom, "triangle": ti, "sommets": vert,
                "repos": [rest[v].round(5).tolist() for v in vert],
                "LBS": [lbs[v].round(5).tolist() for v in vert],
                "SQ": [sq[v].round(5).tolist() for v in vert],
                "aire_repos": float(aire0[ti]), "aire_LBS": float(aL), "aire_SQ": float(aS),
                "rapport_aire_SQ_sur_repos": float(aS / max(aire0[ti], 1e-300)),
                "normale_repos": n0u[ti].round(5).tolist(),
                "normale_SQ_unitaire": (nS / max(np.linalg.norm(nS), 1e-300)).round(5).tolist(),
                "normale_LBS_unitaire": (nL / max(np.linalg.norm(nL), 1e-300)).round(5).tolist(),
                "produit_normale_SQ_reference": float(np.dot(nS / max(np.linalg.norm(nS), 1e-300), ref[ti])),
                "produit_normale_LBS_reference": float(np.dot(nL / max(np.linalg.norm(nL), 1e-300), ref[ti])),
                "produit_normale_SQ_repos_brut": float(np.dot(nS / max(np.linalg.norm(nS), 1e-300), n0u[ti])),
                "poids_sommets": poids, "os_dominants": dom,
                "angle_rotation_os_dominants_deg": angles_os, "angle_relatif_entre_os_dominants_deg": rel,
                "valeurs_singulieres_Mv_moyen": sv.round(5).tolist(),
                "valeurs_singulieres_Dm_repos": sv_Dm.round(5).tolist(),
                "residu_relatif_local": float(resv),
            })
    # 5. ordre et vérification de la catégorie 3 (32 cas attendus)
    cat3 = [x for x in sortie["retournements_nouveaux"]]
    sortie["verification_categorie3"] = {"nombre": len(cat3),
                                         "attendu": 32,
                                         "toutes_categorie_3": all(x["produit_normale_SQ_reference"] < 0 and
                                                                   x["produit_normale_LBS_reference"] >= 0 for x in cat3)}
    print("verif", sortie["verification_categorie3"], flush=True)
    with open(os.path.join(SORTIE, "maria_retournements.json"), "w", encoding="utf-8") as f:
        json.dump(sortie, f, indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print("ECRIT", flush=True)
