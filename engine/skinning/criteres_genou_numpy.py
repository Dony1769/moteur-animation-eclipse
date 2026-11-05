import sys, numpy as np
from scipy.spatial import ConvexHull
exec(open("/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad/articulations/chaine_genou.py").read().split('print("théta')[0])
rng = np.random.default_rng(0)
cz = None
def criteres(W, Ms, th):
    pts = deformer(W, Ms)
    dom_ = W.argmax(1)
    out = {}
    # 1. segments rigides : distances entre paires de sommets d'un même segment
    for nom, sel in (("cuisse", jambe & (rest[:,2] > rest[:,2][jambe].max()-0.0)), ):
        pass
    for nom, mask in (("cuisse", jambe & (rest[:,2] > cz + 0.20)), ("jambe", jambe & (rest[:,2] < cz - 0.20))):
        idx = np.where(mask)[0]
        a = rng.choice(idx, 4000); b = rng.choice(idx, 4000)
        d0 = np.linalg.norm(rest[a]-rest[b],axis=1); d1 = np.linalg.norm(pts[a]-pts[b],axis=1)
        out[f"rigidite_{nom}_ecart_max_mm"] = float(np.abs(d1-d0).max()*1000)
    # 4. section : aire de l'enveloppe convexe (plan xy) des sommets d'une tranche de repos
    for lab, z in (("section_genou", cz), ("section_sous_genou", cz - 0.08)):
        m = jambe & (np.abs(rest[:,2]-z) < 0.01)
        if m.sum() < 10: continue
        A0 = ConvexHull(rest[m][:, [0,1]]).volume
        # section mesurée perpendiculairement à l'axe : on prend la projection sur le plan orthogonal à l'axe du segment
        A1 = ConvexHull(pts[m][:, [0,1]]).volume
        out[lab+"_ratio"] = float(A1/A0)
    # 3. pénétration : plis
    out["plis"] = _plis(pts, dom_, Ms)
    return out
M120=pose_angle(120); cz = np.linalg.lstsq(np.eye(3)-M120[:3,:3], M120[:3,3], rcond=None)[0][2]
import numpy as np
for th in (60, 90, 105, 120):
    base_w = W0; base_M = d["M"][etq.index(f"LeftLeg@{th}")]
    cb = criteres(base_w, base_M, th)
    W, Ms = chaine(th, 8, 0.15)
    cc = criteres(W, Ms, th)
    print(th, "BASE", {k: (round(v,3) if isinstance(v,float) else v) for k,v in cb.items()})
    print(th, "CHAINE", {k: (round(v,3) if isinstance(v,float) else v) for k,v in cc.items()})
