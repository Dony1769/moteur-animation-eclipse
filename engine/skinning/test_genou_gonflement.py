"""Lancer depuis scratchpad/arap. Erreur 91 : gonflement sans penetration, amplitude a limiter."""
import sys, numpy as np
exec(open('genou_calibre.py').read().split('for R_J in (0.0, 0.055):')[0])
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as Rot
def face_normales(P, fs):
    C=[];N=[]
    for f in fs:
        pts=P[list(f)]; C.append(pts.mean(0)); nf=np.cross(pts[1]-pts[0],pts[2]-pts[0]); N.append(nf/max(np.linalg.norm(nf),1e-12))
    return np.array(C), np.array(N)
def gonfle(th, marge=0.006, passes=3):
    R = Rot.from_rotvec(-X*np.radians(th)).as_matrix()
    P = rest0.copy(); P[enf] = rest0[enf] @ R.T + (genou - R @ genou)
    body = ~enf
    cand = [f for f in faces0 if all(body[k] for k in f)]
    for _ in range(passes):
        C, N = face_normales(P, cand)
        tree = cKDTree(C)
        mob = np.where(enf)[0]
        dd, j = tree.query(P[mob])
        prof = np.einsum('ij,ij->i', P[mob] - C[j], N[j])
        pen = prof < -0.0
        # pousser les sommets pénétrants hors de la face la plus proche, avec marge
        idx = mob[pen]
        P[idx] = P[idx] - (prof[pen][:,None] - marge) * N[j[pen]]
    return P
for th in (30, 60, 90, 120):
    P = gonfle(th)
    dep = np.linalg.norm(P[enf]-(rest0[enf]@Rot.from_rotvec(-X*np.radians(th)).as_matrix().T + 0), axis=1)
    n, pm, _ = penetration_nouvelle(rest0, P, faces0, enf, centre=None, dom=dom0)
    print(f"gonflement {th}: pénétrations nouvelles {n}, profondeur min {pm*1000:.1f} mm", flush=True)

print("--- amplitude et localisation du gonflement ---")
for th in (30, 60, 90, 120):
    P = gonfle(th)
    base = rest0 @ Rot.from_rotvec(-X*np.radians(th)).as_matrix().T + (genou - Rot.from_rotvec(-X*np.radians(th)).as_matrix() @ genou)
    base_full = rest0.copy(); base_full[enf] = base[enf]
    dpush = np.linalg.norm(P - base_full, axis=1)
    moved = dpush > 1e-6
    dk = np.linalg.norm(rest0[moved] - genou, axis=1)
    print(f"{th}: sommets gonflés {int(moved.sum())}, déplacement max {dpush.max()*1000:.1f} mm, médian {np.median(dpush[moved])*1000 if moved.any() else 0:.1f} mm, distance au genou (repos) max {dk.max() if moved.any() else 0:.3f} m")
