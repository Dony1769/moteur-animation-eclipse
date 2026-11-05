"""Coude (phase 4, erreur 96) : poussee bornee des sommets de l avant-bras qui penetrent le bras, lissee ; mesure sur sommets d origine (metrique invalide au joint, voir erreur 96).
Dependance : scratchpad/arap (coude_calotte_cousue.py, volume_interpenetration.py) et engine/skinning/mesures_pose.py ; rtree requis."""
import sys, numpy as np, trimesh
from collections import defaultdict
exec(open('volume_interpenetration.py').read().split('for Rs in (0.07,):')[0])
sys.path.insert(0, '/home/claude/moteur_3_0/engine/skinning')
from mesures_pose import plis_retournes, etirement_max
RS = 0.07
def pose(th):
    R = Rot.from_rotvec(ax*np.radians(th)).as_matrix()
    P = rest0.copy(); P[F_mask] = rest0[F_mask] @ R.T + (c - R @ c)
    return P
# voisinage du maillage de l'avant-bras (pour lisser le déplacement)
voisins = defaultdict(set)
for f in faces0:
    for a in f:
        if F_mask[a]:
            for b in f:
                if F_mask[b] and a != b: voisins[a].add(b)
ids_F = np.where(F_mask)[0]
def lisser(D, it=30, alpha=0.5):
    for _ in range(it):
        Dn = D.copy()
        for a in ids_F:
            if voisins[a]:
                Dn[a] = (1-alpha)*D[a] + alpha*np.mean([D[b] for b in voisins[a]], axis=0)
        D = Dn
    return D
def corriger(th):
    P = pose(th)
    bU = piece(U_mask, P)
    pts = P[ids_F]
    dedans = bU.contains(pts)
    hors = np.linalg.norm(pts - c, axis=1) > RS
    cible = dedans & hors
    D = np.zeros_like(P)
    if cible.any():
        cp, dist, tri = trimesh.proximity.closest_point(bU, pts[cible])
        n = bU.face_normals[tri]
        dep = (cp + 0.001*n) - pts[cible]
        D[ids_F[cible]] = dep
    D = lisser(D)
    P2 = P + D
    # vérifications après correction
    bU2 = piece(U_mask, P)  # bras inchangé
    pts2 = P2[ids_F]
    encore = bU2.contains(pts2) & (np.linalg.norm(pts2 - c, axis=1) > RS)
    deplac = np.linalg.norm(D[ids_F], axis=1)
    pl = plis_retournes(rest0, P2, faces0)
    et = etirement_max(rest0, P2, aretes0)
    return dict(th=th, cible=int(cible.sum()), encore=int(encore.sum()),
                depl_max_mm=round(float(deplac.max()*1000),1), depl_moy_mm=round(float(deplac[cible].mean()*1000),1) if cible.any() else 0,
                plis=int(pl), etirement=round(float(et),3))
for th in (0, 30, 60, 90, 120, 145):
    print(corriger(th), flush=True)
