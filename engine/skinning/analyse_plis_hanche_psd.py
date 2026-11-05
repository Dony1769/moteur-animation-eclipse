import sys
sys.argv = ['x', '/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad/arap']
sys.path.insert(0, '/home/claude/moteur_3_0/engine/skinning')
import numpy as np
import psd_hanche_genou as p
from mesures_pose import normales_faces
modele = p.construit("hanche", (0, 30, 60, 90, 120))
for th in (105, 120):
    P = p.corrige(modele, th)
    _, G, _, piv, _ = p.pose_dqs("hanche", th)
    Nr_loc = np.einsum("fij,fj->fi", G[p.dom], normales_faces(p.rest, p.faces))
    rep = np.einsum("fi,fi->f", Nr_loc, normales_faces(P, p.faces)) < 0
    cen = p.rest[p.faces[rep]].mean(axis=1); rel = cen - piv
    ant = rel[:, 1] > 0; dist = np.linalg.norm(rel, axis=1)
    print(f"PSD {th}: plis={len(cen)} antérieurs={int(ant.sum())} postérieurs/latéraux={int((~ant).sum())} "
          f"dist>0,15m={int((dist>=0.15).sum())} ; dz médian={np.round(np.median(rel[:,2]),3)} dy médian={np.round(np.median(rel[:,1]),3)}")
