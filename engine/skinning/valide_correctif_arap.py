"""Validation hors entraînement des correctifs ARAP interpolés (entraînement 60/90/120, test 75/105).
Usage : python3 valide_correctif_arap.py DOSSIER_AVEC_donnees6.npz
"""
import sys, numpy as np
sys.path.insert(0, __import__("os").path.dirname(__file__))
from correctif_arap import arap_cible, _lbs
from plis_numpy import plis_positions
from lbs_numpy import etirements
S = sys.argv[1]  # dossier contenant donnees6.npz
d = np.load(S + "donnees6.npz", allow_pickle=True)
rest, W, M, ar, faces = d["rest"], d["W"], d["M"], d["aretes"], d["faces"]
ang = [0, 60, 75, 90, 105, 120]
os_n = [str(o) for o in d["os"]]
tronc = [os_n.index(n) for n in os_n if n.split(":")[-1] in ("Hips","Spine","Spine1","Spine2","Neck","Head")]
ancre = W[:, tronc].sum(1) > 0.99     # sommets du tronc : fixés pendant l'ARAP
ij_ar = ar
ETIQ = ["mixamorig:LeftArm", "mixamorig:LeftForeArm", "mixamorig:LeftLeg"]
print("ancres:", ancre.sum(), "sommets")
for c in range(3):
    corr = {}
    for k, a in enumerate(ang):
        p = c * 6 + k
        P0, Pa = arap_cible(rest, W, M[p], ij_ar, ancre, iters=40)
        corr[a] = Pa - P0
    # tests hors entraînement : 75 (entre 60 et 90), 105 (entre 90 et 120)
    for test, lo, hi in [(75, 60, 90), (105, 90, 120)]:
        p = c * 6 + ang.index(test)
        P0 = _lbs(rest, W, M[p])
        t = (test - lo) / (hi - lo)
        dlt = corr[lo] + t * (corr[hi] - corr[lo])
        P1 = P0 + dlt
        s0 = etirements(P0, rest, ar); s1 = etirements(P1, rest, ar)
        f0 = plis_positions(rest, P0, W, M[p], faces); f1 = plis_positions(rest, P1, W, M[p], faces)
        print(f"{ETIQ[c]:>22} {test}deg  LBS: plis={f0:4d} etir_max={s0['max']:.3f} min={s0['min']:.3f} | ARAP-interp: plis={f1:4d} etir_max={s1['max']:.3f} min={s1['min']:.3f}")
