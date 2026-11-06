"""Phase 1 : identification du défaut réel sur le MAILLAGE MASCULIN ORIGINAL (aucune modification du maillage).

Poses : les 11 poses masculines pour lesquelles SQ (moyenne arithmétique, λ = 0,1) dépasse LBS sur l'étirement max
(docs/rapports/skinning/intermediaire_hanche_masc/lambda_morphologies.json). Les poses de validation candidates
(hanche G 45/135/150, hanche D 45, genou G 45/120) ne sont PAS utilisées ici.

Sortie : arêtes et triangles classés, avec témoins sans régression ; métriques historiques ET corrigées
(longueurs ≥ 5 mm, percentiles 50/90/95/99, classes de longueur, déplacements en mètres, aire par triangle,
retournements supplémentaires). Les volumes ne sont donnés que globalement (Ms.mesurer), car une variation de
volume locale dépend de l'origine choisie (voir erreur 196).
"""
import importlib.util
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SORTIE = os.path.join(RACINE, "docs", "rapports", "skinning", "defaut_reel")
LAM = 0.1
POSES = ["generative_hanche_G_75", "generative_hanche_G_105", "generative_hanche_G_120",
         "reelle_L_combo_flex120_genou90", "reelle_L_combo_flex60_abd20_int20_genou60", "reelle_L_flex120",
         "reelle_L_flex60", "reelle_R_combo_flex120_genou90", "reelle_R_combo_flex60_abd20_int20_genou60",
         "reelle_R_flex120", "reelle_R_flex60"]
SEUIL_LR = 0.005  # 5 mm : seuil de longueur pour les métriques corrigées


