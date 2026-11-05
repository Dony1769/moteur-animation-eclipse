"""Rotation répartie le long du membre (méthode testée en phase 4 pour la hanche et le genou).

Idée (sources : Le & Hodgins, « Real-time Skeletal Skinning with Optimized Centers of Rotation », SIGGRAPH, lu via
phys.org (secondaire) ; Schüller et al. 2013 « Locally injective mappings » (officiel, pénalisation infinie des
inversions) ; test de la phase 4) :
  - chaque sommet tourne autour de l'axe articulaire passant par le pivot, d'un angle f(s)·θ ;
  - s = position le long du membre (projection sur la direction pivot → extrémité distale) ;
  - f(s) : lissage de 0 (côté proximal) à 1 (côté distal), sur une bande de demi-largeur b = 10 cm autour du pivot ;
  - rotation autour d'un axe fixe : les distances à l'axe sont conservées (pas d'écrasement de la section) ;
  - mélange avec DQS hors de la chaîne du membre (poids de la chaîne) pour ne pas toucher le reste du corps.
Mesures : mêmes critères que dqs / psd (p99 hors bande / dans la bande, plis par plis_locaux).
"""
import sys, json, numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dqs import dqs, skin_transforms
from mesures_pose import plis_locaux, normales_faces
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
Wf = W[faces].sum(axis=1); dom = np.argmax(Wf, axis=1)
CHAINE = {"hanche": ["mixamorig:LeftUpLeg", "mixamorig:LeftLeg", "mixamorig:LeftFoot"],
          "genou": ["mixamorig:LeftLeg", "mixamorig:LeftFoot"]}


def smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def pose(articulation, th, b=0.10):
    if articulation == "hanche":
        pivot = hanche; axe = ax_h; dirl = (genou - hanche) / np.linalg.norm(genou - hanche)
        jb = "mixamorig:LeftUpLeg"
    else:
        pivot = genou; axe = ax_g; dirl = (cheville - genou) / np.linalg.norm(cheville - genou)
        jb = "mixamorig:LeftLeg"
    s = (rest - pivot) @ dirl                                  # position le long du membre
    f = smooth((s + b) / (2 * b))                              # 0 proximal, 1 distal, bande de 2b
    # rotation par sommet : Rot(axe, f·θ) appliquée à (v − pivot)
    rv = Rot.from_rotvec(axe[None, :] * (f * np.radians(th))[:, None]).as_matrix()   # (N,3,3)
    v_rel = rest - pivot
    P_rot = pivot + np.einsum("nij,nj->ni", rv, v_rel)
    # DQS de référence pour la pondération de chaîne
    R = np.tile(np.eye(3), (B, 1, 1))
    R[ix[jb]] = Rot.from_rotvec(axe * np.radians(th)).as_matrix()
    G, dd = skin_transforms(parent, h, R)
    P_dqs = dqs(rest, W, G, dd)
    chaine = W[:, [ix[c] for c in CHAINE[articulation]]].sum(axis=1)
    chaine = np.clip(chaine, 0.0, 1.0)
    P = chaine[:, None] * P_rot + (1 - chaine[:, None]) * P_dqs
    # rotation locale par face pour la métrique de plis : rotation répartie au centroïde de la face
    f_face = f[faces].mean(axis=1)
    Rf = Rot.from_rotvec(axe[None, :] * (f_face * np.radians(th))[:, None]).as_matrix()
    return P, Rf, pivot


def mesure(articulation, th):
    P, Rf, pivot = pose(articulation, th)
    band = np.linalg.norm((rest[aretes[:, 0]] + rest[aretes[:, 1]]) / 2 - pivot, axis=1) < 0.10
    L0 = np.linalg.norm(rest[aretes[:, 0]] - rest[aretes[:, 1]], axis=1)
    L1 = np.linalg.norm(P[aretes[:, 0]] - P[aretes[:, 1]], axis=1)
    r = L1 / np.maximum(L0, 1e-9)
    plis = plis_locaux(rest, P, faces, Rf)
    return dict(articulation=articulation, th=th,
                etirement_hors_p99=round(float(np.percentile(r[~band], 99)), 4),
                etirement_dans_p99=round(float(np.percentile(r[band], 99)), 4),
                plis_total=plis)


if __name__ == "__main__":
    P0, _, _ = pose("hanche", 0)
    print("TEMOIN identité : écart max =", float(np.abs(P0 - rest).max()), flush=True)
    sorties = []
    for art, angles in (("hanche", (30, 60, 90, 105, 120)), ("genou", (30, 60, 90, 120, 135))):
        for th in angles:
            r = mesure(art, th); sorties.append(r); print(art, r, flush=True)
    out = Path(__file__).resolve().parents[2] / "docs" / "rapports" / "phase4_rotation_repartie.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(sorties, indent=2, ensure_ascii=False))
    print("ECRIT", out, flush=True)
