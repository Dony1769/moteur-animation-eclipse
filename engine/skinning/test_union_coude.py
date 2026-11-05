"""Lancer depuis scratchpad/arap (donnees7.npz, os_repos.json, coude_calotte_cousue.py). Erreur 94."""
import numpy as np, trimesh
from scipy.spatial.transform import Rotation as Rot
exec(open('coude_calotte_cousue.py').read().split('print(f"rayons tubes')[0])
tri = np.array([[f[0], f[k], f[k+1]] for f in faces0 for k in range(1, len(f)-1)])
def corps_pose(th):
    R = Rot.from_rotvec(ax*np.radians(th)).as_matrix()
    P = rest0.copy(); P[F_set] = rest0[F_set] @ R.T + (c - R @ c)
    return P
base = trimesh.Trimesh(rest0, tri, process=False)
print("corps au repos : fermé", base.is_watertight, "volume", round(base.volume,4), "orientation cohérente", base.is_winding_consistent)
for Rs in (0.07, 0.08):
    sph = trimesh.creation.icosphere(subdivisions=3, radius=Rs); sph.apply_translation(c)
    for th in (30, 60, 90, 120):
        m = trimesh.Trimesh(corps_pose(th), tri, process=False)
        try:
            u = trimesh.boolean.union([m, sph], engine="manifold")
            print(f"Rs={Rs} θ={th}: union fermé {u.is_watertight}, volume {u.volume:.4f}, faces {len(u.faces)}")
        except Exception as e:
            print(f"Rs={Rs} θ={th}: ERREUR {type(e).__name__}: {str(e)[:120]}")
