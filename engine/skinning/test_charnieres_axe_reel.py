"""Lancer depuis scratchpad/arap (donnees7.npz, os_repos.json). Erreur 89."""
import sys, json, numpy as np
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
from penetration import penetration_nouvelle
from scipy.spatial.transform import Rotation as Rot
d = np.load("donnees7.npz", allow_pickle=True)
rest0, faces0 = d["rest"], d["faces"]
os_ = [str(x) for x in d["os"]]; dom0 = d["W"].argmax(1)
J = json.load(open("os_repos.json"))["os"]
ix = lambda n: os_.index("mixamorig:" + n)
def tete(n): return np.array(J["mixamorig:" + n]["tete"])
def charniere(c, p, q):
    h = np.cross(p - c, q - c); n = np.linalg.norm(h)
    if n < 1e-9:   # jambe verticale : axe non défini par les os, repli sur l'axe gauche-droite X
        return np.array([1.0, 0, 0])
    return h / n
def mesure(nom, c, p, enfants, parent, angles, R_J=0.08, sens=-1, q=None):
    h = charniere(c, p, q); ax = sens * h
    avant0 = np.isin(dom0, enfants)
    dist0 = np.linalg.norm(rest0 - c, axis=1)
    garde = dist0 >= R_J
    im = -np.ones(len(rest0), int); im[garde] = np.arange(garde.sum())
    faces = [[im[k] for k in f] for f in faces0 if all(garde[k] for k in f)]
    rest = rest0[garde]; dom = dom0[garde]; mob = avant0[garde]
    out=[]
    for th in angles:
        R = Rot.from_rotvec(ax * np.radians(th)).as_matrix()
        P = rest.copy(); P[mob] = rest[mob] @ R.T + (c - R @ c)
        n, pm, _ = penetration_nouvelle(rest, P, faces, mob, centre=None, dom=dom)
        out.append(f"{th}:{n}")
    print(f"{nom:9s} axe={np.round(h,3)} sphère={R_J:.2f}  " + "  ".join(out), flush=True)
# genou : cuisse (hanche) - genou - cheville
genou = tete("LeftLeg"); hanche = tete("LeftUpLeg"); cheville = tete("LeftFoot")
q_ch = cheville
mesure("genou", genou, hanche, [ix("LeftLeg"), ix("LeftFoot")], ix("LeftUpLeg"), (30,60,90,120,140), R_J=0.08, sens=-1, q=q_ch)
mesure("genou", genou, hanche, [ix("LeftLeg"), ix("LeftFoot")], ix("LeftUpLeg"), (30,60,90,120,140), R_J=0.0, sens=-1, q=q_ch)
# cheville : jambe - cheville - pied (bout des orteils)
cheville_c = tete("LeftFoot"); jambe = tete("LeftLeg"); orteil = np.array(J["mixamorig:LeftFoot"]["queue"])
mesure("cheville", cheville_c, jambe, [ix("LeftFoot")], ix("LeftLeg"), (-55,-30,15), R_J=0.06, sens=-1, q=orteil)
mesure("cheville", cheville_c, jambe, [ix("LeftFoot")], ix("LeftLeg"), (-55,-30,15), R_J=0.0, sens=-1, q=orteil)
