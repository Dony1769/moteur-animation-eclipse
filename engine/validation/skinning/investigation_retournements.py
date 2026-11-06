"""Phase 4 : retournements supplémentaires SQ (triangles retournés dans SQ et pas dans LBS).

Référence d'orientation : pour chaque triangle, la normale de repos est tournée par la polaire de la moyenne des Mv
de ses sommets (repère rigide commun à toutes les méthodes). Une rotation rigide ne produit donc aucun retournement,
quel que soit son angle ; le comptage ne dépend pas d'un seuil.

A. Synthétique : 144 configurations ; pour les 31 qui produisent des retournements nouveaux, on change UN facteur à la
   fois (géométrie, triangulation, histogramme, arrangement, angles, λ) et on note si les retournements disparaissent.
B. Contrôles d'orientation : pose rigide (aucun retournement attendu) et rotation globale (comptage invariant).
C. Réel : retournements nouveaux de Maria (11 poses), triangles concernés, puis test par λ et par cible polaire.
"""
import importlib.util
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SORTIE = os.path.join(RACINE, "docs", "rapports", "skinning", "comparaison_morphologies")


def charger(nom):
    spec = importlib.util.spec_from_file_location(nom, os.path.join(HERE, nom + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


DEC = charger("investigation_decomposition")
TG = charger("investigation_terme_G")
CMP = charger("investigation_comparaison")


def retournements(tris, rest, lbs, sq, Mv):
    n0 = np.cross(rest[tris[:, 1]] - rest[tris[:, 0]], rest[tris[:, 2]] - rest[tris[:, 0]])
    nL = np.cross(lbs[tris[:, 1]] - lbs[tris[:, 0]], lbs[tris[:, 2]] - lbs[tris[:, 0]])
    nS = np.cross(sq[tris[:, 1]] - sq[tris[:, 0]], sq[tris[:, 2]] - sq[tris[:, 0]])
    Mt = Mv[tris].mean(1)
    ref = np.einsum("tij,tj->ti", DEC.polaire_gen(Mt), n0 / np.maximum(np.linalg.norm(n0, axis=1, keepdims=True), 1e-12))
    fL = np.einsum("ti,ti->t", nL, ref) < 0
    fS = np.einsum("ti,ti->t", nS, ref) < 0
    return fL, fS, fS & ~fL


def cas_synth(geo, tri, arr, hist, th, lam=0.1, nonuni=False):
    TG.LAM = lam
    p = TG.patch(geo, tri, nonuni, 4.0 if geo == "courbe" else 0.0, arr, hist, th)
    fL, fS, nv = retournements(p["tris"], p["rest"], p["lbs"], p["sq"], p["Mv"])
    return int(nv.sum()), p


if __name__ == "__main__":
    os.makedirs(SORTIE, exist_ok=True)
    desc = json.load(open(os.path.join(RACINE, "docs/rapports/skinning/factorielle/descriptif_morphologies.json")))
    H = {"M": desc["masculin"]["histogramme_wG_mixtes_10_classes"], "F": desc["feminin"]["histogramme_wG_mixtes_10_classes"]}
    out = {"A_synthetique": {}, "B_controles": {}, "C_reel_maria": {}}

    # ---------- A : 144 configurations ----------
    base = []
    for geo in ["plat", "courbe"]:
        for nu in [False, True]:
            for tri in ["A", "B"]:
                for arr in ["lisse", "aleatoire", "alterne"]:
                    for hn in ["M", "F"]:
                        for th in [(90, 0), (120, 0), (120, -60)]:
                            n, _ = cas_synth(geo, tri, arr, H[hn], th, nonuni=nu)
                            base.append({"geo": geo, "nonuni": nu, "tri": tri, "arr": arr, "hist": hn,
                                         "th": list(th), "nouveaux": n})
    echecs = [c for c in base if c["nouveaux"] > 0]
    out["A_synthetique"]["nb_configs"] = len(base)
    out["A_synthetique"]["nb_configs_avec_nouveaux"] = len(echecs)
    out["A_synthetique"]["total_nouveaux"] = int(sum(c["nouveaux"] for c in base))
    out["A_synthetique"]["configs"] = base
    print("A: configs", len(base), "avec nouveaux", len(echecs), "total", out["A_synthetique"]["total_nouveaux"], flush=True)

    # un facteur à la fois, sur les configurations en échec
    effets = []
    for c in echecs:
        th = tuple(c["th"])
        variantes = {
            "geometrie_inverse": dict(geo="courbe" if c["geo"] == "plat" else "plat"),
            "triangulation_inverse": dict(tri="B" if c["tri"] == "A" else "A"),
            "histogramme_inverse": dict(hist="F" if c["hist"] == "M" else "M"),
            "arrangement_lisse": dict(arr="lisse"),
            "arrangement_alterne": dict(arr="alterne"),
            "angles_90_0": dict(th=(90, 0)),
            "lambda_0.01": dict(lam=0.01),
            "lambda_1.0": dict(lam=1.0),
        }
        ligne = {"config": c, "variantes": {}}
        for nom, ch in variantes.items():
            args = dict(geo=c["geo"], tri=c["tri"], arr=c["arr"], hist=H[c["hist"]], th=th, lam=0.1, nonuni=c["nonuni"])
            if "geo" in ch:
                args["geo"] = ch["geo"]
            if "tri" in ch:
                args["tri"] = ch["tri"]
            if "hist" in ch:
                args["hist"] = H[ch["hist"]]
            if "arr" in ch:
                args["arr"] = ch["arr"]
            if "th" in ch:
                args["th"] = ch["th"]
            if "lam" in ch:
                args["lam"] = ch["lam"]
            n, _ = cas_synth(**args)
            ligne["variantes"][nom] = n
        effets.append(ligne)
    out["A_synthetique"]["effets_un_facteur_a_la_fois"] = effets
    print("A: effets calculés", len(effets), flush=True)
    # résumé : disparition des retournements par facteur
    resume = {}
    for nom in ["geometrie_inverse", "triangulation_inverse", "histogramme_inverse", "arrangement_lisse",
                "arrangement_alterne", "angles_90_0", "lambda_0.01", "lambda_1.0"]:
        resume[nom] = {"configs_ou_disparaissent": int(sum(l["variantes"][nom] == 0 for l in effets)),
                       "configs_ou_persistent": int(sum(l["variantes"][nom] > 0 for l in effets)),
                       "total_nouveaux_apres": int(sum(l["variantes"][nom] for l in effets))}
    out["A_synthetique"]["resume_par_facteur"] = resume
    print("A résumé", json.dumps(resume, ensure_ascii=False), flush=True)

    # ---------- B : contrôles d'orientation ----------
    _, p = cas_synth("plat", "A", "alterne", H["M"], (120, -60), nonuni=False)
    rest, W, Rs, ts = p["rest"], p["W"], p["Rs"], p["ts"]
    tris = p["tris"]
    fL, fS, nv = retournements(tris, rest, p["lbs"], p["sq"], p["Mv"])
    # B1 : pose rigide commune (toutes les transformations identiques) : aucun retournement attendu
    Rr = np.repeat(Rs[1:2], len(Rs), 0)
    tr = np.repeat(ts[1:2], len(Rs), 0)
    lbsr, Mvr = TG.lbs_et_mv(rest, W, Rr, tr)
    Rsqr = DEC.polaire_gen(Mvr)
    sqr = TG.ARAP.solve_fixe(lbsr, rest, p["A"], Rsqr, 0.1)
    _, _, nvr = retournements(tris, rest, lbsr, sqr, Mvr)
    out["B_controles"]["B1_rigide_commun_nouveaux"] = int(nvr.sum())
    out["B_controles"]["B1_rigide_commun_retournements_SQ"] = int(retournements(tris, rest, lbsr, sqr, Mvr)[1].sum())
    # B2 : rotation globale Q : comptage invariant
    rng = np.random.default_rng(3)
    Q = DEC.polaire_gen(rng.normal(size=(3, 3)))
    Rq = np.einsum("ij,kjl,ml->kim", Q, Rs, Q)
    tq = np.einsum("ij,kj->ki", Q, ts)
    rq = rest @ Q.T
    lbsq, Mvq = TG.lbs_et_mv(rq, W, Rq, tq)
    sqq = TG.ARAP.solve_fixe(lbsq, rq, p["A"], DEC.polaire_gen(Mvq), 0.1)
    _, _, nvq = retournements(tris, rq, lbsq, sqq, Mvq)
    out["B_controles"]["B2_rotation_globale_nouveaux_avant"] = int(nv.sum())
    out["B_controles"]["B2_rotation_globale_nouveaux_apres"] = int(nvq.sum())
    # B3 : rotation rigide de 170° de tout le maillage (LBS et SQ suivent le mouvement) : aucun retournement attendu
    th = np.radians(170)
    Rz = np.array([[np.cos(th), -np.sin(th), 0], [np.sin(th), np.cos(th), 0], [0, 0, 1]])
    lbs170 = rest @ Rz.T
    Mv170 = np.repeat(Rz[None], len(rest), 0)
    sq170 = TG.ARAP.solve_fixe(lbs170, rest, p["A"], DEC.polaire_gen(Mv170), 0.1)
    _, _, nv3 = retournements(tris, rest, lbs170, sq170, Mv170)
    out["B_controles"]["B3_rotation_rigide_170_nouveaux"] = int(nv3.sum())
    print("B", out["B_controles"], flush=True)

    # ---------- C : Maria, retournements nouveaux réels ----------
    M = CMP.charger_morph("maria")
    C = []
    for nom in CMP.POSES:
        pm = CMP.pose_de(M, nom)
        lbs, sq, Mv, R, t = CMP.evaluer(M, pm)
        fL, fS, nv = retournements(M["tris"], M["rest"], lbs, sq, Mv)
        if nv.sum() == 0:
            continue
        ids = np.where(nv)[0]
        W = M["W"]
        detail = []
        for ti in ids[:40]:
            i, j, k = M["tris"][ti]
            detail.append({"sommets": [int(i), int(j), int(k)],
                           "poids_dominants": [[M["noms"][int(np.argmax(W[v]))], round(float(W[v].max()), 3)] for v in (i, j, k)],
                           "aire_repos": float(0.5 * np.linalg.norm(np.cross(M["rest"][j] - M["rest"][i], M["rest"][k] - M["rest"][i]))),
                           "aire_SQ": float(0.5 * np.linalg.norm(np.cross(sq[j] - sq[i], sq[k] - sq[i])))})
        # tests : λ et cible polaire (sur la même pose)
        lam_res = {}
        for lam in [0.01, 1.0]:
            l2, s2, M2, _, _ = CMP.evaluer(M, pm, lam=lam)
            lam_res[str(lam)] = int(retournements(M["tris"], M["rest"], l2, s2, M2)[2].sum())
        a, c = M["A"][:, 0], M["A"][:, 1]
        Rsq = DEC.polaire_gen(Mv)
        sq_pol = DEC.solve_R(lbs, M["rest"], M["A"], DEC.polaire_gen(0.5 * (Rsq[a] + Rsq[c])), 0.1)
        pol = int(retournements(M["tris"], M["rest"], lbs, sq_pol, Mv)[2].sum())
        C.append({"pose": nom, "nouveaux": int(nv.sum()), "nouveaux_si_lambda": lam_res,
                  "nouveaux_si_cible_polaire": pol, "triangles_exemples": detail[:10]})
        print("C", nom, int(nv.sum()), lam_res, pol, flush=True)
    out["C_reel_maria"] = C

    with open(os.path.join(SORTIE, "retournements.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print("ECRIT", flush=True)
