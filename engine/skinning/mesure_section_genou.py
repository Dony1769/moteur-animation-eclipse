import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation as Rot
exec(open("/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad/articulations/criteres_genou.py").read().split('for th in (60')[0])
def aire_perp(P, axe, m):
    a = axe/np.linalg.norm(axe)
    tmp = np.array([1.0,0,0]) if abs(a[0])<0.9 else np.array([0,1.0,0])
    u = np.cross(a,tmp); u/=np.linalg.norm(u); v = np.cross(a,u)
    Q = np.stack([P[m]@u, P[m]@v],1)
    return ConvexHull(Q).volume
def sections(W, Ms, th):
    pts = deformer(W, Ms)
    R = Rot.from_rotvec(np.array([np.deg2rad(th),0,0])).as_matrix()  # axe X, signe comme la pose
    cuisse = np.array([0,0,1.0]); jambe = R @ np.array([0,0,1.0])
    out = {}
    for lab, z, axe_r, axe_p in (("genou", cz, np.array([0,0,1.0]), (cuisse+jambe)/2),
                                  ("sous_genou", cz-0.08, np.array([0,0,1.0]), jambe)):
        m = jambe_mask & (np.abs(rest[:,2]-z) < 0.01)
        out[lab] = round(aire_perp(pts, axe_p, m)/aire_perp(rest, axe_r, m), 3)
    return out
jambe_mask = jambe
for th in (60, 90, 105, 120):
    W, Ms = chaine(th, 8, 0.15)
    print("CHAINE", th, sections(W, Ms, th))
    print("BASE  ", th, sections(W0, d["M"][etq.index(f"LeftLeg@{th}")], th))
