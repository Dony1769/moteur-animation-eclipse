import sys, numpy as np
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
from plis_numpy import plis_positions
from lbs_numpy import etirements
S = sys.argv[1]
d = np.load(S + "/donnees6.npz", allow_pickle=True)
rest, W, M, ar, faces = d["rest"], d["W"], d["M"], d["aretes"], d["faces"]
bl = np.load(S + "/pose_cles_blender.npz")
ANG = [0, 60, 75, 90, 105, 120]
CH = ["mixamorig:LeftArm", "mixamorig:LeftForeArm", "mixamorig:LeftLeg"]
for c, nom in enumerate(CH):
    for T in ANG:
        p = c * 6 + ANG.index(T)
        P = bl[f"{nom}_{T}"]
        s = etirements(P, rest, ar)
        f = plis_positions(rest, P, W, M[p], faces)
        tag = "TEST" if T in (75, 105) else "entr." if T else "temoin"
        print(f"{nom[10:]:>10} {T:3d}deg {tag:6}  plis={f:3d}  etir_max={s['max']:.2f} min={s['min']:.2f}")
