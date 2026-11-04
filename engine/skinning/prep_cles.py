import sys, numpy as np
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
from correctif_arap import arap_cible
S = sys.argv[1]
d = np.load(S + "/donnees6.npz", allow_pickle=True)
rest, W, M, ar = d["rest"], d["W"], d["M"], d["aretes"]
os_n = [str(o) for o in d["os"]]
tronc = [os_n.index(n) for n in os_n if n.split(":")[-1] in ("Hips", "Spine", "Spine1", "Spine2", "Neck", "Head")]
ancre = W[:, tronc].sum(1) > 0.99
ANG = [0, 60, 75, 90, 105, 120]
CH = ["mixamorig:LeftArm", "mixamorig:LeftForeArm", "mixamorig:LeftLeg"]
out = {}
for c, nom in enumerate(CH):
    for a in (60, 90, 120):
        p = c * 6 + ANG.index(a)
        P0, Pa = arap_cible(rest, W, M[p], ar, ancre, iters=40)
        delta = Pa - P0
        # matrice linéaire de skinning A_i = somme_b W_ib R_b (partie 3x3)
        A = np.einsum("ib,bjk->ijk", W, M[p][:, :3, :3])
        dr = np.linalg.solve(A, delta[:, :, None])[:, :, 0]   # d_i = A_i^-1 delta_i (espace repos)
        out[f"{nom}_{a}"] = dr
        print("cle", nom, a, "amplitude rest", float(np.abs(dr).max()), flush=True)
np.savez(S + "/cles_repos.npz", **out)
print("CLES_OK")
