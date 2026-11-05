"""Compare les plis LBS et l'étirement avant/après remplacement de l'auxiliaire de torsion par sa torsion
seule, sur toutes les poses de donnees7. Usage : python3 test_torsion_helper.py DOSSIER/"""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from torsion_helper import axe_os, aux_torsion_seule
from plis_numpy import plis_positions
from lbs_numpy import etirements
from correctif_arap import _lbs

S = sys.argv[1].rstrip("/") + "/"
d = np.load(S + "donnees7.npz", allow_pickle=True)
rest, M, ar, faces, ang, etiq = d["rest"], d["M"], d["aretes"], d["faces"], list(d["angles"]), list(d["etiquettes"])
os_n = [str(o).split(":")[-1] for o in d["os"]]
W0 = np.load(S + "W_seq_final.npy")
ih, ia = os_n.index("LeftArmHelper"), os_n.index("LeftArm")
poids_bras = W0[:, [ia, ih]].sum(1)
M2 = M.copy()
for p in range(len(etiq)):
    M2[p, ih] = aux_torsion_seule(M[p, ih], rest, poids_bras)[0]
print(f"{'pose':>17} | {'plis avant':>10} {'plis après':>10} | {'étir max avant':>14} {'après':>8}")
for p, e in enumerate(etiq):
    if not str(e).startswith("LeftArm@"): continue
    P0 = _lbs(rest, W0, M[p]); P1 = _lbs(rest, W0, M2[p])
    f0 = plis_positions(rest, P0, W0, M[p], faces); f1 = plis_positions(rest, P1, W0, M2[p], faces)
    s0 = etirements(P0, rest, ar)["max"]; s1 = etirements(P1, rest, ar)["max"]
    print(f"{str(e):>17} | {f0:10d} {f1:10d} | {s0:14.3f} {s1:8.3f}")
