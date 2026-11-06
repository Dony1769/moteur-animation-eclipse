"""Concordance gauche/droite des retournements nouveaux de Maria (phase 3).

Pour chaque paire de poses gauche/droite (poses réelles, non miroir exactes), on compte :
  - les retournements nouveaux à gauche (mesure A, introduits par SQ) ;
  - parmi eux, ceux dont le triangle miroir se retourne aussi à droite dans la pose appariée ;
  - les retournements nouveaux à droite dont le miroir ne se retourne pas à gauche.
Aucun seuil n'est modifié.
"""
import json
import os

import numpy as np
from scipy.spatial import cKDTree

import investigation_maria_geometrie as G

SORTIE = os.path.join(G.RACINE, "docs", "rapports", "skinning", "maria_geometrie")

PAIRES = [
    ("reelle_L_flex120", "reelle_R_flex120"),
    ("reelle_L_flex60", "reelle_R_flex60"),
    ("reelle_L_combo_flex120_genou90", "reelle_R_combo_flex120_genou90"),
    ("reelle_L_combo_flex60_abd20_int20_genou60", "reelle_R_combo_flex60_abd20_int20_genou60"),
]

if __name__ == "__main__":
    os.makedirs(SORTIE, exist_ok=True)
    M = G.CMP.charger_morph("maria")
    rest, tris = M["rest"], M["tris"]
    miroir = rest.copy()
    miroir[:, 0] = -rest[:, 0]
    _, im = cKDTree(rest).query(miroir)
    cle = {tuple(sorted(t)): i for i, t in enumerate(tris)}
    mt = np.array([cle.get(tuple(sorted(im[t])), -1) for t in tris])
    out = []
    for pL, pR in PAIRES:
        lL, sL, ML, _ = G.mesure_pose(M, rest, G.CMP.pose_de(M, pL))
        lR, sR, MR, _ = G.mesure_pose(M, rest, G.CMP.pose_de(M, pR))
        fL = G.flags(rest, tris, lL, sL, ML)
        fR = G.flags(rest, tris, lR, sR, MR)
        nL_ = fL["nouveau_A"]
        nR_ = fR["nouveau_A"]
        gauche = np.where(nL_)[0]
        ok_g = [int(t) for t in gauche if mt[t] >= 0 and nR_[mt[t]]]
        sans_miroir_g = [int(t) for t in gauche if mt[t] < 0]
        droite = np.where(nR_)[0]
        ok_d = [int(t) for t in droite if mt[t] >= 0 and nL_[mt[t]]]
        out.append({"pose_gauche": pL, "pose_droite": pR,
                    "nouveaux_gauche": int(len(gauche)), "gauche_dont_miroir_droite_retourne": len(ok_g),
                    "gauche_sans_miroir": len(sans_miroir_g),
                    "nouveaux_droite": int(len(droite)), "droite_dont_miroir_gauche_retourne": len(ok_d)})
        print(out[-1], flush=True)
    res = {"convention": "mesure A (introduit par SQ) ; pose gauche/droite réelles, non miroir exactes",
           "paires": out,
           "total_gauche": sum(p["nouveaux_gauche"] for p in out),
           "total_gauche_concordant": sum(p["gauche_dont_miroir_droite_retourne"] for p in out)}
    with open(os.path.join(SORTIE, "concordance_miroir.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print("ECRIT", res["total_gauche"], res["total_gauche_concordant"], flush=True)
