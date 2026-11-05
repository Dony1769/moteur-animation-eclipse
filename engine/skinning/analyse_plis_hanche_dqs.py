import sys
sys.argv = ['x', '/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad/arap']
sys.path.insert(0, '/home/claude/moteur_3_0/engine/skinning')
import numpy as np
import test_dqs_hanche_genou as m
from mesures_pose import normales_faces

def centres_plis(th):
    P, G, pivot = m.pose("hanche", th)
    Nr = normales_faces(m.rest, m.faces)
    Nr_loc = np.einsum("fij,fj->fi", G[m.dom], Nr)
    Np = normales_faces(P, m.faces)
    repliee = np.einsum("fi,fi->f", Nr_loc, Np) < 0
    cen = m.rest[m.faces[repliee]].mean(axis=1)
    return cen, pivot

print("centre hanche repos (x,y,z) =", np.round(m.hanche, 3))
for th in (90, 105, 120):
    cen, piv = centres_plis(th)
    if len(cen) == 0:
        print(th, "aucun pli"); continue
    rel = cen - piv
    dist = np.linalg.norm(rel, axis=1)
    ant = rel[:, 1] > 0
    print(f"\nthéta {th}: plis={len(cen)}  antérieurs(+Y)={int(ant.sum())}  distance médiane au centre={np.median(dist):.3f} m  distance max={dist.max():.3f} m")
    print("  barycentre rel. hanche (x,y,z) =", np.round(rel.mean(0), 3), " étendue z =", np.round([rel[:,2].min(), rel[:,2].max()], 3))
    print("  part à <0,15 m de la hanche :", round(float((dist < 0.15).mean()), 2), "; antérieurs à <0,15 m :", int(((dist < 0.15) & ant).sum()))
