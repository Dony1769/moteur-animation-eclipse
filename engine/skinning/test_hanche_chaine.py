"""Hanche (sphère) par chaîne de nœuds : tests de diagnostic (numpy).

Résultat (phase 4) : aucune variante ne descend sous ~15 plis à 120°.
Variantes testées : bande plane sur l'axe du fémur, rigidité du fémur, coquilles sphériques
autour du centre de la hanche (r0/r1), bassin qui suit une fraction p de la rotation.
Les plis se situent sur la frontière tronc (fixe) / cuisse (tournante) : diagnostic à compléter
(correctifs de pose ARAP ou modification du maillage). Voir erreur 81.
"""
import numpy as np, sys, json
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
from articulation_chaine import chaine, deformer
from criteres_articulation import evaluer
from scipy.spatial.transform import Rotation as Rot
SCR = "/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad/arap/"
J = json.load(open(SCR + "os_repos.json"))["os"]
hip = np.array(J["mixamorig:LeftUpLeg"]["tete"])
D = np.load(SCR + "donnees7.npz", allow_pickle=True)
rest = D["rest"]; W0 = D["W"]; os_ = [str(x) for x in D["os"]]; faces = D["faces"]
dom = W0.argmax(1); iH = os_.index("mixamorig:Hips"); iU = os_.index("mixamorig:LeftUpLeg")
rng = np.random.default_rng(0)
for th in (90, 120):
    R = Rot.from_rotvec(np.array([1.0, 0, 0]) * np.radians(th)).as_matrix()
    M = np.eye(4); M[:3, :3] = R; M[:3, 3] = hip - R @ hip
    Wc, Ms, info = chaine(rest, dom, iH, [iU], M, 8, 0.04, enfant_rigide=False, bissectrice=True)
    pts = deformer(rest, Wc, Ms)
    print(f"hanche θ={th}:", evaluer(rest, faces, dom == iH, dom == iU, Wc, Ms, pts, th, info, 0.04, rng))
