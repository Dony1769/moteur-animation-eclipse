"""Lancer depuis scratchpad/arap (donnees7.npz, os_repos.json). Erreur 89."""
import sys, json, numpy as np
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
from penetration import penetration_nouvelle
from scipy.spatial.transform import Rotation as Rot
d = np.load("donnees7.npz", allow_pickle=True)
rest0, faces0 = d["rest"], d["faces"]
os_ = [str(x) for x in d["os"]]; dom0 = d["W"].argmax(1)
J = json.load(open("os_repos.json"))["os"]
ix = lambda n: os_.index("mixamorig:" + n)
c = np.array(J["mixamorig:LeftForeArm"]["tete"])
h = np.cross(np.array(J["mixamorig:LeftArm"]["tete"]) - c, np.array(J["mixamorig:LeftHand"]["tete"]) - c); h /= np.linalg.norm(h)
ax = -h
avant0 = np.isin(dom0, [ix("LeftForeArm"), ix("LeftHand")])
dist0 = np.linalg.norm(rest0 - c, axis=1)
def mesure(R_J, angles):
    garde = dist0 >= R_J if R_J > 0 else np.ones(len(rest0), bool)
    im = -np.ones(len(rest0), int); im[garde] = np.arange(garde.sum())
    faces = [[im[k] for k in f] for f in faces0 if all(garde[k] for k in f)]
    rest = rest0[garde]; dom = dom0[garde]; mob = avant0[garde]
    out=[]
    for th in angles:
        R = Rot.from_rotvec(ax * np.radians(th)).as_matrix()
        P = rest.copy(); P[mob] = rest[mob] @ R.T + (c - R @ c)
        n, pm, _ = penetration_nouvelle(rest, P, faces, mob, centre=None, dom=dom)
        out.append(f"{th}:{n}")
    print(f"R_sphere={R_J:.3f}  " + "  ".join(out), flush=True)
mesure(0.0, (30,60,90,105,120,145))
mesure(0.04, (30,60,90,105,120,145))
mesure(0.06, (30,60,90,105,120,145))
mesure(0.08, (30,60,90,105,120,145))
