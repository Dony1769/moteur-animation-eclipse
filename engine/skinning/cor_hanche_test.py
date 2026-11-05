"""Test de la bande de hanche avec centres de rotation par sommet (centres_rotation_optimises.py).

Déformation (bord fixe comme la phase 4) :
  - s < -B : proximal, identité ;
  - s > +B : distal, rotation rigide autour du pivot (même axe que la chaîne) ;
  - |s| < B : chaque sommet tourne autour de SON centre de rotation, d'un angle θ·rampe(s) (rampe linéaire 0→1).
Mesures : étirement des arêtes de la bande (p99), plis par plis_locaux, inversions. Comparaison à la chaîne numpy
(docs/rapports/phase4_chaine_hanche_numpy.json).
Usage : python3 cor_hanche_test.py <dossier_donnees>
"""
import sys, json
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_chaine_hanche as t
import centres_rotation_optimises as cr
from mesures_pose import plis_locaux
from scipy.spatial.transform import Rotation as Rot

B = 0.15
pivot = t.h[t.ix["mixamorig:LeftUpLeg"]]
dirl = t.h[t.ix["mixamorig:LeftLeg"]] - pivot
dirl = dirl / np.linalg.norm(dirl)
axe = np.cross(dirl, t.Y); axe /= np.linalg.norm(axe)
rest = t.rest; faces = t.faces; aretes = t.aretes
s = (rest - pivot) @ dirl
bande = np.abs(s) < B
distal = s >= B
proximal = s <= -B

os_hanche = [t.ix["mixamorig:Hips"], t.ix["mixamorig:LeftUpLeg"], t.ix["mixamorig:RightUpLeg"],
             t.ix["mixamorig:Spine"], t.ix["mixamorig:LeftLeg"]]
Wk = t.W[:, os_hanche]
idx_bande = np.where(bande)[0]
print("sommets de bande :", len(idx_bande), flush=True)
C_bande, ok = cr.centres_de_rotation(rest, faces, Wk, idx_bande)
print("centres valides :", int(ok.sum()), "/", len(idx_bande), flush=True)
C = np.zeros_like(rest)
C[idx_bande] = C_bande

ramp = np.clip((s + B) / (2 * B), 0.0, 1.0)          # 0 côté proximal, 1 côté distal (même convention que la chaîne)
L0 = np.linalg.norm(rest[aretes[:, 0]] - rest[aretes[:, 1]], axis=1)
band_e = np.linalg.norm((rest[aretes[:, 0]] + rest[aretes[:, 1]]) / 2 - pivot, axis=1) < 0.10
out = []
for th in (30.0, 60.0, 90.0, 105.0, 120.0):
    P = rest.copy()
    # distal : rotation rigide autour du pivot
    Rd = Rot.from_rotvec(axe * np.radians(th)).as_matrix()
    P[distal] = pivot + (rest[distal] - pivot) @ Rd.T
    # bande : rotation autour du centre propre de chaque sommet, angle θ·rampe
    ang = np.radians(th) * ramp[idx_bande]
    Rb = Rot.from_rotvec(axe[None, :] * ang[:, None]).as_matrix()
    P[idx_bande] = C[idx_bande] + np.einsum("nij,nj->ni", Rb, rest[idx_bande] - C[idx_bande])
    # rotation locale par face : axe commun, angle θ·moyenne de la rampe sur la face
    ang_face = np.radians(th) * ramp[faces].mean(axis=1)
    Rf = Rot.from_rotvec(axe[None, :] * ang_face[:, None]).as_matrix()
    L1 = np.linalg.norm(P[aretes[:, 0]] - P[aretes[:, 1]], axis=1)
    r = L1 / np.maximum(L0, 1e-9)
    plis = plis_locaux(rest, P, faces, Rf)
    # inversions : signe de la normale par rapport au repos
    n0 = np.cross(rest[faces[:, 1]] - rest[faces[:, 0]], rest[faces[:, 2]] - rest[faces[:, 0]])
    n1 = np.cross(P[faces[:, 1]] - P[faces[:, 0]], P[faces[:, 2]] - P[faces[:, 0]])
    inv = int((np.einsum("fi,fi->f", n0, n1) < 0).sum())
    row = dict(th=th, plis=plis, inversions=inv,
               etirement_bande_p99=round(float(np.percentile(r[band_e], 99)), 4),
               etirement_bande_mediane=round(float(np.median(r[band_e])), 4),
               n_aretes_bande=int(band_e.sum()))
    out.append(row); print(row, flush=True)
Path(__file__).resolve().parents[2].joinpath("docs/rapports/phase4_centres_rotation_hanche.json").write_text(
    json.dumps(out, indent=2, ensure_ascii=False))
print("ECRIT", flush=True)
