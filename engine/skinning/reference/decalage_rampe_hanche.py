import sys
sys.argv = ['x', '/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad/arap']
sys.path.insert(0, '/home/claude/moteur_3_0/engine/skinning')
import numpy as np
import test_chaine_hanche as t
from articulation_chaine import chaine, deformer
from scipy.spatial.transform import Rotation as Rot
p0 = t.h[t.ix["mixamorig:LeftUpLeg"]]; dirl = t.h[t.ix["mixamorig:LeftLeg"]] - p0
dl = dirl / np.linalg.norm(dirl)
axe = np.cross(dl, t.Y); axe /= np.linalg.norm(axe)
parent = t.ix["mixamorig:Hips"]; enf = [t.ix["mixamorig:LeftUpLeg"], t.ix["mixamorig:LeftLeg"], t.ix["mixamorig:LeftFoot"]]
def etat(th, shift):
    s = (t.rest - p0) @ dl
    f = np.clip((t.B + (s - shift)) / (2 * t.B), 0, 1)     # f=1 côté enfant (genou, s>0), f=0 côté bassin ; décalage shift
    W2, Ms, info = chaine(t.rest, t.dom, parent, enf, t.M_de(p0, axe, th), t.K, t.B, f_custom=f)
    P = deformer(t.rest, W2, Ms)
    e = t.aretes
    L0 = np.linalg.norm(t.rest[e[:, 0]] - t.rest[e[:, 1]], axis=1); L1 = np.linalg.norm(P[e[:, 0]] - P[e[:, 1]], axis=1)
    r = L1 / np.maximum(L0, 1e-9)
    mid = (t.rest[e[:, 0]] + t.rest[e[:, 1]]) / 2
    band = np.linalg.norm(mid - p0, axis=1) < 0.10
    rb = r[band]
    return dict(shift=shift, th=th, n=int(band.sum()), mediane=round(float(np.median(rb)), 3),
                p95=round(float(np.percentile(rb, 95)), 3), frac_sup_1_15=round(float((rb > 1.15).mean()), 3))
for shift in (0.0, -0.05, -0.10):
    for th in (90, 120):
        print(etat(th, shift), flush=True)
