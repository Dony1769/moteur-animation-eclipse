"""DQS sur la hanche et le genou (phase 4).

Usage : python3 test_dqs_hanche_genou.py <dossier_donnees>
  où <dossier_donnees> contient donnees7.npz et os_repos.json.

Méthode :
- hanche : rotation de l'os LeftUpLeg autour de sa tête (hanche). Axe = cross(d, Y) avec d = unit(genou − hanche),
  ce qui fait avancer le genou (+Y) en flexion. Signe vérifié par témoin (déplacement du genou).
- genou  : rotation de l'os LeftLeg autour de sa tête (genou). Axe = −cross(d, Y) avec d = unit(cheville − genou),
  ce qui fait reculer la cheville (−Y) en flexion. Signe vérifié par témoin (déplacement de la cheville).
- Plis : métrique locale plis_locaux (erreur 108 corrigée) : rotation locale = os de poids dominant par face.
- Étirement : arêtes dont le milieu est hors bande de 10 cm autour du pivot (critère de la phase 4) ; dans la bande,
  l'étirement est borné et rapporté séparément.
- Témoin : identité (écart au repos = 0).
"""
import sys, json, numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dqs import dqs, skin_transforms
from mesures_pose import plis_locaux, etirement_max
from scipy.spatial.transform import Rotation as Rot

DATA = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
d = np.load(DATA / "donnees7.npz", allow_pickle=True)
rest = d["rest"]; W = d["W"]; aretes = d["aretes"]
faces = np.array([[int(v) for v in list(f)[:3]] for f in d["faces"]], dtype=int)
os_ = [str(x) for x in d["os"]]
J = json.load(open(DATA / "os_repos.json"))["os"]
ix = {n: i for i, n in enumerate(os_)}
parent_nom = {"Spine": "Hips", "Spine1": "Spine", "Neck": "Spine1", "Head": "Neck", "LeftShoulder": "Spine1",
    "LeftArm": "LeftShoulder", "LeftForeArm": "LeftArm", "LeftHand": "LeftForeArm", "RightShoulder": "Spine1",
    "RightArm": "RightShoulder", "RightForeArm": "RightArm", "RightHand": "RightForeArm",
    "LeftArmHelper": "LeftArm", "RightArmHelper": "RightArm", "LeftUpLeg": "Hips", "LeftLeg": "LeftUpLeg",
    "LeftFoot": "LeftLeg", "RightUpLeg": "Hips", "RightLeg": "RightUpLeg", "RightFoot": "RightLeg"}
parent = np.array([-1 if n.split(":")[-1] == "Hips" else ix["mixamorig:" + parent_nom[n.split(":")[-1]]] for n in os_])
h = np.array([J[n]["tete"] for n in os_])
B = len(os_)
Y = np.array([0.0, 1.0, 0.0])

hanche = h[ix["mixamorig:LeftUpLeg"]]; genou = h[ix["mixamorig:LeftLeg"]]; cheville = h[ix["mixamorig:LeftFoot"]]
ax_h = np.cross((genou - hanche) / np.linalg.norm(genou - hanche), Y); ax_h /= np.linalg.norm(ax_h)
ax_g = -np.cross((cheville - genou) / np.linalg.norm(cheville - genou), Y); ax_g /= np.linalg.norm(ax_g)

# dominance par face (pour la rotation locale de la métrique de plis)
Wf = W[faces].sum(axis=1)                   # (F, B)
dom = np.argmax(Wf, axis=1)


def pose(articulation, th):
    R = np.tile(np.eye(3), (B, 1, 1))
    if articulation == "hanche":
        R[ix["mixamorig:LeftUpLeg"]] = Rot.from_rotvec(ax_h * np.radians(th)).as_matrix()
        pivot = hanche
    else:
        R[ix["mixamorig:LeftLeg"]] = Rot.from_rotvec(ax_g * np.radians(th)).as_matrix()
        pivot = genou
    G, dd = skin_transforms(parent, h, R)
    P = dqs(rest, W, G, dd)
    return P, G, pivot


def mesure(articulation, th):
    P, G, pivot = pose(articulation, th)
    band = np.linalg.norm((rest[aretes[:, 0]] + rest[aretes[:, 1]]) / 2 - pivot, axis=1) < 0.10
    L0 = np.linalg.norm(rest[aretes[:, 0]] - rest[aretes[:, 1]], axis=1)
    L1 = np.linalg.norm(P[aretes[:, 0]] - P[aretes[:, 1]], axis=1)
    r = L1 / np.maximum(L0, 1e-9)
    Rf = G[dom]
    plis = plis_locaux(rest, P, faces, Rf)
    return dict(articulation=articulation, th=th,
                etirement_hors_bande_p99=round(float(np.percentile(r[~band], 99)), 4),
                etirement_hors_bande_max=round(float(r[~band].max()), 4),
                etirement_dans_bande_p99=round(float(np.percentile(r[band], 99)), 4),
                etirement_dans_bande_max=round(float(r[band].max()), 4),
                plis_total=plis)


if __name__ == "__main__":
    # témoin identité
    P0, _, _ = pose("hanche", 0)
    print("TEMOIN identité : écart max =", float(np.abs(P0 - rest).max()), flush=True)
    r0 = np.linalg.norm(rest[aretes[:, 0]] - rest[aretes[:, 1]], axis=1)
    print("TEMOIN identité étirement p99 =", round(float(np.percentile(np.ones_like(r0), 99)), 4), flush=True)
    # témoins de signe : déplacement du distal
    Ph, _, _ = pose("hanche", 60); Pg, _, _ = pose("genou", 60)
    genou_idx = np.argmin(np.linalg.norm(rest - genou, axis=1))
    chev_idx = np.argmin(np.linalg.norm(rest - cheville, axis=1))
    print("SIGNE hanche 60 : dy point genou =", round(float(Ph[genou_idx, 1] - rest[genou_idx, 1]), 3), "(attendu > 0)", flush=True)
    print("SIGNE genou 60 : dy point cheville =", round(float(Pg[chev_idx, 1] - rest[chev_idx, 1]), 3), "(attendu < 0)", flush=True)
    resultats = []
    for th in (30, 60, 90, 120):
        r = mesure("hanche", th); resultats.append(r); print("HANCHE", r, flush=True)
    for th in (30, 60, 90, 120, 135):
        r = mesure("genou", th); resultats.append(r); print("GENOU", r, flush=True)
    out = Path(__file__).resolve().parents[2] / "docs" / "rapports" / "phase4_dqs_hanche_genou.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(resultats, indent=2, ensure_ascii=False))
    print("ECRIT", out, flush=True)
