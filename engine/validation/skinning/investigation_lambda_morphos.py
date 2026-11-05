"""Étape 5 : effet de λ sur les trois morphologies, sur des poses RÉELLES indépendantes.

Aucune calibration ici : aucun λ n'est choisi. Tout est rapporté pose par pose, morphologie par morphologie.
Poses : toutes les poses réelles de la morphologie, sauf les deux références de signe (L_flex90, R_flex90), plus
les poses génératives de hanche gauche 75°, 105°, 120° (test du protocole). Méthode étudiée : SQ à moyenne
arithmétique (configuration actuelle), λ ∈ {0,01 ; 0,1 ; 1,0}. Référence : LBS. Aucun seuil modifié.

Verification : LBS calculé contre le contrôle réel (`__ctrl`) pour chaque pose réelle.
"""
import importlib.util
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SORTIE = os.path.join(RACINE, "docs", "rapports", "skinning", "intermediaire_hanche_masc")


def charger(nom):
    spec = importlib.util.spec_from_file_location(nom, os.path.join(HERE, nom + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


DEC = charger("investigation_decomposition")
INV = DEC.INV
P, EXP, ARAP, Ms = INV.P, INV.EXP, INV.ARAP, INV.Ms
LAMBDAS = [0.01, 0.1, 1.0]
POSES_SIGNE = {"L_flex90", "R_flex90"}


def mesure(pos, Mv, rest, b, tot, A):
    g = Ms.mesurer(pos, rest, b, tot, A, Mv=Mv)
    return {"max": float(g["etirement_max"]), "p99": float(g["etirement_p99"]),
            "retournements": int(g["polygones_retournes"]), "volume": float(g["variation_volume_relative"])}


def pose_hanche_G(z, noms, js, th):
    sens = EXP.signe_depuis_pose_reelle(z, noms, js, "LeftUpLeg", "L_flex90")[0]
    c, ax, ch = P.articulation(js, EXP.prefixe(noms) + "LeftUpLeg")
    T = P.transformation_articulation(c, ax, np.radians(th), sens)
    return P.matrices_pose(z["bones_rest_monde"], noms, ch, T)


if __name__ == "__main__":
    os.makedirs(SORTIE, exist_ok=True)
    resultats = {}
    for morph, (npz, js_rel) in EXP.MORPHOS.items():
        z = np.load(os.path.join(INV.DONNEES, npz))
        noms = [str(n) for n in z["noms_os"]]
        js = os.path.join(RACINE, js_rel)
        rest, Wi, Ww, B = z["rest_monde"], z["W_idx"], z["W_w"], z["bones_rest_monde"]
        b, tot = z["b_boucle"], z["b_tot"]
        N = len(rest)
        A = Ms.aretes(b, tot, N)
        poses = {}
        # poses génératives (test du protocole, hanche gauche)
        for th in (75, 105, 120):
            poses[f"generative_hanche_G_{th}"] = pose_hanche_G(z, noms, js, th)
        # poses réelles indépendantes
        for k in sorted(z.keys()):
            if k.endswith("__os") and k[:-4] not in POSES_SIGNE:
                poses["reelle_" + k[:-4]] = z[k]
        res_morph = {}
        for nom, pm in poses.items():
            lbs, Mv, Rsq = DEC.pipeline(Wi, Ww, B, pm, rest)
            ligne = {"LBS": mesure(lbs, Mv, rest, b, tot, A), "knee": "genou" in nom}
            if nom.startswith("reelle_"):
                ctrl = z[nom[len("reelle_"):] + "__ctrl"]
                ligne["verif_LBS_vs_controle_m"] = float(np.abs(lbs - ctrl).max())
            for lam in LAMBDAS:
                sq = ARAP.solve_fixe(lbs, rest, A, Rsq, lam)
                ligne[f"SQ_l{lam}"] = mesure(sq, Mv, rest, b, tot, A)
            res_morph[nom] = ligne
            print(morph, nom, "LBS max", round(ligne["LBS"]["max"], 3),
                  " | ".join(f"SQ l{l} {ligne[f'SQ_l{l}']['max']:.3f}" for l in LAMBDAS), flush=True)
        # bilan par λ : régressions pose par pose (aucun seuil relâché)
        bilan = {}
        for lam in LAMBDAS:
            delta = {n: res_morph[n][f"SQ_l{lam}"]["max"] - res_morph[n]["LBS"]["max"] for n in res_morph}
            pires = sorted(delta.items(), key=lambda t: -t[1])[:5]
            bilan[f"l{lam}"] = {"poses_regressees_sur_max": int(sum(v > 0 for v in delta.values())),
                                "nb_poses": len(delta),
                                "pire_regression_max": float(max(delta.values())),
                                "cinq_pires": [[n, round(v, 4)] for n, v in pires],
                                "genou_regressees": int(sum(v > 0 for n, v in delta.items() if res_morph[n]["knee"])),
                                "retournements_SQ_plus_que_LBS": int(sum(
                                    res_morph[n][f"SQ_l{lam}"]["retournements"] > res_morph[n]["LBS"]["retournements"]
                                    for n in res_morph))}
        resultats[morph] = {"poses": res_morph, "bilan": bilan}
        print(morph, "bilan", bilan, flush=True)
    with open(os.path.join(SORTIE, "lambda_morphologies.json"), "w", encoding="utf-8") as f:
        json.dump(resultats, f, indent=1, ensure_ascii=False)
    print("ECRIT", flush=True)
