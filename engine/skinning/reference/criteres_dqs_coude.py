exec(open('test_dqs_coude.py').read())
import sys
sys.path.insert(0, '/home/claude/moteur_3_0/engine/skinning')
from mesures_pose import plis_locaux
from scipy.spatial.transform import Rotation as Rot
def criteres(th):
    R = np.tile(np.eye(3),(B,1,1)); R[ix["mixamorig:LeftForeArm"]] = Rot.from_rotvec(ax*np.radians(th)).as_matrix()
    G, dd = skin_transforms(parent, h, R)
    P = dqs(rest, W, G, dd)
    Fl = np.array([list(f)[:3] for f in faces])
    cen = np.array([rest[list(f)].mean(0) for f in faces])
    Rf = np.array([G[int(np.argmax(W[list(f)].mean(0)))] for f in faces])
    band_f = np.linalg.norm(cen - c, axis=1) < 0.10
    # plis par bande
    Nr = np.array([np.cross(rest[f[1]]-rest[f[0]], rest[f[2]]-rest[f[0]]) for f in Fl])
    Np = np.array([np.cross(P[f[1]]-P[f[0]], P[f[2]]-P[f[0]]) for f in Fl])
    Nrl = np.einsum("fij,fj->fi", Rf, Nr)
    fold = np.einsum("ij,ij->i", Nrl, Np) < 0
    e = aretes; L0 = np.linalg.norm(rest[e[:,0]]-rest[e[:,1]],axis=1); L1 = np.linalg.norm(P[e[:,0]]-P[e[:,1]],axis=1)
    r = L1/np.maximum(L0,1e-9); mid = (rest[e[:,0]]+rest[e[:,1]])/2
    band_e = np.linalg.norm(mid-c,axis=1) < 0.10
    return dict(th=th, plis_hors=int((fold&~band_f).sum()), plis_dans=int((fold&band_f).sum()),
                etir_hors=round(float(r[~band_e].max()),3), etir_dans=round(float(r[band_e].max()),3),
                etir_hors_p99=round(float(np.percentile(r[~band_e],99)),3))
for th in (30, 60, 90, 120, 145):
    print("DQS", criteres(th), flush=True)
