"""Données du visualiseur v2 (phase 4, méthode des articulations) : pour chaque articulation et angle,
positions « sans méthode » (bascule dure entre os, sans bande) et « avec méthode » (chaîne de nœuds
coaxiaux, bande sur la bissectrice), plis par sommet, étirement par sommet.

Articulations (amplitudes retenues, voir docs/rapports/phase4_*.json) :
  Genou (charnière, validé Blender), Coude (charnière, validé Blender), Cheville (charnière, validé Blender),
  Hanche (sphère, limite 30°), Épaule (sphère, limite 20°), Poignet (condylienne, limite 50°).
Usage : python3 exporter_visualiseur_v2.py DOSSIER_ARAP/ SORTIE.json
"""
import sys, os, json, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from articulation_chaine import chaine, deformer
from plis_numpy import plis_masque
from scipy.spatial.transform import Rotation as Rot

S = sys.argv[1].rstrip("/") + "/"
sortie = sys.argv[2]
d = np.load(S + "donnees7.npz", allow_pickle=True)
rest, faces, ar = d["rest"], d["faces"], d["aretes"]
os_ = [str(x) for x in d["os"]]; etq = [str(x) for x in d["etiquettes"]]
W0 = d["W"]; dom = W0.argmax(1)
J = json.load(open(S + "os_repos.json"))["os"]
ix = lambda n: os_.index("mixamorig:" + n)
hanche = np.array(J["mixamorig:LeftUpLeg"]["tete"])
genou = np.array(J["mixamorig:LeftLeg"]["tete"])
cheville = np.array(J["mixamorig:LeftFoot"]["tete"])
coude = np.array(J["mixamorig:LeftForeArm"]["tete"])
epaule = np.array(J["mixamorig:LeftArm"]["tete"])
poignet = np.array(J["mixamorig:LeftHand"]["tete"])
X = np.array([1.0, 0, 0])

def synth(c, th):
    R = Rot.from_rotvec(X * np.radians(th)).as_matrix()
    M = np.eye(4); M[:3, :3] = R; M[:3, 3] = c - R @ c
    return M

def dur(Wx, Mx, pts_):
    """sans méthode : affectation dure (chaque sommet à son os dominant, rigide)."""
    return Wx, Mx

tri = []
for f in faces:
    b = list(f)
    for k in range(1, len(b) - 1):
        tri.append([b[0], b[k], b[k + 1]])

def plis(P, Wx, Mx):
    m = plis_masque(rest, P, Wx, Mx, faces)
    v = np.zeros(len(rest), np.uint8)
    for k in np.where(m)[0]:
        v[list(faces[k])] = 1
    return int(m.sum()), v

def etir(P):
    r = np.zeros(len(rest))
    i, j = ar[:, 0], ar[:, 1]
    L0 = np.linalg.norm(rest[i] - rest[j], axis=1); L1 = np.linalg.norm(P[i] - P[j], axis=1)
    ratio = L1 / np.maximum(L0, 1e-9)
    np.maximum.at(r, i, ratio); np.maximum.at(r, j, ratio)
    return r

# définition des articulations : (nom, centre, parent, enfants, angles, B, méthode)
ART = [
    ("Genou", genou, ix("LeftUpLeg"), [ix("LeftLeg"), ix("LeftFoot")], [0, 60, 75, 90, 105, 120], 0.15),
    ("Coude", coude, ix("LeftArm"), [ix("LeftForeArm"), ix("LeftHand")], [0, 60, 75, 90, 105, 120], 0.10),
    ("Cheville", cheville, ix("LeftLeg"), [ix("LeftFoot")], [-50, -20, 0, 20], 0.04),
    ("Hanche", hanche, ix("Hips"), [ix("LeftUpLeg"), ix("LeftLeg"), ix("LeftFoot")], [0, 10, 20, 30], 0.04),
    ("Épaule", epaule, ix("LeftShoulder"), [ix("LeftArm"), ix("LeftForeArm"), ix("LeftHand")], [0, 5, 10, 15, 20], 0.04),
    ("Poignet", poignet, ix("LeftForeArm"), [ix("LeftHand")], [0, 10, 20, 30, 40, 50], 0.04),
]
frames = []; chaines = []; angles = []
for nom, c, par, kids, angs, B in ART:
    chaines.append(nom); angles.append(angs)
    for th in angs:
        M = synth(c, th)
        # sans méthode : bascule dure (bande nulle) entre parent et enfants
        Wh, Mh, _ = chaine(rest, dom, par, kids, M, 8, 1e-4, bissectrice=True, enfant_rigide=True)
        Ph = deformer(rest, Wh, Mh)
        # avec méthode : bande (sur la bissectrice), enfant rigide pour la cheville, sinon bande
        Wm, Mm, _ = chaine(rest, dom, par, kids, M, 8, B, bissectrice=True)
        Pm = deformer(rest, Wm, Mm)
        pl_h, vl_h = plis(Ph, Wh, Mh); pl_m, vl_m = plis(Pm, Wm, Mm)
        # déplacements en millimètres (entiers) par rapport au repos ; étirement en dixièmes
        dl = np.round((Ph - rest) * 1000).astype(int).ravel().tolist()
        dc = np.round((Pm - rest) * 1000).astype(int).ravel().tolist()
        frames.append({"chaine": nom, "angle": th,
                       "dlbs": dl, "dcor": dc,
                       "etir_lbs": np.round(etir(Ph) * 10).astype(int).tolist(), "etir_cor": np.round(etir(Pm) * 10).astype(int).tolist(),
                       "plis_lbs": pl_h, "plis_cor": pl_m,
                       "pli_v_lbs": vl_h.tolist(), "pli_v_cor": vl_m.tolist()})
        print(nom, th, "plis sans méthode", pl_h, "avec méthode", pl_m, flush=True)
tri_out = tri
out = {"rest": np.round(rest, 3).ravel().tolist(), "tri": tri_out, "unite": "mm (déplacements), dixièmes (étirement)",
       "chaines": chaines, "angles": angles, "frames": frames,
       "validations": [
           {"articulation": "Genou", "angles": [60, 90, 105, 120], "methode": "Blender LBS", "plis": 0, "rigidite": "0,00 mm", "section": "0,995–0,999"},
           {"articulation": "Coude", "angles": [60, 90, 105, 120], "methode": "Blender LBS", "plis": 0, "rigidite": "0,00 mm", "section": "0,993–0,998"},
           {"articulation": "Cheville", "angles": [20, -20, -50], "methode": "Blender LBS", "plis": 0, "rigidite": "0,00 mm", "section": "1,00 / 0,95 / 0,88"},
           {"articulation": "Hanche", "angles": [30], "methode": "numpy", "plis": 0, "rigidite": "—", "section": "limite : 30°"},
           {"articulation": "Épaule", "angles": [20], "methode": "numpy", "plis": 0, "rigidite": "—", "section": "limite : 20°"},
           {"articulation": "Poignet", "angles": [50], "methode": "numpy", "plis": 0, "rigidite": "—", "section": "limite : 50°"}]}
json.dump(out, open(sortie, "w"))
print("ECRIT", sortie, os.path.getsize(sortie) // 1024, "Ko")
