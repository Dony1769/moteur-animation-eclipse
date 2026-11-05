"""Décomposition mathématique de la déformation locale autour de l'entrejambe (masculin, hanche G 120°).

Quatre blocs, un facteur à la fois, mêmes entrées partout (repos, poids, transformations, pose) :
1. Arêtes incidentes aux sommets défectueux : longueurs LBS / SQ / SQV1, déplacements des extrémités, décomposition
   de la variation d'arête SQ − LBS en composante le long de l'arête et perpendiculaire, cible de SQ R_ab (r_a − r_b).
2. Triangles incidents : gradient de déformation 3×2 par triangle, valeurs singulières, rotation extraite, écart
   entre le gradient LBS réel et Mv moyen (terme de gradient des poids), taille des triangles.
3. Expériences de contrôle sur le maillage complet : facteur unique sur R_ab (moyenne / polaire de la moyenne /
   identité). Le patch n'est pas extrait : SQ est un système linéaire global, un patch changerait les conditions aux
   limites. Les mesures sont restreintes aux arêtes et sommets du patch (défauts + voisins).
4. Distributions de poids synthétiques entre les deux cuisses sur le patch, somme conservée égale à 1 ; homogénéité
   d'échelle (test de cohérence).

Aucun critère, aucun seuil et aucune méthode de référence ne sont modifiés.
"""
import importlib.util
import json
import os

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import factorized

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SORTIE = os.path.join(RACINE, "docs", "rapports", "skinning", "decomposition_hanche_masc")


