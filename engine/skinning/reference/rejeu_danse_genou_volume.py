import json, numpy as np, trimesh
from collections import Counter
from scipy.spatial.transform import Rotation as Rot
exec(open('volume_interpenetration.py').read().split('for Rs in (0.07,):')[0])
# --- articulation du genou (gauche) depuis les os du squelette de référence ---
hanche = np.array(J["mixamorig:LeftUpLeg"]["tete"]); genou_c = np.array(J["mixamorig:LeftLeg"]["tete"])
cheville = np.array(J["mixamorig:LeftFoot"]["tete"]); orteil = np.array(J["mixamorig:LeftFoot"]["queue"])
h = np.cross(hanche - genou_c, cheville - genou_c)
if np.linalg.norm(h) < 1e-9:   # jambe verticale : produit vectoriel nul -> normale au plan sagittal (jambe x orteils)
    h = np.cross(cheville - hanche, np.array(J["mixamorig:LeftFoot"]["queue"]) - cheville)
h /= np.linalg.norm(h)
toe = (orteil - cheville); toe /= np.linalg.norm(toe)
# signe : en flexion positive, la cheville doit reculer (déplacement · orteil < 0)
dep = Rot.from_rotvec(h*np.radians(10)).as_matrix() @ (cheville - genou_c) + genou_c - cheville
sign = -1.0 if dep @ toe > 0 else 1.0
ax_g = h * sign
print("axe genou (bones)", np.round(ax_g,4), "signe", sign, "centre", np.round(genou_c,4), flush=True)
# --- masques : cuisse = dominance LeftUpLeg, jambe = LeftLeg + LeftFoot ---
dom_cuisse = ix("LeftUpLeg"); dom_jambe = [ix("LeftLeg"), ix("LeftFoot")]
U_mask = (dom0 == dom_cuisse)
F_mask = np.isin(dom0, dom_jambe)
c = genou_c; ax = ax_g
for nom, m in (("cuisse", U_mask), ("jambe", F_mask)):
    fs = [f for f in faces0 if all(m[k] for k in f)]
    idx = -np.ones(len(rest0), int); idx[m] = np.arange(m.sum())
    V, Fc = fermer(rest0[m], [[idx[k] for k in f] for f in fs])
    mm = maille(V, Fc)
    print(nom, "watertight", mm.is_watertight, "volume", mm.is_volume, "euler", mm.euler_number, "winding", mm.is_winding_consistent, "bords", len(aretes_bord_boucles(fs)), flush=True)
print("sommets cuisse", int(U_mask.sum()), "jambe", int(F_mask.sum()), flush=True)
S = '/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad/hiphop/serie.json'
d = json.load(open(S))
angles = [round(x/5)*5 for x in d["genou_gauche"]]
cnt = Counter(angles); res = {}
for th in sorted(cnt):
    v, fu, ff = mesure(th, 0.07)
    res[th] = None if v is None else round(float(v), 3)
    print(f"θ={th}: images={cnt[th]} interpénétration={res[th]} cm3 (cuisse fermée {fu}, jambe fermée {ff})", flush=True)
n_pen = sum(cnt[th] for th in cnt if (res[th] or 0) > 0)
print("images avec pénétration :", n_pen, "sur", len(angles), flush=True)
json.dump({"theta_images": cnt, "volume_cm3": res, "axe": ax_g.tolist(), "signe": sign}, open('/home/claude/rejeu_genou.json','w'), default=str, indent=1)
