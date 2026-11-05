import sys, json, numpy as np
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
from correctif_arap import arap_cible, _lbs
from plis_numpy import plis_masque
from lbs_numpy import etirements
S = sys.argv[1]; W = np.load(S + "W_heat.npz")["W"]; W = W / W.sum(1, keepdims=True)
d = np.load(S + "donnees7.npz", allow_pickle=True)
rest, M, ar, faces, etiq = d["rest"], d["M"], d["aretes"], d["faces"], list(d["etiquettes"])
os_n = [str(o) for o in d["os"]]
tronc = [os_n.index(n) for n in ("mixamorig:Hips","mixamorig:Spine","mixamorig:Spine1","mixamorig:Neck","mixamorig:Head")]
ancre = W[:, tronc].sum(1) > 0.99
p = etiq.index("LeftArm@120")
_, P = arap_cible(rest, W, M[p], ar, ancre, iters=40)
m = plis_masque(rest, P, W, M[p], faces)
idx = np.where(m)[0]
verts = np.unique(np.concatenate([np.array(list(faces[k])) for k in idx]))
print("faces repliées :", len(idx), " sommets concernés :", len(verts))
print("sommets : x", rest[verts,0].min().round(3), rest[verts,0].max().round(3), " y", rest[verts,1].min().round(3), rest[verts,1].max().round(3), " z", rest[verts,2].min().round(3), rest[verts,2].max().round(3))
dom = np.bincount(W[verts].argmax(1), minlength=W.shape[1])
print({os_n[i].split(":")[-1]: int(dom[i]) for i in np.argsort(-dom)[:5] if dom[i] > 0})
# les replis sont-ils à la frontière d'ancrage (tronc) ?
print("sommets près de l'ancre (dist < 0.05 au tronc) :", int(np.sum([np.min(np.linalg.norm(rest[ancre]-rest[v],axis=1))<0.05 for v in verts])))
