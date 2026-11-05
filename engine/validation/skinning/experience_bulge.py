"""Variante DQS + anti-gonflement (Kim & Han 2014, correction_bulge.py) comparée au DQS et au DQS + volume (Rohmer).
Mêmes poses et mesures que comparer_v2. Usage : python3 experience_bulge.py POSES.npz NOM SORTIE.json
"""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import methodes as M  # noqa: E402
import mesures as Ms  # noqa: E402
import metriques_locales as ML  # noqa: E402
import correction_bulge as CB  # noqa: E402
import correction_volume as CV  # noqa: E402


def mesurer(p, rest, b, tot, A, Mv, zone):
    mes = Ms.mesurer(p, rest, b, tot, A, Mv=Mv)
    dfx = ML.defauts(p, rest, b, tot, A)
    dfx.pop("_vertex_etirement"); dfx.pop("_vertex_compression")
    vol = ML.volume_local(p, rest, b, tot, zone_polygone=zone)
    return {"etirement_max": dfx["etirement_max"], "etirement_p99": mes["etirement_p99"],
            "n>1.1": dfx["sommets_etires_>1.1"], "n>1.25": dfx["sommets_etires_>1.25"],
            "n>1.5": dfx["sommets_etires_>1.5"], "retournements": mes["polygones_retournes"],
            "volume_total": vol["variation_volume_total"], "volume_zone": vol["variation_volume_zone"]}


def main():
    npz, nom, sortie = sys.argv[1], sys.argv[2], sys.argv[3]
    d = np.load(npz)
    rest, Wi, Ww, B = d["rest_monde"], d["W_idx"], d["W_w"], d["bones_rest_monde"]
    b, tot = d["b_boucle"], d["b_tot"]
    noms = [str(n) for n in d["noms_os"]]
    A = Ms.aretes(b, tot, len(rest))
    T = CV._triangles(b, tot)
    head = B[noms.index("mixamorig:LeftUpLeg")][:3, 3]
    zs = np.where(np.linalg.norm(rest - head, axis=1) < 0.20)[0]
    mz = np.zeros(len(rest), bool); mz[zs] = True
    debut = np.concatenate([[0], np.cumsum(tot)[:-1]]).astype(np.int64)
    zone = np.array([mz[b[debut[p]:debut[p] + tot[p]]].mean() > 0.5 for p in range(len(tot))])
    out = {"personnage": nom, "approximation_segments_m": CB.LONGUEUR_DEFAUT, "poses": {}, "cpu_s": {}}
    poses = sorted({k[:-4] for k in d.files if k.endswith("__os")})
    for pose in poses:
        pm = d[pose + "__os"]
        pos_m, _ = M.calculer_toutes(rest, Wi, Ww, B, pm)
        Mv = M.repere_rigide(Wi, Ww, B, pm)
        T_pose = pm @ np.linalg.inv(B)
        pd = pos_m["DQS"]
        tic = time.process_time()
        pk, info = CB.corriger(pd, rest, Wi, Ww, B, T_pose, noms)
        out["cpu_s"].setdefault("DQS+KH", []).append(time.process_time() - tic)
        pv, _ = CV.corriger(pd, rest, Wi, Ww, b, tot, T=T, M=3)
        out["poses"][pose] = {"DQS": mesurer(pd, rest, b, tot, A, Mv, zone),
                              "DQS+KH": mesurer(pk, rest, b, tot, A, Mv, zone),
                              "DQS+Rohmer3": mesurer(pv, rest, b, tot, A, Mv, zone),
                              "DQS+KH_sommets_corriges": info["part_corriges"]}
    out["cpu_s"] = {k: float(np.mean(v)) for k, v in out["cpu_s"].items()}
    json.dump(out, open(sortie, "w"), indent=2, ensure_ascii=False)
    print("BULGE_OK", nom, out["cpu_s"])


if __name__ == "__main__":
    main()
