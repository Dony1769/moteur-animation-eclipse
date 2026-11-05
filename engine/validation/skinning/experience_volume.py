"""Étape B (phase 4) : correction locale de volume (Rohmer et al. 2008) appliquée au LBS et au DQS, mêmes poses et
mesures que comparer_v2. Variantes : LBS, LBS+C1 (1 étape), LBS+C3 (3 étapes), DQS, DQS+C3.
Usage : python3 experience_volume.py POSES.npz NOM SORTIE.json
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
import correction_volume as CV  # noqa: E402


def mesurer(p, rest, b, tot, A, Mv, zone):
    mes = Ms.mesurer(p, rest, b, tot, A, Mv=Mv)
    dfx = ML.defauts(p, rest, b, tot, A)
    vmax = np.nan_to_num(dfx.pop("_vertex_etirement"), nan=1.0)
    dfx.pop("_vertex_compression")
    vol = ML.volume_local(p, rest, b, tot, zone_polygone=zone)
    return {"etirement_max": dfx["etirement_max"], "etirement_p99": mes["etirement_p99"],
            "n>1.1": dfx["sommets_etires_>1.1"], "n>1.25": dfx["sommets_etires_>1.25"],
            "n>1.5": dfx["sommets_etires_>1.5"], "retournements": mes["polygones_retournes"],
            "volume_total": vol["variation_volume_total"], "volume_zone": vol["variation_volume_zone"],
            "max_zone_hanche": float(vmax[zone_sommets_hanche].max())}


zone_sommets_hanche = None


def main():
    global zone_sommets_hanche
    npz, nom, sortie = sys.argv[1], sys.argv[2], sys.argv[3]
    d = np.load(npz)
    rest, Wi, Ww, B = d["rest_monde"], d["W_idx"], d["W_w"], d["bones_rest_monde"]
    b, tot = d["b_boucle"], d["b_tot"]
    noms = [str(n) for n in d["noms_os"]]
    A = Ms.aretes(b, tot, len(rest))
    T = CV._triangles(b, tot)
    head = B[noms.index("mixamorig:LeftUpLeg")][:3, 3]
    zone_sommets_hanche = np.where(np.linalg.norm(rest - head, axis=1) < 0.20)[0]
    debut = np.concatenate([[0], np.cumsum(tot)[:-1]]).astype(np.int64)
    zone = np.zeros(len(tot), bool)
    mz = np.zeros(len(rest), bool); mz[zone_sommets_hanche] = True
    for p_i in range(len(tot)):
        zone[p_i] = mz[b[debut[p_i]:debut[p_i] + tot[p_i]]].mean() > 0.5
    poses = sorted({k[:-4] for k in d.files if k.endswith("__os")})
    out = {"personnage": nom, "G_locale": CV.G_LOCAL, "poses": {}, "temps_cpu_s": {}}
    for pose in poses:
        pm = d[pose + "__os"]
        pos_m, _ = M.calculer_toutes(rest, Wi, Ww, B, pm)
        Mv = M.repere_rigide(Wi, Ww, B, pm)
        res = {}
        for base in ["LBS", "DQS"]:
            p0 = pos_m[base]
            res[base] = mesurer(p0, rest, b, tot, A, Mv, zone)
            tic = time.process_time()
            p1, dg1 = CV.corriger(p0, rest, Wi, Ww, b, tot, T=T, M=1)
            t1 = time.process_time() - tic
            tic = time.process_time()
            p3, dg3 = CV.corriger(p0, rest, Wi, Ww, b, tot, T=T, M=3)
            t3 = time.process_time() - tic
            res[base + "+C1"] = mesurer(p1, rest, b, tot, A, Mv, zone)
            res[base + "+C1"]["volume_residuel_relatif"] = float(dg1["relatif_apres"])
            res[base + "+C3"] = mesurer(p3, rest, b, tot, A, Mv, zone)
            res[base + "+C3"]["volume_residuel_relatif"] = float(dg3["relatif_apres"])
            out["temps_cpu_s"].setdefault(base + "+C1", []).append(t1)
            out["temps_cpu_s"].setdefault(base + "+C3", []).append(t3)
        out["poses"][pose] = res
        print(nom, pose, "LBS max %.3f  LBS+C3 max %.3f vol %+.4f->%+.1e | DQS max %.3f DQS+C3 max %.3f" % (
            res["LBS"]["etirement_max"], res["LBS+C3"]["etirement_max"], res["LBS"]["volume_total"],
            res["LBS+C3"]["volume_residuel_relatif"], res["DQS"]["etirement_max"], res["DQS+C3"]["etirement_max"]), flush=True)
    out["temps_cpu_s"] = {k: float(np.mean(v)) for k, v in out["temps_cpu_s"].items()}
    json.dump(out, open(sortie, "w"), indent=2, ensure_ascii=False)
    print("VOLUME_OK", nom, out["temps_cpu_s"])


if __name__ == "__main__":
    main()
