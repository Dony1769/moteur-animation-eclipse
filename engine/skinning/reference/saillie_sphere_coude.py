import numpy as np, trimesh
from scipy.spatial.transform import Rotation as Rot
exec(open('volume_interpenetration.py').read().split('for Rs in (0.07,):')[0])
RS = 0.07
epaule = np.array(J["mixamorig:LeftArm"]["tete"]); poignet = np.array(J["mixamorig:LeftHand"]["tete"])
R_BRAS, R_AVANT = 0.055, 0.042   # rayons mesurés des tubes (coude_calotte_cousue.py)
def posed(th):
    R = Rot.from_rotvec(ax*np.radians(th)).as_matrix()
    P = rest0.copy(); P[F_mask] = rest0[F_mask] @ R.T + (c - R @ c); return P, R
def dist_axe(p, a, b):
    ab = b - a; t = np.clip(((p - a) @ ab)/(ab @ ab), 0, 1)
    return np.linalg.norm(p - (a + np.outer(t, ab)), axis=1)
for th in (0, 30, 60, 90, 100, 120):
    P, R = posed(th)
    bU = piece(U_mask, P); bF = piece(F_mask, P)
    sph = trimesh.creation.icosphere(subdivisions=3, radius=RS); sph.apply_translation(c)
    dedans = bU.contains(sph.vertices) | bF.contains(sph.vertices)
    expo = sph.vertices[~dedans]
    if len(expo) == 0:
        print(f"θ={th}: sphère entièrement cachée"); continue
    # axes posés : bras fixe épaule→coude ; avant-bras coude→poignet (tourné)
    poig_p = R @ (poignet - c) + c
    d_bras = dist_axe(expo, epaule, c) - R_BRAS
    d_avant = dist_axe(expo, c, poig_p) - R_AVANT
    saillie = np.minimum(np.maximum(d_bras, -1), np.maximum(d_avant, -1))
    frac = len(expo)/len(sph.vertices)
    print(f"θ={th}: sommets sphère exposés {round(frac*100,1)} %, saillie max au-delà du membre = {round(float(saillie.max())*100,2)} cm, saillie médiane = {round(float(np.median(saillie))*100,2)} cm", flush=True)
