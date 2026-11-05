import sys, json, numpy as np
sys.path.insert(0, '/home/claude/moteur_3_0/engine/skinning')
from dqs import dqs, skin_transforms
from scipy.spatial.transform import Rotation as Rot
d = np.load('donnees7.npz', allow_pickle=True)
rest = d['rest']; W = d['W']; faces = d['faces']; aretes = d['aretes']
os_ = [str(x) for x in d['os']]; J = json.load(open('os_repos.json'))['os']
ix = {n: i for i, n in enumerate(os_)}
parent_nom = {"Spine":"Hips","Spine1":"Spine","Neck":"Spine1","Head":"Neck","LeftShoulder":"Spine1",
    "LeftArm":"LeftShoulder","LeftForeArm":"LeftArm","LeftHand":"LeftForeArm","RightShoulder":"Spine1",
    "RightArm":"RightShoulder","RightForeArm":"RightArm","RightHand":"RightForeArm",
    "LeftArmHelper":"LeftArm","RightArmHelper":"RightArm","LeftUpLeg":"Hips","LeftLeg":"LeftUpLeg",
    "LeftFoot":"LeftLeg","RightUpLeg":"Hips","RightLeg":"RightUpLeg","RightFoot":"RightLeg"}
parent = np.array([-1 if n.split(":")[-1] == "Hips" else ix["mixamorig:"+parent_nom[n.split(":")[-1]]] for n in os_])
h = np.array([J[n]["tete"] for n in os_])
c = h[ix["mixamorig:LeftForeArm"]]; epaule = h[ix["mixamorig:LeftArm"]]; poignet = h[ix["mixamorig:LeftHand"]]
ax = np.cross(epaule - c, poignet - c); ax /= np.linalg.norm(ax)   # sens de flexion vérifié : poignet vers l avant (erreur 110)
B = len(os_)
def pose(th):
    R = np.tile(np.eye(3), (B,1,1))
    R[ix["mixamorig:LeftForeArm"]] = Rot.from_rotvec(ax*np.radians(th)).as_matrix()
    R[ix["mixamorig:LeftHand"]] = np.eye(3)
    G, dd = skin_transforms(parent, h, R)
    return dqs(rest, W, G, dd)
# témoin 1 : identité
P0 = pose(0)
print("TEMOIN identité : écart max au repos =", float(np.abs(P0-rest).max()), flush=True)
# arêtes et faces
def crit(P, th):
    e = aretes; L0 = np.linalg.norm(rest[e[:,0]]-rest[e[:,1]],axis=1); L1 = np.linalg.norm(P[e[:,0]]-P[e[:,1]],axis=1)
    r = L1/np.maximum(L0,1e-9); mid = (rest[e[:,0]]+rest[e[:,1]])/2
    band = np.linalg.norm(mid-c,axis=1) < 0.10
    fl_h = fl_b = 0; cen_d = []
    for f in faces:
        f = list(f)
        a,b,cc = f[0],f[1],f[2]
        n0 = np.cross(rest[b]-rest[a], rest[cc]-rest[a]); n1 = np.cross(P[b]-P[a], P[cc]-P[a])
        cen = rest[f].mean(0)
        if n0@n1 < 0:
            if np.linalg.norm(cen-c) < 0.10: fl_b += 1
            else: fl_h += 1
    return dict(th=th, etirement_hors=round(float(r[~band].max()),3), etirement_dans=round(float(r[band].max()),3),
                plis_hors=fl_h, plis_dans=fl_b)
if __name__ == "__main__":
    for th in (30, 60, 90, 120, 145):
        print("COUDE", crit(pose(th), th), flush=True)
