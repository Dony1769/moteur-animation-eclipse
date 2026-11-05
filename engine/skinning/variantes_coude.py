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
VAR = {
  "chaine B=0.10 (actuelle)": dict(B=0.10, bissectrice=True, enfant_rigide=False),
  "segments durs B=1e-4 enfant rigide": dict(B=1e-4, bissectrice=True, enfant_rigide=True),
  "chaine B=0.04": dict(B=0.04, bissectrice=True, enfant_rigide=False),
}
for nom, kw in VAR.items():
    out = []
    for th in (60, 90, 105, 120):
        W, Ms, _ = chaine(rest, dom, ix("LeftArm"), kids, synth(coude, th), 8, kw["B"], bissectrice=kw["bissectrice"], enfant_rigide=kw["enfant_rigide"])
        P = deformer(rest, W, Ms)
        n, pm, _ = penetration_nouvelle(rest, P, faces, mob, centre=coude, dom=dom)
        out.append(f"{th}:{n}")
    print(f"{nom:38s} " + "  ".join(out), flush=True)
