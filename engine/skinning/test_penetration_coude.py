"""Lancer depuis le dossier contenant donnees7.npz et os_repos.json (scratchpad/arap). Erreur 86."""
import sys, json, numpy as np
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
from articulation_chaine import chaine, deformer
from penetration import penetration_nouvelle
from scipy.spatial.transform import Rotation as Rot
d = np.load("donnees7.npz", allow_pickle=True)
rest, faces = d["rest"], d["faces"]
os_ = [str(x) for x in d["os"]]; dom = d["W"].argmax(1)
J = json.load(open("os_repos.json"))["os"]
ix = lambda n: os_.index("mixamorig:" + n)
coude = np.array(J["mixamorig:LeftForeArm"]["tete"])
def synth(c, th):
    R = Rot.from_rotvec(np.array([1.0, 0, 0]) * np.radians(th)).as_matrix()
    M = np.eye(4); M[:3, :3] = R; M[:3, 3] = c - R @ c; return M
kids = [ix("LeftForeArm"), ix("LeftHand")]
mob = np.isin(dom, kids)
for th in (0, 60, 90, 105, 120):
    if th == 0:
        P = rest.copy()
    else:
        W, Ms, _ = chaine(rest, dom, ix("LeftArm"), kids, synth(coude, th), 8, 0.10, bissectrice=True)
        P = deformer(rest, W, Ms)
    n, pm, m = penetration_nouvelle(rest, P, faces, mob, centre=coude, dom=dom)
    print(f"coude {th}: pénétrations nouvelles {n}, profondeur min {pm*1000:.1f} mm", flush=True)
