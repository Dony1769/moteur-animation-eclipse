"""Mesure la part de flexion (swing) et de torsion de l'auxiliaire LeftArmHelper, par pose, et teste
le remplacement par la torsion seule. Usage : python3 diagnostic_torsion.py DOSSIER/"""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from torsion_helper import swing_twist, axe_os, pivot_fixe, aux_torsion_seule
from scipy.spatial.transform import Rotation

S = sys.argv[1].rstrip("/") + "/"
d = np.load(S + "donnees7.npz", allow_pickle=True)
rest, M, ang, etiq = d["rest"], d["M"], list(d["angles"]), list(d["etiquettes"])
os_n = [str(o).split(":")[-1] for o in d["os"]]
W0 = np.load(S + "W_seq_final.npy")
ih, ia = os_n.index("LeftArmHelper"), os_n.index("LeftArm")
poids_bras = W0[:, [ia, ih]].sum(1)
a = axe_os(rest, poids_bras)
print("axe du bras (ACP) :", np.round(a, 3))
print("pivot épaule (point fixe LeftArm, 120°) :", np.round(pivot_fixe(M[ang.index(120), ia]), 3))
for p, e in enumerate(etiq):
    if not str(e).startswith("LeftArm@"): continue
    Mh = M[p, ih]
    sw, tw = swing_twist(Mh[:3, :3], a)
    ang_sw = np.degrees(Rotation.from_matrix(sw).magnitude())
    print(f"{str(e):>16}  torsion {np.degrees(tw):7.2f}°  flexion (swing) {ang_sw:7.2f}°")
