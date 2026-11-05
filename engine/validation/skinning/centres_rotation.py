"""Axe 1 : balayage du centre de rotation de la hanche GAUCHE, poids et méthodes inchangés.

Principe : la tête de l'os UpLeg (h) est le pivot de l'armature. Un pivot c donne, pour toute la chaîne de la jambe
(UpLeg, Leg, Foot), la transformation T' = Tr((I - R)(c - h)) · T, où R est la rotation de la hanche. Cette
formule est exacte (conjugaison de translation) et n'agit que sur les transformations d'os, jamais sur les poids.

Référence anatomique (bornes du balayage, pas une vérité) : Fiorentino et al. 2015, PMC4893978, table 1 : centre
fémoral environ 80 mm sous l'origine du bassin, incertitude 11 à 23 mm selon les méthodes (origine non précisée).
Le centre choisi par le balayage n'est donc PAS validé anatomiquement : il est choisi par les métriques, et doit être
confirmé sur d'autres morphologies (axe 4).

Usage : python3 engine/validation/skinning/centres_rotation.py POSES.npz POIDS_HR.npz SORTIE.json
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import methodes as M  # noqa: E402
import mesures as Ms  # noqa: E402
from experience_poids_lissage import creuser  # noqa: E402

CHAINE = ["mixamorig:LeftUpLeg", "mixamorig:LeftLeg", "mixamorig:LeftFoot"]
DECALAGES = [(0.0, 0.0, 0.0), (0.0, 0.0, -0.03), (0.0, 0.0, -0.06), (0.0, 0.0, 0.03), (0.0, 0.0, 0.06),
             (0.02, 0.0, 0.0), (-0.02, 0.0, 0.0), (0.0, 0.02, 0.0), (0.0, -0.02, 0.0)]
POSES = ["L_flex90", "L_flex120", "L_abd30", "L_add20", "L_ext30", "L_combo_flex90_abd30_ext30",
         "L_combo_flex120_genou90"]


def appliquer_pivot(T, noms, h, c, pose_flex_R):
    """Pivot c au lieu de h pour la chaîne gauche. pose_flex_R : rotation monde de la hanche (3x3)."""
    delta = (np.eye(3) - pose_flex_R) @ (c - h)
    A = np.eye(4)
    A[:3, 3] = delta
    T2 = T.copy()
    for nom in CHAINE:
        j = noms.index(nom)
        T2[j] = A @ T[j]
    return T2


def main():
    npz, poids, sortie = sys.argv[1], sys.argv[2], sys.argv[3]
    d = np.load(npz)
    rest = d["rest_monde"]
    B = d["bones_rest_monde"]
    noms = [str(n) for n in d["noms_os"]]
    b, tot = d["b_boucle"], d["b_tot"]
    h_pos = B[noms.index("mixamorig:LeftUpLeg")][:3, 3].copy()
    h_pose = d["L_flex90__os"]  # sert seulement à obtenir le repère de pose (T construit ci-dessous)
    # maillage de base
    A = Ms.aretes(b, tot, len(rest))
    Wi, Ww = d["W_idx"], d["W_w"]
    # maillage haute résolution (poids Blender)
    ph = np.load(poids)
    hr = d["hr_rest"].astype(np.float64)
    hWi, hWw = creuser(ph["hr_pesos"].astype(np.float64))
    Ahr = Ms.aretes(d["hr_boucle"], d["hr_tot"], len(hr))
    resultats = {"pivot_tete_os_m": h_pos.tolist(), "decalages_m": DECALAGES, "poses": {}}
    for pose in POSES:
        pm = d[pose + "__os"]
        T0 = pm @ np.linalg.inv(B)
        Rh = T0[noms.index("mixamorig:LeftUpLeg"), :3, :3]
        entree = {}
        for dec in DECALAGES:
            c = h_pos + np.array(dec)
            T = appliquer_pivot(T0, noms, h_pos, c, Rh)
            base_pos, _ = M.calculer_depuis_T(rest, Wi, Ww, T)
            mv = M.repere_depuis_T(Wi, Ww, T)
            res = {}
            for m in ["LBS", "DQS"]:
                mes = Ms.mesurer(base_pos[m], rest, b, tot, A, Mv=mv)
                res[f"base_{m}"] = {k: mes[k] for k in ["etirement_max", "etirement_p99", "polygones_retournes",
                                                       "variation_volume_relative", "sommets_aberrants"]}
            hr_pos, _ = M.calculer_depuis_T(hr, hWi, hWw, T)
            mvh = M.repere_depuis_T(hWi, hWw, T)
            for m in ["LBS", "DQS"]:
                mes = Ms.mesurer(hr_pos[m], hr, d["hr_boucle"], d["hr_tot"], Ahr, Mv=mvh)
                res[f"hr_{m}"] = {k: mes[k] for k in ["etirement_max", "etirement_p99", "polygones_retournes",
                                                     "variation_volume_relative", "sommets_aberrants"]}
            entree[str(dec)] = res
            print(pose, dec, "base LBS etir %.3f flips %d vol %+.4f | hr LBS flips %d vol %+.4f" % (
                res["base_LBS"]["etirement_max"], res["base_LBS"]["polygones_retournes"],
                res["base_LBS"]["variation_volume_relative"], res["hr_LBS"]["polygones_retournes"],
                res["hr_LBS"]["variation_volume_relative"]), flush=True)
        resultats["poses"][pose] = entree
    with open(sortie, "w") as f:
        json.dump(resultats, f, indent=2, ensure_ascii=False)
    print("CENTRES_OK", sortie)


if __name__ == "__main__":
    main()
