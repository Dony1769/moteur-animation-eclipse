"""Diagnostic des plis à 120° sur le bras gauche (phase 4).

1. Localise les faces repliées en LBS pur : os dominant et étendue (coordonnées de repos).
2. Teste si reporter une part du poids de l'os auxiliaire de torsion (LeftArmHelper) sur LeftArm supprime les plis.
Usage : python3 diagnostic_plis_120.py DOSSIER/ (contient donnees7.npz et W_seq_final.npy)
Résultat mesuré (session du 4 nov. 2026) : 20 plis en LBS à 120° ; report de 50 % ou 100 % du poids de
l'auxiliaire : 17 et 23 plis. Le report seul ne résout pas le problème.
"""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from plis_numpy import plis_masque, plis_positions
from lbs_numpy import etirements
from correctif_arap import _lbs

S = sys.argv[1].rstrip("/") + "/"
d = np.load(S + "donnees7.npz", allow_pickle=True)
rest, M, faces, ar = d["rest"], d["M"], d["faces"], d["aretes"]
os_n = [str(o).split(":")[-1] for o in d["os"]]
ang = list(d["angles"]); p = ang.index(120)          # bras gauche à 120° (c = 0)
W0 = np.load(S + "W_seq_final.npy")

m = plis_masque(rest, _lbs(rest, W0, M[p]), W0, M[p], faces)
idx = np.where(m)[0]
print("LBS 120° : plis", int(m.sum()))
if len(idx):
    sommets = np.unique(np.concatenate([np.array(list(faces[k])) for k in idx]))
    dom = np.bincount(W0[sommets].argmax(1), minlength=W0.shape[1])
    print("  os dominants :", {os_n[i]: int(dom[i]) for i in np.argsort(-dom)[:4] if dom[i] > 0})
    print("  étendue repos x", rest[sommets, 0].min().round(3), rest[sommets, 0].max().round(3),
          " z", rest[sommets, 2].min().round(3), rest[sommets, 2].max().round(3))

ih, ia = os_n.index("LeftArmHelper"), os_n.index("LeftArm")
for frac in (0.5, 1.0):
    W = W0.copy()
    W[:, ia] += frac * W[:, ih]; W[:, ih] *= (1 - frac)
    P = _lbs(rest, W, M[p])
    e = etirements(P, rest, ar)
    print(f"report {frac:.0%} : plis {plis_positions(rest, P, W, M[p], faces)}, étirement max {e['max']:.3f}")
