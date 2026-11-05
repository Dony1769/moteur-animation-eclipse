"""Chaîne de nœuds coaxiaux (articulation_chaine.chaine) appliquée à la hanche et au genou, en numpy.

Contrôle : le genou reproduit le résultat validé dans Blender (docs/rapports/phase4_genou_chaine_blender.json :
K = 8, demi-bande 0,15 m, plis 0 de 60 à 120°). Si le genou numpy ne donne pas 0 pli, la méthode numpy n'est pas
fiable pour la hanche.

Critère : étirement p99 hors bande (10 cm autour du pivot) ; p99 dans la bande ; plis (métrique plis_locaux avec
rotation locale par face estimée à partir de la rotation du nœud au centroïde de la face).
"""
import sys, json, numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from articulation_chaine import chaine, deformer
from mesures_pose import plis_locaux
from scipy.spatial.transform import Rotation as Rot

DATA = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
d = np.load(DATA / "donnees7.npz", allow_pickle=True)
rest = d["rest"]; W = d["W"]; aretes = d["aretes"]
faces = np.array([[int(v) for v in list(f)[:3]] for f in d["faces"]], dtype=int)
os_ = [str(x) for x in d["os"]]
J = json.load(open(DATA / "os_repos.json"))["os"]
ix = {n: i for i, n in enumerate(os_)}
h = np.array([J[n]["tete"] for n in os_])
dom = np.argmax(W, axis=1)
Y = np.array([0.0, 1.0, 0.0])
K = 8; B = 0.15


def M_de(pivot, axe, th):
    R = Rot.from_rotvec(axe * np.radians(th)).as_matrix()
    M = np.eye(4); M[:3, :3] = R; M[:3, 3] = pivot - R @ pivot
    return M


def run(articulation, th, bissectrice=False):
    if articulation == "hanche":
        parent = ix["mixamorig:Hips"]
        enfants = [ix["mixamorig:LeftUpLeg"], ix["mixamorig:LeftLeg"], ix["mixamorig:LeftFoot"]]
        enfant0 = ix["mixamorig:LeftUpLeg"]
        p0 = h[enfant0]; dirl = h[ix["mixamorig:LeftLeg"]] - p0
    else:
        parent = ix["mixamorig:LeftUpLeg"]
        enfants = [ix["mixamorig:LeftLeg"], ix["mixamorig:LeftFoot"]]
        enfant0 = ix["mixamorig:LeftLeg"]
        p0 = h[enfant0]; dirl = h[ix["mixamorig:LeftFoot"]] - p0
    axe = np.cross(dirl / np.linalg.norm(dirl), Y); axe /= np.linalg.norm(axe)
    M_enf = M_de(p0, axe, th)
    W2, Ms, info = chaine(rest, dom, parent, enfants, M_enf, K, B, bissectrice=bissectrice)
    P = deformer(rest, W2, Ms)
    # rotation locale par face : φ·f(centroïde) autour de l'axe
    f_face = W2[faces].mean(axis=1)                              # (F, K+1)
    phi = np.radians(th)
    jw = np.arange(K + 1) / K
    angle_face = (f_face * jw).sum(axis=1) * phi
    Rf = Rot.from_rotvec(info["axe"][None, :] * angle_face[:, None]).as_matrix()
    band = np.linalg.norm((rest[aretes[:, 0]] + rest[aretes[:, 1]]) / 2 - info["pivot"], axis=1) < 0.10
    L0 = np.linalg.norm(rest[aretes[:, 0]] - rest[aretes[:, 1]], axis=1)
    L1 = np.linalg.norm(P[aretes[:, 0]] - P[aretes[:, 1]], axis=1)
    r = L1 / np.maximum(L0, 1e-9)
    plis = plis_locaux(rest, P, faces, Rf)
    return dict(articulation=articulation, th=th, bissectrice=bissectrice,
                etirement_hors_p99=round(float(np.percentile(r[~band], 99)), 4),
                etirement_dans_p99=round(float(np.percentile(r[band], 99)), 4),
                plis_total=plis)


if __name__ == "__main__":
    sorties = []
    for art, angles in (("genou", (60, 90, 105, 120)), ("hanche", (30, 60, 90, 105, 120))):
        for th in angles:
            r = run(art, th); sorties.append(r); print(art, r, flush=True)
    out = Path(__file__).resolve().parents[2] / "docs" / "rapports" / "phase4_chaine_hanche_numpy.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(sorties, indent=2, ensure_ascii=False))
    print("ECRIT", out, flush=True)
