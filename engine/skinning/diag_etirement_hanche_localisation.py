import sys
sys.argv = ['x', '/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad/arap']
sys.path.insert(0, '/home/claude/moteur_3_0/engine/skinning')
import numpy as np
import test_chaine_hanche as t
from articulation_chaine import chaine, deformer
from scipy.spatial.transform import Rotation as Rot
th = 120
parent = t.ix["mixamorig:Hips"]; enfants = [t.ix["mixamorig:LeftUpLeg"], t.ix["mixamorig:LeftLeg"], t.ix["mixamorig:LeftFoot"]]
p0 = t.h[t.ix["mixamorig:LeftUpLeg"]]; dirl = t.h[t.ix["mixamorig:LeftLeg"]] - p0
axe = np.cross(dirl/np.linalg.norm(dirl), t.Y); axe /= np.linalg.norm(axe)
W2, Ms, info = chaine(t.rest, t.dom, parent, enfants, t.M_de(p0, axe, th), t.K, t.B)
P = deformer(t.rest, W2, Ms)
piv = info["pivot"]
e = t.aretes
L0 = np.linalg.norm(t.rest[e[:,0]]-t.rest[e[:,1]],axis=1); L1 = np.linalg.norm(P[e[:,0]]-P[e[:,1]],axis=1)
r = L1/np.maximum(L0,1e-9)
mid = (t.rest[e[:,0]]+t.rest[e[:,1]])/2
band = np.linalg.norm(mid-piv,axis=1) < 0.10
rel = mid - piv
ant = rel[:,1] > 0
dz = rel[:,2]
sel = band & (r > np.percentile(r[band], 95))
print("arêtes dans la bande :", int(band.sum()), "; au-dessus du p95 :", int(sel.sum()))
print("  p95 dans la bande =", round(float(np.percentile(r[band],95)),3), " ; p99 =", round(float(np.percentile(r[band],99)),3))
print("  parmi les plus étirées : antérieures =", int((sel&ant).sum()), " postérieures =", int((sel&~ant).sum()))
print("  z médian (rel. hanche) des plus étirées :", round(float(np.median(dz[sel])),3), " ; des autres dans bande :", round(float(np.median(dz[band&~sel])),3))
print("  y médian des plus étirées :", round(float(np.median(rel[sel,1])),3))
