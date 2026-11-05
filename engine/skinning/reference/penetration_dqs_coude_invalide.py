exec(open('dqs_criteres.py').read().split('for th in (30, 60, 90, 120, 145):')[0])
import trimesh
tri = np.array([[f[0],f[k],f[k+1]] for f in faces for k in range(1,len(f)-1)])
m0 = trimesh.Trimesh(rest, tri, process=False)
print("corps repos : étanche", m0.is_watertight, "volume", m0.is_volume, flush=True)
avant = np.isin(np.argmax(W,1), [ix["mixamorig:LeftForeArm"], ix["mixamorig:LeftHand"]])
hors = np.linalg.norm(rest-c,axis=1) > 0.10
pts_idx = np.where(avant & hors)[0]
def pen(th):
    R = np.tile(np.eye(3),(B,1,1)); R[ix["mixamorig:LeftForeArm"]] = Rot.from_rotvec(ax*np.radians(th)).as_matrix()
    G, dd = skin_transforms(parent, h, R)
    P = dqs(rest, W, G, dd)
    m = trimesh.Trimesh(P, tri, process=False)
    # sommets d'avant-bras hors bande dont le sommet posé est à l'intérieur de la surface du corps (autre partie)
    inside = m.contains(P[pts_idx])
    return int(inside.sum())
base = pen(0)
print("repos : sommets avant-bras hors bande à l'intérieur =", base, flush=True)
for th in (30, 60, 90, 120, 145):
    print("θ", th, "sommets avant-bras à l'intérieur (nouveaux par rapport au repos) =", pen(th)-base, flush=True)
