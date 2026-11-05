import sys
sys.argv = ['x', '/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad/arap']
sys.path.insert(0, '/home/claude/moteur_3_0/engine/skinning')
import numpy as np
import test_chaine_hanche as t
from articulation_chaine import chaine, deformer
# --- référence X-Bot, image 231 (hanche à 89° de la verticale)
d = np.load('ref_mixamo/skin_frames.npz', allow_pickle=True)
V = d['V']; H = d['H']; F = d['faces']; noms = list(d['noms'])
iL = {n: i for i, n in enumerate(noms)}
fr = list(d['frames']).index(231)
hip_r = H[fr][iL['LeftUpLeg']]; knee_r = H[fr][iL['LeftLeg']]
dl_r = (knee_r - hip_r) / np.linalg.norm(knee_r - hip_r); L_r = np.linalg.norm(knee_r - hip_r)
def champ(rest_v, pose_v, F_, hip, dl, L, rayon_bande=0.6):
    e = np.unique(np.sort(np.vstack([F_[:, [0, 1]], F_[:, [1, 2]], F_[:, [2, 0]]]), axis=1), axis=0)
    L0 = np.linalg.norm(rest_v[e[:, 0]] - rest_v[e[:, 1]], axis=1)
    L1 = np.linalg.norm(pose_v[e[:, 0]] - pose_v[e[:, 1]], axis=1)
    r = L1 / np.maximum(L0, 1e-9)
    mid = (rest_v[e[:, 0]] + rest_v[e[:, 1]]) / 2
    s = ((mid - hip) @ dl) / L                       # position normalisée le long de la cuisse (0 = hanche)
    sel = np.abs(s) < rayon_bande
    return s[sel], r[sel]
s_ref, r_ref = champ(V[0], V[fr], F, hip_r, dl_r, L_r)
# --- notre chaîne à 90°
th = 90
P_model_parent = t.ix["mixamorig:Hips"]; enf = [t.ix["mixamorig:LeftUpLeg"], t.ix["mixamorig:LeftLeg"], t.ix["mixamorig:LeftFoot"]]
p0 = t.h[t.ix["mixamorig:LeftUpLeg"]]; dirl = t.h[t.ix["mixamorig:LeftLeg"]] - p0
axe = np.cross(dirl / np.linalg.norm(dirl), t.Y); axe /= np.linalg.norm(axe)
W2, Ms, info = chaine(t.rest, t.dom, P_model_parent, enf, t.M_de(p0, axe, th), t.K, t.B)
P = deformer(t.rest, W2, Ms)
L_m = np.linalg.norm(t.h[t.ix["mixamorig:LeftLeg"]] - p0)
dl_m = dirl / np.linalg.norm(dirl)
s_m, r_m = champ(t.rest, P, t.faces, p0, dl_m, L_m, rayon_bande=0.6)
print("référence (89°) : n arêtes", len(r_ref), " ; modèle (90°) : n arêtes", len(r_m))
bins = np.linspace(-0.6, 0.6, 7)
print("bande s/L      réf médiane  réf p95  réf %>1,15   |  modèle médiane  modèle p95  modèle %>1,15")
for a, b in zip(bins[:-1], bins[1:]):
    mr = (s_ref >= a) & (s_ref < b); mm = (s_m >= a) & (s_m < b)
    f = lambda x, q: (np.percentile(x, q) if len(x) else np.nan)
    print(f"[{a:+.2f},{b:+.2f}) {np.median(r_ref[mr]) if mr.any() else np.nan:9.3f} {f(r_ref[mr],95):9.3f} {(r_ref[mr]>1.15).mean() if mr.any() else np.nan:9.3f}   |  {np.median(r_m[mm]) if mm.any() else np.nan:9.3f} {f(r_m[mm],95):9.3f} {(r_m[mm]>1.15).mean() if mm.any() else np.nan:9.3f}")
