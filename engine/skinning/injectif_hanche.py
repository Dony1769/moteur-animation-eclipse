"""Déformation de la jonction de hanche par ARAP local/global à pas acceptés sans inversion (Schüller et al. 2013).

Sources lues en détail :
- Schüller, Kavan, Panozzo, Sorkine-Hornung, « Locally Injective Mappings » (SGP 2013), PDF du laboratoire de Kavan
  (https://users.cs.utah.edu/~ladislav/schuller13local/schuller13local.pdf) : barrière qui devient infinie quand un
  élément s'inverse ; pas de descente accepté seulement s'il réduit l'énergie (recul de moitié du pas : σ ← σ/2) ;
  sous-pas : l'angle est augmenté par petits incréments, chaque état restant valide.
- Sorkine & Alexa (2007), ARAP local/global : déjà dans correctif_arap.py.

Méthode :
  1. Marche en angle de 0 à θ par pas de 5°. Chaque état est sans inversion.
  2. Bords imposés (règle de phase 4 : rigide hors jonction, déformable dans la bande) :
     - proximal (hors bande, côté bassin) : fixé au repos ;
     - distal (côté cuisse/genou, hors bande) : mouvement rigide Rot(axe, θ) autour du pivot ;
     - bande de jonction (|s| < B) : libre, déformée par ARAP.
  3. Par sous-pas : étape locale (rotations polaires), étape globale (solve du Laplacien), puis pas σ accepté
     seulement s'il n'inverse aucune face (test de signe sur la normale locale).

Pas de correctif d'artiste : la cible est géométrique (ARAP), sous contrainte d'injectivité.
Usage : python3 injectif_hanche.py <dossier_donnees>
"""
import sys, json, numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_chaine_hanche as t
from correctif_arap import _rotations
from mesures_pose import plis_locaux, normales_faces
from scipy.spatial.transform import Rotation as Rot
import scipy.sparse as sp
import scipy.sparse.linalg as spl

N = len(t.rest)
ij = np.vstack([t.aretes, t.aretes[:, ::-1]])
wij = np.ones(len(ij))

# repère du membre (hanche)
pivot = t.h[t.ix["mixamorig:LeftUpLeg"]]
dirl = t.h[t.ix["mixamorig:LeftLeg"]] - pivot
dirl = dirl / np.linalg.norm(dirl)
axe = np.cross(dirl, t.Y); axe /= np.linalg.norm(axe)
B = 0.15
s = (t.rest - pivot) @ dirl                       # position le long du membre (0 = hanche)
bande = np.abs(s) < B
proximal = (~bande) & (s < 0)
distal = (~bande) & (s >= 0)
libre = bande

# sommets fixés : repos (proximal) et mouvement rigide (distal)
Lmat = None


A_DISTAL = 1.0   # part de la rotation prise par le segment distal (1.0 = bord proximal fixe, sans répartition)


def cible_rigide(theta):
    """Cible du segment distal : rotation a·θ (a = A_DISTAL)."""
    R = Rot.from_rotvec(axe * np.radians(theta * A_DISTAL)).as_matrix()
    return pivot + (t.rest - pivot) @ R.T


def cible_proximale(theta):
    """Cible du segment proximal : rotation −(1−a)·θ (répartition type épaule, rapport phase 4)."""
    R = Rot.from_rotvec(axe * np.radians(-theta * (1.0 - A_DISTAL))).as_matrix()
    return pivot + (t.rest - pivot) @ R.T


def factoriser():
    idx = -np.ones(N, dtype=int); idx[libre] = np.arange(libre.sum())
    deg = np.bincount(ij[:, 0], weights=wij, minlength=N)
    mask = libre[ij[:, 0]] & libre[ij[:, 1]]
    rows = idx[ij[mask, 0]]; cols = idx[ij[mask, 1]]
    L = (sp.diags(deg[libre]) - sp.coo_matrix((wij[mask], (rows, cols)), shape=(libre.sum(),) * 2).tocsr()).tocsc()
    return spl.factorized(L)


def etape_globale(p, R, fixe, solveur):
    dx = t.rest[ij[:, 0]] - t.rest[ij[:, 1]]
    Rm = 0.5 * (R[ij[:, 0]] + R[ij[:, 1]])
    contrib = wij[:, None] * np.einsum("eij,ej->ei", Rm, dx)
    b = np.zeros((N, 3)); np.add.at(b, ij[:, 0], contrib)
    fixed_nb = ~libre[ij[:, 1]]
    fb = np.zeros((N, 3)); np.add.at(fb, ij[fixed_nb, 0], wij[fixed_nb, None] * fixe[ij[fixed_nb, 1]])
    rhs = b[libre] + fb[libre]
    p_new = fixe.copy()
    for c in range(3):
        p_new[libre, c] = solveur(rhs[:, c])
    return p_new


def inversions(p):
    """Nombre de faces inversées par rapport au repos (signe de la normale)."""
    n0 = normales_faces(t.rest, t.faces); n1 = normales_faces(p, t.faces)
    return int(np.sum(np.einsum("fi,fi->f", n0, n1) < 0))


def pose(theta_total, pas=5.0, iters=10):
    solveur = factoriser()
    p = t.rest.copy()
    th = 0.0
    while th < theta_total - 1e-9:
        th = min(th + pas, theta_total)
        fixe = p.copy()
        fixe[proximal] = cible_proximale(th)[proximal]
        fixe[distal] = cible_rigide(th)[distal]
        for _ in range(iters):
            R = _rotations(t.rest, p, ij, N, wij)
            p_new = etape_globale(p, R, fixe, solveur)
            sigma = 1.0
            ok = False
            while sigma > 1.0 / 64:
                p_try = p + sigma * (p_new - p)
                if inversions(p_try) == 0:
                    p = p_try; ok = True; break
                sigma /= 2.0
            if not ok:
                break
    return p


if __name__ == "__main__":
    sorties = []
    A_DISTAL = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
    for th in (30, 60, 90, 105, 120):
        P = pose(th)
        n_inv = inversions(P)
        # rotation locale par face : moyenne des rotations polaires des sommets, projetée sur SO(3) (erreur 108)
        Rv = _rotations(t.rest, P, ij, N, wij)
        Rm_face = Rv[t.faces].mean(axis=1)
        U, _, Vt = np.linalg.svd(Rm_face)
        Rf = U @ Vt
        det = np.linalg.det(Rf); U[det < 0, :, 2] *= -1; Rf = U @ Vt
        m = plis_locaux(t.rest, P, t.faces, Rf)
        L0 = np.linalg.norm(t.rest[t.aretes[:, 0]] - t.rest[t.aretes[:, 1]], axis=1)
        L1 = np.linalg.norm(P[t.aretes[:, 0]] - P[t.aretes[:, 1]], axis=1)
        r = L1 / np.maximum(L0, 1e-9)
        mid = (t.rest[t.aretes[:, 0]] + t.rest[t.aretes[:, 1]]) / 2
        band = np.linalg.norm(mid - pivot, axis=1) < 0.10
        rb = r[band]
        ligne = dict(th=th, inversions=n_inv, n_aretes_bande=int(band.sum()),
                     mediane=round(float(np.median(rb)), 4), p95=round(float(np.percentile(rb, 95)), 4),
                     p99=round(float(np.percentile(rb, 99)), 4), fraction_sup_1_15=round(float((rb > 1.15).mean()), 4))
        sorties.append(ligne); print(ligne, flush=True)
    out = Path(__file__).resolve().parents[2] / "docs" / "rapports" / "phase4_injectif_hanche.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(sorties, indent=2, ensure_ascii=False))
    print("ECRIT", out, flush=True)
