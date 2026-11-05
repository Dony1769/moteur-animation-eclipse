import sys
sys.argv = ['x', '/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad/arap']
sys.path.insert(0, '/home/claude/moteur_3_0/engine/skinning')
import numpy as np
import test_chaine_hanche as t
from articulation_chaine import chaine, deformer
p0 = t.h[t.ix["mixamorig:LeftUpLeg"]]; dirl = t.h[t.ix["mixamorig:LeftLeg"]] - p0
dl = dirl/np.linalg.norm(dirl); axe = np.cross(dl, t.Y); axe /= np.linalg.norm(axe)
parent = t.ix["mixamorig:Hips"]; enf = [t.ix["mixamorig:LeftUpLeg"], t.ix["mixamorig:LeftLeg"], t.ix["mixamorig:LeftFoot"]]
for th in (60, 90, 120):
    W2, Ms, info = chaine(t.rest, t.dom, parent, enf, t.M_de(p0, axe, th), t.K, t.B)
    P = deformer(t.rest, W2, Ms)
    e = t.aretes
    L0 = np.linalg.norm(t.rest[e[:,0]]-t.rest[e[:,1]],axis=1); L1 = np.linalg.norm(P[e[:,0]]-P[e[:,1]],axis=1)
    tau = (L0 - L1)/np.maximum(L0,1e-9)           # >0 = raccourci (compression), <0 = allongement
    mid = (t.rest[e[:,0]]+t.rest[e[:,1]])/2
    band = np.linalg.norm(mid-p0,axis=1) < 0.15
    ant = (mid - p0)[:,1] > 0
    for nom, m in (("antérieur (fléchisseur)", band&ant), ("postérieur (extenseur)", band&~ant)):
        x = tau[m]
        if len(x)==0: continue
        print(f"θ={th} {nom}: n={len(x)}  compression moyenne={np.mean(np.maximum(x,0)):.3f}  part en compression={np.mean(x>0):.2f}  part en traction={np.mean(x<0):.2f}  max traction={-x.min():.3f}", flush=True)
