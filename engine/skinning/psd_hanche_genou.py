"""Correctif de pose (PSD, Lewis et al. 2000) par articulation, sur la base DQS (hanche et genou).

Méthode (sources : PSD officielle Lewis et al. 2000 ; skinning.org « example-based » ; PSD pondérée par les poids,
Kurihara & Miyata 2004, cité par skinning.org) :
  1. Exemples : pour des angles d'entraînement θ_k, la pose DQS P_k est corrigée par une cible ARAP géométrique
     T_k (correctif_arap, partant de DQS au lieu de LBS). δ_k = T_k − P_k.
  2. Repère local : δ_k est exprimé dans le repère de l'os articulé (rotation G_j(θ_k)), pour que la correction
     suive la rotation (PSD : « interpolate the desired deviation … expressed in the local frame »).
  3. Interpolation : RBF gaussienne 1D en θ, poids résolus par Φ w = δ (exacte aux exemples).
  4. Pondération par les poids de peau de l'os articulé (PSD pondérée) : un sommet non influencé par l'os ne bouge pas.
  5. Validation : angles d'entraînement (0,30,60,90,120) et angles TEST jamais vus (45,75,105). Le témoin identité
     (θ=0) doit donner correction nulle.

Limite connue : la cible ARAP est géométrique (préserve les longueurs d'arêtes), pas anatomique. Les plis de la
face fléchisseur et la forme exacte du pli ne sont pas encore fixés par une cible anatomique (phase 4 à compléter).
"""
import sys, json, numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dqs import dqs, skin_transforms
from mesures_pose import plis_locaux, etirement_max
from correctif_arap import _rotations
from scipy.spatial.transform import Rotation as Rot
import scipy.sparse as sp
import scipy.sparse.linalg as spl

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
B = len(os_); N = len(rest)
Y = np.array([0.0, 1.0, 0.0])
hanche = h[ix["mixamorig:LeftUpLeg"]]; genou = h[ix["mixamorig:LeftLeg"]]; cheville = h[ix["mixamorig:LeftFoot"]]
ax_h = np.cross((genou - hanche) / np.linalg.norm(genou - hanche), Y); ax_h /= np.linalg.norm(ax_h)
ax_g = -np.cross((cheville - genou) / np.linalg.norm(cheville - genou), Y); ax_g /= np.linalg.norm(ax_g)
Wf = W[faces].sum(axis=1)
dom = np.argmax(Wf, axis=1)
ij = np.vstack([aretes, aretes[:, ::-1]])


def pose_dqs(articulation, th):
    R = np.tile(np.eye(3), (B, 1, 1))
    if articulation == "hanche":
        R[ix["mixamorig:LeftUpLeg"]] = Rot.from_rotvec(ax_h * np.radians(th)).as_matrix(); pivot = hanche; jb = "mixamorig:LeftUpLeg"
    else:
        R[ix["mixamorig:LeftLeg"]] = Rot.from_rotvec(ax_g * np.radians(th)).as_matrix(); pivot = genou; jb = "mixamorig:LeftLeg"
    G, dd = skin_transforms(parent, h, R)
    P = dqs(rest, W, G, dd)
    Gj = G[ix[jb]]
    return P, G, Gj, pivot, jb


def arap_depuis(P0, ancre, Rf=None, alpha=0.5, iters=12):
    """ARAP partant de P0 (DQS), sommets ancre fixés à P0. Même logique que correctif_arap.arap_cible.
    Rf (F,3,3) : rotation locale par face de la pose DQS ; faces repliées -> rotation ramenée vers l'identité
    (limitation de correctif_arap, erreur 58), sans quoi la cible crée des plis (diagnostic phase 4)."""
    from mesures_pose import normales_faces
    free = ~ancre
    idx = -np.ones(N, dtype=int); idx[free] = np.arange(free.sum())
    wij = np.ones(len(ij))
    deg = np.bincount(ij[:, 0], weights=wij, minlength=N)
    mask = free[ij[:, 0]] & free[ij[:, 1]]
    rows = idx[ij[mask, 0]]; cols = idx[ij[mask, 1]]
    L = (sp.diags(deg[free]) - sp.coo_matrix((wij[mask], (rows, cols)), shape=(free.sum(),) * 2).tocsr()).tocsc()
    solveur = spl.factorized(L)
    p = P0.copy()
    for _ in range(iters):
        R = _rotations(rest, p, ij, N, wij)
        if Rf is not None:
            Nr_loc = np.einsum("fij,fj->fi", Rf, normales_faces(rest, faces))
            repliee = np.einsum("fi,fi->f", Nr_loc, normales_faces(p, faces)) < 0
            if repliee.any():
                touches = np.unique(faces[repliee].ravel())
                melange = alpha * R[touches] + (1 - alpha) * np.eye(3)
                U2, _, Vt2 = np.linalg.svd(melange)
                R[touches] = Vt2.transpose(0, 2, 1) @ U2.transpose(0, 2, 1)
        dx = rest[ij[:, 0]] - rest[ij[:, 1]]
        Rm = 0.5 * (R[ij[:, 0]] + R[ij[:, 1]])
        contrib = wij[:, None] * np.einsum("eij,ej->ei", Rm, dx)
        b = np.zeros((N, 3)); np.add.at(b, ij[:, 0], contrib)
        fixed_nb = ~free[ij[:, 1]]
        fb = np.zeros((N, 3)); np.add.at(fb, ij[fixed_nb, 0], wij[fixed_nb, None] * P0[ij[fixed_nb, 1]])
        rhs = b[free] + fb[free]
        p_new = np.zeros((N, 3))
        for c in range(3):
            p_new[free, c] = solveur(rhs[:, c])
        p_new[ancre] = P0[ancre]
        p = p_new
    return p


