"""Test : flexion du genou par chaîne de nœuds de jonction coaxiaux (répartition de l'angle).

Chaque nœud j tourne de f_j * r autour de l'axe du genou (f_j = j/K). Un sommet à la hauteur s du genou
reçoit une fraction f(s) de l'angle (0 au-dessus de la bande, 1 en dessous). Le repos reste l'identité.
Comparaison : LBS actuelle (2 os, mélange sur les poids heat) contre chaîne de K nœuds.
"""
import sys, numpy as np
from scipy.spatial.transform import Rotation as Rot
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
from plis_numpy import plis
from lbs_numpy import etirements
S = "/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad/arap/"
d = np.load(S + "donnees7.npz", allow_pickle=True)
rest, W0, faces, aretes = d["rest"], d["W"], d["faces"], d["aretes"]
os_ = [str(x) for x in d["os"]]
etq = [str(x) for x in d["etiquettes"]]
iUp, iLeg, iFoot = os_.index("mixamorig:LeftUpLeg"), os_.index("mixamorig:LeftLeg"), os_.index("mixamorig:LeftFoot")
dom = W0.argmax(1)
jambe = np.isin(dom, [iUp, iLeg, iFoot])
print("sommets jambe gauche :", jambe.sum())

def pose_angle(theta):
    return d["M"][etq.index(f"LeftLeg@{theta}")][iLeg]  # 4x4 du genou à l'angle theta

def chaine(theta, K, B):
    Ml = pose_angle(theta)
    R = Ml[:3, :3]; t = Ml[:3, 3]
    c = np.linalg.lstsq(np.eye(3) - R, t, rcond=None)[0]  # un point de l axe de rotation
    rv = Rot.from_matrix(R).as_rotvec()    # rotation totale = rv
    s = rest[:, 2] - c[2]                  # hauteur relative au genou (axe vertical)
    f = np.clip((B - s) / (2 * B), 0, 1)   # 0 au-dessus de la bande, 1 en dessous
    W = np.zeros((len(rest), K + 2)); W[:, 0] = 1.0  # colonne 0 : identité (hors jambe)
    Ms = [np.eye(4)]
    for j in range(K + 1):
        Rj = Rot.from_rotvec(rv * j / K).as_matrix()
        M = np.eye(4); M[:3, :3] = Rj; M[:3, 3] = c - Rj @ c
        Ms.append(M)
    Ms = np.array(Ms)  # (K+2,4,4) : identité + K+1 nœuds
    Wl = np.zeros((len(rest), K + 2))
    x = f[jambe] * K                           # position dans la chaîne
    j0 = np.clip(np.floor(x).astype(int), 0, K - 1)
    a = np.clip(x - j0, 0, 1)
    idx = np.where(jambe)[0]
    Wl[idx, 1 + j0] = 1 - a
    Wl[idx, 2 + j0] = a
    W = np.where(jambe[:, None], Wl, W)
    return W, Ms

def deformer(W, M):
    R4 = np.concatenate([rest, np.ones((len(rest), 1))], 1)
    return np.einsum("ib,bjk,ik->ij", W, M, R4)[:, :3]

def mesurer(W, M):
    pts = deformer(W, M)
    e = etirements(pts, rest, aretes)
    dom_ = W.argmax(1)
    return plis(rest, W, M, faces) if False else _plis(pts, dom_, M), e

def _plis(pts, dom_, M):
    from plis_numpy import plis_positions
    return plis_positions(rest, pts, np.eye(len(M))[dom_], M, faces)

print("théta | LBS actuelle : plis, étirement max | chaîne K=4,8 (B=0.05)")
for th in (60, 90, 105, 120):
    Mall = d["M"][etq.index(f"LeftLeg@{th}")]
    Wb = W0
    base = mesurer(Wb, Mall)
    row = [f"{th:>4} | {base[0]:>3} plis, {base[1]['max']:.2f}"]
    for K in (4, 8):
        W, Ms = chaine(th, K, 0.05)
        pl, e = mesurer(W, Ms)
        row.append(f"K={K}: {pl} plis, {e['max']:.3f}")
    print(" | ".join(row))
