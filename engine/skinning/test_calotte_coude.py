"""Lancer depuis le dossier contenant donnees7.npz et os_repos.json (scratchpad/arap). Erreur 88."""
"""Coude : segments rigides + calotte (sphère de jonction) coupée au plan bissecteur.
Groupe mobile = sommets qui bougent dans la pose ; groupe fixe = les autres. Pénétration nouvelle
mesurée du mobile dans le fixe (relative au repos)."""
import sys, json, numpy as np
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
from penetration import penetration_nouvelle
from scipy.spatial.transform import Rotation as Rot
d = np.load("donnees7.npz", allow_pickle=True)
rest, faces = d["rest"], d["faces"]
os_ = [str(x) for x in d["os"]]; dom = d["W"].argmax(1)
J = json.load(open("os_repos.json"))["os"]
ix = lambda n: os_.index("mixamorig:" + n)
c = np.array(J["mixamorig:LeftForeArm"]["tete"])
a = np.array(J["mixamorig:LeftArm"]["tete"]) - c; a /= np.linalg.norm(a)
f0 = np.array(J["mixamorig:LeftHand"]["tete"]) - c; f0 /= np.linalg.norm(f0)
X = np.array([1.0, 0, 0])
avant = np.isin(dom, [ix("LeftForeArm"), ix("LeftHand")])
R_CALOTTE = 0.041   # rayon de la sphère de jonction du coude (marqueur X-Bot, 4,1 cm)
dist = np.linalg.norm(rest - c, axis=1)
def pose(th, mode):
    R = Rot.from_rotvec(X * np.radians(th)).as_matrix()
    M = np.eye(4); M[:3, :3] = R; M[:3, 3] = c - R @ c
    Q = rest @ R.T + M[:3, 3]
    f = R @ f0
    n = a - f; n /= np.linalg.norm(n)
    cote = (rest - c) @ n           # >0 : côté bras supérieur
    tourne = avant & (dist >= R_CALOTTE)            # hors sphère : rigide par os
    if mode == "calotte":
        dans = dist < R_CALOTTE
        tourne |= dans & avant & (cote <= 0)          # sphère : avant-bras du côté opposé au bras
        tourne |= dans & ~avant & (cote <= 0) & False  # réservé : sommets du bras supérieur (non utilisé ici)
    P = rest.copy(); P[tourne] = Q[tourne]
    return P, tourne
for mode in ("rigide", "calotte"):
    out = []
    for th in (30, 60, 90, 105, 120):
        P, mob = pose(th, mode)
        nn, pm, _ = penetration_nouvelle(rest, P, faces, mob, centre=None, dom=dom)
        out.append(f"{th}:{nn}")
    print(f"{mode:8s} pénétrations nouvelles (groupe mobile contre fixe) " + "  ".join(out), flush=True)

# localisation des pénétrations de la variante rigide
for th in (60, 90, 120):
    P, mob = pose(th, "rigide")
    nn, pm, masque = penetration_nouvelle(rest, P, faces, mob, centre=None, dom=dom)
    idx = np.where(masque)[0]
    if len(idx):
        dc = np.linalg.norm(rest[idx] - c, axis=1)
        print(f"loc {th}: n={len(idx)} distance au coude min {dc.min():.3f} max {dc.max():.3f} médiane {np.median(dc):.3f}")
