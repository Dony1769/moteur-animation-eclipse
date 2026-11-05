"""Correctifs ARAP ramenés à l'espace de repos (phase 4), pour validation dans Blender.

Pour chaque chaîne (LeftArm, LeftForeArm, LeftLeg) et chaque angle d'entraînement (60, 90, 120) :
  delta = positions ARAP - positions LBS (espace armature, pose donnée)
  d     = A^-1 · delta,  A_i = somme_b W_ib R_b  (R_b : partie 3x3 de M_b)
Ainsi LBS(repos + d) ≈ LBS(repos) + delta. Sortie : npz clé f"{chaine}_{angle}".
Usage : python3 corrections_repos.py DOSSIER/ BASE.npz SORTIE.npz
"""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from correctif_arap import arap_cible

S, base, sortie = sys.argv[1].rstrip("/") + "/", sys.argv[2], sys.argv[3]
d = np.load(S + "donnees7.npz", allow_pickle=True)
rest, M, ar, etiq = d["rest"], d["M"], d["aretes"], list(d["etiquettes"])
os_n = [str(o) for o in d["os"]]
W = np.load(base)["W"]; W = W / W.sum(1, keepdims=True)
tronc = [os_n.index(n) for n in ("mixamorig:Hips", "mixamorig:Spine", "mixamorig:Spine1", "mixamorig:Neck", "mixamorig:Head")]
ancre = W[:, tronc].sum(1) > 0.99
out = {}
for chaine in ("LeftArm", "LeftForeArm", "LeftLeg"):
    for a in (60, 90, 120):
        p = etiq.index(f"{chaine}@{a}")
        P0, Pa = arap_cible(rest, W, M[p], ar, ancre, iters=40)
        delta = Pa - P0
        R = M[p][:, :3, :3]                                   # (B, 3, 3)
        A = np.einsum("ib,bjk->ijk", W, R)                    # (N, 3, 3)
        A += 1e-6 * np.eye(3)[None]
        d_rest = np.linalg.solve(A, delta[:, :, None])[:, :, 0]
        out[f"{chaine}_{a}"] = d_rest
        print(chaine, a, "|delta| max", round(float(np.linalg.norm(delta, axis=1).max()), 4), flush=True)
np.savez(sortie, **out)
print("ECRIT", sortie)
