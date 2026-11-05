exec(open('test_dqs_coude.py').read())
from scipy.spatial.transform import Rotation as Rot
def normale(p, f):
    a,b,cc = f[0],f[1],f[2]
    return np.cross(p[b]-p[a], p[cc]-p[a])
def plis_faux(P, G, th):
    """Ancienne métrique : normale monde repos vs posé (signalait toute rotation > 90°)."""
    n = 0
    for f in faces:
        f = list(f)
        if normale(rest, f) @ normale(P, f) < 0: n += 1
    return n
def plis_corriges(P, G, th):
    """Nouvelle métrique : normale de repos tournée par la rotation de peau moyenne du sommet centre de la face."""
    n = 0
    q = Rot.from_matrix(G).as_quat()                 # (B,4)
    for f in faces:
        f = list(f)
        wbar = W[f].mean(0)
        # rotation moyenne : os de poids max (approximation par quaternion dominant)
        b = int(np.argmax(wbar))
        Rf = Rot.from_matrix(G[b])
        n0 = normale(rest, f); n1 = normale(P, f)
        if np.linalg.norm(n0) < 1e-12: continue
        if (Rf.apply(n0)) @ n1 < 0: n += 1
    return n
for th in (30, 60, 90, 120, 145):
    R = np.tile(np.eye(3),(B,1,1)); R[ix["mixamorig:LeftForeArm"]] = Rot.from_rotvec(ax*np.radians(th)).as_matrix()
    G, dd = skin_transforms(parent, h, R)
    P = pose(th)
    print(f"θ={th}: plis ancienne métrique={plis_faux(P,G,th)}  plis métrique corrigée={plis_corriges(P,G,th)}", flush=True)
