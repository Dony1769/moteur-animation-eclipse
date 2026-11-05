"""Reproduction intermédiaire du défaut de l'entrejambe masculin, sur le MAILLAGE COMPLET (aucun patch isolé).

Poids, géométrie et transformations originaux, inchangés.

Bloc 1 : zones d'analyse = 24 défauts ; 1er voisinage ; 2e voisinage ; voisinage à 6 arêtes (propagation).
Bloc 2 : quatre configurations, mêmes entrées :
  A. LBS ; B. SQ moyenne arithmétique ; C. SQ polaire de la moyenne ;
  D. = C, la propagation étant mesurée séparément sur les sommets à poids pur (même solution, mesure séparée).
Bloc 3 : interaction poids / rotations : les deux cuisses reçoivent des angles contrôlés (poids et géométrie fixes),
         puis régression exploratoire (non causale) sur les arêtes défectueuses.
Bloc 4 : décomposition de l'énergie : vérification δ = M⁻¹ g, où g = somme des résidus d'arêtes ; spectre du Laplacien.
"""
import importlib.util
import json
import os

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import factorized, eigsh

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SORTIE = os.path.join(RACINE, "docs", "rapports", "skinning", "intermediaire_hanche_masc")


def charger(nom):
    spec = importlib.util.spec_from_file_location(nom, os.path.join(HERE, nom + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


DEC = charger("investigation_decomposition")
S = charger("investigation_synthetique")
INV = DEC.INV
P, EXP, ARAP, CV, Ms, M = INV.P, INV.EXP, INV.ARAP, INV.CV, INV.Ms, INV.M
LAM = 0.1


def pose_deux(z, noms, js, thG, thD):
    """Cuisse gauche tournée de thG, cuisse droite de thD (degrés), autour de leurs articulations réelles."""
    B = z["bones_rest_monde"]
    sG = EXP.signe_depuis_pose_reelle(z, noms, js, "LeftUpLeg", "L_flex90")[0]
    sD = EXP.signe_depuis_pose_reelle(z, noms, js, "RightUpLeg", "R_flex90")[0]
    cG, aG, chG = P.articulation(js, EXP.prefixe(noms) + "LeftUpLeg")
    cD, aD, chD = P.articulation(js, EXP.prefixe(noms) + "RightUpLeg")
    pG = P.matrices_pose(B, noms, chG, P.transformation_articulation(cG, aG, np.radians(thG), sG))
    pD = P.matrices_pose(B, noms, chD, P.transformation_articulation(cD, aD, np.radians(thD), sD))
    pm = B.copy()
    for n in chG:
        pm[noms.index(n)] = pG[noms.index(n)]
    for n in chD:
        pm[noms.index(n)] = pD[noms.index(n)]
    return pm


def angle_relatif(pm, noms, B):
    """Angle réel entre les rotations des deux cuisses (degrés)."""
    kG, kD = noms.index(EXP.prefixe(noms) + "LeftUpLeg"), noms.index(EXP.prefixe(noms) + "RightUpLeg")
    RG = (pm[kG] @ np.linalg.inv(B[kG]))[:3, :3]
    RD = (pm[kD] @ np.linalg.inv(B[kD]))[:3, :3]
    ang, _ = P.angle_et_axe(RG.T @ RD)
    return float(np.degrees(ang))


def sq_deux(lbs, rest, A, Rsq, lam=LAM):
    a, c = A[:, 0], A[:, 1]
    arith = ARAP.solve_fixe(lbs, rest, A, Rsq, lam)
    polaire = DEC.solve_R(lbs, rest, A, DEC.polaire_gen(0.5 * (Rsq[a] + Rsq[c])), lam)
    return arith, polaire


def stretch_zone(pos, rest, A, mask):
    a, c = A[:, 0], A[:, 1]
    lr = np.linalg.norm(rest[a] - rest[c], axis=1)
    r = np.linalg.norm(pos[a] - pos[c], axis=1) / lr
    m = mask[a] | mask[c]
    return {"max": float(r[m].max()), "p99": float(np.quantile(r[m], 0.99)), "n_aretes": int(m.sum())}


def corr_(x, y):
    if np.std(x) < 1e-12 or np.std(y) < 1e-12:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def zone_triangles(TRI, mask):
    return TRI[mask[TRI].any(1)]


def tri_zone(TRI_z, rest, lbs, sq, Mv):
    if len(TRI_z) == 0:
        return {}
    ar, an, comp = [], [], 0
    for t in TRI_z:
        m = DEC.tri_mesure(t, rest, lbs, sq, Mv)
        ar.append(m["SQ"]["aire_ratio"])
        an.append(m["SQ"]["anisotropie"])
        comp += int(m["SQ"]["aire_ratio"] < 1)
    ar, an = np.array(ar), np.array(an)
    return {"aire_min_SQ": float(ar.min()), "aire_mediane_SQ": float(np.median(ar)),
            "anisotropie_mediane_SQ": float(np.median(an)), "triangles_compression": int(comp),
            "n_triangles": len(TRI_z)}


if __name__ == "__main__":
    os.makedirs(SORTIE, exist_ok=True)
    z, noms, rest, Wi, Ww, B, b, tot, A, sortie = INV.tous_les_defauts()
    N = len(rest)
    a, c = A[:, 0], A[:, 1]
    D = np.array(sortie["defauts_union"], int)
    js = INV.JSON_SQ
    TRI = CV._triangles(b, tot)
    lr_all = np.linalg.norm(rest[a] - rest[c], axis=1)
    h = float(np.median(lr_all))

    # ----- Bloc 1 : zones -----
    dist_D = S.bfs(N, A, D)
    zones = {"defauts_24": dist_D == 0, "voisin_1": (dist_D >= 0) & (dist_D <= 1),
             "voisin_2": (dist_D >= 0) & (dist_D <= 2), "large_6": (dist_D >= 0) & (dist_D <= 6)}
    zones_n = {k: int(v.sum()) for k, v in zones.items()}
    print("zones (sommets) :", zones_n, flush=True)

    # ----- Bloc 2 : configurations A, B, C, D sur la pose de référence (G 120°, D 0°) -----
    pm = pose_deux(z, noms, js, 120.0, 0.0)
    ref_old, _, _, _ = INV.pose_test(z, noms, js, "hanche_G", 120)
    print("écart pose_deux vs pose_test (doit être ~0) :", float(np.abs(pm - ref_old).max()), flush=True)
    lbs, Mv, Rsq = DEC.pipeline(Wi, Ww, B, pm, rest)
    sqA, sqC = sq_deux(lbs, rest, A, Rsq)
    configs = {"A_LBS": lbs, "B_SQ_arithmetique": sqA, "C_SQ_polaire": sqC, "D_C_propagation_separee": sqC}

    gG, gD = noms.index("mixamorig:LeftUpLeg"), noms.index("mixamorig:RightUpLeg")
    wG = np.where(Wi == gG, Ww, 0).sum(1)
    wD = np.where(Wi == gD, Ww, 0).sum(1)
    pur = (np.isclose(wG, 1) | np.isclose(wG, 0)) & (np.isclose(wD, 1) | np.isclose(wD, 0))
    cle = np.round(wG, 6) * 100 + np.round(wD, 6)
    interf = np.zeros(N, bool)
    dif = np.abs(cle[a] - cle[c]) > 1e-9
    interf[a[dif]] = True
    interf[c[dif]] = True
    bloc2 = {}
    for nom, pos in configs.items():
        glob = Ms.mesurer(pos, rest, b, tot, A, Mv=Mv)
        r = {"global": {"etirement_max": float(glob["etirement_max"]), "etirement_p99": float(glob["etirement_p99"]),
                        "retournements": int(glob["polygones_retournes"]),
                        "variation_volume": float(glob["variation_volume_relative"])}, "zones": {}}
        for zn, mz in zones.items():
            r["zones"][zn] = {"etirement": stretch_zone(pos, rest, A, mz),
                              "deplacement_sur_h_mediane": float(np.median(np.linalg.norm(pos - lbs, axis=1)[mz]) / h),
                              "triangles": tri_zone(zone_triangles(TRI, mz), rest, lbs, pos, Mv)}
        bloc2[nom] = r
        print(nom, "max global", round(r["global"]["etirement_max"], 4), "p99", round(r["global"]["etirement_p99"], 4),
              "retour", r["global"]["retournements"], "vol", round(r["global"]["variation_volume"], 5),
              "| zone 24 max", round(r["zones"]["defauts_24"]["etirement"]["max"], 4), flush=True)
    # D : propagation mesurée séparément (sommets à poids pur vs interfaces)
    disp = np.linalg.norm(sqC - lbs, axis=1)
    prof = S.profil(N, A, cle, pur & (wG > 0.5), pur & (wG < 0.5), disp, h)
    bloc2["D_C_propagation_separee"]["propagation_par_distance"] = prof
    bloc2["D_C_propagation_separee"]["deplacement_sur_h"] = {
        "sommets_purs": float(np.median(disp[pur] / h)) if pur.any() else None,
        "sommets_mixtes": float(np.median(disp[~pur] / h)),
        "interfaces": float(np.median(disp[interf] / h)) if interf.any() else None}
    print("D propagation (médiane en h) :", bloc2["D_C_propagation_separee"]["deplacement_sur_h"], flush=True)

    # ----- Bloc 3 : interaction poids / rotations (géométrie et poids fixes) -----
    arêtes_D = np.where(np.isin(a, D) | np.isin(c, D))[0]
    classes = {}
    for e in arêtes_D:
        wa, wc = wG[a[e]], wG[c[e]]
        cl = []
        for w_ in (wa, wc):
            if w_ >= 0.99:
                cl.append("G_pur")
            elif w_ <= 0.01:
                cl.append("D_pur")
            elif 0.4 <= w_ <= 0.6:
                cl.append("mixte_equilibre")
            else:
                cl.append("mixte_asymetrique")
        classes[int(e)] = " / ".join(sorted(cl))
    grille = []
    for thG in (60.0, 120.0):
        for thD in (0.0, 60.0, -60.0):
            pmx = pose_deux(z, noms, js, thG, thD)
            lbx, Mvx, Rsx = DEC.pipeline(Wi, Ww, B, pmx, rest)
            sqa, sqp = sq_deux(lbx, rest, A, Rsx)
            mismatch = angle_relatif(pmx, noms, B)
            llx = np.linalg.norm(lbx[a] - lbx[c], axis=1)
            lsa = np.linalg.norm(sqa[a] - sqa[c], axis=1)
            lsp = np.linalg.norm(sqp[a] - sqp[c], axis=1)
            for e in arêtes_D:
                grille.append({"thG": thG, "thD": thD, "ecart_angle_deg": mismatch, "e": int(e),
                               "amp_arith": float((lsa[e] - llx[e]) / lr_all[e]),
                               "amp_polaire": float((lsp[e] - llx[e]) / lr_all[e]),
                               "wG_moy": float((wG[a[e]] + wG[c[e]]) / 2),
                               "gradient_wG": float(abs(wG[a[e]] - wG[c[e]]) / lr_all[e]),
                               "longueur_repos_m": float(lr_all[e]), "classe": classes[int(e)]})
            print(f"thG {thG} thD {thD} ecart {mismatch:.1f} : amp arith moy {np.mean([g['amp_arith'] for g in grille[-len(arêtes_D):]]):+.4f}",
                  flush=True)
    # effet de l'angle à géométrie et poids fixes (intervention)
    par_ecart = {}
    for g in grille:
        k = f"{round(g['ecart_angle_deg'])}"
        par_ecart.setdefault(k, []).append(g["amp_arith"])
    effet_angle = {k: {"n": len(v), "amp_arith_mediane": float(np.median(v))} for k, v in sorted(par_ecart.items(), key=lambda t: float(t[0]))}
    # régression exploratoire (non causale)
    X = np.array([[g["ecart_angle_deg"], g["wG_moy"], g["gradient_wG"], g["longueur_repos_m"] / h] for g in grille])
    y = np.array([g["amp_arith"] for g in grille])
    Xs = (X - X.mean(0)) / (X.std(0) + 1e-12)
    Xd = np.column_stack([np.ones(len(y)), Xs])
    coef, *_ = np.linalg.lstsq(Xd, y, rcond=None)
    pred = Xd @ coef
    r2 = float(1 - ((y - pred) ** 2).sum() / max(((y - y.mean()) ** 2).sum(), 1e-12))
    regression = {"variables": ["ecart_angle", "poids_G_moyen", "gradient_poids", "longueur_sur_h"],
                  "coefficients_standardises": [float(v) for v in coef[1:]], "R2": r2,
                  "avertissement": "régression exploratoire sur des arêtes d'un même maillage : aucune causalité établie"}
    par_classe = {}
    for g in grille:
        if g["ecart_angle_deg"] is not None:
            par_classe.setdefault(g["classe"], []).append(g["amp_arith"])
    par_classe = {k: {"n": len(v), "amp_arith_mediane": float(np.median(v))} for k, v in par_classe.items()}

    # ----- Bloc 4 : décomposition de l'énergie -----
    Rab_mean = 0.5 * (Rsq[a] + Rsq[c])
    Rab_pol = DEC.polaire_gen(Rab_mean)                         # même cible que la configuration C
    d0 = rest[a] - rest[c]
    re = np.einsum("eij,ej->ei", Rab_pol, d0)                   # cible des arêtes (configuration C)
    res_arete = re - (lbs[a] - lbs[c])                          # résidu d'arête au LBS

    # décomposition exacte du LBS d'arête (indépendante de l'origine) :
    #   lbs_a − lbs_c = Mv_a·d + G,  avec  G = Σ_k (w_ak − w_ck) · T_k·r_c   (terme de gradient de poids)
    #   cible SQ − LBS = (Mv_a − R_ab)·d − G  (terme de rotation moyennée + terme de gradient)
    nb = len(B)
    Wd = np.zeros((N, nb))
    for col in range(Wi.shape[1]):
        np.add.at(Wd, (np.arange(N), Wi[:, col]), Ww[:, col])
    Tk_all = np.einsum("kij,kjl->kil", pm, np.linalg.inv(B))
    Tr = np.einsum("kij,nj->nki", Tk_all[:, :3, :3], rest) + Tk_all[:, :3, 3][None]   # T_k r_n (N,nb,3)
    G_e = np.einsum("ek,ekd->ed", Wd[a] - Wd[c], Tr[c])
    rigide_e = np.einsum("eij,ej->ei", Mv[a], d0)                       # Mv_a · d
    verif_G = float(np.abs((lbs[a] - lbs[c]) - rigide_e - G_e).max())
    rot_e = rigide_e - re                                               # (Mv_a − R_ab)·d
    amp_arith_e = (np.linalg.norm(sqA[a] - sqA[c], axis=1) - np.linalg.norm(lbs[a] - lbs[c], axis=1)) / lr_all
    gn_e = np.linalg.norm(G_e, axis=1) / lr_all
    rn_e = np.linalg.norm(rot_e, axis=1) / lr_all
    bloc4_arete = {
        "verification_identite_G_m": verif_G,
        "terme_gradient_G_sur_longueur_mediane": float(np.median(gn_e[arêtes_D])),
        "terme_rotation_sur_longueur_mediane": float(np.median(rn_e[arêtes_D])),
        "terme_rotation_sur_longueur_max": float(rn_e[arêtes_D].max()),
        "correlation_amp_arith_vs_terme_gradient": corr_(gn_e[arêtes_D], amp_arith_e[arêtes_D]),
        "correlation_amp_arith_vs_terme_rotation": corr_(rn_e[arêtes_D], amp_arith_e[arêtes_D]),
        "nb_aretes_defaut": int(len(arêtes_D)),
    }
    print("décomposition arêtes :", bloc4_arete, flush=True)
    g_vec = np.zeros((N, 3))
    np.add.at(g_vec, a, res_arete)
    np.add.at(g_vec, c, -res_arete)                             # g = somme des résidus incidents
    deg = np.bincount(np.concatenate([a, c]), minlength=N).astype(float)
    lam = LAM
    Mm = sp.coo_matrix((np.concatenate([deg + lam, -np.ones(2 * len(a))]),
                        (np.concatenate([np.arange(N), a, c]), np.concatenate([np.arange(N), c, a]))),
                       shape=(N, N)).tocsc()
    delta_theo = np.column_stack([factorized(Mm)(g_vec[:, k]) for k in range(3)])
    delta_num = sqC - lbs
    verif_identite = float(np.abs(delta_theo - delta_num).max())
    print("identité δ = M⁻¹ g, écart max :", verif_identite, flush=True)
    gn = np.linalg.norm(g_vec, axis=1)
    bloc4 = {
        "verification_identite_delta_M_inv_g_m": verif_identite,
        "norme_g_defauts_mediane": float(np.median(gn[D])),
        "norme_g_purs_mediane": float(np.median(gn[pur])) if pur.any() else None,
        "norme_g_purs_non_nuls_nb": int(((gn > 1e-12) & pur).sum()),
        "nb_sommets_purs": int(pur.sum()),
        "norme_g_interfaces_mediane": float(np.median(gn[interf])),
    }
    bloc4.update(bloc4_arete)
    L = sp.diags(deg) - sp.coo_matrix((np.ones(2 * len(a)), (np.concatenate([a, c]), np.concatenate([c, a]))), shape=(N, N))
    vals = eigsh(L.tocsc() + 1e-8 * sp.identity(N), k=6, which="SM", return_eigenvectors=False)
    bloc4["spectre_laplacien_plus_petites_valeurs"] = sorted(float(v) for v in vals)
    print("bloc4", bloc4, flush=True)

    res = {"zones_nb_sommets": zones_n, "bloc2": bloc2, "bloc3": {
        "nb_aretes_defaut": int(len(arêtes_D)), "effet_angle_geometrie_fixe": effet_angle,
        "par_classe_arete": par_classe, "regression": regression}, "bloc4": bloc4,
        "pas_de_proprietes_injectees": "poids, géométrie, transformations originaux ; seul l'angle de chaque cuisse varie au bloc 3"}
    with open(os.path.join(SORTIE, "resultats_intermediaire.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    print("ECRIT", flush=True)
