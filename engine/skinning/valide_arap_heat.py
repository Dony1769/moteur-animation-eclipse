"""Correctif ARAP interpolé sur une base de poids donnée (bras gauche), validation hors entraînement.

Entraînement : 60, 90, 120° ; test : 75 et 105° (interpolation entre les deux clés voisines), comme
valide_correctif_arap.py. Mesure plis et étirement avant/après. Usage :
  python3 valide_arap_heat.py DOSSIER/ FICHIER_POIDS.npz [CHAINE]
CHAINE : LeftArm (défaut), LeftForeArm ou LeftLeg.
"""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from correctif_arap import arap_cible, _lbs
from plis_numpy import plis_positions
from lbs_numpy import etirements

S = sys.argv[1].rstrip("/") + "/"
f = sys.argv[2]
chaine = sys.argv[3] if len(sys.argv) > 3 else "LeftArm"
W = np.load(f)["W"] if f.endswith(".npz") else np.load(f)
W = W / W.sum(1, keepdims=True)
d = np.load(S + "donnees7.npz", allow_pickle=True)
rest, M, ar, faces, ang, etiq = d["rest"], d["M"], d["aretes"], d["faces"], list(d["angles"]), list(d["etiquettes"])
os_n = [str(o) for o in d["os"]]
tronc = [os_n.index(n) for n in ("mixamorig:Hips", "mixamorig:Spine", "mixamorig:Spine1", "mixamorig:Neck", "mixamorig:Head")]
ancre = W[:, tronc].sum(1) > 0.99
c0 = 0  # bras gauche : lignes 0..7 de donnees7
def idx(a): return etiq.index(f"{chaine}@{a}")
corr = {}
for a in (60, 90, 120):
    p = idx(a)
    P0, Pa = arap_cible(rest, W, M[p], ar, ancre, iters=40)
    corr[a] = Pa - P0
print(chaine)
print(f"{'test':>6} | {'LBS plis':>8} {'ARAP plis':>9} | {'LBS étir':>8} {'ARAP étir':>9}")
for test, lo, hi in ((75, 60, 90), (105, 90, 120)):
    p = idx(test)
    P0 = _lbs(rest, W, M[p])
    t = (test - lo) / (hi - lo)
    P1 = P0 + corr[lo] + t * (corr[hi] - corr[lo])
    print(f"{test:>5}° | {plis_positions(rest,P0,W,M[p],faces):8d} {plis_positions(rest,P1,W,M[p],faces):9d} | "
          f"{etirements(P0,rest,ar)['max']:8.3f} {etirements(P1,rest,ar)['max']:9.3f}")
P0 = _lbs(rest, W, M[idx(120)]); P1 = P0 + corr[120]
print(f"120° (entraînement) | LBS plis {plis_positions(rest,P0,W,M[idx(120)],faces)} ; ARAP plis {plis_positions(rest,P1,W,M[idx(120)],faces)} ; étir {etirements(P1,rest,ar)['max']:.3f}")
