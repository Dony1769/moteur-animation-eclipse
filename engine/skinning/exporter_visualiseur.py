"""Exporte les données du visualiseur 3D (phase 4) : pour chaque chaîne et angle, positions LBS et
positions corrigées (LBS(repos + correctif)), plis par sommet et étirement par sommet.

Usage : python3 exporter_visualiseur.py DOSSIER/ W_final.npz CORR.npz SORTIE.json
"""
import sys, os, json, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from correctif_arap import _lbs
from plis_numpy import plis_masque

S, w_f, c_f, sortie = sys.argv[1].rstrip("/") + "/", sys.argv[2], sys.argv[3], sys.argv[4]
d = np.load(S + "donnees7.npz", allow_pickle=True)
rest, M, faces, ar, etiq = d["rest"], d["M"], d["faces"], d["aretes"], list(d["etiquettes"])
W = np.load(w_f)["W"]; W = W / W.sum(1, keepdims=True)
C = np.load(c_f)
ANG = (0, 60, 75, 90, 105, 120)
CH = ("LeftArm", "LeftForeArm", "LeftLeg")

def corr_pour(chaine, a):
    if a in (0, 60, 90, 120):
        return np.zeros_like(rest) if a == 0 else C[f"{chaine}_{a}"]
    lo, hi = (60, 90) if a < 90 else (90, 120)
    t = (a - lo) / (hi - lo)
    return (1 - t) * C[f"{chaine}_{lo}"] + t * C[f"{chaine}_{hi}"]

def etirement_par_sommet(P):
    r = np.zeros(len(rest)); cnt = np.zeros(len(rest))
    i, j = ar[:, 0], ar[:, 1]
    L0 = np.linalg.norm(rest[i] - rest[j], axis=1); L1 = np.linalg.norm(P[i] - P[j], axis=1)
    ratio = L1 / np.maximum(L0, 1e-9)
    np.maximum.at(r, i, ratio); np.maximum.at(r, j, ratio)
    return r

def plis_sommets(P, Wx, Mx):
    m = plis_masque(rest, P, Wx, Mx, faces)
    v = np.zeros(len(rest), np.uint8)
    for k in np.where(m)[0]:
        v[list(faces[k])] = 1
    return int(m.sum()), v

tri = []
for f in faces:
    b = list(f)
    for k in range(1, len(b) - 1):
        tri.append([b[0], b[k], b[k + 1]])
frames = []
for c in CH:
    for a in ANG:
        p = etiq.index(f"{c}@{a}") if a != 0 else etiq.index(f"{c}@0")
        P_l = _lbs(rest, W, M[p])
        P_c = _lbs(rest + corr_pour(c, a), W, M[p]) if a != 0 else P_l
        pl, vl = plis_sommets(P_l, W, M[p]); pc, vc = plis_sommets(P_c, W, M[p])
        frames.append({"chaine": c, "angle": a,
                       "lbs": np.round(P_l, 3).ravel().tolist(), "cor": np.round(P_c, 3).ravel().tolist(),
                       "etir_lbs": np.round(etirement_par_sommet(P_l), 2).tolist(),
                       "etir_cor": np.round(etirement_par_sommet(P_c), 2).tolist(),
                       "plis_lbs": pl, "plis_cor": pc,
                       "pli_v_lbs": vl.tolist(), "pli_v_cor": vc.tolist()})
        print(c, a, "plis lbs", pl, "cor", pc, flush=True)
out = {"rest": np.round(rest, 3).ravel().tolist(), "tri": tri, "angles": list(ANG), "chaines": list(CH), "frames": frames}
json.dump(out, open(sortie, "w"))
print("ECRIT", sortie, os.path.getsize(sortie) // 1024, "Ko")
