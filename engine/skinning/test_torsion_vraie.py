import sys, json, numpy as np
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
from torsion_helper import swing_twist
from plis_numpy import plis_positions
from lbs_numpy import etirements
from correctif_arap import _lbs
from scipy.spatial.transform import Rotation
S = sys.argv[1]
d = np.load(S + "donnees7.npz", allow_pickle=True)
rest, M, ar, faces, ang, etiq = d["rest"], d["M"], d["aretes"], d["faces"], list(d["angles"]), list(d["etiquettes"])
os_n = [str(o) for o in d["os"]]
W0 = np.load(S + "W_seq_final.npy")
ob = json.load(open(S + "os_repos.json"))["os"]
ih, ia = os_n.index("mixamorig:LeftArmHelper"), os_n.index("mixamorig:LeftArm")
tete = np.array(ob["mixamorig:LeftArmHelper"]["tete"]); queue = np.array(ob["mixamorig:LeftArmHelper"]["queue"])
a = (queue - tete) / np.linalg.norm(queue - tete)
print("axe os vrai :", np.round(a, 3), " pivot :", np.round(tete, 3))
def remplace(Mh):
    _, ang_tw = swing_twist(Mh[:3, :3], a)
    R = Rotation.from_rotvec(a * ang_tw).as_matrix()
    out = np.eye(4); out[:3, :3] = R; out[:3, 3] = tete - R @ tete
    return out
M2 = M.copy()
for p in range(len(etiq)): M2[p, ih] = remplace(M[p, ih])
print(f"{'pose':>17} | {'plis avant':>10} {'après':>6} | {'étir max':>9} {'après':>7}")
for p, e in enumerate(etiq):
    if not str(e).startswith("LeftArm@"): continue
    P0 = _lbs(rest, W0, M[p]); P1 = _lbs(rest, W0, M2[p])
    print(f"{str(e):>17} | {plis_positions(rest,P0,W0,M[p],faces):10d} {plis_positions(rest,P1,W0,M2[p],faces):6d} | {etirements(P0,rest,ar)['max']:9.3f} {etirements(P1,rest,ar)['max']:7.3f}")
