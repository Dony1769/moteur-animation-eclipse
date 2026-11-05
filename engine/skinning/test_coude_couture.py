"""Lancer depuis scratchpad/arap. Erreur 93 : couture sans geometrie = ouverture. Voir docs/recherches_phase4.md."""
"""Coude : couture au plan bissecteur, recalculée à chaque angle. Sommets proches de la jointure (rayon Rz)
attribués au côté bras supérieur (fixe) ou avant-bras (tourné) selon le plan bissecteur ; les faces qui
traversent la couture sont supprimées ; le reste est rigide par os.
Mesures : pénétration nouvelle, plis retournés, ouverture de couture (écart max des bords ouverts mobiles)."""
import sys, json, numpy as np
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
from penetration import penetration_nouvelle
from mesures_pose import plis_retournes
from scipy.spatial.transform import Rotation as Rot
from scipy.spatial import cKDTree
from collections import Counter
d = np.load("donnees7.npz", allow_pickle=True)
rest0, faces0 = d["rest"], d["faces"]
os_ = [str(x) for x in d["os"]]; dom0 = d["W"].argmax(1)
J = json.load(open("os_repos.json"))["os"]
ix = lambda n: os_.index("mixamorig:" + n)
c = np.array(J["mixamorig:LeftForeArm"]["tete"])
a = np.array(J["mixamorig:LeftArm"]["tete"]) - c; a /= np.linalg.norm(a)
f0 = np.array(J["mixamorig:LeftHand"]["tete"]) - c; f0 /= np.linalg.norm(f0)
h = np.cross(a, f0); h /= np.linalg.norm(h); ax = -h
F_set = np.isin(dom0, [ix("LeftForeArm"), ix("LeftHand")])
dist0 = np.linalg.norm(rest0 - c, axis=1)
def mesure(th, Rz):
    R = Rot.from_rotvec(ax * np.radians(th)).as_matrix()
    f = R @ f0
    n = a - f; n /= np.linalg.norm(n)
    cote = (rest0 - c) @ n                     # > 0 : côté bras supérieur
    zone = dist0 < Rz
    tourne = F_set & ~(zone & (cote > 0))      # avant-bras rigide, sauf zone côté bras
    tourne = tourne | (zone & F_set & (cote <= 0))
    fixe_zone = zone & ~F_set & (cote > 0)
    # sommets du bras supérieur dans la zone côté avant-bras : suivent l'avant-bras
    tourne |= (zone & (dom0 == ix("LeftArm")) & (cote <= 0))
    garde = np.ones(len(rest0), bool)
    faces = [f for f in faces0]
    # couture : supprimer les faces dont les sommets ne sont pas tous du même groupe
    fs = [f for f in faces0 if all(tourne[k] for k in f) or all(not tourne[k] for k in f)]
    P = rest0.copy(); P[tourne] = rest0[tourne] @ R.T + (c - R @ c)
    n_pen, pm, _ = penetration_nouvelle(rest0, P, fs, tourne, centre=None, dom=dom0)
    pl = plis_retournes(rest0, P, fs)
    # ouverture : bords ouverts (arêtes d'une seule face) ; écart max des bords mobiles à la pièce fixe
    cnt = Counter()
    for f in fs:
        for k in range(len(f)):
            cnt[tuple(sorted((f[k], f[(k+1) % len(f)])))] += 1
    bord = np.unique([v for e, m_ in cnt.items() if m_ == 1 for v in e])
    fixe = np.where(~tourne)[0]
    if len(bord):
        bm = bord[tourne[bord]]
        ouv = float(np.max(cKDTree(P[fixe]).query(P[bm])[0])) if len(bm) else 0.0
    else:
        ouv = 0.0
    return n_pen, pl, ouv, len(fs)
for Rz in (0.06, 0.10):
    out = []
    for th in (30, 60, 90, 120):
        n_pen, pl, ouv, nf = mesure(th, Rz)
        out.append(f"{th}: pén {n_pen}, plis {pl}, ouverture {ouv*1000:.0f}mm, faces {nf}")
    print(f"Rz={Rz:.2f} | " + " | ".join(out), flush=True)
