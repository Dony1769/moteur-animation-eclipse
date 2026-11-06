"""Comparaison rigoureuse des trois morphologies (masculin, féminin, Maria) avec un protocole identique.

Phase 1 : mêmes 29 poses (noms identiques ; génératives de hanche G calculées avec la même convention) ;
          mêmes définitions de métriques pour les trois morphologies ; métriques normalisées par la distance
          entre les centres de hanche (dimension anatomique commune).
Phase 2 : régions anatomiques définies en coordonnées normalisées par rapport aux centres articulaires
          (aucun transfert de poids entre maillages).
Phase 3 : tests contrôlés sur le MÊME maillage (interventions) pour les hypothèses 1 à 6 :
          H1 répartition spatiale des poids (permutation et réarrangement lisse, histogramme conservé) ;
          H2 courbure / géométrie locale (dilatation locale de la zone entrejambe) ;
          H3 taille des arêtes locales (même intervention, lecture en taille d'arête) ;
          H4 position des articulations (décalage du pivot de la hanche de ±1 cm) ;
          H5 propagation / conditions aux limites (balayage de λ et profil de propagation) ;
          H6 volume (corrélation seulement : pas de volume local bien défini).
Phase 4 : retournements synthétiques (voir investigation_retournements.py).
"""
import importlib.util
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SORTIE = os.path.join(RACINE, "docs", "rapports", "skinning", "comparaison_morphologies")
LAM = 0.1
MORPHS = ["masculin", "feminin", "maria"]


