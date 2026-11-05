import sys
sys.argv = ['x', '/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad/arap']
sys.path.insert(0, '/home/claude/moteur_3_0/engine/skinning')
import numpy as np
import psd_hanche_genou as p
from mesures_pose import normales_faces
def smooth(t):
    t = np.clip(t, 0, 1); return t*t*(3-2*t)
# pondération lisse : 0 à Y = hanche − 0,03 m, 1 à Y = hanche + 0,07 m (transition de 10 cm, continue)
w_lisse = smooth(((p.rest - p.hanche)[:, 1] + 0.03) / 0.10)
modele = p.construit("hanche", (0, 30, 60, 90, 120))
modele["poids"] = modele["poids"] * w_lisse
for th in (60, 90, 105, 120):
    P = p.corrige(modele, th)
    m = p.mesure(P, "hanche", th)
    _, G, _, piv, _ = p.pose_dqs("hanche", th)
    Nr_loc = np.einsum("fij,fj->fi", G[p.dom], normales_faces(p.rest, p.faces))
    rep = np.einsum("fi,fi->f", Nr_loc, normales_faces(P, p.faces)) < 0
    cen = p.rest[p.faces[rep]].mean(axis=1); rel = cen - piv
    print(f"lisse {th}: p99 hors={m['etirement_hors_p99']} dans={m['etirement_dans_p99']} plis={m['plis_total']} posterieurs={int((rel[:,1]<=0).sum())}", flush=True)
