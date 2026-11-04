import sys, numpy as np
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
from correctif_arap import arap_cible
from plis_numpy import plis_positions
S = sys.argv[1]
d = np.load(S + "/donnees6.npz", allow_pickle=True)
rest, W, faces, ar = d["rest"], d["W"], d["faces"], d["aretes"]
e = np.load(S + "/pose_epaule.npz", allow_pickle=True)
os_n = [str(o) for o in d["os"]]
tronc = [os_n.index(n) for n in os_n if n.split(":")[-1] in ("Hips", "Spine", "Spine1", "Spine2", "Neck", "Head")]
ancre = W[:, tronc].sum(1) > 0.99
out = {}
for a in (60, 90, 120):
    M = e[f"M_{a}"]
    P0, Pa = arap_cible(rest, W, M, ar, ancre, iters=40)
    P0l, Pl = arap_cible(rest, W, M, ar, ancre, iters=40, faces=faces, alpha=0.8, debut_limite=25)
    choisi = Pl if plis_positions(rest, Pl, W, M, faces) < plis_positions(rest, Pa, W, M, faces) else Pa
    delta = choisi - P0
    A = np.einsum("ib,bjk->ijk", W, M[:, :3, :3])
    out[f"epaule_{a}"] = np.linalg.solve(A, delta[:, :, None])[:, :, 0]
np.savez(S + "/cles_epaule_repos.npz", **out)
print("PREP_EPAULE_OK")
