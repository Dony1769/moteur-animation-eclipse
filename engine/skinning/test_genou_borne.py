"""Lancer depuis scratchpad/arap. Erreur 92 : plis et etirement mesures ; le genou par segments durs se dechire."""
import sys, numpy as np
sys.path.insert(0,"/home/claude/moteur_3_0/engine/skinning")
from mesures_pose import plis_retournes, etirement_max, deplacement
exec(open('genou_gonflement.py').read().split('for th in (30, 60, 90, 120):')[0])
aretes = d["aretes"]
def rigide(th):
    R = Rot.from_rotvec(-X*np.radians(th)).as_matrix()
    P = rest0.copy(); P[enf] = rest0[enf] @ R.T + (genou - R @ genou)
    return P
def gonfle_borne(th, cap, marge=0.006, passes=3):
    P0 = rigide(th); P = P0.copy()
    body = ~enf
    cand = [f for f in faces0 if all(body[k] for k in f)]
    for _ in range(passes):
        C, N = face_normales(P, cand)
        from scipy.spatial import cKDTree
        mob = np.where(enf)[0]
        dd, j = cKDTree(C).query(P[mob])
        prof = np.einsum('ij,ij->i', P[mob] - C[j], N[j])
        pen = prof < 0
        idx = mob[pen]
        push = (prof[pen][:,None] - marge) * N[j[pen]]
        P[idx] = P[idx] - push
    # borne : déplacement par rapport à la pose rigide, plafonné à cap
    dv = P - P0
    nrm = np.linalg.norm(dv, axis=1, keepdims=True)
    fac = np.minimum(1.0, cap / np.maximum(nrm, 1e-12))
    return P0 + dv * fac
for cap in (None, 0.015, 0.010):
    line=[]
    for th in (30, 60, 90, 120):
        P = rigide(th) if cap is None and False else (gonfle_borne(th, cap) if cap else rigide(th))
        n,pm,_ = penetration_nouvelle(rest0, P, faces0, enf, centre=None, dom=dom0)
        pl = plis_retournes(rest0, P, faces0); et = etirement_max(rest0, P, aretes)
        dmax, dmed = deplacement(rigide(th), P)
        line.append(f"{th}: pén {n}, plis {pl}, étir {et:.2f}, dépl.corr max {dmax*1000:.0f}mm")
    print(f"cap={cap}: " + " | ".join(line), flush=True)
