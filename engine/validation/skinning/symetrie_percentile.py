"""Critère d'asymétrie robuste à la topologie (Maria). Critère fixé dans docs/rapports/skinning/criteres_asymetrie_maria.md.

Usage : python3 engine/validation/skinning/symetrie_percentile.py POSES.npz [SORTIE.json]
"""
import json
import os
import sys

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import methodes as M  # noqa: E402
import mesures as Ms  # noqa: E402

SEUIL_RELATIF = 0.05  # critère 3, fixé à l'avance
MOUVEMENTS = ["flex30", "flex60", "flex90", "flex120", "abd30", "add20", "ext30", "int30",
              "genou30", "genou60", "genou90", "combo_flex90_abd30_ext30", "combo_flex120_genou90",
              "combo_flex60_abd20_int20_genou60"]


def ratios(pos, rest, A, filtre):
    l0 = np.linalg.norm(rest[A[:, 0]] - rest[A[:, 1]], axis=1)
    l1 = np.linalg.norm(pos[A[:, 0]] - pos[A[:, 1]], axis=1)
    return np.where(filtre, l1 / np.maximum(l0, 1e-12), np.nan)


def main():
    npz = sys.argv[1]
    sortie = sys.argv[2] if len(sys.argv) > 2 else None
    d = np.load(npz)
    meta = json.load(open(npz.replace(".npz", ".json")))
    rest, Wi, Ww, B = d["rest_monde"], d["W_idx"], d["W_w"], d["bones_rest_monde"]
    b, tot = d["b_boucle"], d["b_tot"]
    A = Ms.aretes(b, tot, len(rest))
    xc = float(meta["plan_median_x"])
    refl = rest.copy(); refl[:, 0] = 2 * xc - rest[:, 0]
    _, assoc = cKDTree(rest).query(refl)
    # appariement des arêtes : arête (a,b) gauche <-> arête (image a, image b) droite
    cle = {tuple(sorted(e)): k for k, e in enumerate(np.asarray(A))}
    paires_g, paires_d = [], []
    for k, (a, c) in enumerate(np.asarray(A)):
        kd = cle.get(tuple(sorted((assoc[a], assoc[c]))))
        if kd is not None:
            paires_g.append(k); paires_d.append(kd)
    pg_idx, pd_idx = np.array(paires_g), np.array(paires_d)
    filtre_repos = np.linalg.norm(rest[A[:, 0]] - rest[A[:, 1]], axis=1) >= 0.005
    res = {"nb_aretes": int(len(A)), "nb_paires": int(len(pg_idx)),
            "part_paires": float(len(pg_idx) / len(A)), "seuil": SEUIL_RELATIF, "mouvements": {}}
    echecs = []
    for mv in MOUVEMENTS:
        gauche, droite = "L_" + mv, "R_" + mv
        if gauche + "__os" not in d.files or droite + "__os" not in d.files:
            continue
        pg = M.calculer_toutes(rest, Wi, Ww, B, d[gauche + "__os"])[0]["LBS"]
        pdr = M.calculer_toutes(rest, Wi, Ww, B, d[droite + "__os"])[0]["LBS"]
        rg = ratios(pg, rest, A, filtre_repos)[pg_idx]
        rd = ratios(pdr, rest, A, filtre_repos)[pd_idx]
        ok_g = ~np.isnan(rg) & ~np.isnan(rd)
        p99g = float(np.percentile(rg[ok_g], 99)); p99d = float(np.percentile(rd[ok_g], 99))
        ecart = abs(p99g - p99d) / p99d
        ok = ecart < SEUIL_RELATIF
        if not ok:
            echecs.append(mv)
        res["mouvements"][mv] = {"p99_gauche": p99g, "p99_droite": p99d, "ecart_relatif": ecart, "OK": ok}
        print(("OK   " if ok else "ECHEC") + f" {mv}: p99 étirement G {p99g:.3f} D {p99d:.3f} (écart {ecart*100:.2f} %)",
              flush=True)
    res["echecs"] = echecs
    if sortie:
        json.dump(res, open(sortie, "w"), indent=2, ensure_ascii=False)
    print("SYMETRIE_PERCENTILE", "OK" if not echecs else "ECHEC " + ",".join(echecs))
    return 0 if not echecs else 1


if __name__ == "__main__":
    sys.exit(main())