def ancre_pour(articulation):
    """Ancres : sommets peu influencés par l'os articulé et ses enfants (restent à DQS)."""
    jb = ["mixamorig:LeftUpLeg", "mixamorig:LeftLeg", "mixamorig:LeftFoot"]
    poids_chaine = W[:, [ix[b] for b in jb]].sum(axis=1)
    return poids_chaine < 0.05


def construit(articulation, exemples):
    """Apprend la correction (RBF 1D en θ) sur les angles d'entraînement."""
    ancre = ancre_pour(articulation)
    termes = []
    for th in exemples:
        P, G, Gj, pivot, jb = pose_dqs(articulation, th)
        T = arap_depuis(P, ancre, Rf=None)  # Rf désactivé : aggrave les plis (diagnostic phase 4)
        delta_monde = T - P
        delta_local = np.einsum("ji,nj->ni", Gj, delta_monde)   # Gj^T · δ (repère local de l'os)
        termes.append(delta_local)
    D = np.stack(termes)                                 # (K, N, 3)
    sigma = np.radians(25.0)
    th_k = np.radians(np.array(exemples, dtype=float))
    Phi = np.exp(-((th_k[:, None] - th_k[None, :]) ** 2) / (2 * sigma ** 2)) + 1e-9 * np.eye(len(th_k))
    Wrbf = np.linalg.solve(Phi, D.reshape(len(th_k), -1)).reshape(len(th_k), N, 3)
    return dict(articulation=articulation, th_k=th_k, sigma=sigma, Wrbf=Wrbf, jb=jb, poids=(~ancre_pour(articulation)).astype(float))


def corrige(modele, th):
    """Pose corrigée : DQS + correction RBF exprimée dans le repère local, pondérée par les poids de l'os articulé."""
    P, G, Gj, pivot, jb = pose_dqs(modele["articulation"], th)
    phi = np.exp(-((np.radians(th) - modele["th_k"]) ** 2) / (2 * modele["sigma"] ** 2))
    delta_local = np.tensordot(phi, modele["Wrbf"], axes=1)   # (N,3)
    delta_monde = delta_local @ Gj.T
    return P + modele["poids"][:, None] * delta_monde


def mesure(P, articulation, th):
    _, G, _, pivot, _ = pose_dqs(articulation, th)
    band = np.linalg.norm((rest[aretes[:, 0]] + rest[aretes[:, 1]]) / 2 - pivot, axis=1) < 0.10
    L0 = np.linalg.norm(rest[aretes[:, 0]] - rest[aretes[:, 1]], axis=1)
    L1 = np.linalg.norm(P[aretes[:, 0]] - P[aretes[:, 1]], axis=1)
    r = L1 / np.maximum(L0, 1e-9)
    plis = plis_locaux(rest, P, faces, G[dom])
    return dict(articulation=articulation, th=th,
                etirement_hors_p99=round(float(np.percentile(r[~band], 99)), 4),
                etirement_dans_p99=round(float(np.percentile(r[band], 99)), 4),
                plis_total=plis)


if __name__ == "__main__":
    ENTRAINEMENT = (0, 30, 60, 90, 120)
    TEST = (45, 75, 105)
    sorties = []
    for art in ("hanche", "genou"):
        modele = construit(art, ENTRAINEMENT)
        # témoin identité : correction à 0 doit être nulle
        P0c = corrige(modele, 0)
        P0d, _, _, _, _ = pose_dqs(art, 0)
        print(art, "TEMOIN correction à 0 : écart max =", float(np.abs(P0c - P0d).max()), flush=True)
        # témoin d'exactitude : aux exemples, la correction reproduit l'ARAP
        for th in ENTRAINEMENT:
            r = mesure(corrige(modele, th), art, th)
            r["jeu"] = "entrainement"; sorties.append(r); print(art, r, flush=True)
        for th in TEST:
            r = mesure(corrige(modele, th), art, th)
            r["jeu"] = "test"; sorties.append(r); print(art, r, flush=True)
    out = Path(__file__).resolve().parents[2] / "docs" / "rapports" / "phase4_psd_hanche_genou.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(sorties, indent=2, ensure_ascii=False))
    print("ECRIT", out, flush=True)
