"""Lancer depuis scratchpad/arap (donnees7.npz, os_repos.json). Erreur 90."""
import sys, json, numpy as np
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
from penetration import penetration_nouvelle
from scipy.spatial.transform import Rotation as Rot
d = np.load("donnees7.npz", allow_pickle=True)
rest0, faces0 = d["rest"], d["faces"]
os_ = [str(x) for x in d["os"]]; dom0 = d["W"].argmax(1)
J = json.load(open("os_repos.json"))["os"]
ix = lambda n: os_.index("mixamorig:" + n)
genou = np.array(J["mixamorig:LeftLeg"]["tete"]); cheville = np.array(J["mixamorig:LeftFoot"]["tete"])
orteil = np.array(J["mixamorig:LeftFoot"]["queue"])
X = np.array([1.0, 0, 0])
toe = (orteil - cheville); toe /= np.linalg.norm(toe)
# critère anatomique : en flexion, le talon (cheville) doit se déplacer à l'opposé des orteils
R_test = Rot.from_rotvec(X * np.radians(30)).as_matrix()
dep = (R_test @ (cheville - genou)) - (cheville - genou)
sens = 1 if np.dot(dep, toe) < 0 else -1
print("sens anatomique choisi", sens, "déplacement talon·orteil", round(float(np.dot(dep, toe)),4))
enf = np.isin(dom0, [ix("LeftLeg"), ix("LeftFoot")])
def mesure(R_J, ax, angles):
    dist0 = np.linalg.norm(rest0 - genou, axis=1)
    garde = dist0 >= R_J if R_J > 0 else np.ones(len(rest0), bool)
    im = -np.ones(len(rest0), int); im[garde] = np.arange(garde.sum())
    faces = [[im[k] for k in f] for f in faces0 if all(garde[k] for k in f)]
    rest = rest0[garde]; dom = dom0[garde]; mob = enf[garde]
    out = []
    for th in angles:
        R = Rot.from_rotvec(ax * np.radians(th)).as_matrix()
        P = rest.copy(); P[mob] = rest[mob] @ R.T + (genou - R @ genou)
        n, pm, _ = penetration_nouvelle(rest, P, faces, mob, centre=None, dom=dom)
        out.append(f"{th}:{n}")
    print(f"R={R_J:.3f} " + "  ".join(out), flush=True)
for R_J in (0.0, 0.055):
    mesure(R_J, sens * X, (30, 60, 90, 120, 140))
