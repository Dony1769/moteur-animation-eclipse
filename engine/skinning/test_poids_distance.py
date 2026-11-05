"""Compare les poids par distance (sans optimisation) aux poids optimisés de référence, sur le bras gauche,
sur les poses de donnees7 (LBS seul). Usage : python3 test_poids_distance.py DOSSIER/ (donnees7.npz, W_seq_final.npy, os_repos.json)"""
import sys, os, json, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from poids_distance import poids_distance
from plis_numpy import plis_positions
from lbs_numpy import etirements
from correctif_arap import _lbs

S = sys.argv[1].rstrip("/") + "/"
d = np.load(S + "donnees7.npz", allow_pickle=True)
rest, M, ar, faces, etiq = d["rest"], d["M"], d["aretes"], d["faces"], list(d["etiquettes"])
os_n = [str(o) for o in d["os"]]
W_ref = np.load(S + "W_seq_final.npy")
os_repos = json.load(open(S + "os_repos.json"))["os"]
W_dist = poids_distance(rest, os_n, os_repos)
print("sommets sans poids (dist) :", int((W_dist.sum(1) == 0).sum()), " influences max :", int((W_dist > 0).sum(1).max()))
print(f"{'pose':>17} | {'plis réf':>8} {'plis dist':>9} | {'étir réf':>8} {'étir dist':>9}")
for p, e in enumerate(etiq):
    if not str(e).startswith("LeftArm@") and not str(e).startswith("LeftForeArm@"): continue
    Pr = _lbs(rest, W_ref, M[p]); Pd = _lbs(rest, W_dist, M[p])
    print(f"{str(e):>17} | {plis_positions(rest,Pr,W_ref,M[p],faces):8d} {plis_positions(rest,Pd,W_dist,M[p],faces):9d} | "
          f"{etirements(Pr,rest,ar)['max']:8.3f} {etirements(Pd,rest,ar)['max']:9.3f}")
