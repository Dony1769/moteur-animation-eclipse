"""Lancer depuis scratchpad/arap (donnees7.npz, os_repos.json). Erreur 90."""
import sys, json, numpy as np
exec(open('genou_calibre.py').read().split('for R_J in (0.0, 0.055):')[0])
hanche = np.array(J["mixamorig:LeftUpLeg"]["tete"])
a = hanche - genou; a /= np.linalg.norm(a)
f0 = cheville - genou; f0 /= np.linalg.norm(f0)
dist0 = np.linalg.norm(rest0 - genou, axis=1)
def mesure(R_Z, angles):
    out = []
    for th in angles:
        R = Rot.from_rotvec(-X * np.radians(th)).as_matrix()   # sens anatomique -1
        f = R @ f0
        n = a - f; n /= np.linalg.norm(n)
        cote = (rest0 - genou) @ n           # >0 : côté cuisse
        zone = dist0 < R_Z
        tourne = enf & ~(zone & (cote > 0))  # mollet rigide, sauf sa partie côté cuisse dans la zone
        tourne |= zone & enf & (cote <= 0)
        # cuisse dans la zone côté mollet : elle suit le mollet
        tourne |= zone & (dom0 == ix("LeftUpLeg")) & (cote <= 0)
        P = rest0.copy(); Q = rest0 @ R.T + (genou - R @ genou)
        P[tourne] = Q[tourne]
        nn, pm, _ = penetration_nouvelle(rest0, P, faces0, tourne, centre=None, dom=dom0)
        out.append(f"{th}:{nn}")
    print(f"zone={R_Z:.2f}  " + "  ".join(out), flush=True)
for R_Z in (0.0, 0.08, 0.12, 0.16):
    mesure(R_Z, (30, 60, 90, 120))
