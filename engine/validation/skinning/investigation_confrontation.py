"""Phases 2 et 3 : confrontation entre patchs synthétiques et défaut réel, puis analyse des deux échecs.

Phase 2 : métriques locales réelles (zone hanche, pose L_flex120 du maillage masculin) comparées à des patchs
synthétiques dont on fait varier UN paramètre à la fois à partir d'une référence « appariée » :
    h   : pas d'arête (mesuré) ; w : largeur de transition des poids (liée au gradient mesuré) ;
    θ   : angles réels des cuisses ; arrangement : lisse (le long du gradient) ou aléatoire.
Phase 3A : écarts SQ − LBS sur sommets à poids purs, en fonction de la distance au bord de la zone mixte,
           pour le maillage réel et pour un patch à solution connue.
Phase 3B : triangles qui retournent dans SQ et pas dans LBS, dans la configuration synthétique qui en produit.
Aucun paramètre de validation n'est modifié. Les poses de validation candidates ne sont pas utilisées.
"""
import importlib.util
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SORTIE = os.path.join(RACINE, "docs", "rapports", "skinning", "defaut_reel")
LAM = 0.1


def charger(nom):
    spec = importlib.util.spec_from_file_location(nom, os.path.join(HERE, nom + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


DEC = charger("investigation_decomposition")
INV = DEC.INV
P, EXP, ARAP, Ms = INV.P, INV.EXP, INV.ARAP, INV.Ms
S = charger("investigation_synthetique")
TG = charger("investigation_terme_G")
DR = charger("investigation_defaut_reel")


def angle_rot(R):
    return float(np.degrees(np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1))))


def metriques_zone(rest, A, lbs, sq, Rs, ts, W, mask_zone):
    """Métriques de la zone : mêmes définitions que investigation_defaut_reel (arêtes ≥ 5 mm pour le réel)."""
    a, c = A[:, 0], A[:, 1]
    lr = np.linalg.norm(rest[a] - rest[c], axis=1)
    z = mask_zone[a] & mask_zone[c]
    ok = z & (lr >= 0.005)  # mêmes arêtes ≥ 5 mm que investigation_defaut_reel
    rho_L = np.linalg.norm(lbs[a] - lbs[c], axis=1) / np.maximum(lr, 1e-12)
    rho_S = np.linalg.norm(sq[a] - sq[c], axis=1) / np.maximum(lr, 1e-12)
    exc = rho_S - rho_L
    dW = W[a] - W[c]
    Tc = np.einsum("kij,ej->eki", Rs, rest[c]) + ts[None]
    G = np.einsum("ek,eki->ei", dW, Tc)
    Mv = np.einsum("nk,kij->nij", W, Rs)
    Mvd = np.einsum("eij,ej->ei", Mv[a], rest[a] - rest[c])
    grad = np.abs(dW).sum(1) / np.maximum(lr, 1e-12)
    e = ok
    return {
        "nb_aretes": int(e.sum()),
        "longueur_mediane_m": float(np.median(lr[e])),
        "gradient_L1_mediane_par_m": float(np.median(grad[e])),
        "G_sur_longueur_mediane": float(np.median(np.linalg.norm(G[e], axis=1) / lr[e])),
        "Mvd_sur_longueur_mediane": float(np.median(np.linalg.norm(Mvd[e], axis=1) / lr[e])),
        "part_regression_0_05": float((exc[e] > 0.05).mean()),
        "exc_p50": float(np.quantile(exc[e], 0.5)),
        "exc_p90": float(np.quantile(exc[e], 0.9)),
        "exc_p99": float(np.quantile(exc[e], 0.99)),
        "rho_SQ_p99": float(np.quantile(rho_S[e], 0.99)),
    }


