import numpy as np, trimesh
from scipy.spatial.transform import Rotation as Rot
exec(open('volume_interpenetration.py').read().split('for Rs in (0.07,):')[0])
RS = 0.07
epaule = np.array(J["mixamorig:LeftArm"]["tete"]); poignet = np.array(J["mixamorig:LeftHand"]["tete"])
R_BRAS, R_AVANT = 0.055, 0.042
# loi publiée (Hermawati & Marshall, fig. 5) : rapport UAF/UAM en fonction de l'angle
loi = lambda x: -6e-6*x**2 - 0.0018*x + 0.9478
def r(theta): return loi(theta) / loi(0)
def posed(th):
    R = Rot.from_rotvec(ax*np.radians(th)).as_matrix()
    P = rest0.copy(); P[F_mask] = rest0[F_mask] @ R.T + (c - R @ c); return P, R
def dist_axe(p, a, b):
    ab = b - a; t = np.clip(((p - a) @ ab)/(ab @ ab), 0, 1)
    return np.linalg.norm(p - (a + np.outer(t, ab)), axis=1)
def mesure(th, appliquer):
    P, R = posed(th)
    bU = piece(U_mask, P); bF = piece(F_mask, P)
    sph = trimesh.creation.icosphere(subdivisions=3, radius=RS); sph.apply_translation(c)
    V = sph.vertices.copy()
    if appliquer:
        a_hat = (epaule - c); a_hat /= np.linalg.norm(a_hat)
        poig_p = R @ (poignet - c) + c
        b_hat = (poig_p - c); b_hat /= np.linalg.norm(b_hat)
        u = a_hat + b_hat
        if np.linalg.norm(u) > 1e-6:
            u /= np.linalg.norm(u)
            d = V - c; dn = d / np.linalg.norm(d, axis=1, keepdims=True)
            cosf = dn @ u
            w = np.clip(cosf, 0, 1)**2             # côté fléchisseur seulement, transition douce
            delta = 0.015 * (1 - r(th)) * w        # réduction de saillie (m), 1,5 cm au repos
            V = V - dn * delta[:, None]
    # sommets exposés : hors des pièces (le contact est vérifié avec les pièces posées)
    dedans = bU.contains(V) | bF.contains(V)
    expo = V[~dedans]
    poig_p = R @ (poignet - c) + c
    d_bras = dist_axe(expo, epaule, c) - R_BRAS
    d_avant = dist_axe(expo, c, poig_p) - R_AVANT
    sail = np.minimum(np.maximum(d_bras, -1), np.maximum(d_avant, -1))
    # séparer côté fléchisseur / extenseur (même test que la correction)
    a_hat = (epaule - c); a_hat /= np.linalg.norm(a_hat)
    b_hat = (poig_p - c); b_hat /= np.linalg.norm(b_hat)
    u = a_hat + b_hat
    flex = (expo - c) @ (u/np.linalg.norm(u)) > 0 if np.linalg.norm(u) > 1e-6 else np.zeros(len(expo), bool)
    return (np.median(sail[flex])*100, np.percentile(sail[flex],90)*100) if flex.any() else (0,0), (np.median(sail[~flex])*100, np.percentile(sail[~flex],90)*100) if (~flex).any() else (0,0)
for th in (0, 30, 60, 90, 120, 135):
    avant = mesure(th, False); apres = mesure(th, True)
    print(f"θ={th}: fléchisseur médiane/p90 {avant[0][0]:.2f}/{avant[0][1]:.2f} -> {apres[0][0]:.2f}/{apres[0][1]:.2f} cm ; extenseur {avant[1][0]:.2f}/{avant[1][1]:.2f} -> {apres[1][0]:.2f}/{apres[1][1]:.2f} cm ; r={r(th):.3f}", flush=True)