def charger(nom):
    spec = importlib.util.spec_from_file_location(nom, os.path.join(HERE, nom + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


DEC = charger("investigation_decomposition")
INV = DEC.INV
P, EXP, ARAP, Ms = INV.P, INV.EXP, INV.ARAP, INV.Ms
DR = charger("investigation_defaut_reel")
TG = charger("investigation_terme_G")
LM = charger("investigation_lambda_morphos")
S = charger("investigation_synthetique")

POSES = [k for k in json.load(open(os.path.join(RACINE, "docs/rapports/skinning/intermediaire_hanche_masc/lambda_morphologies.json")))["masculin"]["poses"]]
SUB = ["reelle_L_flex120", "generative_hanche_G_120", "reelle_L_combo_flex120_genou90"]


def quant(x):
    x = np.asarray(x, float)
    if x.size == 0:
        return {"p50": None, "p90": None, "p95": None, "p99": None, "max": None, "n": 0}
    return {"p50": float(np.quantile(x, 0.5)), "p90": float(np.quantile(x, 0.9)),
            "p95": float(np.quantile(x, 0.95)), "p99": float(np.quantile(x, 0.99)),
            "max": float(x.max()), "n": int(x.size)}


def normaliser(W):
    """Poids normalisés par somme, comme methodes._valides (le pipeline d'origine normalise ; le féminin a des
    sommes de 0,878 à 1,0). Sans effet sur les maillages déjà normalisés."""
    s = W.sum(1, keepdims=True)
    return np.where(s > 1e-12, W / np.maximum(s, 1e-12), W)


def charger_morph(m):
    npz, js_rel = EXP.MORPHOS[m]
    z = np.load(os.path.join(INV.DONNEES, npz))
    noms = [str(n) for n in z["noms_os"]]
    js = os.path.join(RACINE, js_rel)
    rest, Wi, Ww, B = z["rest_monde"], z["W_idx"], z["W_w"], z["bones_rest_monde"]
    b, tot = z["b_boucle"], z["b_tot"]
    N = len(rest)
    pref = EXP.prefixe(noms)
    cG = P.articulation(js, pref + "LeftUpLeg")[0]
    cD = P.articulation(js, pref + "RightUpLeg")[0]
    kG = P.articulation(js, pref + "LeftLeg")[0]
    kD = P.articulation(js, pref + "RightLeg")[0]
    return {"nom": m, "z": z, "noms": noms, "js": js, "rest": rest, "Wi": Wi, "Ww": Ww, "B": B, "b": b, "tot": tot,
            "N": N, "A": Ms.aretes(b, tot, N), "W": normaliser(DR.poids_denses(z, N)), "tris": DR.triangles_from(b, tot),
            "cG": cG, "cD": cD, "kG": kG, "kD": kD,
            "hipd": float(np.linalg.norm(cG - cD))}


def pose_de(M, nom):
    if nom.startswith("generative_hanche_G_"):
        return LM.pose_hanche_G(M["z"], M["noms"], M["js"], int(nom.rsplit("_", 1)[1]))
    return M["z"][nom[len("reelle_"):] + "__os"]


def pm_pivot(M, th, delta):
    """Pose de hanche G à angle th, pivot décalé de delta (m). Même convention de signe que LM.pose_hanche_G."""
    z, noms, js, B = M["z"], M["noms"], M["js"], M["B"]
    sens = EXP.signe_depuis_pose_reelle(z, noms, js, "LeftUpLeg", "L_flex90")[0]
    c, ax, ch = P.articulation(js, EXP.prefixe(noms) + "LeftUpLeg")
    T = P.transformation_articulation(c + np.asarray(delta), ax, np.radians(th), sens)
    return P.matrices_pose(B, noms, ch, T)


def evaluer(M, pm, lam=LAM, W=None, rest=None):
    """LBS et SQ. W=None : pipeline d'origine (poids creux). W fourni : chemin dense équivalent (interventions)."""
    rest = M["rest"] if rest is None else rest
    if W is None:
        lbs, Mv, Rsq = DEC.pipeline(M["Wi"], M["Ww"], M["B"], pm, rest)
        R, t = DR.matrices_bones(M["z"], pm)
    else:
        R, t = DR.matrices_bones(M["z"], pm)
        lbs, Mv = TG.lbs_et_mv(rest, W, R, t)
        Rsq = DEC.polaire_gen(Mv)
    sq = ARAP.solve_fixe(lbs, rest, M["A"], Rsq, lam)
    return lbs, sq, Mv, R, t


def metriques(M, rest, W, lbs, sq, Mv, R, t):
    A, tris, b, tot = M["A"], M["tris"], M["b"], M["tot"]
    a, c = A[:, 0], A[:, 1]
    lr = np.linalg.norm(rest[a] - rest[c], axis=1)
    ok5 = lr >= 0.005
    rL = np.linalg.norm(lbs[a] - lbs[c], axis=1) / np.maximum(lr, 1e-12)
    rS = np.linalg.norm(sq[a] - sq[c], axis=1) / np.maximum(lr, 1e-12)
    exc = rS - rL
    dW = W[a] - W[c]
    mixte_arete = np.abs(dW).max(1) > 1e-9
    Tc = np.einsum("kij,ej->eki", R, rest[c]) + t[None]
    G = np.einsum("ek,eki->ei", dW, Tc)
    Mvd = np.einsum("eij,ej->ei", Mv[a], rest[a] - rest[c])
    pur = W.max(1) > 1 - 1e-6
    classe = np.where(pur[a] & pur[c], "pur", "mixte")
    reg = ok5 & (exc > 0.05)
    hd = M["hipd"]
    # triangles : déformation, retournements (référence = polaire de Mv moyen, rigide-cohérente)
    n0 = np.cross(rest[tris[:, 1]] - rest[tris[:, 0]], rest[tris[:, 2]] - rest[tris[:, 0]])
    nL = np.cross(lbs[tris[:, 1]] - lbs[tris[:, 0]], lbs[tris[:, 2]] - lbs[tris[:, 0]])
    nS = np.cross(sq[tris[:, 1]] - sq[tris[:, 0]], sq[tris[:, 2]] - sq[tris[:, 0]])
    aire0 = 0.5 * np.linalg.norm(n0, axis=1)
    aL = 0.5 * np.linalg.norm(nL, axis=1)
    aS = 0.5 * np.linalg.norm(nS, axis=1)
    Mt = Mv[tris].mean(1)
    ref = np.einsum("tij,tj->ti", DEC.polaire_gen(Mt), n0 / np.maximum(np.linalg.norm(n0, axis=1, keepdims=True), 1e-12))
    fL = np.einsum("ti,ti->t", nL, ref) < 0
    fS = np.einsum("ti,ti->t", nS, ref) < 0
    nouv = fS & ~fL
    valide = aire0 > 1e-12
    vL = Ms.mesurer(lbs, rest, b, tot, A, Mv=Mv)["variation_volume_relative"]
    vS = Ms.mesurer(sq, rest, b, tot, A, Mv=Mv)["variation_volume_relative"]
    dep = np.linalg.norm(sq - lbs, axis=1)
    out = {
        "etirement_LBS": quant(rL[ok5]), "etirement_SQ": quant(rS[ok5]),
        "difference_SQ_moins_LBS": quant(exc[ok5]),
        "deplacement_absolu_m": quant(dep),
        "deplacement_normalise_hanche": quant(dep / hd),
        "aretes_ge5mm": int(ok5.sum()),
        "aretes_regressees": int(reg.sum()),
        "part_aretes_regressees": float(reg.sum() / max(ok5.sum(), 1)),
        "triangles": int(len(tris)),
        "retournements_LBS": int(fL.sum()), "retournements_SQ": int(fS.sum()),
        "retournements_nouveaux_SQ": int(nouv.sum()),
        "surface_ratio_LBS": quant((aL / np.maximum(aire0, 1e-12))[valide]),
        "surface_ratio_SQ": quant((aS / np.maximum(aire0, 1e-12))[valide]),
        "volume_relatif_LBS": float(vL), "volume_relatif_SQ": float(vS),
        "G_sur_longueur_aretes_mixtes": quant((np.linalg.norm(G, axis=1) / np.maximum(lr, 1e-12))[ok5 & mixte_arete]),
        "terme_rigide_sur_longueur_aretes_mixtes": quant((np.linalg.norm(Mvd, axis=1) / np.maximum(lr, 1e-12))[ok5 & mixte_arete]),
        "G_sur_longueur_toutes_aretes": quant((np.linalg.norm(G, axis=1) / np.maximum(lr, 1e-12))[ok5]),
        "gradient_poids_L1_par_m_mixtes": quant((np.abs(dW).sum(1) / np.maximum(lr, 1e-12))[ok5 & mixte_arete]),
        "sommets_poids_purs": float(pur.mean()), "sommets_poids_mixtes": float(1 - pur.mean()),
        "aretes_mixtes_part": float(mixte_arete[ok5].mean()),
        "aretes_regressees_mixtes": int((reg & (classe == "mixte")).sum()),
        "aretes_regressees_pures": int((reg & (classe == "pur")).sum()),
    }
    arr = {"exc": exc, "ok5": ok5, "a": a, "c": c, "classe": classe, "lr": lr, "fS": fS, "nouv": nouv}
    return out, arr


def regions(M):
    rest = M["rest"]
    cG, cD, hd = M["cG"], M["cD"], M["hipd"]
    mid = (cG + cD) / 2
    xm = mid[0]
    sideG = np.sign(cG[0] - xm) if cG[0] != xm else 1.0
    dz = (rest[:, 2] - mid[2]) / hd
    dx = sideG * (rest[:, 0] - xm) / hd
    lab = np.full(len(rest), "autre", dtype=object)
    lab[dz > 0.1] = "bassin"
    lab[(dx > 0.35) & (dz <= 0.1)] = "cuisse_G"
    lab[(dx < -0.35) & (dz <= 0.1)] = "cuisse_D"
    lab[(np.abs(dx) < 0.35) & (dz <= 0.1) & (dz >= -0.8)] = "entrejambe"
    lab[np.linalg.norm(rest - cG, axis=1) / hd < 0.5] = "hanche_G"
    lab[np.linalg.norm(rest - cD, axis=1) / hd < 0.5] = "hanche_D"
    lab[np.linalg.norm(rest - M["kG"], axis=1) / hd < 0.5] = "genou_G"
    lab[np.linalg.norm(rest - M["kD"], axis=1) / hd < 0.5] = "genou_D"
    return lab


def stats_regions(M, labs, arrs_list):
    """Pour chaque région : part améliorée (exc < −0.02), aggravée (exc > 0.05), neutre, médiane, et classe des aggravées."""
    a, c = M["A"][:, 0], M["A"][:, 1]
    er = np.where(labs[a] == labs[c], labs[a], "frontiere")
    res = {}
    exc = np.concatenate([x["exc"] for x in arrs_list])
    ok = np.concatenate([x["ok5"] for x in arrs_list])
    cls = np.concatenate([x["classe"] for x in arrs_list])
    reg_lab = np.concatenate([er for _ in arrs_list])
    for r in sorted(set(reg_lab)):
        m = (reg_lab == r) & ok
        if not m.any():
            continue
        e = exc[m]
        worse = e > 0.05
        res[r] = {"n": int(m.sum()), "ameliore": float((e < -0.02).mean()), "aggrave": float(worse.mean()),
                  "neutre": float((np.abs(e) <= 0.02).mean()), "exc_mediane": float(np.median(e)),
                  "aggravees_mixtes": int((worse & (cls[m] == "mixte")).sum()),
                  "aggravees_pures": int((worse & (cls[m] == "pur")).sum())}
    return res


def propagation(M, pm_arr_W, lbs, sq):
    """Déviation SQ − LBS sur sommets à poids pur (même os, 1-anneau pur) selon la distance au bord."""
    W = M["W"]; A = M["A"]; N = M["N"]
    pur = W.max(1) > 1 - 1e-6
    dom = np.argmax(W, axis=1)
    src = S.interface(N, A, np.where(pur, dom, -1))
    dist = S.bfs(N, A, src)
    dev = np.linalg.norm(sq - lbs, axis=1)
    out = {}
    for d in range(8):
        m = pur & (dist == d)
        if m.any():
            out[str(d)] = {"n": int(m.sum()), "max_m": float(dev[m].max()), "mediane_m": float(np.median(dev[m]))}
    return out


if __name__ == "__main__":
    os.makedirs(SORTIE, exist_ok=True)
    Ms_ = {m: charger_morph(m) for m in MORPHS}
    resultats = {"protocole": {"poses": POSES, "lambda": LAM, "normalisation": "distance entre centres de hanche",
                               "hipd_m": {m: Ms_[m]["hipd"] for m in MORPHS},
                               "N": {m: Ms_[m]["N"] for m in MORPHS},
                               "triangles": {m: int(len(Ms_[m]["tris"])) for m in MORPHS},
                               "os": {m: len(Ms_[m]["noms"]) for m in MORPHS}},
                 "phase1": {}, "phase2": {}, "phase3": {}, "verification": {}}

    # vérification : chemin dense équivalent au pipeline d'origine
    for m in MORPHS:
        M = Ms_[m]
        pm = pose_de(M, "reelle_L_flex120")
        l1, s1, _, _, _ = evaluer(M, pm)
        l2, s2, _, _, _ = evaluer(M, pm, W=M["W"])
        resultats["verification"][m] = {"erreur_LBS_dense_vs_pipeline_m": float(np.abs(l1 - l2).max()),
                                        "erreur_SQ_dense_vs_pipeline_m": float(np.abs(s1 - s2).max())}
        print("vérif", m, resultats["verification"][m], flush=True)

    # ---------- Phase 1 et 2 ----------
    labs = {m: regions(Ms_[m]) for m in MORPHS}
    arrs_par_morph = {m: [] for m in MORPHS}
    for m in MORPHS:
        M = Ms_[m]
        resultats["phase1"][m] = {}
        for nom in POSES:
            pm = pose_de(M, nom)
            lbs, sq, Mv, R, t = evaluer(M, pm)
            met, arr = metriques(M, M["rest"], M["W"], lbs, sq, Mv, R, t)
            met["propagation_pur_par_distance"] = propagation(M, None, lbs, sq)
            resultats["phase1"][m][nom] = met
            arrs_par_morph[m].append(arr)
            print(m, nom, "régressées", met["aretes_regressees"], "retour LBS/SQ/nouv",
                  met["retournements_LBS"], met["retournements_SQ"], met["retournements_nouveaux_SQ"],
                  "vol", round(met["volume_relatif_LBS"], 4), round(met["volume_relatif_SQ"], 4), flush=True)
        resultats["phase2"][m] = {"agrege_29_poses": stats_regions(M, labs[m], arrs_par_morph[m]),
                                  "agrege_poses_SUB": stats_regions(M, labs[m],
                                                                    [arrs_par_morph[m][POSES.index(n)] for n in SUB])}
        print("phase2", m, {k: (v["n"], round(v["aggrave"], 3)) for k, v in resultats["phase2"][m]["agrege_29_poses"].items()}, flush=True)

    # ---------- Phase 3 : interventions contrôlées (poses SUB) ----------
    for m in MORPHS:
        M = Ms_[m]
        r3 = {}
        # H1 : répartition spatiale (histogramme conservé)
        W = M["W"]
        pur = W.max(1) > 1 - 1e-6
        idx = np.where(~pur)[0]
        base = {}
        perm_res = {}
        for nom in SUB:
            pm = pose_de(M, nom)
            lbs, sq, Mv, R, t = evaluer(M, pm, W=W)
            base[nom], _ = metriques(M, M["rest"], W, lbs, sq, Mv, R, t)
        r3["H1_base"] = {n: {k: base[n][k] for k in ["part_aretes_regressees", "difference_SQ_moins_LBS", "retournements_nouveaux_SQ"]} for n in SUB}
        for mode in ["aleatoire_x5", "lisse"]:
            vals = []
            seeds = range(5) if mode == "aleatoire_x5" else [0]
            for sd in seeds:
                W2 = W.copy()
                if mode == "aleatoire_x5":
                    rng = np.random.default_rng(sd)
                    W2[idx] = W[rng.permutation(idx)]
                else:
                    # réarrangement lisse : les lignes triées par poids G sont placées selon l'ordre de x
                    wG = W[idx, :]
                    ordre_val = idx[np.argsort(-(wG.max(1)))]
                    ordre_x = idx[np.argsort(M["rest"][idx, 0], kind="stable")]
                    W2[ordre_x] = W[ordre_val]
                row = {}
                for nom in SUB:
                    pm = pose_de(M, nom)
                    lbs, sq, Mv, R, t = evaluer(M, pm, W=W2)
                    mt, _ = metriques(M, M["rest"], W2, lbs, sq, Mv, R, t)
                    row[nom] = {k: mt[k] for k in ["part_aretes_regressees", "retournements_nouveaux_SQ"]}
                    row[nom]["difference_p99"] = mt["difference_SQ_moins_LBS"]["p99"]
                vals.append(row)
            perm_res[mode] = vals
        r3["H1_permutation"] = perm_res
        # H2 / H3 : dilatation locale de la zone entrejambe (même topologie, mêmes poids, mêmes poses)
        mid = (M["cG"] + M["cD"]) / 2
        p0 = mid + np.array([0.0, 0.0, -0.3 * M["hipd"]])
        dloc = np.linalg.norm(M["rest"] - p0, axis=1) / M["hipd"]
        wloc = np.clip((0.9 - dloc) / 0.4, 0, 1)
        h2 = {}
        for f in [0.8, 1.0, 1.25]:
            rest2 = p0 + (M["rest"] - p0) * (1 + (f - 1) * wloc)[:, None]
            row = {}
            for nom in SUB:
                pm = pose_de(M, nom)
                lbs, sq, Mv, R, t = evaluer(M, pm, W=W, rest=rest2)
                mt, _ = metriques(M, rest2, W, lbs, sq, Mv, R, t)
                row[nom] = {k: mt[k] for k in ["part_aretes_regressees", "retournements_nouveaux_SQ", "etirement_SQ"]}
                row[nom]["difference_p99"] = mt["difference_SQ_moins_LBS"]["p99"]
                row[nom]["lr_mediane_m"] = float(np.median(np.linalg.norm(rest2[M["A"][:, 0]] - rest2[M["A"][:, 1]], axis=1)))
            h2[str(f)] = row
        r3["H2_H3_dilatation_locale"] = h2
        # H4 : position des articulations (pivot ±1 cm, pose générative 120)
        h4 = {}
        for dl, nm in [((0, 0, 0), "0"), ((-0.01, 0, 0), "x-1cm"), ((0.01, 0, 0), "x+1cm"),
                       ((0, 0, -0.01), "z-1cm"), ((0, 0, 0.01), "z+1cm")]:
            pm = pm_pivot(M, 120, dl)
            lbs, sq, Mv, R, t = evaluer(M, pm)
            mt, _ = metriques(M, M["rest"], M["W"], lbs, sq, Mv, R, t)
            h4[nm] = {k: mt[k] for k in ["part_aretes_regressees", "retournements_nouveaux_SQ"]}
            h4[nm]["difference_p99"] = mt["difference_SQ_moins_LBS"]["p99"]
        r3["H4_pivot"] = h4
        # H5 : λ et propagation
        h5 = {}
        for lam in [0.01, 0.1, 1.0]:
            row = {}
            for nom in SUB:
                pm = pose_de(M, nom)
                lbs, sq, Mv, R, t = evaluer(M, pm, lam=lam)
                mt, _ = metriques(M, M["rest"], M["W"], lbs, sq, Mv, R, t)
                row[nom] = {"part_aretes_regressees": mt["part_aretes_regressees"],
                            "difference_p99": mt["difference_SQ_moins_LBS"]["p99"],
                            "propagation": propagation(M, None, lbs, sq)}
            h5[str(lam)] = row
        r3["H5_lambda"] = h5
        resultats["phase3"][m] = r3
        print("phase3", m, "H4", {k: round(v["part_aretes_regressees"], 4) for k, v in h4.items()}, flush=True)

    # H6 : corrélation volume / régressions, par pose (corrélation seulement)
    h6 = {}
    for m in MORPHS:
        xs, ys = [], []
        for nom in POSES:
            r = resultats["phase1"][m][nom]
            xs.append(r["volume_relatif_SQ"] - r["volume_relatif_LBS"])
            ys.append(r["part_aretes_regressees"])
        xs, ys = np.array(xs), np.array(ys)
        h6[m] = {"corr_delta_volume_vs_part_regressee": float(np.corrcoef(xs, ys)[0, 1]) if xs.std() > 0 and ys.std() > 0 else None,
                 "nb_poses": len(xs), "avertissement": "corrélation globale par pose uniquement ; aucun volume local"}
    resultats["phase3"]["H6_volume"] = h6

    with open(os.path.join(SORTIE, "comparaison.json"), "w", encoding="utf-8") as f:
        json.dump(resultats, f, indent=1, ensure_ascii=False)
    print("ECRIT", flush=True)
