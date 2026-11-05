"""Banc comparatif LBS / DQS / hybrides sur le corps HBM (phase 4).

Usage : python3 engine/validation/skinning/comparer.py POSES.npz DOSSIER_SORTIE

Entrées : sortie de extraire_poses.py (Blender). Pour chaque pose, les quatre méthodes reçoivent exactement les mêmes
positions au repos, poids, matrices d'os et topologie. Sorties :
  comparatif_base.json   : maillage de base (10 582 sommets), toutes les poses, mesures par méthode ;
  comparatif_hr.json     : maillage haute résolution MULTIRES niveau 3 (poids transférés, voir plus bas) ;
  captures_*.png         : vues de profil du maillage haute résolution, coloré par étirement par sommet.
Contrôles : LBS reconstruit doit coïncider avec la déformation évaluée par Blender (erreur mesurée et écrite).
"""
import json
import os
import sys

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import methodes as M  # noqa: E402
import mesures as Ms  # noqa: E402

METHODES = ["LBS", "DQS", "HYBRIDE_global", "HYBRIDE_angle"]
CAPTURES_POSES = ["L_flex120", "L_genou90"]


def sommet_etirement_max(pos, rest, A):
    N = len(rest)
    a, b = A[:, 0], A[:, 1]
    lr = np.linalg.norm(rest[a] - rest[b], axis=1)
    lp = np.linalg.norm(pos[a] - pos[b], axis=1)
    r = np.where(lr > 1e-9, lp / np.maximum(lr, 1e-12), 1.0)
    v = np.ones(N)
    np.maximum.at(v, a, r)
    np.maximum.at(v, b, r)
    return v


def arrondir(obj):
    if isinstance(obj, dict):
        return {k: arrondir(v) for k, v in obj.items()}
    if isinstance(obj, float):
        return float(f"{obj:.6g}")
    return obj


def main():
    npz, sortie = sys.argv[1], sys.argv[2]
    os.makedirs(sortie, exist_ok=True)
    d = np.load(npz)
    rest = d["rest_monde"]
    W_idx, W_w = d["W_idx"], d["W_w"]
    B = d["bones_rest_monde"]
    b_boucle, b_tot = d["b_boucle"], d["b_tot"]
    A = Ms.aretes(b_boucle, b_tot, len(rest))
    poses = sorted({k[: -len("__os")] for k in d.files if k.endswith("__os")})

    # ---- maillage de base ----
    base = {}
    poses_base = [("neutre", B)] + [(p, d[p + "__os"]) for p in poses]
    for nom, pm in poses_base:
        pos_m, diag = M.calculer_toutes(rest, W_idx, W_w, B, pm)
        entree = {"diagnostic_transformations": diag, "methodes": {}}
        if nom != "neutre":
            erreur = float(np.abs(pos_m["LBS"] - d[nom + "__ctrl"]).max())
            entree["erreur_LBS_vs_Blender_m"] = erreur
        Mv = M.repere_rigide(W_idx, W_w, B, pm)
        for m in METHODES:
            entree["methodes"][m] = Ms.mesurer(pos_m[m], rest, b_boucle, b_tot, A, Mv=Mv)
        base[nom] = entree
        print("BASE", nom, {m: round(entree["methodes"][m]["polygones_retournes"]) for m in METHODES},
              "erreur_LBS" , entree.get("erreur_LBS_vs_Blender_m"), flush=True)

    # ---- maillage haute résolution : poids transférés du sommet de base le plus proche ----
    hr = {}
    if "hr_rest" in d.files:
        hr_rest = d["hr_rest"].astype(np.float64)
        Nh = len(hr_rest)
        _, plus_proche = cKDTree(rest).query(hr_rest)
        hW_idx, hW_w = W_idx[plus_proche], W_w[plus_proche]
        hb, ht = d["hr_boucle"], d["hr_tot"]
        Ahr = Ms.aretes(hb, ht, Nh)
        poses_hr = [("neutre", B)] + [(k[: -len("__hr")], d[k[: -len("__hr")] + "__os"])
                                    for k in d.files if k.endswith("__hr")]
        captures = {}
        for nom, pm in poses_hr:
            pos_m, diag = M.calculer_toutes(hr_rest, hW_idx, hW_w, B, pm)
            entree = {"diagnostic_transformations": diag, "methodes": {}}
            if nom != "neutre":
                entree["erreur_LBS_vs_Blender_m"] = float(np.abs(pos_m["LBS"] - d[nom + "__hr"]).max())
            Mv = M.repere_rigide(hW_idx, hW_w, B, pm)
            for m in METHODES:
                entree["methodes"][m] = Ms.mesurer(pos_m[m], hr_rest, hb, ht, Ahr, Mv=Mv)
            hr[nom] = entree
            if nom in CAPTURES_POSES:
                captures[nom] = {m: pos_m[m] for m in METHODES}
                captures[nom]["vmax"] = {m: sommet_etirement_max(pos_m[m], hr_rest, Ahr) for m in METHODES}
            print("HR", nom, {m: round(entree["methodes"][m]["polygones_retournes"]) for m in METHODES},
                  "erreur_LBS", entree.get("erreur_LBS_vs_Blender_m"), flush=True)

        # captures : profil (axes Y, Z), couleur = étirement maximal du sommet, calculé pour la méthode du panneau
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        rng = np.random.default_rng(0)
        choix = rng.choice(Nh, size=min(150000, Nh), replace=False)
        fig, axes = plt.subplots(len(METHODES), len(CAPTURES_POSES), figsize=(5 * len(CAPTURES_POSES), 3.6 * len(METHODES)))
        for i, m in enumerate(METHODES):
            for j, nom in enumerate(CAPTURES_POSES):
                ax = axes[i][j]
                p = captures[nom][m][choix]
                ax.scatter(p[:, 1], p[:, 2], s=0.2, c=np.clip(captures[nom]["vmax"][m][choix], 1.0, 2.0),
                           cmap="viridis", vmin=1.0, vmax=2.0)
                ax.set_title(f"{m} - {nom}", fontsize=9)
                ax.set_aspect("equal")
                ax.set_xlim(-0.6, 0.6)
                ax.set_ylim(-0.1, 2.0)
        fig.tight_layout()
        fig.savefig(os.path.join(sortie, "captures_profil.png"), dpi=110)
        plt.close(fig)

    resume = {"fichier_source": npz, "methodes": METHODES, "poses_base": ["neutre"] + poses,
              "poses_hr": sorted(hr.keys()), "signes": json.loads(open(npz.replace(".npz", ".json")).read())["signes"],
              "base": arrondir(base), "hr": arrondir(hr)}
    with open(os.path.join(sortie, "comparatif.json"), "w") as f:
        json.dump(resume, f, indent=2, ensure_ascii=False)
    print("COMPARATIF_OK", os.path.join(sortie, "comparatif.json"))


if __name__ == "__main__":
    main()