def charger(nom):
    spec = importlib.util.spec_from_file_location(nom, os.path.join(HERE, nom + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


INV = charger("investigation_hanche_masc")
M, ARAP, CV, Ms = INV.M, INV.ARAP, INV.CV, INV.Ms


def polaire_gen(X):
    """Polaire orthogonale de matrices (..., n, n), déterminant +1 forcé."""
    U, _, Vt = np.linalg.svd(X)
    R = U @ Vt
    flip = np.linalg.det(R) < 0
    U2 = U.copy()
    U2[..., :, -1] = np.where(flip[..., None], -U[..., :, -1], U[..., :, -1])
    return U2 @ Vt


def solve_R(pos_lbs, rest, A, Rab, lam):
    """Même système que ARAP.solve_fixe, mais R_ab fourni arête par arête (E,3,3)."""
    a, c = A[:, 0], A[:, 1]
    N = len(rest)
    d0 = rest[a] - rest[c]
    deg = np.bincount(np.concatenate([a, c]), minlength=N).astype(float)
    Mm = sp.coo_matrix((np.concatenate([deg + lam, -np.ones(2 * len(a))]),
                        (np.concatenate([np.arange(N), a, c]), np.concatenate([np.arange(N), c, a]))),
                       shape=(N, N)).tocsc()
    solve = factorized(Mm)
    re = np.einsum("eij,ej->ei", Rab, d0)
    rhs = np.zeros((N, 3))
    np.add.at(rhs, a, re)
    np.add.at(rhs, c, -re)
    rhs += lam * pos_lbs
    return np.column_stack([solve(rhs[:, k]) for k in range(3)])


def pipeline(Wi_, Ww_, B_, pm_, rest_):
    ref = M.calculer_toutes(rest_, Wi_, Ww_, B_, pm_)[0]
    lbs = ref["LBS"]
    Mv = M.repere_rigide(Wi_, Ww_, B_, pm_)
    Rsq = polaire_gen(Mv)
    return lbs, Mv, Rsq


def angle_deg(u, v):
    cu = np.linalg.norm(u, axis=-1) * np.linalg.norm(v, axis=-1)
    return np.degrees(np.arccos(np.clip(np.einsum("...i,...i->...", u, v) / np.maximum(cu, 1e-12), -1, 1)))


def corr(x, y):
    if len(x) < 3 or np.std(x) < 1e-12 or np.std(y) < 1e-12:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def angle_rot(X, Y):
    """Angle entre deux repères 3×2 (colonnes orthonormées)."""
    P = polaire_gen((X.T @ Y)[None])[0]
    return float(np.degrees(np.arccos(np.clip((np.trace(P)) / 2, -1, 1))))


def tri_mesure(ids, rest, lbs, sq, Mv):
    i, j, k = ids
    ri, rj, rk = rest[i], rest[j], rest[k]
    e1 = rj - ri
    e1n = e1 / np.linalg.norm(e1)
    nrm = np.cross(e1, rk - ri)
    area = 0.5 * np.linalg.norm(nrm)
    nn = nrm / np.linalg.norm(nrm)
    e2 = np.cross(nn, e1n)
    Q = np.column_stack([e1n, e2])
    Dm2 = np.column_stack([Q.T @ (rj - ri), Q.T @ (rk - ri)])
    Dm3 = Q @ Dm2
    Mt = Mv[[i, j, k]].mean(0)
    Rmv = polaire_gen(Mt[None])[0]
    out = {"taille": float(np.sqrt(area))}
    rots = {}
    for nom, p in (("LBS", lbs), ("SQ", sq)):
        Dd = np.column_stack([p[j] - p[i], p[k] - p[i]])
        G = Dd @ np.linalg.inv(Dm2)
        U, s, Vt = np.linalg.svd(G, full_matrices=False)
        rots[nom] = U @ Vt
        out[nom] = {"s1": float(s[0]), "s2": float(s[1]), "aire_ratio": float(s[0] * s[1]),
                    "anisotropie": float(s[0] / s[1]),
                    "ecart_Mv": float(np.linalg.norm(Dd - Mt @ Dm3) / np.linalg.norm(Dm3))}
    out["angle_rot_LBS_SQ"] = angle_rot(rots["LBS"], rots["SQ"])
    out["angle_rot_LBS_Mv"] = angle_rot(rots["LBS"], Rmv @ Q)
    out["angle_rot_SQ_Mv"] = angle_rot(rots["SQ"], Rmv @ Q)
    return out


def mesures(pos, rest, A, N, D, Mv_):
    s, _ = INV.ratio_par_sommet(pos, rest, A, N)
    mes = Ms.mesurer(pos, rest, b_g, tot_g, A, Mv=Mv_)
    return {"max_D": float(s[D].max()), "med_D": float(np.median(s[D])), "max_tous": float(s.max()),
            "p99_tous": float(mes["etirement_p99"]), "retournements": int(mes["polygones_retournes"]),
            "variation_volume": float(mes["variation_volume_relative"])}


if __name__ == "__main__":
    os.makedirs(SORTIE, exist_ok=True)
    z, noms, rest, Wi, Ww, B, b, tot, A, sortie = INV.tous_les_defauts()
    b_g, tot_g = b, tot
    N = len(rest)
    D = np.array(sortie["defauts_union"], int)
    pm, centre, chaine, sens = INV.pose_test(z, noms, INV.JSON_SQ, "hanche_G", 120)
    TRI = CV._triangles(b, tot)
    a, c = A[:, 0], A[:, 1]
    lbs, Mv, Rsq = pipeline(Wi, Ww, B, pm, rest)
    sq = ARAP.solve_fixe(lbs, rest, A, Rsq, 0.1)
    sqv1, _ = CV.corriger(sq, rest, Wi, Ww, b, tot, T=TRI, M=1)
    verif = float(np.abs(solve_R(lbs, rest, A, 0.5 * (Rsq[a] + Rsq[c]), 0.1) - sq).max())
    print(f"verification solveur reimplemente vs ARAP.solve_fixe : {verif:.2e} m", flush=True)

    # ---------- Bloc 1 : arêtes incidentes aux défauts ----------
    L = lambda p: np.linalg.norm(p[a] - p[c], axis=1)
    lr, ll, ls, lv = L(rest), L(lbs), L(sq), L(sqv1)
    inc = np.isin(a, D) | np.isin(c, D)
    ie = np.where(inc)[0]
    d0 = rest[a] - rest[c]
    uL = (lbs[a] - lbs[c]) / np.maximum(ll[:, None], 1e-12)
    dA, dC = sq[a] - lbs[a], sq[c] - lbs[c]          # déplacements SQ − LBS des extrémités
    Delta = dA - dC                                  # variation de l'arête SQ − LBS
    along = np.einsum("ei,ei->e", Delta, uL)
    perp = np.linalg.norm(Delta - along[:, None] * uL, axis=1)
    Rab_mean = 0.5 * (Rsq[a] + Rsq[c])
    tgt = np.einsum("eij,ej->ei", Rab_mean, d0)     # cible de SQ
    shrink = np.linalg.norm(tgt, axis=1) / lr
    smin = np.linalg.svd(Rab_mean, compute_uv=False)[:, -1]
    res_L = np.linalg.norm((lbs[a] - lbs[c]) - tgt, axis=1) / lr
    res_S = np.linalg.norm((sq[a] - sq[c]) - tgt, axis=1) / lr
    rel_angle = np.degrees(np.arccos(np.clip((np.trace(np.matmul(Rsq[a].transpose(0, 2, 1), Rsq[c]), axis1=1, axis2=2) - 1) / 2, -1, 1)))
    amp = (ls - ll) / lr
    dispL_a, dispS_a = lbs[a] - rest[a], sq[a] - rest[a]
    dispL_c, dispS_c = lbs[c] - rest[c], sq[c] - rest[c]
    arete_L, arete_S = lbs[a] - lbs[c], sq[a] - sq[c]

    recs = []
    for e in ie:
        recs.append({
            "a": int(a[e]), "c": int(c[e]), "defaut_a": bool(np.isin(a[e], D)), "defaut_c": bool(np.isin(c[e], D)),
            "L_repos": float(lr[e]), "L_LBS": float(ll[e]), "L_SQ": float(ls[e]), "L_SQV1": float(lv[e]),
            "amplification_SQ_moins_LBS": float(amp[e]),
            "deplacement_LBS_a": float(np.linalg.norm(dispL_a[e])), "deplacement_LBS_c": float(np.linalg.norm(dispL_c[e])),
            "deplacement_SQ_a": float(np.linalg.norm(dispS_a[e])), "deplacement_SQ_c": float(np.linalg.norm(dispS_c[e])),
            "delta_SQ_LBS_a": float(np.linalg.norm(dA[e])), "delta_SQ_LBS_c": float(np.linalg.norm(dC[e])),
            "cos_delta_a_delta_c": float(np.dot(dA[e], dC[e]) / max(np.linalg.norm(dA[e]) * np.linalg.norm(dC[e]), 1e-12)),
            "variation_le_long_arete": float(along[e]), "variation_perp_arete": float(perp[e]),
            "angle_repos_LBS_deg": float(angle_deg(d0[e], arete_L[e])), "angle_repos_SQ_deg": float(angle_deg(d0[e], arete_S[e])),
            "cible_retrecissement_R_ab": float(shrink[e]), "sigma_min_R_ab": float(smin[e]),
            "ecart_LBS_a_cible": float(res_L[e]), "ecart_SQ_a_cible": float(res_S[e]),
            "angle_rotations_extremites_deg": float(rel_angle[e]),
        })

    def med(x):
        return float(np.median(x)) if len(x) else None

    amp_i = amp[ie]
    resume_aretes = {
        "nb_aretes_defaut": int(len(ie)),
        "amplification_mediane": med(amp_i),
        "amplification_max": float(amp_i.max()),
        "part_variation_le_arete": med(np.abs(along[ie]) / np.maximum(np.abs(along[ie]) + perp[ie], 1e-12)),
        "cos_deplacements_extremites_mediane": med(np.array([r["cos_delta_a_delta_c"] for r in recs])),
        "cible_retrecissement_mediane": med(shrink[ie]),
        "sigma_min_mediane": med(smin[ie]),
        "ecart_LBS_cible_mediane": med(res_L[ie]),
        "ecart_SQ_cible_mediane": med(res_S[ie]),
        "angle_rotations_extremites_mediane_deg": med(rel_angle[ie]),
        "correlations_avec_amplification": {
            "retrecissement_cible": corr(shrink[ie], amp_i),
            "sigma_min": corr(smin[ie], amp_i),
            "ecart_LBS_cible": corr(res_L[ie], amp_i),
            "angle_rotations_extremites": corr(rel_angle[ie], amp_i),
            "longueur_repos": corr(lr[ie], amp_i),
            "composante_perp": corr(perp[ie], amp_i),
            "composante_le_long": corr(along[ie], amp_i),
        },
    }
    print("ARETES", json.dumps(resume_aretes, indent=1, ensure_ascii=False), flush=True)

    # ---------- Bloc 2 : triangles incidents aux défauts ----------
    sel = TRI[np.isin(TRI, D).any(1)]
    tris = [tri_mesure(t, rest, lbs, sq, Mv) for t in sel]
    tl = np.array([t["taille"] for t in tris])
    aL = np.array([t["LBS"]["aire_ratio"] for t in tris]); aS = np.array([t["SQ"]["aire_ratio"] for t in tris])
    eL = np.array([t["LBS"]["ecart_Mv"] for t in tris]); eS = np.array([t["SQ"]["ecart_Mv"] for t in tris])
    rLS = np.array([t["angle_rot_LBS_SQ"] for t in tris]); rLM = np.array([t["angle_rot_LBS_Mv"] for t in tris])
    anL = np.array([t["LBS"]["anisotropie"] for t in tris]); anS = np.array([t["SQ"]["anisotropie"] for t in tris])
    q = np.quantile(tl, [1 / 3, 2 / 3])
    classe = np.digitize(tl, q)
    bins = {}
    for k_, nom in enumerate(["petit", "moyen", "grand"]):
        m_ = classe == k_
        bins[nom] = {"n": int(m_.sum()), "ecart_aire_SQ_LBS_mediane": med(np.abs(aS[m_] - aL[m_])),
                     "ecart_Mv_LBS_mediane": med(eL[m_])}
    resume_tri = {
        "nb_triangles": int(len(tris)),
        "aire_ratio_LBS_mediane": med(aL), "aire_ratio_SQ_mediane": med(aS),
        "aire_ratio_SQ_min": float(aS.min()), "aire_ratio_SQ_max": float(aS.max()),
        "compression_SQ_nb_aire_ratio_below_1": int((aS < 1).sum()),
        "anisotropie_LBS_mediane": med(anL), "anisotropie_SQ_mediane": med(anS),
        "ecart_Mv_LBS_mediane": med(eL), "ecart_Mv_SQ_mediane": med(eS),
        "angle_rot_LBS_SQ_mediane_deg": med(rLS), "angle_rot_LBS_Mv_mediane_deg": med(rLM),
        "correlations": {
            "ecart_Mv_LBS_vs_ecart_aire_SQ_LBS": corr(eL, np.abs(aS - aL)),
            "angle_LBS_Mv_vs_angle_LBS_SQ": corr(rLM, rLS),
            "taille_vs_ecart_aire_SQ_LBS": corr(tl, np.abs(aS - aL)),
        },
        "par_taille": bins,
    }
    print("TRIANGLES", json.dumps(resume_tri, indent=1, ensure_ascii=False), flush=True)

    # ---------- Bloc 3 : un facteur à la fois sur R_ab (maillage complet) ----------
    var = {"LBS": mesures(lbs, rest, A, N, D, Mv),
           "SQ_moyenne": mesures(sq, rest, A, N, D, Mv)}
    var["SQ_moyenne_polaire (diagnostic, pas un candidat)"] = mesures(
        solve_R(lbs, rest, A, polaire_gen(Rab_mean), 0.1), rest, A, N, D, Mv)
    var["SQ_identite (diagnostic, pas un candidat)"] = mesures(
        solve_R(lbs, rest, A, np.broadcast_to(np.eye(3), (len(A), 3, 3)).copy(), 0.1), rest, A, N, D, Mv)
    for k_, v_ in var.items():
        print(f"{k_:55s} {v_}", flush=True)

    # ---------- Bloc 4a : distributions de poids synthétiques entre les deux cuisses ----------
    gG, gD = noms.index("mixamorig:LeftUpLeg"), noms.index("mixamorig:RightUpLeg")
    slotG = (Wi == gG)
    slotD = (Wi == gD)
    both = slotG.any(1) & slotD.any(1)
    voisin = np.unique(np.concatenate([D, a[np.isin(c, D)], c[np.isin(a, D)]]))
    S = np.where(both & np.isin(np.arange(N), voisin))[0]
    print("sommets modifiés (deux cuisses, défauts + voisins) :", len(S), flush=True)
    sweep = {}
    for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
        Wt = Ww.copy()
        for v in S:
            kG = np.where(slotG[v])[0][0]
            kD = np.where(slotD[v])[0][0]
            s_ = Ww[v, kG] + Ww[v, kD]
            Wt[v, kG] = s_ * t
            Wt[v, kD] = s_ * (1 - t)
        lb_t, Mv_t, Rs_t = pipeline(Wi, Wt, B, pm, rest)
        sq_t = ARAP.solve_fixe(lb_t, rest, A, Rs_t, 0.1)
        sweep[str(t)] = {"LBS": mesures(lb_t, rest, A, N, D, Mv_t), "SQ": mesures(sq_t, rest, A, N, D, Mv_t),
                         "amplification_mediane_D": med(((L(sq_t) - L(lb_t)) / lr)[ie])}
        print("poids G=", t, "LBS", sweep[str(t)]["LBS"], "SQ", sweep[str(t)]["SQ"], flush=True)

    # ---------- Bloc 4b : homogénéité d'échelle (cohérence du calcul) ----------
    echelle = {}
    for s in (0.5, 2.0):
        S4 = np.diag([s, s, s, 1.0])
        Bs = np.array([S4 @ Bk @ np.linalg.inv(S4) for Bk in B])
        pms = np.array([S4 @ Pk @ np.linalg.inv(S4) for Pk in pm])
        lb_s, Mv_s, Rs_s = pipeline(Wi, Ww, Bs, pms, rest * s)
        sq_s = ARAP.solve_fixe(lb_s, rest * s, A, Rs_s, 0.1)
        echelle[str(s)] = float(np.abs(sq_s / s - sq).max())
    print("homogénéité d'échelle, écart max (doit être ~0) :", echelle, flush=True)

    with open(os.path.join(SORTIE, "resultats.json"), "w", encoding="utf-8") as f:
        json.dump({"verification_solveur_m": verif, "aretes": resume_aretes, "aretes_detail": recs,
                   "triangles": resume_tri, "variantes_R_ab": var, "sweep_poids_cuisses": sweep,
                   "echelle_ecart_m": echelle, "nb_sommets_sweep": int(len(S))},
                  f, indent=1, ensure_ascii=False)
    print("ECRIT", os.path.join(SORTIE, "resultats.json"), flush=True)
