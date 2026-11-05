import numpy as np
from scipy.spatial.transform import Rotation as Rot
exec(open('volume_interpenetration.py').read().split('for Rs in (0.07,):')[0])
BANDE = 0.10   # m : bande de jonction autour du centre articulaire
def pose_(U, F, cc, aa, th):
    R = Rot.from_rotvec(aa*np.radians(th)).as_matrix()
    P = rest0.copy(); P[F] = rest0[F] @ R.T + (cc - R @ cc); return P
def mesurer(U, F, cc, aa, th):
    P = pose_(U, F, cc, aa, th)
    # arêtes : étirement = longueur posée / longueur de repos
    e = np.array([x for x in aretes0]); L0 = np.linalg.norm(rest0[e[:,0]]-rest0[e[:,1]], axis=1)
    L1 = np.linalg.norm(P[e[:,0]]-P[e[:,1]], axis=1)
    ratio = L1/np.maximum(L0,1e-9)
    mid = (rest0[e[:,0]]+rest0[e[:,1]])/2
    dc = np.linalg.norm(mid-cc, axis=1); hors = dc > BANDE
    # plis : normale de face (triangle fan) : produit scalaire repos/pose < 0
    fl = 0; fl_band = 0; ht = 0
    for f in faces0:
        a,b,cc3 = f[0],f[1],f[2]
        n0 = np.cross(rest0[b]-rest0[a], rest0[cc3]-rest0[a]); n1 = np.cross(P[b]-P[a], P[cc3]-P[a])
        cen = rest0[list(f)].mean(0)
        if n0 @ n1 < 0:
            if np.linalg.norm(cen-cc) > BANDE: fl += 1
            else: fl_band += 1
    return dict(th=th, etirement_hors_bande=round(float(ratio[hors].max()),3),
                etirement_dans_bande=round(float(ratio[~hors].max()),3),
                plis_hors_bande=int(fl), plis_dans_bande=int(fl_band))
# coude gauche (bras fixe, avant-bras tourne)
for th in (0, 30, 60, 90, 100, 120):
    print("COUDE", mesurer(U_mask, F_mask, c, ax, th), flush=True)