def charger(nom):
    spec = importlib.util.spec_from_file_location(nom, os.path.join(HERE, nom + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


DEC = charger("investigation_decomposition")
INV = DEC.INV
P, EXP, ARAP, Ms = INV.P, INV.EXP, INV.ARAP, INV.Ms
POSE_FN = charger("investigation_lambda_morphos").pose_hanche_G


def matrices_bones(z, pm):
    """T_k = pm_k · inv(B_k) ; retourne (K,3,3) rotations et (K,3) translations (repère monde, pose courante)."""
    B = z["bones_rest_monde"]
    T = np.einsum("kij,kjl->kil", pm, np.linalg.inv(B))
    return T[:, :3, :3], T[:, :3, 3]


def poids_denses(z, N):
    Wi, Ww = z["W_idx"], z["W_w"]
    K = len(z["noms_os"])
    W = np.zeros((N, K))
    rows = np.repeat(np.arange(N), Wi.shape[1])
    np.add.at(W, (rows, Wi.ravel()), Ww.ravel())
    return W


def triangles_from(b, tot):
    debut = np.concatenate([[0], np.cumsum(tot)[:-1]])
    tris = []
    for d0, n in zip(debut, tot):
        p = b[d0:d0 + n]
        for k in range(1, n - 1):
            tris.append((p[0], p[k], p[k + 1]))
    return np.array(tris)


def aire_normale(p, tris):
    n = np.cross(p[tris[:, 1]] - p[tris[:, 0]], p[tris[:, 2]] - p[tris[:, 0]])
    return 0.5 * np.linalg.norm(n, axis=1), n


if __name__ == "__main__":
    os.makedirs(SORTIE, exist_ok=True)
    z = np.load(os.path.join(INV.DONNEES, "skin", "poses2.npz"))
    noms = [str(n) for n in z["noms_os"]]
    js = os.path.join(RACINE, "docs/rapports/skinning/anatomie/squelette_masc.json")
    rest, Wi, Ww, B = z["rest_monde"], z["W_idx"], z["W_w"], z["bones_rest_monde"]
    b, tot = z["b_boucle"], z["b_tot"]
    N = len(rest)
    A = Ms.aretes(b, tot, N)
    a, c = A[:, 0], A[:, 1]
    lr0 = np.linalg.norm(rest[a] - rest[c], axis=1)
    W = poids_denses(z, N)
    tris = triangles_from(b, tot)
    aire0, n0 = aire_normale(rest, tris)
    cla = np.quantile(lr0, [0, 0.2, 0.4, 0.6, 0.8, 1.0])
    classe_arete = np.clip(np.searchsorted(cla, lr0, side="right") - 1, 0, 4)
    print("arêtes", len(A), "triangles", len(tris), "N", N, "os", len(noms), flush=True)

    # --- vérification de la décomposition sur ce maillage (une pose) ---
    pm0 = POSE_FN(z, noms, js, 120)
    lbs0, Mv0, Rsq0 = DEC.pipeline(Wi, Ww, B, pm0, rest)
    R0, t0 = matrices_bones(z, pm0)
    lbs_rec = np.einsum("nk,nki->ni", W, np.einsum("kij,nj->nki", R0, rest) + t0[None])
    erreur_lbs_rec = float(np.abs(lbs_rec - lbs0).max())
    print("vérification LBS reconstruit (T_k = pm·inv(B)) :", erreur_lbs_rec, flush=True)

    resultats = {"verification_LBS_reconstruit_m": erreur_lbs_rec, "poses": {}}
    candidats_edges, candidats_tris, controles = [], [], []
    resultats_zone = {}

    for nom in POSES:
        if nom.startswith("generative_hanche_G_"):
            th = int(nom.rsplit("_", 1)[1])
            pm = POSE_FN(z, noms, js, th)
        else:
            pm = z[nom[len("reelle_"):] + "__os"]
        lbs, Mv, Rsq = DEC.pipeline(Wi, Ww, B, pm, rest)
        sq = ARAP.solve_fixe(lbs, rest, A, Rsq, LAM)
        R, t = matrices_bones(z, pm)
        # --- arêtes ---
        l_L = np.linalg.norm(lbs[a] - lbs[c], axis=1)
        l_S = np.linalg.norm(sq[a] - sq[c], axis=1)
        rho_L = l_L / np.maximum(lr0, 1e-12)
        rho_S = l_S / np.maximum(lr0, 1e-12)
        exc = rho_S - rho_L
        dW = W[a] - W[c]
        Tc = np.einsum("kij,ej->eki", R, rest[c]) + t[None]
        G = np.einsum("ek,eki->ei", dW, Tc)
        Mvd = np.einsum("eij,ej->ei", Mv[a], rest[a] - rest[c])
        err_id = float(np.abs((lbs[a] - lbs[c]) - (Mvd + G)).max())
        ok5 = lr0 >= SEUIL_LR
        # classes de longueur
        par_classe = []
        for k in range(5):
            m = classe_arete == k
            par_classe.append({"classe": k, "lr_min_m": float(cla[k]), "lr_max_m": float(cla[k + 1]),
                               "nb_aretes": int(m.sum()),
                               "part_regression": float((exc[m] > 0.05).mean()) if m.any() else None,
                               "exc_mediane": float(np.median(exc[m])) if m.any() else None})
        # --- triangles : déformation et retournements ---
        Tt_L = np.array([DEC.tri_mesure(tr, rest, lbs, sq, Mv) for tr in tris])
        s_L1 = np.array([t_["LBS"]["s1"] for t_ in Tt_L]); s_L2 = np.array([t_["LBS"]["s2"] for t_ in Tt_L])
        s_S1 = np.array([t_["SQ"]["s1"] for t_ in Tt_L]); s_S2 = np.array([t_["SQ"]["s2"] for t_ in Tt_L])
        aL, nL = aire_normale(lbs, tris)
        aS, nS = aire_normale(sq, tris)
        Mt = np.array([Mv[tr].mean(0) for tr in tris])
        Rref = DEC.polaire_gen(Mt)
        ref_n = np.einsum("tij,tj->ti", Rref, n0 / np.maximum(np.linalg.norm(n0, axis=1, keepdims=True), 1e-12))
        flip_L = np.einsum("ti,ti->t", nL / np.maximum(np.linalg.norm(nL, axis=1, keepdims=True), 1e-12), ref_n) < 0
        flip_S = np.einsum("ti,ti->t", nS / np.maximum(np.linalg.norm(nS, axis=1, keepdims=True), 1e-12), ref_n) < 0
        nouveaux = flip_S & ~flip_L
        dist_S = np.maximum(np.abs(np.log(np.maximum(s_S1, 1e-12))), np.abs(np.log(np.maximum(s_S2, 1e-12))))
        dist_L = np.maximum(np.abs(np.log(np.maximum(s_L1, 1e-12))), np.abs(np.log(np.maximum(s_L2, 1e-12))))
        aire_ratio_S = aS / np.maximum(aire0, 1e-12)
        aire_ratio_L = aL / np.maximum(aire0, 1e-12)
        volume = Ms.mesurer(sq, rest, b, tot, A, Mv=Mv)
        volume_L = Ms.mesurer(lbs, rest, b, tot, A, Mv=Mv)

        def qs(x):
            return {f"p{p}": float(np.quantile(x, p / 100)) for p in (50, 90, 95, 99)}

        resultats["poses"][nom] = {
            "erreur_decomposition_m": err_id,
            "aretes": {"nb": int(len(A)), "nb_ge5mm": int(ok5.sum()),
                       "rho_LBS": qs(rho_L[ok5]), "rho_SQ": qs(rho_S[ok5]), "exc": qs(exc[ok5]),
                       "max_rho_LBS_tout": float(rho_L.max()), "max_rho_SQ_tout": float(rho_S.max()),
                       "nb_regression_ge5mm_seuil_0.05": int((exc[ok5] > 0.05).sum()),
                       "deplacement_max_m_LBS_vs_SQ": float(np.linalg.norm(sq - lbs, axis=1).max()),
                       "classes_longueur": par_classe},
            "triangles": {"nb": int(len(tris)), "aire_ratio_LBS": qs(aire_ratio_L),
                          "aire_ratio_SQ": qs(aire_ratio_S), "distorsion_LBS_p99": float(np.quantile(dist_L, 0.99)),
                          "distorsion_SQ_p99": float(np.quantile(dist_S, 0.99)),
                          "retournements_LBS": int(flip_L.sum()), "retournements_SQ": int(flip_S.sum()),
                          "nouveaux_retournements_SQ": int(nouveaux.sum())},
            "volume_global_relatif": {"LBS": float(volume_L["variation_volume_relative"]),
                                      "SQ": float(volume["variation_volume_relative"])},
            "deplacement_max_m": float(np.linalg.norm(sq - lbs, axis=1).max()),
        }
        print(nom, "exc p99", round(resultats["poses"][nom]["aretes"]["exc"]["p99"], 3),
              "reg>0.05", resultats["poses"][nom]["aretes"]["nb_regression_ge5mm_seuil_0.05"],
              "flips LBS/SQ/nouveaux", int(flip_L.sum()), int(flip_S.sum()), int(nouveaux.sum()), flush=True)

        # --- enregistrements détaillés (arêtes) ---
        cG_, _, _ = P.articulation(js, EXP.prefixe(noms) + "LeftUpLeg")
        cD_, _, _ = P.articulation(js, EXP.prefixe(noms) + "RightUpLeg")
        milieu_h = (cG_ + cD_) / 2
        reg_m = ok5 & (exc > 0.05)
        centre_reg = np.mean(np.vstack([rest[a[reg_m]], rest[c[reg_m]]]), axis=0) if reg_m.any() else None
        d_milieu_reg = np.linalg.norm(0.5 * (rest[a[reg_m]] + rest[c[reg_m]]) - milieu_h, axis=1) if reg_m.any() else np.array([])
        zone_hanche = {
            "nb_regressees": int(reg_m.sum()),
            "centre_regressees_repos": None if centre_reg is None else centre_reg.round(4).tolist(),
            "part_dans_0_30m_du_milieu_hanches": float((d_milieu_reg < 0.30).mean()) if reg_m.any() else None,
            "part_dans_0_15m_du_milieu_hanches": float((d_milieu_reg < 0.15).mean()) if reg_m.any() else None,
            "sommets_distincts": int(len(np.unique(np.concatenate([a[reg_m], c[reg_m]])))) if reg_m.any() else 0,
            "distance_milieu_hanches_max_m": float(d_milieu_reg.max()) if reg_m.any() else None,
        }
        resultats_zone[nom] = zone_hanche
        dom_a = np.argmax(W[a], axis=1)
        dom_c = np.argmax(W[c], axis=1)
        for e in np.where(ok5)[0]:
            candidats_edges.append({
                "pose": nom, "sommets": [int(a[e]), int(c[e])],
                "repos_a": rest[a[e]].round(5).tolist(), "repos_c": rest[c[e]].round(5).tolist(),
                "pos_LBS_a": lbs[a[e]].round(5).tolist(), "pos_LBS_c": lbs[c[e]].round(5).tolist(),
                "pos_SQ_a": sq[a[e]].round(5).tolist(), "pos_SQ_c": sq[c[e]].round(5).tolist(),
                "longueur_repos_m": float(lr0[e]), "longueur_LBS_m": float(l_L[e]), "longueur_SQ_m": float(l_S[e]),
                "rho_LBS": float(rho_L[e]), "rho_SQ": float(rho_S[e]), "exc": float(exc[e]),
                "poids_a": {noms[k]: float(W[a[e], k]) for k in np.where(W[a[e]] > 1e-6)[0]},
                "poids_c": {noms[k]: float(W[c[e], k]) for k in np.where(W[c[e]] > 1e-6)[0]},
                "delta_poids_L1": float(np.abs(dW[e]).sum()),
                "gradient_par_m": float(np.abs(dW[e]).sum() / max(lr0[e], 1e-12)),
                "os_dominant_a": noms[dom_a[e]], "os_dominant_c": noms[dom_c[e]],
                "G_norme_m": float(np.linalg.norm(G[e])), "G_sur_longueur": float(np.linalg.norm(G[e]) / lr0[e]),
                "Mvd_sur_longueur": float(np.linalg.norm(Mvd[e]) / lr0[e]),
                "contribution_G_identite_erreur_m": err_id,
                "classe_longueur": int(classe_arete[e]),
            })
        ex_ok = np.where(ok5 & (exc <= 0) & (lr0 >= 0.015) & (lr0 <= 0.05))[0]  # témoins appariés en longueur (0,015–0,05 m)
        rng = np.random.default_rng(11)
        for e in rng.choice(ex_ok, size=min(100, len(ex_ok)), replace=False):
            controles.append({"pose": nom, "sommets": [int(a[e]), int(c[e])], "exc": float(exc[e]),
                              "longueur_repos_m": float(lr0[e]), "rho_SQ": float(rho_S[e]), "rho_LBS": float(rho_L[e]),
                              "G_sur_longueur": float(np.linalg.norm(G[e]) / lr0[e]),
                              "gradient_par_m": float(np.abs(dW[e]).sum() / max(lr0[e], 1e-12))})
        # triangles
        for t_i in np.argsort(-dist_S)[:300]:
            candidats_tris.append({"pose": nom, "sommets": [int(v) for v in tris[t_i]],
                                   "aire_repos": float(aire0[t_i]), "aire_LBS": float(aL[t_i]), "aire_SQ": float(aS[t_i]),
                                   "distorsion_SQ": float(dist_S[t_i]), "distorsion_LBS": float(dist_L[t_i]),
                                   "retournement_SQ_nouveau": bool(nouveaux[t_i])})

    # sélection finale : 100 arêtes les plus régressées (toutes poses confondues), 100 témoins, 100 triangles
    candidats_edges.sort(key=lambda r: -r["exc"])
    top_aretes = candidats_edges[:100]
    temoins = controles[:100]
    candidats_tris.sort(key=lambda r: -r["distorsion_SQ"])
    top_tris = candidats_tris[:100]
    retourn = [t_ for t_ in candidats_tris if t_["retournement_SQ_nouveau"]]
    resultats["zone_des_regressions_par_pose"] = resultats_zone
    resultats["top100_aretes_regression"] = top_aretes
    resultats["temoins_sans_regression"] = temoins
    resultats["top100_triangles_distorsion"] = top_tris
    resultats["retournements_SQ_nouveaux"] = retourn[:200]
    resultats["retournements_SQ_nouveaux_total"] = int(sum(v["triangles"]["nouveaux_retournements_SQ"]
                                                          for v in resultats["poses"].values()))
    with open(os.path.join(SORTIE, "defaut_reel_masculin.json"), "w", encoding="utf-8") as f:
        json.dump(resultats, f, indent=1, ensure_ascii=False)
    print("ECRIT", "aretes", len(top_aretes), "temoins", len(temoins), "tris", len(top_tris), flush=True)
