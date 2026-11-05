import numpy as np, trimesh
from scipy.spatial.transform import Rotation as Rot
exec(open('volume_interpenetration.py').read().split('for Rs in (0.07,):')[0])
RS = 0.07; BANDE = 0.10
def posed(th):
    R = Rot.from_rotvec(ax*np.radians(th)).as_matrix()
    P = rest0.copy(); P[F_mask] = rest0[F_mask] @ R.T + (c - R @ c); return P
def union(th):
    P = posed(th)
    bU = piece(U_mask, P); bF = piece(F_mask, P)
    sph = trimesh.creation.icosphere(subdivisions=3, radius=RS); sph.apply_translation(c)
    return trimesh.boolean.union([bU, bF, sph], engine="manifold")
U0 = union(0)
print("union repos : fermee", U0.is_watertight, "volume", U0.is_volume, flush=True)
for th in (30, 60, 90, 100, 120):
    Ut = union(th)
    cen = Ut.triangles_center
    _, _, tri = trimesh.proximity.closest_point(U0, cen)
    n_rest = U0.face_normals[tri]; n_pose = Ut.face_normals
    plis = (np.einsum("ij,ij->i", n_rest, n_pose) < 0)
    hors = np.linalg.norm(cen - c, axis=1) > BANDE
    print(f"θ={th}: faces={len(Ut.faces)} fermee={Ut.is_watertight} plis_hors_bande={int((plis&hors).sum())} plis_dans_bande={int((plis&~hors).sum())}", flush=True)