def patch_parametre(h, largeur, th_G, th_D, arrangement, nx=21, rng_seed=0):
    """Patch plat : pelvis au-dessus de y = 0 ; transition de largeur `largeur` ; cuisses séparées en x = 0.
    Centres d'articulation réels (repère du patch : origine au milieu des hanches)."""
    xs = (np.arange(nx) - (nx - 1) / 2) * h
    ys = xs.copy()
    rest, tris, A = S.grille(xs, ys)
    X, Y = rest[:, 0], rest[:, 1]
    pf = np.clip(Y / largeur, 0, 1)
    thigh = 1 - pf
    side = np.clip(0.5 + X / largeur, 0, 1)  # 1 pour x positif (cuisse G), 0 pour x négatif (cuisse D)
    wG = thigh * side
    wD = thigh * (1 - side)
    if arrangement == "aleatoire":
        rng = np.random.default_rng(rng_seed)
        perm = rng.permutation(len(X))
        wG, wD = wG[perm], wD[perm]
        pf = pf[perm]
        thigh = 1 - pf
        # recalcul cohérent : mêmes valeurs, ordre des sommets permuté
        W = np.column_stack([pf, wG, wD])
    else:
        W = np.column_stack([pf, wG, wD])
    # centres : hanches au niveau y = 0 et x = ±0,1 (cotes réelles approximées à l'échelle du patch)
    Rs, ts = TG.transformations([0, th_G, th_D], [(0, 0, 0), (0.1, 0, 0), (-0.1, 0, 0)])
    lbs, Mv = TG.lbs_et_mv(rest, W, Rs, ts)
    sq = ARAP.solve_fixe(lbs, rest, A, DEC.polaire_gen(Mv), LAM)
    return {"rest": rest, "tris": tris, "A": A, "W": W, "Rs": Rs, "ts": ts, "lbs": lbs, "sq": sq, "Mv": Mv}


if __name__ == "__main__":
    os.makedirs(SORTIE, exist_ok=True)
    z = np.load(os.path.join(INV.DONNEES, "skin", "poses2.npz"))
    noms = [str(n) for n in z["noms_os"]]
    js = os.path.join(RACINE, "docs/rapports/skinning/anatomie/squelette_masc.json")
    rest, Wi, Ww, B = z["rest_monde"], z["W_idx"], z["W_w"], z["bones_rest_monde"]
    b, tot = z["b_boucle"], z["b_tot"]
    N = len(rest)
    A = Ms.aretes(b, tot, N)
    W = DR.poids_denses(z, N)
    cG, _, _ = P.articulation(js, EXP.prefixe(noms) + "LeftUpLeg")
    cD, _, _ = P.articulation(js, EXP.prefixe(noms) + "RightUpLeg")
    milieu = (cG + cD) / 2
    zone = np.linalg.norm(rest - milieu, axis=1) < 0.30

    out = {"phase2": {}, "phase3A": {}, "phase3B": {}}

    # ---------------- Phase 2 : réel ----------------
    pm = z["L_flex120__os"]
    lbs, Mv, Rsq = DEC.pipeline(Wi, Ww, B, pm, rest)
    sq = ARAP.solve_fixe(lbs, rest, A, Rsq, LAM)
    R_b, t_b = DR.matrices_bones(z, pm)
    angles_reels = {noms[k]: angle_rot(R_b[k]) for k in range(len(noms)) if angle_rot(R_b[k]) > 1.0}
    reel = metriques_zone(rest, A, lbs, sq, R_b, t_b, W, zone)
    out["phase2"]["reel_zone_L_flex120"] = {"metriques": reel,
                                            "angles_os_remarquables_deg": {k: round(v, 1) for k, v in angles_reels.items()
                                                                           if "UpLeg" in k or "Hips" in k or "Spine" in k}}
    print("REEL", {k: round(v, 4) if isinstance(v, float) else v for k, v in reel.items()}, flush=True)
    print("angles", {k: round(v, 1) for k, v in angles_reels.items() if "UpLeg" in k}, flush=True)

    # Largeur de transition appariée au gradient réel : gradient L1 = 2·pente, pente = 1/largeur  ⇒  largeur = 2 / g
    g_reel = reel["gradient_L1_mediane_par_m"]
    h_reel = reel["longueur_mediane_m"]
    largeur_appariee = 2.0 / g_reel
    th_G_reel = angles_reels.get("mixamorig:LeftUpLeg", 120.0)
    th_D_reel = angles_reels.get("mixamorig:RightUpLeg", 0.0)
    print("appariement : h", round(h_reel, 4), "largeur", round(largeur_appariee, 4), "θG", th_G_reel, "θD", th_D_reel, flush=True)

    variantes = {
        "V0_apparie": dict(h=h_reel, largeur=largeur_appariee, th_G=th_G_reel, th_D=th_D_reel, arrangement="lisse"),
        "V1_largeur_0.30": dict(h=h_reel, largeur=0.30, th_G=th_G_reel, th_D=th_D_reel, arrangement="lisse"),
        "V2_pas_0.10": dict(h=0.10, largeur=largeur_appariee, th_G=th_G_reel, th_D=th_D_reel, arrangement="lisse"),
        "V3_angles_120_0": dict(h=h_reel, largeur=largeur_appariee, th_G=120.0, th_D=0.0, arrangement="lisse"),
        "V4_angles_90_0": dict(h=h_reel, largeur=largeur_appariee, th_G=90.0, th_D=0.0, arrangement="lisse"),
        "V5_arrangement_aleatoire": dict(h=h_reel, largeur=largeur_appariee, th_G=th_G_reel, th_D=th_D_reel,
                                         arrangement="aleatoire"),
    }
    out["phase2"]["variantes"] = {}
    for nom, v in variantes.items():
        p = patch_parametre(v["h"], v["largeur"], v["th_G"], v["th_D"], v["arrangement"])
        m = metriques_zone(p["rest"], p["A"], p["lbs"], p["sq"], p["Rs"], p["ts"], p["W"],
                           np.ones(len(p["rest"]), bool))
        out["phase2"]["variantes"][nom] = {"parametres": v, "metriques": m}
        print(nom, {k: round(x, 4) if isinstance(x, float) else x for k, x in m.items()}, flush=True)

    # ---------------- Phase 3A : poids purs ----------------
    pur_mask = np.all((W > 1 - 1e-9) | (W < 1e-9), axis=1)
    # sommets dont le 1-anneau est pur ET dont le poids est 100 % pour le même os
    dom = np.argmax(W, axis=1)
    voisin_pur = pur_mask.copy()
    for u, v_ in A:
        if not pur_mask[u] or not pur_mask[v_] or dom[u] != dom[v_]:
            voisin_pur[u] = False
            voisin_pur[v_] = False
    src = S.interface(N, A, np.where(pur_mask, dom, -1))
    dist = S.bfs(N, A, src)
    dev = np.linalg.norm(sq - lbs, axis=1)
    par_dist = {}
    for d_ in range(0, 8):
        m_ = pur_mask & (dist == d_)
        if m_.any():
            par_dist[str(d_)] = {"nb": int(m_.sum()), "deplacement_max_m": float(dev[m_].max()),
                                 "deplacement_median_m": float(np.median(dev[m_]))}
    out["phase3A"]["reel_pose_L_flex120"] = {
        "nb_sommets_pur_voisinage_pur_meme_os": int(voisin_pur.sum()),
        "deplacement_max_voisinage_pur_m": float(dev[voisin_pur].max()) if voisin_pur.any() else None,
        "deplacement_par_distance_au_bord_pur": par_dist,
    }
    print("3A réel", out["phase3A"]["reel_pose_L_flex120"]["deplacement_max_voisinage_pur_m"],
          out["phase3A"]["reel_pose_L_flex120"]["nb_sommets_pur_voisinage_pur_meme_os"], flush=True)

    # même mesure sur le patch à solution connue (V0)
    p = patch_parametre(h_reel, largeur_appariee, th_G_reel, th_D_reel, "lisse")
    pur_p = np.all((p["W"] > 1 - 1e-9) | (p["W"] < 1e-9), axis=1)
    dom_p = np.argmax(p["W"], axis=1)
    Ap = p["A"]
    vp = pur_p.copy()
    for u, v_ in Ap:
        if not pur_p[u] or not pur_p[v_] or dom_p[u] != dom_p[v_]:
            vp[u] = False
            vp[v_] = False
    dist_p = S.bfs(len(p["rest"]), Ap, S.interface(len(p["rest"]), Ap, np.where(pur_p, dom_p, -1)))
    devp = np.linalg.norm(p["sq"] - p["lbs"], axis=1)
    out["phase3A"]["patch_V0"] = {
        "nb_sommets_pur_voisinage_pur_meme_os": int(vp.sum()),
        "deplacement_max_voisinage_pur_m": float(devp[vp].max()) if vp.any() else None,
        "deplacement_par_distance_au_bord_pur": {str(d_): {
            "nb": int((pur_p & (dist_p == d_)).sum()),
            "deplacement_max_m": float(devp[pur_p & (dist_p == d_)].max()) if (pur_p & (dist_p == d_)).any() else None}
            for d_ in range(0, 8)},
    }
    print("3A patch", out["phase3A"]["patch_V0"]["deplacement_max_voisinage_pur_m"], flush=True)

    # ---------------- Phase 3B : triangles retournés dans SQ et pas dans LBS ----------------
    tris_p = p["tris"]
    n0 = np.cross(p["rest"][tris_p[:, 1]] - p["rest"][tris_p[:, 0]], p["rest"][tris_p[:, 2]] - p["rest"][tris_p[:, 0]])
    nL = np.cross(p["lbs"][tris_p[:, 1]] - p["lbs"][tris_p[:, 0]], p["lbs"][tris_p[:, 2]] - p["lbs"][tris_p[:, 0]])
    nS = np.cross(p["sq"][tris_p[:, 1]] - p["sq"][tris_p[:, 0]], p["sq"][tris_p[:, 2]] - p["sq"][tris_p[:, 0]])
    Mt = np.array([p["Mv"][t].mean(0) for t in tris_p])
    ref = np.einsum("tij,tj->ti", DEC.polaire_gen(Mt), n0 / np.linalg.norm(n0, axis=1, keepdims=True))
    fL = np.einsum("ti,ti->t", nL, ref) < 0
    fS = np.einsum("ti,ti->t", nS, ref) < 0
    nouveaux = np.where(fS & ~fL)[0]
    detail = []
    for t_ in nouveaux:
        i, j, k = tris_p[t_]
        detail.append({"sommets": [int(i), int(j), int(k)],
                       "poids_sommets": [p["W"][v].round(3).tolist() for v in (i, j, k)],
                       "aire_repos": float(0.5 * np.linalg.norm(n0[t_])),
                       "aire_SQ": float(0.5 * np.linalg.norm(nS[t_])),
                       "produit_scalaire_normale_SQ_reference": float(np.dot(nS[t_] / np.linalg.norm(nS[t_]), ref[t_]))})
    out["phase3B"]["patch_V0_nouveaux_retournements"] = detail
    out["phase3B"]["nb_nouveaux_retournements_patch_V0"] = int(len(nouveaux))
    print("3B V0 nouveaux", len(nouveaux), flush=True)

    # cas synthétique qui produit des retournements supplémentaires (3 configurations de la phase précédente)
    hist_M = json.load(open(os.path.join(RACINE, "docs/rapports/skinning/factorielle/descriptif_morphologies.json")))["masculin"][
        "histogramme_wG_mixtes_10_classes"]
    cfg = TG.patch("plat", "A", False, 0.0, "lisse", hist_M, (120, -60))
    tc = cfg["tris"]
    n0c = np.cross(cfg["rest"][tc[:, 1]] - cfg["rest"][tc[:, 0]], cfg["rest"][tc[:, 2]] - cfg["rest"][tc[:, 0]])
    nLc = np.cross(cfg["lbs"][tc[:, 1]] - cfg["lbs"][tc[:, 0]], cfg["lbs"][tc[:, 2]] - cfg["lbs"][tc[:, 0]])
    nSc = np.cross(cfg["sq"][tc[:, 1]] - cfg["sq"][tc[:, 0]], cfg["sq"][tc[:, 2]] - cfg["sq"][tc[:, 0]])
    Mtc = np.array([cfg["Mv"][t].mean(0) for t in tc])
    refc = np.einsum("tij,tj->ti", DEC.polaire_gen(Mtc), n0c / np.linalg.norm(n0c, axis=1, keepdims=True))
    fLc = np.einsum("ti,ti->t", nLc, refc) < 0
    fSc = np.einsum("ti,ti->t", nSc, refc) < 0
    nvc = np.where(fSc & ~fLc)[0]
    det_c = []
    for t_ in nvc:
        i, j, k = tc[t_]
        det_c.append({"sommets": [int(i), int(j), int(k)],
                      "poids_sommets": [cfg["W"][v].round(3).tolist() for v in (i, j, k)],
                      "aire_repos": float(0.5 * np.linalg.norm(n0c[t_])),
                      "aire_LBS": float(0.5 * np.linalg.norm(nLc[t_])),
                      "aire_SQ": float(0.5 * np.linalg.norm(nSc[t_])),
                      "ecart_poids_max_arete": float(max(np.abs(cfg["W"][i] - cfg["W"][j]).max(),
                                                         np.abs(cfg["W"][j] - cfg["W"][k]).max(),
                                                         np.abs(cfg["W"][k] - cfg["W"][i]).max()))})
    out["phase3B"]["config_120_moins60_lisse"] = {"nb_nouveaux_retournements": int(len(nvc)), "triangles": det_c}
    print("3B config", len(nvc), flush=True)

    with open(os.path.join(SORTIE, "confrontation.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print("ECRIT", flush=True)
